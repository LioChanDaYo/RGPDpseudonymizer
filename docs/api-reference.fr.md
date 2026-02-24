# Référence API

**GDPR Pseudonymizer** — Documentation des modules pour les développeurs

---

## Vue d'ensemble

Le package `gdpr_pseudonymizer` est organisé en sous-packages :

| Package | Rôle |
|---------|------|
| `core` | Orchestration du traitement de documents |
| `nlp` | Pipeline de reconnaissance d'entités nommées (NER) |
| `pseudonym` | Attribution des pseudonymes et gestion des bibliothèques |
| `data` | Base de données, modèles, chiffrement et dépôts |
| `validation` | Processus de validation interactive avec contrôle humain |
| `cli` | Interface en ligne de commande (basée sur Typer) |
| `utils` | Gestion des fichiers, configuration et journalisation |

---

## Module Core (`gdpr_pseudonymizer.core`)

### DocumentProcessor

Orchestre le traitement d'un document : détection des entités, validation, attribution des pseudonymes et production du fichier de sortie.

```python
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

processor = DocumentProcessor(
    db_path="mappings.db",
    passphrase="your-secure-passphrase",
    theme="neutral",        # neutral | star_wars | lotr
    model_name="spacy"
)

result = processor.process_document(
    input_path="input.txt",
    output_path="output.txt",
    skip_validation=False,    # Passer à True pour un usage programmatique (sans interface)
    entity_type_filter=None   # Facultatif : ensemble de types, ex. {"PERSON", "LOCATION"}
)
```

### ProcessingResult

Objet retourné par `DocumentProcessor.process_document()` :

| Attribut | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Indique si le traitement s'est terminé sans erreur |
| `input_file` | `str` | Chemin du fichier d'entrée |
| `output_file` | `str` | Chemin du fichier de sortie |
| `entities_detected` | `int` | Nombre total d'entités détectées |
| `entities_new` | `int` | Nouveaux pseudonymes attribués |
| `entities_reused` | `int` | Pseudonymes réutilisés (idempotence) |
| `processing_time_seconds` | `float` | Durée totale du traitement |
| `error_message` | `str | None` | Description de l'erreur en cas d'échec |

---

## Module NLP (`gdpr_pseudonymizer.nlp`)

### DetectedEntity

Objet représentant une entité nommée détectée :

| Attribut | Type | Description |
|----------|------|-------------|
| `text` | `str` | Texte d'origine de l'entité |
| `entity_type` | `str` | Classification : `PERSON`, `LOCATION`, `ORG` |
| `start_pos` | `int` | Position de début dans le texte (en caractères) |
| `end_pos` | `int` | Position de fin dans le texte (en caractères) |
| `confidence` | `float | None` | Score de confiance NER (0.0-1.0) |
| `gender` | `str | None` | Genre : `male`, `female`, `neutral`, `unknown` |
| `is_ambiguous` | `bool` | Indique si l'entité est signalée comme ambiguë |
| `source` | `str` | Source de la détection : `spacy`, `regex` ou `hybrid` |

### EntityDetector (classe abstraite)

Interface que tout détecteur NER doit implémenter :

```python
class EntityDetector(ABC):
    @abstractmethod
    def load_model(self, model_name: str) -> None: ...

    @abstractmethod
    def detect_entities(self, text: str) -> list[DetectedEntity]: ...

    @abstractmethod
    def get_model_info(self) -> dict[str, str]: ...

    @property
    @abstractmethod
    def supports_gender_classification(self) -> bool: ...
```

### HybridDetector

Détecteur par défaut, qui combine le NER spaCy avec la détection par expressions régulières. C'est le détecteur utilisé par `DocumentProcessor`.

```python
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

detector = HybridDetector()
detector.load_model("fr_core_news_lg")
entities = detector.detect_entities("Marie Dubois travaille a Paris.")
```

### SpaCyDetector

Détecteur NER utilisant uniquement spaCy :

```python
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector

detector = SpaCyDetector()
detector.load_model("fr_core_news_lg")
entities = detector.detect_entities(text)
```

### RegexMatcher

Détection d'entités par expressions régulières : titres français, noms composés, dictionnaires de noms, suffixes d'organisations :

```python
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher

matcher = RegexMatcher()
matcher.load_patterns()  # Charge depuis config/detection_patterns.yaml
entities = matcher.match_entities(text)
stats = matcher.get_pattern_stats()
```

### NameDictionary

Dictionnaire de noms français pour la détection par expressions régulières :

```python
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary

names = NameDictionary()
names.load()
names.is_first_name("Marie")  # True
names.is_last_name("Dubois")  # True
```

### EntityGrouping (module `entity_grouping`)

Regroupe les différentes formes d'une même entité en un seul élément à valider, ce qui réduit la charge de validation pour l'utilisateur. Par exemple, « Marie Dubois », « Pr. Dubois » et « Dubois » sont regroupés en un seul élément.

