# Plan de Refactoring — GDPR Pseudonymizer

**Date** : 2026-02-10
**Version analysee** : v0.1.0-alpha (Epic 3 complete, Stories 4.1-4.6)
**Codebase** : 8 500+ lignes, 54 fichiers Python, 814 tests (86%+ coverage)

---

## Contexte

Le projet est architecturalement solide : bonne separation en modules (NLP, Pseudonym, Data, Validation, CLI, Core), interfaces abstraites, tests, chiffrement AES-256-SIV. Cependant, la croissance organique au fil des stories a introduit de la duplication, une methode monolithique, et quelques violations architecturales qu'il faut corriger **avant d'ajouter de nouvelles fonctionnalites**.

---

## R1 — Violation de couche : core importe CLI

**Priorite : CRITIQUE**
**Effort : Faible**
**Fichiers concernes :**
- `gdpr_pseudonymizer/core/document_processor.py:314`
- `gdpr_pseudonymizer/core/naive_processor.py:18`

### Probleme

Le module `core` (couche metier) importe directement la couche de presentation :

```python
# document_processor.py:314
from gdpr_pseudonymizer.cli.formatters import console
console.print(f"[dim]Auto-accepted {auto_accept_count} known entities...")
```

Cela couple le processeur de documents au terminal Rich. Si le processeur est utilise via une API REST, une lib Python, ou des tests headless, cet import provoquera des effets de bord ou des erreurs.

### Solution

Injecter un callback de notification dans `DocumentProcessor.__init__()` :

```python
# Type du callback
from typing import Callable, Protocol

class ProcessingNotifier(Protocol):
    def notify(self, message: str, level: str = "info") -> None: ...

# Dans DocumentProcessor.__init__:
def __init__(self, ..., notifier: ProcessingNotifier | None = None):
    self._notifier = notifier or NullNotifier()

# Usage dans process_document:
self._notifier.notify(
    f"Auto-accepted {auto_accept_count} known entities ({unique_known} unique)",
    level="info"
)
```

L'implementation CLI fournit un `RichNotifier` qui appelle `console.print()`. Les tests utilisent `NullNotifier` (no-op).

### Tests a mettre a jour

- Tous les tests de `document_processor.py` qui mockent ou dependent de la sortie console
- Verifier que `naive_processor.py:18` (`from gdpr_pseudonymizer.cli.naive_data import NAIVE_ENTITIES`) est egalement decouple, ou deplacer `NAIVE_ENTITIES` vers un module `data/` ou `core/`

---

## R2 — Centraliser les patterns et fonctions utilitaires francais

**Priorite : HAUTE**
**Effort : Faible**
**Fichiers concernes :**
- `gdpr_pseudonymizer/nlp/hybrid_detector.py:25`
- `gdpr_pseudonymizer/pseudonym/assignment_engine.py:25, 32`
- `gdpr_pseudonymizer/nlp/entity_grouping.py:19, 22`
- `gdpr_pseudonymizer/validation/workflow.py:15` (import)

### Probleme

#### 2a. `FRENCH_TITLE_PATTERN` defini 3 fois (copier-coller exact)

```
nlp/hybrid_detector.py:25       → FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|..."
pseudonym/assignment_engine.py:25 → FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|..."  (identique)
nlp/entity_grouping.py:19       → FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|..."  (identique)
```

Preuve du risque : la Story 3.9 a du modifier ce pattern dans 3 fichiers pour ajouter `Maitre|Me\.?` (cf. `docs/stories/3.9.ner-title-handling-improvements.story.md:121-122`).

#### 2b. Pattern de preposition defini 2 fois (variantes divergentes)

```
assignment_engine.py:32  → r"^[\s]*(?:a|au|aux|en|de|du|des|d'|l'|la|le|les)\s+"
entity_grouping.py:22    → r"^(?:a|de|du|en|au|aux|d'|l')\s*"
```

Les deux patterns ne matchent **pas les memes prepositions** (`des`, `la`, `le`, `les` manquent dans le 2e). C'est un bug latent.

#### 2c. Logique de stripping de titres dupliquee 3 fois

La meme boucle `while True: stripped = re.sub(PATTERN, ...); if stripped == text: break` existe dans :

- `hybrid_detector.py:_normalize_entity_text()` (lignes 351-360)
- `assignment_engine.py:strip_titles()` (lignes 234-242)
- `entity_grouping.py:_normalize_person()` (lignes 37-44)

### Solution

Creer un module `gdpr_pseudonymizer/utils/french_patterns.py` :

