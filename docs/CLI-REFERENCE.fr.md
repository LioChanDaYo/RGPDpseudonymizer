# Référence de la ligne de commande

Ce document décrit en détail toutes les commandes et options de l'interface en ligne de commande `gdpr-pseudo`.

## Sommaire

- [Options générales](#options-generales)
- [Commandes](#commandes)
  - [init](#init)
  - [process](#process)
  - [batch](#batch)
  - [config](#config)
  - [list-mappings](#list-mappings)
  - [validate-mappings](#validate-mappings)
  - [stats](#stats)
  - [import-mappings](#import-mappings)
  - [export](#export)
  - [delete-mapping](#delete-mapping)
  - [list-entities](#list-entities)
  - [destroy-table](#destroy-table)
- [Conformité RGPD](#conformite-rgpd)
- [Fichier de configuration](#fichier-de-configuration)
- [Scénarios d'utilisation courants](#scenarios-dutilisation-courants)
- [Résolution de problèmes](#resolution-de-problemes)

---

## Options générales

Ces options sont disponibles pour toutes les commandes :

| Option | Abrégé | Description |
|--------|--------|-------------|
| `--version` | | Affiche la version et quitte |
| `--config CHEMIN` | `-c` | Chemin du fichier de configuration (par défaut : `~/.gdpr-pseudo.yaml` ou `./.gdpr-pseudo.yaml`) |
| `--verbose` | `-v` | Active les logs détaillés (niveau DEBUG) |
| `--quiet` | `-q` | N'affiche que les erreurs |
| `--help` | | Affiche l'aide et quitte |

**Exemple :**
```bash
gdpr-pseudo --version
gdpr-pseudo --config ./custom-config.yaml process input.txt
```

---

## Commandes

### init

Crée une nouvelle base de données chiffrée pour stocker les correspondances.

**Syntaxe :**
```bash
gdpr-pseudo init [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin du fichier de base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données (12 caractères minimum) |
| `--force` | `-f` | | Écrase la base de données existante |

**Exemples :**
```bash
# Créer la base avec saisie interactive du mot de passe
gdpr-pseudo init

# Créer la base à un emplacement personnalisé
gdpr-pseudo init --db project_mappings.db

# Utiliser le mot de passe depuis une variable d'environnement
export GDPR_PSEUDO_PASSPHRASE="votre_mot_de_passe"
gdpr-pseudo init

# Écraser une base existante
gdpr-pseudo init --force
```

**Exigences du mot de passe :**
- 12 caractères minimum
- Conservé uniquement en mémoire (jamais écrit sur le disque)
- Pour l'automatisation, utiliser la variable d'environnement `GDPR_PSEUDO_PASSPHRASE`

---

### process

Pseudonymise un document.

**Syntaxe :**
```bash
gdpr-pseudo process FICHIER_ENTREE [OPTIONS]
```

**Arguments :**

| Argument | Obligatoire | Description |
|----------|-------------|-------------|
| `FICHIER_ENTREE` | Oui | Chemin du fichier à traiter (.txt, .md, .pdf ou .docx) |

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--output CHEMIN` | `-o` | `<entrée>_pseudonymized.ext` | Chemin du fichier de sortie |
| `--theme TEXTE` | `-t` | `neutral` | Thème de pseudonymes (neutral/star_wars/lotr) |
| `--model TEXTE` | `-m` | `spacy` | Modèle NLP à utiliser |
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--entity-types TEXTE` | | (tous) | Types d'entités à traiter, séparés par des virgules (PERSON,LOCATION,ORG). Seuls les types indiqués seront détectés et pseudonymisés. |

**Exemples :**
```bash
# Traiter avec les réglages par défaut
gdpr-pseudo process input.txt

# Spécifier le fichier de sortie
gdpr-pseudo process input.txt -o output.txt

# Utiliser le thème Star Wars
gdpr-pseudo process input.txt --theme star_wars

# Utiliser une base de données spécifique
gdpr-pseudo process input.txt --db project.db

# Ne traiter que les personnes et les lieux (ignorer les organisations)
gdpr-pseudo process input.txt --entity-types PERSON,LOCATION

# Traiter un document PDF (prérequis : pip install gdpr-pseudonymizer[pdf])
gdpr-pseudo process report.pdf

# Traiter un document DOCX (prérequis : pip install gdpr-pseudonymizer[docx])
gdpr-pseudo process interview.docx -o interview_pseudonymized.txt
```

**Remarques sur les formats PDF/DOCX :**
- La prise en charge des PDF et DOCX nécessite des dépendances optionnelles : `pip install gdpr-pseudonymizer[formats]`.
- Pour les fichiers PDF/DOCX, la sortie est toujours en texte brut (`.txt`). La conservation du format d'origine est prévue pour la v1.2+.
- Les PDF numérisés (à base d'images) déclenchent un avertissement si peu de texte est extrait. L'OCR n'est pas pris en charge.

---

### batch

Traite plusieurs documents contenus dans un répertoire (traitement par lot).

**Syntaxe :**
```bash
gdpr-pseudo batch CHEMIN_ENTREE [OPTIONS]
```

**Arguments :**

| Argument | Obligatoire | Description |
|----------|-------------|-------------|
| `CHEMIN_ENTREE` | Oui | Répertoire ou fichier à traiter |

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--output CHEMIN` | `-o` | Identique à l'entrée, suffixé `_pseudonymized` | Répertoire de sortie |
| `--theme TEXTE` | `-t` | `neutral` | Thème de pseudonymes |
| `--model TEXTE` | `-m` | `spacy` | Modèle NLP à utiliser |
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--recursive` | `-r` | | Traite aussi les sous-répertoires |
| `--continue-on-error` | | Oui | Continue le traitement si un fichier produit une erreur |
| `--stop-on-error` | | | Arrête le traitement dès la première erreur |
| `--workers` | `-w` | 1 | Nombre de processus parallèles (1-8). Utiliser 1 pour la validation interactive, 2-8 pour le traitement parallèle sans validation |
| `--entity-types TEXTE` | | (tous) | Types d'entités à traiter, séparés par des virgules (PERSON,LOCATION,ORG). Seuls les types indiqués seront détectés et pseudonymisés. |

**Exemples :**
```bash
# Traiter tous les fichiers d'un répertoire
gdpr-pseudo batch ./documents/

# Traiter récursivement vers un répertoire de sortie spécifique
gdpr-pseudo batch ./documents/ -o ./output/ --recursive

# Utiliser un thème spécifique
gdpr-pseudo batch ./documents/ --theme star_wars

# S'arrêter à la première erreur
gdpr-pseudo batch ./documents/ --stop-on-error

# Traitement parallèle (sans validation, plus rapide pour les entités déjà validées)
gdpr-pseudo batch ./documents/ --workers 4

# Traitement séquentiel avec validation (par défaut)
gdpr-pseudo batch ./documents/ --workers 1

# Ne traiter que les personnes dans tous les documents
gdpr-pseudo batch ./documents/ --entity-types PERSON

# Traiter les personnes et organisations en parallèle
gdpr-pseudo batch ./documents/ --entity-types PERSON,ORG --workers 4

# Traiter un répertoire contenant des formats variés (.txt, .pdf, .docx)
gdpr-pseudo batch ./documents/ --recursive
```

**Formats pris en charge :** `.txt`, `.md`, `.pdf`, `.docx`. Les formats PDF et DOCX nécessitent les dépendances optionnelles (`pip install gdpr-pseudonymizer[formats]`). Les fichiers de sortie issus de PDF/DOCX portent l'extension `.txt`.

---

### config

Affiche ou modifie la configuration.

**Syntaxe :**
```bash
gdpr-pseudo config [OPTIONS] [COMMANDE]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--init` | | | Génère un fichier modèle `.gdpr-pseudo.yaml` dans le répertoire courant |
| `--force` | `-f` | | Écrase le fichier de configuration existant (avec `--init`) |

**Sous-commandes :**

| Sous-commande | Description |
|---------------|-------------|
| `set CLÉ VALEUR` | Modifie un paramètre de configuration |

**Exemples :**
```bash
# Afficher la configuration en vigueur
gdpr-pseudo config

# Générer un fichier de configuration modèle
gdpr-pseudo config --init

# Écraser la configuration existante
gdpr-pseudo config --init --force

# Modifier des paramètres
gdpr-pseudo config set pseudonymization.theme star_wars
gdpr-pseudo config set database.path my_mappings.db
gdpr-pseudo config set batch.workers 4
gdpr-pseudo config set logging.level DEBUG
```

**Paramètres disponibles :**

| Clé | Type | Description |
|-----|------|-------------|
| `database.path` | chaîne | Chemin du fichier de base de données |
| `pseudonymization.theme` | chaîne | Thème de pseudonymes (neutral/star_wars/lotr) |
| `pseudonymization.model` | chaîne | Modèle NLP (spacy) |
| `batch.workers` | entier | Processus parallèles (1-8) |
| `batch.output_dir` | chaîne | Répertoire de sortie par défaut |
| `logging.level` | chaîne | Niveau de log (DEBUG/INFO/WARNING/ERROR) |

---

### list-mappings

Affiche les correspondances entre entités et pseudonymes enregistrées dans la base de données.

**Syntaxe :**
```bash
gdpr-pseudo list-mappings [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--type TEXTE` | `-t` | | Filtrer par type d'entité (PERSON/LOCATION/ORG) |
| `--search TEXTE` | `-s` | | Rechercher par nom d'entité (insensible à la casse) |
| `--export CHEMIN` | `-e` | | Exporter les correspondances au format CSV |
| `--limit ENTIER` | `-l` | | Nombre maximal de résultats |

**Exemples :**
```bash
# Afficher toutes les correspondances
gdpr-pseudo list-mappings

# Filtrer par type
gdpr-pseudo list-mappings --type PERSON

# Rechercher une entité
gdpr-pseudo list-mappings --search "Marie"

# Exporter en CSV
gdpr-pseudo list-mappings --export mappings.csv

# Combiner filtres et limite
gdpr-pseudo list-mappings --type PERSON --search "Dubois" --limit 10
```

---

### validate-mappings

Passe en revue les correspondances existantes sans traiter de document.

**Syntaxe :**
```bash
gdpr-pseudo validate-mappings [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--interactive` | `-i` | | Mode interactif : chaque correspondance est présentée individuellement |
| `--type TEXTE` | `-t` | | Filtrer par type d'entité |

**Exemples :**
```bash
# Afficher toutes les correspondances avec leurs métadonnées
gdpr-pseudo validate-mappings

# Passer en revue interactivement
gdpr-pseudo validate-mappings --interactive

# Filtrer par type
gdpr-pseudo validate-mappings --type PERSON
```

**Remarque :** cette commande est en lecture seule et ne modifie pas la base de données.

---

### stats

Affiche les statistiques d'utilisation de la base de données.

**Syntaxe :**
```bash
gdpr-pseudo stats [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |

**Exemples :**
```bash
# Afficher les statistiques
gdpr-pseudo stats

# Pour une base de données spécifique
gdpr-pseudo stats --db project.db
```

**Informations affichées :**
- Base de données : chemin, taille, date de création
- Nombre d'entités par type (PERSON, LOCATION, ORG)
- Répartition des thèmes
- Historique des traitements (opérations réussies/échouées)
- Dernière opération effectuée

---

### import-mappings

Importe les correspondances depuis une autre base de données.

**Syntaxe :**
```bash
gdpr-pseudo import-mappings BASE_SOURCE [OPTIONS]
```

**Arguments :**

| Argument | Obligatoire | Description |
|----------|-------------|-------------|
| `BASE_SOURCE` | Oui | Fichier de base de données source |

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données cible |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base cible |
| `--source-passphrase TEXTE` | | (saisie interactive) | Mot de passe de la base source |
| `--skip-duplicates` | | Oui | Ignore les doublons |
| `--prompt-duplicates` | | | Demande confirmation pour chaque doublon |

**Exemples :**
```bash
# Importer depuis une autre base
gdpr-pseudo import-mappings old_project.db

# Importer vers une base spécifique
gdpr-pseudo import-mappings old_project.db --db new_project.db

# Gérer les doublons au cas par cas
gdpr-pseudo import-mappings old.db --prompt-duplicates
```

---

### export

Exporte le journal d'audit au format JSON ou CSV.

**Syntaxe :**
```bash
gdpr-pseudo export CHEMIN_SORTIE [OPTIONS]
```

**Arguments :**

| Argument | Obligatoire | Description |
|----------|-------------|-------------|
| `CHEMIN_SORTIE` | Oui | Chemin du fichier de sortie (.json ou .csv) |

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--type TEXTE` | `-t` | | Filtrer par type d'opération (PROCESS/BATCH/etc.) |
| `--from DATE` | | | N'inclure que les opérations postérieures à cette date (AAAA-MM-JJ) |
| `--to DATE` | | | N'inclure que les opérations antérieures à cette date (AAAA-MM-JJ) |
| `--success-only` | | | Exporter uniquement les opérations réussies |
| `--failures-only` | | | Exporter uniquement les opérations échouées |
| `--limit ENTIER` | `-l` | | Nombre maximal de résultats |

**Exemples :**
```bash
# Exporter toutes les opérations en JSON
gdpr-pseudo export audit_log.json

# Exporter en CSV
gdpr-pseudo export audit_log.csv

# Filtrer par période
gdpr-pseudo export audit.json --from 2026-01-01 --to 2026-01-31

# Filtrer par type d'opération
gdpr-pseudo export audit.json --type PROCESS

# N'exporter que les opérations réussies
gdpr-pseudo export audit.json --success-only
```

---

### delete-mapping

Supprime une correspondance de la base de données (effacement au titre de l'article 17 du RGPD).

Supprimer une correspondance transforme la pseudonymisation en **anonymisation** : sans correspondance, le pseudonyme ne peut plus être relié à une personne identifiable, et les données sortent du champ d'application du RGPD.

**Syntaxe :**
```bash
gdpr-pseudo delete-mapping [NOM_ENTITE] [OPTIONS]
```

**Arguments :**

| Argument | Obligatoire | Description |
|----------|-------------|-------------|
| `NOM_ENTITE` | Non* | Nom de l'entité à supprimer (*indiquer le nom ou `--id`) |

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--id TEXTE` | | | UUID de l'entité à supprimer (alternative au nom) |
| `--reason TEXTE` | `-r` | | Motif de suppression (référence de la demande RGPD) |
| `--force` | `-f` | | Ne pas demander de confirmation |

**Exemples :**
```bash
# Supprimer par nom (avec confirmation interactive)
gdpr-pseudo delete-mapping "Marie Dupont"

# Supprimer par UUID (obtenu via list-entities)
gdpr-pseudo delete-mapping --id abc12345

# Supprimer en précisant le motif pour la traçabilité
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# Supprimer sans confirmation (pour l'automatisation)
gdpr-pseudo delete-mapping "Marie Dupont" --force

# Utiliser une base de données spécifique
gdpr-pseudo delete-mapping "Marie Dupont" --db project.db
```

**Traçabilité :**
Chaque suppression crée une entrée `ERASURE` dans la table des opérations contenant :
- Le nom, le type et l'identifiant de l'entité
- L'horodatage de la suppression
- Le motif éventuel (option `--reason`)

---

### list-entities

Liste les entités enregistrées, avec recherche intégrée. Conçue pour le processus d'effacement RGPD.

**Syntaxe :**
```bash
gdpr-pseudo list-entities [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base de données |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe de la base de données |
| `--search TEXTE` | `-s` | | Rechercher par nom (sous-chaîne, insensible à la casse) |
| `--type TEXTE` | `-t` | | Filtrer par type d'entité (PERSON/LOCATION/ORG) |
| `--limit ENTIER` | `-l` | | Nombre maximal de résultats |

**Exemples :**
```bash
# Lister toutes les entités
gdpr-pseudo list-entities

# Rechercher par nom
gdpr-pseudo list-entities --search "Dupont"

# Filtrer par type
gdpr-pseudo list-entities --type PERSON

# Combiner filtres et limite
gdpr-pseudo list-entities --search "Marie" --type PERSON --limit 10
```

**Colonnes affichées :**
- **ID entité** (UUID tronqué) — à utiliser avec `delete-mapping --id`
- **Nom de l'entité** — nom d'origine (déchiffré)
- **Type** — PERSON, LOCATION ou ORG
- **Pseudonyme** — pseudonyme attribué
- **Première détection** — date à laquelle l'entité a été détectée pour la première fois
- **Nb documents** — N/D (suivi par entité prévu pour la v1.2)

**Différence avec `list-mappings` :**
- `list-mappings` — orientée révision des correspondances (affiche le thème, la confiance, export CSV)
- `list-entities` — orientée effacement RGPD (affiche l'identifiant pour la suppression via `--id`, date de première détection)

---

### destroy-table

Supprime la base de données de correspondances de manière sécurisée.

**Syntaxe :**
```bash
gdpr-pseudo destroy-table [OPTIONS]
```

**Options :**

| Option | Abrégé | Défaut | Description |
|--------|--------|--------|-------------|
| `--db CHEMIN` | | `mappings.db` | Chemin de la base à détruire |
| `--force` | `-f` | | Ne pas demander de confirmation |
| `--passphrase TEXTE` | `-p` | (saisie interactive) | Mot de passe pour vérifier que vous êtes bien le propriétaire de la base (recommandé) |
| `--skip-passphrase-check` | | | Ne pas vérifier le mot de passe (déconseillé) |

**Exemples :**
```bash
# Supprimer avec confirmation et vérification du mot de passe (le plus sûr)
gdpr-pseudo destroy-table

# Supprimer une base spécifique
gdpr-pseudo destroy-table --db project.db -p "votre_mot_de_passe"

# Sans confirmation (le mot de passe reste requis par défaut)
gdpr-pseudo destroy-table --force

# Sans confirmation ni mot de passe (dangereux !)
gdpr-pseudo destroy-table --force --skip-passphrase-check
```

**Mécanismes de sécurité :**

1. **Vérification du mot de passe :** par défaut, vous devez saisir le mot de passe correct pour prouver que vous êtes bien le propriétaire de la base avant sa suppression.

2. **Vérification du format SQLite :** l'outil vérifie que le fichier est bien une base de données SQLite valide avant de tenter la suppression (pour éviter de détruire accidentellement un fichier qui n'est pas une base).

3. **Protection contre les liens symboliques :** les liens symboliques sont refusés afin d'empêcher les attaques par redirection de la suppression vers un autre fichier.

4. **Effacement sécurisé en 3 passes :** les données sont écrasées avant la suppression du fichier, pour empêcher toute récupération.

**ATTENTION :** cette opération est irréversible ! N'utilisez `--skip-passphrase-check` que si vous n'avez aucune autre option.

---

## Conformité RGPD

### Article 17 — Droit à l'effacement

L'article 17 du RGPD confère aux personnes concernées le droit de demander la suppression de leurs données personnelles. La commande `delete-mapping` répond à cette exigence.

**Principe de fonctionnement :**

1. **Pseudonymisation vs anonymisation :** lors du traitement d'un document, les noms d'entités sont remplacés par des pseudonymes (par ex. « Marie Dupont » devient « Leia Organa »). La correspondance entre le nom réel et le pseudonyme est conservée dans la base de données chiffrée. Tant que cette correspondance existe, les données pseudonymisées restent des données personnelles au sens du RGPD.

2. **Suppression = anonymisation :** lorsqu'une correspondance est supprimée via `delete-mapping`, le lien entre le pseudonyme et l'identité réelle est définitivement détruit. Les documents pseudonymisés ne sont pas modifiés, mais ils deviennent **anonymes** : le pseudonyme « Leia Organa » ne peut plus être relié à « Marie Dupont ». Les données anonymes sortent du champ d'application du RGPD.

3. **Traçabilité :** chaque suppression crée une entrée `ERASURE` dans le journal d'audit, qui enregistre quelle personne a été supprimée, à quelle date et pour quel motif. Cette entrée constitue la preuve que la demande d'effacement a bien été exécutée.

**Processus d'effacement :**

```bash
# 1. Réception d'une demande d'effacement RGPD pour « Marie Dupont »
# 2. Rechercher l'entité
gdpr-pseudo list-entities --search "Dupont"

# 3. Supprimer la correspondance en précisant le motif
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# 4. Vérifier la suppression
gdpr-pseudo list-entities --search "Dupont"

# 5. Exporter le journal d'audit pour les dossiers de conformité
gdpr-pseudo export erasure_audit.json --type ERASURE
```

**Points importants :**
- La suppression est **définitive et irréversible** : la correspondance ne peut pas être récupérée
- Les documents pseudonymisés **ne sont pas modifiés** : seule la base de correspondances est concernée
- Les autres entités de la base **ne sont pas affectées** par la suppression
- L'entrée du journal d'audit est conservée même après la suppression, et sert de preuve de conformité

**Conservation de données personnelles dans le journal d'audit :**

L'entrée `ERASURE` du journal d'audit conserve volontairement le **nom**, le **type** et l'**identifiant interne** de l'entité supprimée. C'est indispensable pour prouver qu'une demande d'effacement précise a bien été exécutée : sans cette information, il serait impossible de vérifier la conformité avec la demande RGPD d'origine.

Cette conservation est justifiée au titre de l'article 17(3)(e) du RGPD (constatation, exercice ou défense de droits en justice) et de l'article 5(2) (principe de responsabilité : le responsable de traitement doit pouvoir démontrer sa conformité). Le journal d'audit constitue la preuve que le droit à l'effacement de la personne concernée a été exercé.

Les données personnelles conservées dans le journal d'audit sont :
- Protégées par le même chiffrement AES-256-SIV que l'ensemble de la base de données
- Accessibles uniquement avec le mot de passe de la base
- Minimales (nom et type uniquement, sans adresse, coordonnées ni autres données personnelles)
- Nécessaires à la finalité légitime de preuve de conformité

---

## Fichier de configuration

L'outil prend en charge les fichiers de configuration au format YAML. Ordre de priorité (du plus prioritaire au moins prioritaire) :

1. Options passées en ligne de commande
2. Fichier de configuration personnalisé (`--config`)
3. Configuration du projet (`./.gdpr-pseudo.yaml`)
4. Configuration du répertoire personnel (`~/.gdpr-pseudo.yaml`)
5. Valeurs par défaut

### Structure du fichier de configuration

```yaml
database:
  path: mappings.db

pseudonymization:
  theme: neutral    # neutral | star_wars | lotr
  model: spacy

logging:
  level: INFO       # DEBUG | INFO | WARNING | ERROR
  file: gdpr-pseudo.log  # Facultatif : active la journalisation dans un fichier
```

### Sécurité du mot de passe

**Le mot de passe ne peut PAS figurer dans le fichier de configuration**, pour des raisons de sécurité. Le stockage de mots de passe en clair est interdit.

Utilisez plutôt l'une de ces méthodes :
1. **Saisie interactive** (le plus sûr — comportement par défaut)
2. **Variable d'environnement** `GDPR_PSEUDO_PASSPHRASE` (pour l'automatisation)
3. **Option en ligne de commande** `--passphrase` (visible dans la liste des processus — à utiliser avec précaution)

**Mise en garde concernant `--passphrase` :**
Lorsque le mot de passe est passé en ligne de commande, il peut être :
- Visible dans l'historique du shell (`~/.bash_history`, `~/.zsh_history`)
- Visible dans la liste des processus (`ps aux`)
- Enregistré par les systèmes d'audit

Pour les environnements sensibles, privilégiez la variable d'environnement ou la saisie interactive.

---

## Scénarios d'utilisation courants

### Première mise en route

```bash
# 1. Créer la base de données
gdpr-pseudo init

# 2. Traiter un premier document
gdpr-pseudo process interview.txt

# 3. Consulter les résultats
gdpr-pseudo list-mappings
```

### Traitement par lot

```bash
# 1. Créer la base de données (si ce n'est pas déjà fait)
gdpr-pseudo init --db project.db

# 2. Traiter tous les documents d'un répertoire
gdpr-pseudo batch ./raw_interviews/ -o ./pseudonymized/ --db project.db

# 3. Consulter les statistiques
gdpr-pseudo stats --db project.db
```

### Gestion des correspondances

```bash
# 1. Lister les correspondances actuelles
gdpr-pseudo list-mappings

# 2. Filtrer par type
gdpr-pseudo list-mappings --type PERSON

# 3. Vérifier les correspondances en mode interactif
gdpr-pseudo validate-mappings --interactive

# 4. Exporter pour révision
gdpr-pseudo list-mappings --export review.csv
```

### Effacement RGPD

```bash
# 1. Rechercher l'entité à supprimer
gdpr-pseudo list-entities --search "Dupont"

# 2. Supprimer la correspondance (avec motif pour la traçabilité)
gdpr-pseudo delete-mapping "Marie Dupont" --reason "GDPR-REQ-2026-042"

# 3. Vérifier la suppression
gdpr-pseudo list-entities --search "Dupont"

# 4. Exporter le journal d'audit pour la conformité
gdpr-pseudo export erasure_log.json --type ERASURE
```

### Export du journal d'audit

```bash
# Exporter toutes les opérations
gdpr-pseudo export audit_complete.json

# Exporter les opérations d'une période donnée
gdpr-pseudo export audit_january.json --from 2026-01-01 --to 2026-01-31

# N'exporter que les opérations réussies
gdpr-pseudo export audit_success.csv --success-only
```

### Fusion de projets

```bash
# Importer les correspondances d'un ancien projet vers un nouveau
gdpr-pseudo import-mappings old_project.db --db new_project.db

# Vérifier l'importation
gdpr-pseudo stats --db new_project.db
```

---

## Méthodologie de pseudonymisation

### Attribution de pseudonymes selon le genre

Depuis la v1.1, le pseudonymiseur détecte automatiquement le genre des prénoms français et attribue des pseudonymes du même genre. Cela préserve la cohérence de genre dans les documents pseudonymisés, ce qui améliore la lisibilité et l'exploitation par les LLM.

**Principe de fonctionnement :**

1. **Détection du genre :** lorsqu'une entité PERSON est détectée (par ex. « Marie Dupont »), le prénom est recherché dans un dictionnaire de genre français (~930 prénoms issus des données publiques de l'INSEE).

2. **Sélection par genre :** le moteur de pseudonymes choisit un prénom de remplacement dans le groupe de genre correspondant :
   - Prénom féminin (par ex. « Marie ») → pseudonyme féminin (par ex. « Léa »)
   - Prénom masculin (par ex. « Jean ») → pseudonyme masculin (par ex. « Lucas »)
   - Prénom inconnu ou ambigu → tirage aléatoire dans la liste combinée masculin+féminin (comportement identique aux versions précédentes)

3. **Prénoms composés :** pour les prénoms à trait d'union, c'est le premier élément qui détermine le genre :
   - « Jean-Pierre » → « Jean » → masculin
   - « Marie-Claire » → « Marie » → féminin

4. **Prénoms épicènes :** les prénoms véritablement mixtes en français (Camille, Dominique, Claude, etc.) sont traités comme inconnus et reçoivent un pseudonyme tiré de la liste combinée.

**Sources des données :**
- Dictionnaire de genre construit à partir du Fichier des prénoms de l'INSEE (Licence Ouverte 2.0 / Etalab) et des données de la bibliothèque de pseudonymes
- ~470 prénoms masculins, ~457 prénoms féminins, ~18 prénoms épicènes
- Couverture : ≥90 % des prénoms français courants

**Aucune configuration nécessaire :** l'attribution selon le genre est automatique et fonctionne avec tous les thèmes de pseudonymes (neutral, star_wars, lotr).

---

## Résolution de problèmes

### Base de données introuvable

**Erreur :** `Database file not found: mappings.db`

**Solution :** exécutez `gdpr-pseudo init` pour créer une nouvelle base de données.

### Mot de passe incorrect

**Erreur :** `Incorrect passphrase. Please check your passphrase and try again.`

**Solution :**
- Vérifiez que vous utilisez le bon mot de passe
- En cas d'oubli, la base de données ne peut pas être récupérée
- Créez une nouvelle base avec `gdpr-pseudo init --force`

### Mot de passe dans le fichier de configuration

**Erreur :** `Passphrase in config file is forbidden for security`

**Solution :** supprimez le champ `passphrase` du fichier de configuration. Utilisez plutôt :
- La variable d'environnement : `export GDPR_PSEUDO_PASSPHRASE="votre_mot_de_passe"`
- La saisie interactive (par défaut)
- L'option en ligne de commande : `--passphrase` (déconseillé pour la sécurité)

### Thème non reconnu

**Erreur :** `Invalid theme 'xyz' is not recognized`

**Solution :** utilisez l'un des thèmes disponibles : `neutral`, `star_wars`, `lotr`

### Erreurs de permissions

**Erreur :** `Permission denied: cannot access file`

**Solution :**
- Vérifiez les permissions du fichier avec `ls -la`
- Assurez-vous de disposer des droits de lecture et d'écriture
- Sous Windows, fermez les applications qui utilisent le fichier

### Corruption de la base de données

**Erreur :** `Database may be corrupted`

**Solution :**
1. Restaurez une sauvegarde si vous en avez une
2. Essayez d'exporter les données récupérables avec `gdpr-pseudo export`
3. Créez une nouvelle base avec `gdpr-pseudo init --force`

### Problèmes de mémoire sur les gros lots

**Symptôme :** le traitement ralentit ou plante sur de grands répertoires

**Solution :**
- Traitez les fichiers par lots plus petits
- Utilisez `--limit` pour ne traiter qu'un sous-ensemble
- Fermez les autres applications pour libérer de la mémoire

---

## Codes de sortie

| Code | Signification |
|------|---------------|
| 0 | Succès |
| 1 | Erreur utilisateur (entrée non valide, fichier introuvable) |
| 2 | Erreur système (exception inattendue) |

---

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `GDPR_PSEUDO_PASSPHRASE` | Mot de passe de la base de données (pour l'automatisation) |

---

## Documentation associée

- [Guide d'installation](installation.md) — Instructions d'installation pour toutes les plateformes
- [Tutoriel](tutorial.md) — Guide d'utilisation pas à pas
- [FAQ](faq.md) — Questions fréquentes
- [Résolution de problèmes](troubleshooting.md) — Référence des erreurs et solutions