```python
from gdpr_pseudonymizer.nlp.entity_grouping import group_entity_variants

groups = group_entity_variants(detected_entities)
for canonical, occurrences, variant_texts in groups:
    print(f"{canonical.text} (formes rencontrées : {variant_texts})")
```

**Type de retour :** `list[tuple[DetectedEntity, list[DetectedEntity], set[str]]]`

Chaque tuple contient :

| Élément | Type | Description |
|---------|------|-------------|
| `canonical` | `DetectedEntity` | Entité représentative (forme textuelle la plus longue) |
| `occurrences` | `list[DetectedEntity]` | Toutes les occurrences de l'entité dans le groupe |
| `variant_texts` | `set[str]` | Formes textuelles distinctes au sein du groupe |

**Règles de regroupement par type d'entité :**

| Type | Règle |
|------|-------|
| `PERSON` | Suppression des titres + correspondance par nom de famille. « Marie Dubois » et « Dubois » sont regroupés. Des prénoms différents restent séparés (« Marie Dubois » vs « Jean Dubois »). Les noms de famille ambigus correspondant à plusieurs personnes sont isolés. |
| `LOCATION` | Suppression des prépositions françaises. « à Lyon » et « Lyon » sont regroupés. |
| `ORG` | Correspondance insensible à la casse. « ACME Corp » et « acme corp » sont regroupés. |

---

## Module Pseudonym (`gdpr_pseudonymizer.pseudonym`)

### LibraryBasedPseudonymManager

Charge les bibliothèques de pseudonymes depuis des fichiers JSON et attribue les pseudonymes en tenant compte du genre :

```python
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager

manager = LibraryBasedPseudonymManager()
manager.load_library("star_wars")

assignment = manager.assign_pseudonym(
    entity_type="PERSON",
    first_name="Marie",
    last_name="Dubois",
    gender="female"
)
print(assignment.pseudonym_full)  # ex. "Leia Organa"
```

### PseudonymAssignment

Objet retourné lors de l'attribution d'un pseudonyme :

| Attribut | Type | Description |
|----------|------|-------------|
| `pseudonym_full` | `str` | Pseudonyme complet |
| `pseudonym_first` | `str | None` | Prénom du pseudonyme (PERSON uniquement) |
| `pseudonym_last` | `str | None` | Nom de famille du pseudonyme (PERSON uniquement) |
| `theme` | `str` | Thème de la bibliothèque utilisée |
| `exhaustion_percentage` | `float` | Taux d'utilisation de la bibliothèque (0.0-1.0) |
| `is_ambiguous` | `bool` | Indique une ambiguïté |
| `ambiguity_reason` | `str | None` | Motif de l'ambiguïté |

### GenderDetector

Détecte automatiquement le genre des prénoms français à partir d'un dictionnaire embarqué de 945 prénoms issu de l'INSEE. Utilisé par `CompositionalPseudonymEngine` pour attribuer automatiquement des pseudonymes du même genre.

```python
from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector

detector = GenderDetector()
detector.load()

detector.detect_gender("Marie")          # "female"
detector.detect_gender("Jean")           # "male"
detector.detect_gender("Camille")        # None (épicène)
detector.detect_gender("Xyzabc")         # None (inconnu)

# Détection à partir du nom complet (extrait le prénom, vérifie le type d'entité)
detector.detect_gender_from_full_name("Marie Dupont", "PERSON")    # "female"
detector.detect_gender_from_full_name("Jean-Pierre Martin", "PERSON")  # "male" (composé : utilise le premier élément)
detector.detect_gender_from_full_name("Paris", "LOCATION")         # None (entité non-PERSON)
```

Méthodes principales :

| Méthode | Description |
|---------|-------------|
| `load()` | Charge le dictionnaire de genre depuis le fichier JSON (chargement différé au premier appel) |
| `detect_gender(first_name)` | Détecte le genre d'un prénom. Retourne `"male"`, `"female"` ou `None` |
| `detect_gender_from_full_name(full_name, entity_type)` | Extrait le prénom du nom complet et détecte le genre. Retourne toujours `None` pour les entités non-PERSON |

Statistiques du dictionnaire : 470 masculins, 457 féminins, 18 épicènes. Recherche insensible à la casse.

### CompositionalPseudonymEngine

Gère la logique de résolution par composition : « Marie Dubois » correspond à « Leia Organa », et « Marie » seul correspond à « Leia » pour garantir la cohérence. Peut intégrer `GenderDetector` pour attribuer automatiquement des pseudonymes du même genre.