```python
"""Patterns et fonctions utilitaires pour le traitement du francais."""

import re

FRENCH_TITLE_PATTERN = r"\b(?:Docteur|Professeur|Madame|Monsieur|Mademoiselle|Maitre|Dr\.?|Pr\.?|Prof\.?|M\.?|Mme\.?|Mlle\.?|Me\.?)(?!\w)\s*"

FRENCH_PREPOSITION_PATTERN = r"^[\s]*(?:a|au|aux|en|de|du|des|d'|l'|la|le|les)\s+"


def strip_french_titles(text: str) -> str:
    """Supprime iterativement les titres honorifiques francais."""
    while True:
        stripped = re.sub(FRENCH_TITLE_PATTERN, "", text, flags=re.IGNORECASE).strip()
        if stripped == text:
            break
        text = stripped
    return text


def strip_french_prepositions(text: str) -> str:
    """Supprime les prepositions francaises en debut de texte."""
    return re.sub(FRENCH_PREPOSITION_PATTERN, "", text, flags=re.IGNORECASE).strip()
```

Puis remplacer les 3 definitions par des imports dans `hybrid_detector.py`, `assignment_engine.py`, `entity_grouping.py`, et `validation/workflow.py`.

### Tests a mettre a jour

- Ajouter des tests unitaires pour `french_patterns.py`
- Les tests existants des 4 modules ne changent pas (meme comportement)
- Verifier que le pattern de preposition unifie ne cause pas de regressions dans les tests d'accuracy

---

## R3 — Decouper `process_document()` (God Method)

**Priorite : HAUTE**
**Effort : Moyen**
**Fichier concerne :** `gdpr_pseudonymizer/core/document_processor.py:127-720`

### Probleme

La methode `process_document()` fait ~550 lignes et gere 10+ responsabilites :

1. Lecture fichier (L171-172)
2. Detection NLP (L176-177)
3. Filtrage par type (L180-190)
4. Ouverture DB + init repositories (L202-218)
5. Construction du `pseudonym_assigner` closure (L226-275)
6. Separation entites connues/inconnues (L292-311)
7. Affichage auto-accept + workflow validation (L317-356)
8. Reset etat pseudonym manager (L362-374)
9. Boucle de traitement par entite avec cache, component matching, stripping (L388-587)
10. Deduplication des remplacements (L608-627)
11. Application des remplacements textuels (L630-638)
12. Ecriture fichier + audit log (L641-676)
13. Gestion d'erreurs (L678-720)

Les commentaires `# CRITICAL FIX` (lignes 362, 395, 436, 509) temoignent d'une accumulation de patches.

### Solution

Extraire en sous-methodes privees. Voici le decoupage recommande :

```python
def process_document(self, input_path, output_path, ...) -> ProcessingResult:
    """Methode principale simplifiee."""
    start_time = time.time()
    try:
        document_text = read_file(input_path)
        detected_entities = self._detect_and_filter_entities(document_text, entity_type_filter)

        with open_database(self.db_path, self.passphrase) as db_session:
            context = self._init_processing_context(db_session)
            validated_entities = self._run_validation(
                detected_entities, document_text, input_path, context, skip_validation
            )
            self._reset_pseudonym_state(context)
            replacements, entities_new, entities_reused = self._resolve_pseudonyms(
                validated_entities, context
            )
            pseudonymized_text = self._apply_replacements(document_text, replacements)
            write_file(output_path, pseudonymized_text)
            self._log_audit(context, input_path, validated_entities, start_time)

        return ProcessingResult(success=True, ...)

    except ...:
        return self._handle_error(...)
```

Sous-methodes a extraire :

| Methode | Lignes actuelles | Responsabilite |
|---------|-----------------|----------------|
| `_detect_and_filter_entities()` | 171-196 | Detection NLP + filtre de types |
| `_init_processing_context()` | 204-218 | Init repositories + engine + manager |
| `_build_pseudonym_assigner()` | 226-275 | Construction de la closure de preview |
| `_run_validation()` | 278-356 | Separation known/unknown + workflow |
| `_reset_pseudonym_state()` | 362-374 | Reset manager apres validation |
| `_resolve_pseudonyms()` | 376-587 | Boucle entites, cache, component matching, replacements |
| `_apply_replacements()` | 604-638 | Deduplication + application texte |
| `_normalize_entity_text()` | (repete 3x) | Strip titres + prepositions |
| `_build_replacement_with_prefix()` | 556-587 | Extraction prefix titre/preposition |

La methode `_resolve_pseudonyms()` est elle-meme trop longue (~200 lignes). Envisager d'en extraire `_resolve_single_entity()` et `_check_component_match()`.