```python
from gdpr_pseudonymizer.pseudonym.assignment_engine import CompositionalPseudonymEngine

engine = CompositionalPseudonymEngine(
    pseudonym_manager=manager,
    mapping_repository=repo,
    gender_detector=detector  # Facultatif : active la détection automatique du genre
)

result = engine.assign_compositional_pseudonym(
    entity_text="Marie Dubois",
    entity_type="PERSON",
    gender="female"
)
```

Méthodes principales :

| Méthode | Description |
|---------|-------------|
| `assign_compositional_pseudonym(entity_text, entity_type, gender)` | Attribue un pseudonyme avec réutilisation des composants |
| `strip_titles(text)` | Supprime les titres honorifiques français (Dr., Mme, Maître) |
| `strip_prepositions(text)` | Supprime les prépositions françaises des noms de lieux |
| `parse_full_name(entity_text)` | Décompose en (prénom, nom, est_composé) |
| `find_standalone_components(component, component_type)` | Recherche une correspondance existante pour un composant |

---

## Module Data (`gdpr_pseudonymizer.data`)

### Fonctions de base de données

```python
from gdpr_pseudonymizer.data.database import init_database, open_database

# Créer une nouvelle base de données chiffrée
init_database("mappings.db", "your-passphrase")

# Ouvrir une base existante (gestionnaire de contexte)
with open_database("mappings.db", "your-passphrase") as db_session:
    # Utiliser les dépôts avec db_session
    pass
```

### Modèles SQLAlchemy

#### Entity (table `entities`)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | `str` (UUID) | Clé primaire |
| `entity_type` | `str` | PERSON, LOCATION, ORG |
| `first_name` | `str | None` | Prénom d'origine (chiffré) |
| `last_name` | `str | None` | Nom de famille d'origine (chiffré) |
| `full_name` | `str` | Texte complet de l'entité (chiffré, unique) |
| `pseudonym_first` | `str | None` | Prénom du pseudonyme attribué |
| `pseudonym_last` | `str | None` | Nom de famille du pseudonyme attribué |
| `pseudonym_full` | `str` | Pseudonyme complet |
| `gender` | `str | None` | Genre détecté |
| `confidence_score` | `float | None` | Score de confiance NER |
| `theme` | `str` | Thème de la bibliothèque utilisée |
| `first_seen_timestamp` | `datetime` | Date de première détection |

#### Operation (table `operations`)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | `str` (UUID) | Clé primaire |
| `timestamp` | `datetime` | Horodatage de l'opération |
| `operation_type` | `str` | PROCESS, BATCH, VALIDATE, etc. |
| `files_processed` | `list[str]` | Tableau JSON des chemins de fichiers |
| `entity_count` | `int` | Nombre d'entités traitées |
| `processing_time_seconds` | `float` | Durée |
| `success` | `bool` | Résultat |

### Dépôts

#### MappingRepository (abstrait)

```python
class MappingRepository(ABC):
    def find_by_full_name(self, full_name: str) -> Entity | None: ...
    def find_by_component(self, component: str, component_type: str) -> list[Entity]: ...
    def save(self, entity: Entity) -> Entity: ...
    def save_batch(self, entities: list[Entity]) -> list[Entity]: ...
    def find_all(self, entity_type=None, is_ambiguous=None) -> list[Entity]: ...
```

#### AuditRepository

```python
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository

repo = AuditRepository(session)
repo.log_operation(operation)
operations = repo.find_operations(operation_type="PROCESS", success=True)
repo.export_to_csv("audit_log.csv")
```

### EncryptionService

Chiffrement authentifié déterministe AES-256-SIV :

```python
from gdpr_pseudonymizer.data.encryption import EncryptionService

salt = EncryptionService.generate_salt()
valid, msg = EncryptionService.validate_passphrase("my-passphrase")

service = EncryptionService(passphrase="...", salt=salt)
ciphertext = service.encrypt("Marie Dubois")
plaintext = service.decrypt(ciphertext)
```

---

## Module Validation (`gdpr_pseudonymizer.validation`)

### Processus de validation

```python
from gdpr_pseudonymizer.validation.workflow import run_validation_workflow

validated_entities = run_validation_workflow(
    entities=detected_entities,
    document_text=text,
    document_path="input.txt",
    pseudonym_assigner=my_assigner_fn  # Fonction de rappel facultative
)
```

### États de révision

| État | Description |
|------|-------------|
| `PENDING` | En attente de révision |
| `CONFIRMED` | Confirmé comme entité correcte |
| `REJECTED` | Rejeté (faux positif) |
| `MODIFIED` | Texte de l'entité modifié par l'utilisateur |
| `ADDED` | Ajouté manuellement par l'utilisateur |

### Actions utilisateur

| Classe | Description |
|--------|-------------|
| `ConfirmAction(entity)` | Accepter l'entité et son pseudonyme |
| `RejectAction(entity)` | Signaler comme faux positif |
| `ModifyAction(entity, new_text)` | Modifier le texte de l'entité |
| `AddAction(text, entity_type, start_pos, end_pos)` | Ajouter une entité non détectée |
| `ChangePseudonymAction(entity, new_pseudonym)` | Remplacer le pseudonyme |