### Points d'attention

- La logique de stripping titres/prepositions est executee a **3 endroits differents** dans cette methode (lignes 240-248, 296-304, 398-406). Extraire une methode `_normalize_entity_text(entity: DetectedEntity) -> str` et l'appeler une seule fois.
- La closure `pseudonym_assigner` (lignes 226-275) capture `preview_cache`, `compositional_engine`, et `mapping_repo` par cloture. Apres extraction, passer ces dependances explicitement ou les encapsuler dans un objet `ProcessingContext`.

### Tests a mettre a jour

- Les tests unitaires de `DocumentProcessor` testent `process_document()` comme boite noire via ses resultats. Le refactoring interne ne devrait **pas** casser ces tests tant que la signature et le comportement de `process_document()` ne changent pas.
- Ajouter des tests unitaires pour chaque sous-methode extraite.

---

## R4 — Corriger les violations d'encapsulation

**Priorite : MOYENNE**
**Effort : Faible**
**Fichiers concernes :**
- `gdpr_pseudonymizer/core/document_processor.py:366-370`
- `gdpr_pseudonymizer/pseudonym/assignment_engine.py:412-418`

### Probleme

#### 4a. `document_processor.py` accede aux attributs prives de `LibraryBasedPseudonymManager`

```python
# document_processor.py:366-367
pseudonym_manager._used_pseudonyms.clear()
pseudonym_manager._component_mappings.clear()
```

#### 4b. `assignment_engine.py` accede aux attributs prives via `hasattr`

```python
# assignment_engine.py:412-413
if hasattr(self.pseudonym_manager, "_component_mappings"):
    component_mappings = self.pseudonym_manager._component_mappings
```

Le `CompositionalPseudonymEngine` est couple a l'implementation interne de `LibraryBasedPseudonymManager` alors qu'il est type comme `PseudonymManager` (interface abstraite).

### Solution

Ajouter des methodes publiques sur `PseudonymManager` (interface) et `LibraryBasedPseudonymManager` (implementation) :

```python
# Sur PseudonymManager (ABC) — ajouter au contrat d'interface :
@abstractmethod
def reset_preview_state(self) -> None:
    """Reinitialise l'etat de preview (apres validation)."""
    pass

@abstractmethod
def get_component_mapping(self, component: str, component_type: str) -> str | None:
    """Retourne le pseudonyme mappe pour un composant donne, ou None."""
    pass

# Implementation dans LibraryBasedPseudonymManager :
def reset_preview_state(self) -> None:
    self._used_pseudonyms.clear()
    self._component_mappings.clear()

def get_component_mapping(self, component: str, component_type: str) -> str | None:
    return self._component_mappings.get((component, component_type))
```

Puis dans `document_processor.py:366` :
```python
pseudonym_manager.reset_preview_state()
```

Et dans `assignment_engine.py:412` :
```python
result = self.pseudonym_manager.get_component_mapping(component, component_type)
if result is not None:
    return result
```

### Tests a mettre a jour

- Ajouter des tests pour `reset_preview_state()` et `get_component_mapping()`
- Mettre a jour `SimplePseudonymManager` (si conserve, cf. R7) pour implementer les nouvelles methodes abstraites
- Verifier que les tests existants qui mockent `PseudonymManager` continuent de passer

---

## R5 — Factoriser Union-Find dans `entity_grouping.py`

**Priorite : MOYENNE**
**Effort : Faible**
**Fichier concerne :** `gdpr_pseudonymizer/nlp/entity_grouping.py`

### Probleme

Les fonctions `find()` et `union()` sont definies localement dans **3 fonctions** :

- `_cluster_person_variants()` (lignes 267-276)
- `_cluster_location_variants()` (lignes 315-324)
- `_cluster_org_variants()` (lignes 362-371)

De plus, `_cluster_location_variants` et `_cluster_org_variants` sont quasi-identiques (seule la fonction de normalisation differe).

### Solution