---

## Module Utils (`gdpr_pseudonymizer.utils`)

### Gestion des fichiers

```python
from gdpr_pseudonymizer.utils.file_handler import read_file, write_file, validate_file_path

text = read_file("input.txt")
write_file("output.txt", pseudonymized_text)
validate_file_path("doc.txt", allowed_extensions=[".txt", ".md"])
```

### Configuration

```python
from gdpr_pseudonymizer.utils.config_manager import load_config, Config

config = load_config("config.yaml")  # Ou None pour les valeurs par défaut
# config.theme, config.model_name, config.db_path, etc.
```

### Journalisation

```python
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

configure_logging("INFO")
logger = get_logger("my_module")
logger.info("entity_detected", entity_type="PERSON", confidence=0.92)
```

---

## Exceptions

Toutes les exceptions héritent de `PseudonymizerError` :

| Exception | Déclenchée lorsque |
|-----------|-------------------|
| `ConfigurationError` | Configuration invalide ou manquante |
| `ModelNotFoundError` | Le modèle NLP n'a pas pu être chargé |
| `EncryptionError` | Le chiffrement ou le déchiffrement échoue |
| `ValidationError` | Erreur dans le processus de validation |
| `FileProcessingError` | Erreur de lecture ou d'écriture de fichier |

```python
from gdpr_pseudonymizer.exceptions import (
    PseudonymizerError,
    ConfigurationError,
    ModelNotFoundError,
    EncryptionError,
    ValidationError,
    FileProcessingError,
)
```

---

## Points d'extension

### Bibliothèques de pseudonymes personnalisées

Créez un fichier JSON dans `data/pseudonyms/` en respectant ce schéma :

```json
{
  "theme": "my_theme",
  "data_sources": [
    {
      "source_name": "Description",
      "url": "https://...",
      "license": "Type de licence",
      "usage_justification": "Justification de l'utilisation",
      "extraction_date": "2026-01-01",
      "extraction_method": "Méthode de collecte des données"
    }
  ],
  "first_names": {
    "male": ["Name1", "Name2"],
    "female": ["Name3", "Name4"],
    "neutral": ["Name5", "Name6"]
  },
  "last_names": ["LastName1", "LastName2"],
  "locations": {
    "cities": ["City1", "City2"],
    "regions": ["Region1", "Region2"]
  },
  "organizations": {
    "companies": ["Company1", "Company2"],
    "agencies": ["Agency1"],
    "institutions": ["Institute1"]
  }
}
```

**Contenu minimal :** 500+ prénoms, 500+ noms de famille, 80+ lieux, 35+ organisations.

**Utilisation :**
```python
manager = LibraryBasedPseudonymManager()
manager.load_library("my_theme")
```

Ou en ligne de commande :
```bash
poetry run gdpr-pseudo process doc.txt --theme my_theme
```

### Détecteur NLP personnalisé

Créez une sous-classe de `EntityDetector` :

```python
from gdpr_pseudonymizer.nlp.entity_detector import EntityDetector, DetectedEntity

class MyDetector(EntityDetector):
    def load_model(self, model_name: str) -> None:
        # Charger votre modèle
        pass

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        # Retourner les entités détectées
        pass

    def get_model_info(self) -> dict[str, str]:
        return {"name": "my_model", "version": "1.0"}

    @property
    def supports_gender_classification(self) -> bool:
        return False
```

---

## Exemple d'utilisation programmatique

Exemple complet de pseudonymisation d'un document par programme :

```python
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

# Initialiser le processeur
processor = DocumentProcessor(
    db_path="project.db",
    passphrase="MySecurePassphrase123",
    theme="neutral",
    model_name="spacy"
)

# Traiter le document (skip_validation=True pour un usage non interactif)
result = processor.process_document(
    input_path="interview.txt",
    output_path="interview_pseudonymized.txt",
    skip_validation=True,
    entity_type_filter={"PERSON", "LOCATION"}  # Facultatif : ne traiter que ces types
)

if result.success:
    print(f"Traité : {result.entities_detected} entités")
    print(f"Nouvelles : {result.entities_new}, réutilisées : {result.entities_reused}")
    print(f"Durée : {result.processing_time_seconds:.2f}s")
else:
    print(f"Erreur : {result.error_message}")
```

---

## Documentation associée

- [Référence de la ligne de commande](CLI-REFERENCE.md) — Documentation des commandes
- [Méthodologie](methodology.md) — Approche technique et conformité RGPD
- [Guide d'installation](installation.md) — Instructions d'installation
- [Tutoriel](tutorial.md) — Guide d'utilisation