```python
class UnionFind:
    """Structure Union-Find avec compression de chemin."""

    def __init__(self, keys: list) -> None:
        self._parent = {k: k for k in keys}

    def find(self, k):
        while self._parent[k] != k:
            self._parent[k] = self._parent[self._parent[k]]
            k = self._parent[k]
        return k

    def union(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def clusters(self) -> list[list]:
        groups = defaultdict(list)
        for k in self._parent:
            groups[self.find(k)].append(k)
        return list(groups.values())


def _cluster_by_normalization(
    keys: list[tuple[str, str]],
    normalize_fn: Callable[[str], str],
    variant_fn: Callable[[str, str], bool] | None = None,
) -> list[list[tuple[str, str]]]:
    """Clustering generique par normalisation + comparaison optionnelle."""
    if len(keys) <= 1:
        return [[k] for k in keys]

    normalized = {key: normalize_fn(key[0]) for key in keys}
    uf = UnionFind(keys)

    compare = variant_fn or (lambda a, b: a == b)
    for i, ka in enumerate(keys):
        for kb in keys[i+1:]:
            if compare(normalized[ka], normalized[kb]):
                uf.union(ka, kb)

    return uf.clusters()
```

`_cluster_location_variants` et `_cluster_org_variants` deviennent des one-liners. `_cluster_person_variants` conserve sa logique speciale pour les noms ambigus mais utilise `UnionFind` au lieu de redefinir `find/union`.

### Tests a mettre a jour

- Les tests unitaires de `entity_grouping.py` existants doivent passer sans modification (refactoring interne)
- Ajouter des tests unitaires pour `UnionFind` et `_cluster_by_normalization`

---

## R6 — Factoriser le code duplique entre process et batch (CLI)

**Priorite : MOYENNE**
**Effort : Faible**
**Fichiers concernes :**
- `gdpr_pseudonymizer/cli/commands/process.py`
- `gdpr_pseudonymizer/cli/commands/batch.py`

### Probleme

Trois blocs de logique sont dupliques entre ces deux commandes :

#### 6a. Parsing du filtre `entity_types`
- `process.py:221-239`
- `batch.py:418-436`

Meme code : split par virgule, validation contre `{"PERSON", "LOCATION", "ORG"}`, warning pour types invalides.

#### 6b. Initialisation de la base de donnees
- `process.py:168-186`
- `batch.py:468-484`

Meme pattern : verifier si le fichier DB existe, sinon `init_database()` avec spinner Rich.

#### 6c. Validation du theme
- `process.py:155-163`
- `batch.py:451-458`

Meme validation contre `["neutral", "star_wars", "lotr"]`.

### Solution

Extraire dans des fonctions utilitaires CLI :

```python
# gdpr_pseudonymizer/cli/validators.py (existant, l'enrichir)

def parse_entity_type_filter(entity_types: str | None, console: Console) -> set[str] | None:
    """Parse et valide le filtre de types d'entites depuis un argument CLI."""
    ...

def validate_theme(theme: str, console: Console) -> None:
    """Valide le theme et exit(1) si invalide."""
    ...

def ensure_database(db_path: str, passphrase: str, console: Console) -> None:
    """Initialise la BDD si elle n'existe pas, avec spinner de progression."""
    ...
```

### Tests a mettre a jour

- Ajouter des tests unitaires pour les fonctions extraites
- Les tests d'integration CLI existants ne changent pas

---

## R7 — Supprimer `SimplePseudonymManager` (code mort)

**Priorite : BASSE**
**Effort : Trivial**
**Fichiers concernes :**
- `gdpr_pseudonymizer/pseudonym/assignment_engine.py:120-179`
- `tests/integration/test_module_loading.py:86, 91, 232-237`

### Probleme

`SimplePseudonymManager` est un stub qui retourne `"PLACEHOLDER"`. Les commentaires disent "Full implementation in Epic 2" mais `LibraryBasedPseudonymManager` est l'implementation de production depuis Epic 2.

Seuls 2 tests le referencent : un test d'import et un test d'instanciation.

### Solution

- Supprimer la classe `SimplePseudonymManager`
- Mettre a jour les tests dans `test_module_loading.py` pour ne plus la referencer
- Mettre a jour `docs/module-dependencies.md:297` si applicable

### Risque

Aucun code de production ne l'utilise. Risque zero.

---

## R8 — Centraliser les exceptions

**Priorite : BASSE**
**Effort : Trivial**
**Fichiers concernes :**
- `gdpr_pseudonymizer/exceptions.py` (centralise)
- `gdpr_pseudonymizer/data/database.py:287` — `CorruptedDatabaseError`
- `gdpr_pseudonymizer/data/repositories/mapping_repository.py:407-416` — `DuplicateEntityError`, `DatabaseError`
- `gdpr_pseudonymizer/cli/config.py:65` — `ConfigValidationError`

### Probleme

Quatre exceptions sont definies en dehors de `exceptions.py`, qui est sense etre le module centralise pour toutes les exceptions custom.

De plus, `CorruptedDatabaseError`, `DuplicateEntityError` et `DatabaseError` heritent directement de `Exception` au lieu de `PseudonymizerError`.

### Solution

Deplacer dans `exceptions.py` et les faire heriter de `PseudonymizerError` :

```python
# exceptions.py — ajouter :
class DatabaseError(PseudonymizerError):
    """Raised when database operation fails."""
    pass

class CorruptedDatabaseError(DatabaseError):
    """Raised when database metadata is missing or invalid."""
    pass

class DuplicateEntityError(DatabaseError):
    """Raised when attempting to save entity with duplicate full_name."""
    pass

class ConfigValidationError(PseudonymizerError):
    """Raised when config file validation fails."""
    pass
```

Dans les fichiers d'origine, remplacer par des re-exports ou des imports directs.

### Tests a mettre a jour

- Grep pour tous les `from ... import CorruptedDatabaseError` etc. et mettre a jour les imports
- Les `except` blocks existants continuent de fonctionner (heritage compatible)

---

## R9 — Harmoniser le logging

**Priorite : BASSE**
**Effort : Faible**
**Fichiers concernes :**
- `gdpr_pseudonymizer/pseudonym/assignment_engine.py:17`
- `gdpr_pseudonymizer/pseudonym/library_manager.py:17`
- `gdpr_pseudonymizer/nlp/spacy_detector.py:18`
- `gdpr_pseudonymizer/nlp/stanza_detector.py:18`

### Probleme

Le projet utilise `structlog` via `get_logger()` (defini dans `utils/logger.py`) dans la majorite des modules. Mais **4 modules** utilisent `logging.getLogger()` de la stdlib :

```python
# Ces 4 fichiers :
import logging
logger = logging.getLogger(__name__)

# Tous les autres fichiers :
from gdpr_pseudonymizer.utils.logger import get_logger
logger = get_logger(__name__)
```

Cela cree une incoherence dans le format des logs : les 4 modules produisent des logs en format texte classique tandis que le reste produit du structured logging.

### Solution

Remplacer dans les 4 fichiers :

```python
# Avant :
import logging
logger = logging.getLogger(__name__)

# Apres :
from gdpr_pseudonymizer.utils.logger import get_logger
logger = get_logger(__name__)
```

Verifier que les appels `logger.info("message: %s", var)` (style %-formatting) dans `library_manager.py` et `assignment_engine.py` sont convertis en style structlog `logger.info("event_name", key=var)`.

### Tests a mettre a jour

Aucun changement fonctionnel. Les tests qui capturent des logs pourraient necessiter un ajustement du format attendu.

---

## Resume et ordre d'execution recommande

| # | Refactoring | Priorite | Effort | Risque regression |
|---|------------|----------|--------|-------------------|
| R1 | Decouplage core/CLI (violation de couche) | CRITIQUE | Faible | Faible |
| R2 | Centralisation patterns/fonctions francais | HAUTE | Faible | Faible |
| R3 | Decoupage `process_document()` | HAUTE | Moyen | Moyen |
| R4 | Encapsulation `_used_pseudonyms` / `_component_mappings` | MOYENNE | Faible | Faible |
| R5 | Factorisation Union-Find | MOYENNE | Faible | Faible |
| R6 | Factorisation CLI process/batch | MOYENNE | Faible | Faible |
| R7 | Suppression `SimplePseudonymManager` | BASSE | Trivial | Nul |
| R8 | Centralisation exceptions | BASSE | Trivial | Faible |
| R9 | Harmonisation logging | BASSE | Faible | Faible |

### Ordre d'execution recommande

1. **R7** en premier (suppression code mort, zero risque, quick win)
2. **R2** ensuite (centralisation patterns, elimine de la duplication, peu risque)
3. **R1** (decouplage core/CLI, changement structurel mais localise)
4. **R4** (encapsulation, prerecquis pour R3)
5. **R3** (decoupage process_document, le plus gros chantier)
6. **R5, R6, R8, R9** dans n'importe quel ordre

### Points de vigilance

- Faire tourner la suite de tests complete apres chaque refactoring (`pytest` + `black` + `ruff` + `mypy`)
- Les refactorings R1-R4 doivent etre faits **avant** d'ajouter de nouvelles features pour eviter d'amplifier la dette
- R3 est le plus risque : bien tester les cas limites (entites avec titres + prepositions, component matching cross-document, deduplication d'overlaps)
- Le pattern de preposition divergent (R2b) est potentiellement un **bug en production** : verifier avec les tests d'accuracy si `des`, `la`, `le`, `les` sont effectivement des prepositions a stripper pour les entites LOCATION dans `entity_grouping.py`
