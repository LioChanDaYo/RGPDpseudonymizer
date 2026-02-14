# Guide d'utilisation

**GDPR Pseudonymizer** - Tutoriels pas à pas pour les workflows courants.

---

## Tutoriel 1 : Pseudonymisation d'un document unique (5 minutes)

Découvrez les bases en pseudonymisant un document français.

### Étape 1 : Créer un document de test

Créez un fichier contenant du texte français avec des informations personnelles :

```bash
echo "Marie Dubois travaille a Paris pour Acme SA. Elle collabore avec Jean Martin de Lyon." > interview.txt
```

**Entités présentes dans ce texte :**
- **PERSON** : Marie Dubois, Jean Martin
- **LOCATION** : Paris, Lyon
- **ORGANIZATION** : Acme SA

### Étape 2 : Définir votre mot de passe

L'outil chiffre tous les appariements d'entités. Définissez un mot de passe (minimum 12 caractères) :

**Windows (PowerShell) :**
```powershell
$env:GDPR_PSEUDO_PASSPHRASE = "MySecurePassphrase123"
```

**macOS/Linux :**
```bash
export GDPR_PSEUDO_PASSPHRASE="MySecurePassphrase123"
```

**Important :** Stockez ce mot de passe en sécurité. Sans lui, vous ne pourrez pas inverser la pseudonymisation.

### Étape 3 : Lancer la pseudonymisation

```bash
poetry run gdpr-pseudo process interview.txt
```

Vous accédez au **processus de validation interactif** - voir [Présentation de l'interface de validation](#presentation-de-linterface-de-validation) ci-dessous.

### Étape 4 : Examiner le résultat

Après validation, vérifiez le fichier pseudonymisé :

```bash
cat interview_pseudonymized.txt
```

**Exemple de résultat (avec thème neutre) :**
```
Sophie Martin travaille a Marseille pour TechnoPlus SARL. Elle collabore avec Pierre Laurent de Bordeaux.
```

### Étape 5 : Consulter la base de données de correspondance

Visualisez les appariements d'entités stockés dans la base de données chiffrée :

```bash
poetry run gdpr-pseudo list-mappings
```

---

## Tutoriel 2 : Traitement par lot de plusieurs documents

Traitez plusieurs documents en garantissant la cohérence des pseudonymes dans tous les fichiers.

### Étape 1 : Créer des documents de test

```bash
mkdir documents
echo "Marie Dubois est directrice chez Acme SA." > documents/doc1.txt
echo "Jean Martin collabore avec Marie Dubois a Paris." > documents/doc2.txt
echo "Acme SA organise une reunion a Lyon avec Marie Dubois." > documents/doc3.txt
```

### Étape 2 : Initialiser la base de données

```bash
poetry run gdpr-pseudo init --db project.db
```

Saisissez un mot de passe quand vous y êtes invité (ou utilisez la variable d'environnement).

### Étape 3 : Traiter tous les documents

```bash
poetry run gdpr-pseudo batch documents/ --db project.db -o output/
```

**Déroulement :**
- Chaque document suit le processus de validation
- Les mêmes entités reçoivent les **mêmes pseudonymes** dans tous les documents
- Une barre de progression affiche l'état d'avancement

### Étape 4 : Vérifier la cohérence

```bash
cat output/doc1_pseudonymized.txt
cat output/doc2_pseudonymized.txt
cat output/doc3_pseudonymized.txt
```

« Marie Dubois » doit avoir le même pseudonyme dans les trois documents.

### Étape 5 : Visualiser les statistiques

```bash
poetry run gdpr-pseudo stats --db project.db
```

Affiche les comptes d'entités, les thèmes utilisés et l'historique du traitement.

### Filtrer par type d'entité

Si vous ne devez pseudonymiser que certains types d'entités, utilisez l'option `--entity-types` :

```bash
# Traiter uniquement les entités PERSON (ignorer LOCATION et ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON

# Traiter les entités PERSON et LOCATION (ignorer ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON,LOCATION
```

Ceci est utile quand :
- Vous devez uniquement masquer les noms de personnes mais conserver les vraies localités
- Vous souhaitez traiter les types d'entités en plusieurs passes pour plus d'efficacité de révision
- Vos documents contiennent de nombreuses détections ORG superflues que vous désirez ignorer

L'option `--entity-types` fonctionne également avec la commande `process` pour les documents uniques.

---

## Tutoriel 3 : Utiliser des fichiers de configuration

Créez un fichier de configuration pour définir les options par défaut.

### Étape 1 : Générer un modèle de configuration

```bash
poetry run gdpr-pseudo config --init
```

Cela crée `.gdpr-pseudo.yaml` dans le répertoire courant.

### Étape 2 : Modifier la configuration

Ouvrez `.gdpr-pseudo.yaml` et personnalisez-le :

```yaml
database:
  path: project_mappings.db

pseudonymization:
  theme: star_wars    # neutral | star_wars | lotr
  model: spacy

batch:
  workers: 4          # 1-8 (utiliser 1 pour validation interactif)
  output_dir: pseudonymized_output

logging:
  level: INFO
```

### Étape 3 : Afficher la configuration effective

```bash
poetry run gdpr-pseudo config
```

Affiche la configuration fusionnée depuis toutes les sources.

### Étape 4 : Mettre à jour la configuration par CLI

Changez les paramètres sans éditer le fichier :

```bash
# Changer le thème
poetry run gdpr-pseudo config set pseudonymization.theme lotr

# Changer le chemin de la base de données
poetry run gdpr-pseudo config set database.path my_mappings.db

# Visualiser la configuration mise à jour
poetry run gdpr-pseudo config
```

### Priorité de la configuration

Les paramètres sont appliqués dans cet ordre (priorité décroissante) :

1. Options de la ligne de commande (ex. `--theme star_wars`)
2. Fichier de configuration personnalisé (`--config /path/to/config.yaml`)
3. Configuration du projet (`./.gdpr-pseudo.yaml`)
4. Configuration personnelle (`~/.gdpr-pseudo.yaml`)
5. Valeurs par défaut

**Exemple :** L'option CLI remplace le fichier de configuration :
```bash
# Utilise le thème lotr même si la config indique neutre
poetry run gdpr-pseudo process doc.txt --theme lotr
```

---

## Tutoriel 4 : Choisir un thème de pseudonymes

Comparez les trois thèmes disponibles pour sélectionner le plus approprié à votre cas d'usage.

### Comparaison des thèmes

| Type d'entité | Neutre | Star Wars | Seigneur des anneaux |
|-------------|---------|-----------|-------------------|
| **PERSON** | Sophie Martin | Leia Organa | Arwen Evenstar |
| **LOCATION** | Marseille | Coruscant | Rivendell |
| **ORGANIZATION** | TechnoPlus SARL | Rebel Alliance | House of Elrond |

### Thème neutre (par défaut)

Idéal pour : Documents professionnels, conformité légale, résultats réalistes.

```bash
poetry run gdpr-pseudo process doc.txt --theme neutral
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Résultat : Sophie Martin travaille a Marseille pour TechnoPlus SARL.
```

**Caractéristiques :**
- Noms à consonance française
- Vraies villes et régions françaises
- Noms de sociétés réalistes avec suffixes appropriés (SA, SARL, SAS)

### Thème Star Wars

Idéal pour : Identification facile du contenu pseudonymisé, tests amusants.

```bash
poetry run gdpr-pseudo process doc.txt --theme star_wars
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Résultat : Leia Organa travaille a Coruscant pour Rebel Alliance.
```

**Caractéristiques :**
- Noms de personnages emblématiques de Star Wars
- Planètes et lieux de l'univers Star Wars
- Factions et organisations (Rebel Alliance, Galactic Empire, etc.)

### Thème Seigneur des anneaux

Idéal pour : Projets littéraires, pseudonymisation distinctive, amateurs de fantasy.

```bash
poetry run gdpr-pseudo process doc.txt --theme lotr
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Résultat : Arwen Evenstar travaille a Rivendell pour House of Elrond.
```

**Caractéristiques :**
- Personnages du Monde du Milieu de Tolkien
- Localités : Rivendell, Gondor, La Comté, etc.
- Organisations : Royaumes, maisons et alliances

### Changer de thème

**Important :** Une fois que vous avez traité des documents avec un thème, conservez-le pour la cohérence. Changer de thème en cours de projet crée des pseudonymes incohérents.

Si vous devez vraiment le faire :
```bash
# Créer une nouvelle base de données pour le nouveau thème
poetry run gdpr-pseudo init --db star_wars_project.db --force
poetry run gdpr-pseudo batch documents/ --db star_wars_project.db --theme star_wars
```

---

## Présentation de l'interface de validation

Chaque document passe par une validation interactif afin de garantir une précision optimale.

### L'écran de validation

Lors du traitement d'un document, vous voyez :

```
================================================================================
Entity Validation Session
================================================================================
Total entities detected: 5
Unique entities to validate: 3 (2 duplicates grouped)

Processing entity 1 of 3
--------------------------------------------------------------------------------
Entity: Marie Dubois
Type: PERSON (detected by spaCy NER)
Confidence: High (92%)

Context:
  "...travaille avec Marie Dubois depuis trois ans. Elle dirige..."
                      ^^^^^^^^^^^^

Proposed pseudonym: [Sophie Martin] (theme: neutral)
--------------------------------------------------------------------------------
[Space] Accept  [R] Reject  [E] Edit  [C] Change pseudonym  [H] Help
```

### Raccourcis clavier

**Actions principales :**
| Touche | Action | Description |
|-----|--------|-------------|
| `Space` | Accept | Confirmer l'entité et le pseudonyme |
| `R` | Reject | Marquer comme faux positif (conserver l'original) |
| `E` | Edit | Modifier le texte de l'entité |
| `A` | Add | Ajouter manuellement une entité oubliée |
| `C` | Change | Choisir un pseudonyme différent |

**Navigation :**
| Touche | Action | Description |
|-----|--------|-------------|
| `N` / `Right Arrow` | Next | Aller à l'entité suivante |
| `P` / `Left Arrow` | Previous | Aller à l'entité précédente |
| `X` | Cycle contexts | Afficher les autres occurrences de l'entité |
| `Q` | Quit | Quitter la validation (avec confirmation) |

**Actions groupées (masquées - appuyez sur H pour voir) :**
| Touche | Action | Description |
|-----|--------|-------------|
| `Shift+A` | Accept All Type | Accepter toutes les entités du type actuel |
| `Shift+R` | Reject All Type | Rejeter toutes les entités du type actuel |

**Aide :**
| Touche | Action |
|-----|--------|
| `H` / `?` | Afficher l'écran d'aide (affiche tous les raccourcis y compris les actions groupées) |

### Regroupement des variantes

L'interface de validation regroupe automatiquement les formes connexes d'une entité en un seul élément de validation. Par exemple, si un document contient « Marie Dubois », « Pr. Dubois » et « Dubois », ils sont présentés comme un seul élément :

```
Entity: Marie Dubois
Type: PERSON
Also appears as: Pr. Dubois, Dubois
```

Accepter ou rejeter cet élément applique la décision à toutes les formes variantes. Cela réduit la fatigue de validation lorsque les documents utilisent plusieurs formes pour désigner la même personne (titres, noms de famille, abréviations).

### Processus de validation

1. **Écran récapitulatif :** Voir les comptes d'entités par type (PERSON, LOCATION, ORG)
2. **Examiner les entités :** Parcourez chaque entité avec contexte (variantes regroupées)
3. **Prendre des décisions :** Accepter, rejeter, modifier ou changer le pseudonyme
4. **Confirmation finale :** Examiner le résumé des modifications
5. **Traiter le document :** Pseudonymisation appliquée

### Conseils pour une validation efficace

1. **Appuyez sur H pour tous les raccourcis :** De nombreux raccourcis (comme Shift+A/Shift+R) ne sont pas affichés sur l'écran principal
2. **Utilisez les actions groupées :** Appuyez sur `Shift+A` pour accepter toutes les entités PERSON si elles semblent correctes
3. **Faites défiler les contextes :** Appuyez sur `X` pour voir toutes les occurrences d'une entité avant de décider
4. **Faites confiance aux hautes confiances :** Les entités avec >90% de confiance sont généralement correctes
5. **Examinez les basses confiances :** Les scores jaunes/rouges exigent un examen prudent

---

## Workflows courants

### Recherche académique : Transcriptions d'entretiens

```bash
# Configurer le projet
export GDPR_PSEUDO_PASSPHRASE="AcademicResearch2026!"
poetry run gdpr-pseudo init --db research_project.db

# Traiter tous les entretiens
poetry run gdpr-pseudo batch interviews/ --db research_project.db -o anonymized/

# Exporter le journal d'audit pour le comité d'éthique
poetry run gdpr-pseudo export audit_log.json --db research_project.db

# Partager les fichiers anonymisés (garder mappings.db sécurisé !)
```

### Ressources humaines : Retours d'employés

```bash
# Pseudonymiser pour analyse ChatGPT
poetry run gdpr-pseudo process feedback_report.txt --theme star_wars

# Télécharger la version pseudonymisée sur ChatGPT
# Analyser la sortie (références « Luke Skywalker » au lieu de vrais noms)
# Remapper les perspectives en utilisant list-mappings
poetry run gdpr-pseudo list-mappings --search "Luke"
```

### Domaine juridique : Préparation de documents judiciaires

```bash
# Initialiser avec un mot de passe robuste
poetry run gdpr-pseudo init --db case_12345.db

# Traiter les documents du dossier
poetry run gdpr-pseudo batch case_documents/ --db case_12345.db --theme neutral

# Exporter les appariements comme référence
poetry run gdpr-pseudo list-mappings --db case_12345.db --export mappings.csv
```

---

## Tutoriel 5 : Gérer les appariements

Examinez et gérez vos appariements d'entités vers pseudonymes.

### Valider les appariements existants

Examinez les appariements stockés sans traiter de documents :

```bash
# Afficher tous les appariements avec métadonnées
poetry run gdpr-pseudo validate-mappings

# Mode examen interactif
poetry run gdpr-pseudo validate-mappings --interactive

# Filtrer par type d'entité
poetry run gdpr-pseudo validate-mappings --type PERSON
```

### Importer les appariements d'un autre projet

Combinez les appariements de plusieurs bases de données :

```bash
# Importer de l'ancien projet vers le nouveau
poetry run gdpr-pseudo import-mappings old_project.db --db new_project.db

# Demander confirmation pour chaque doublon (au lieu de passer automatiquement)
poetry run gdpr-pseudo import-mappings old_project.db --prompt-duplicates
```

### Détruire une base de données de manière sécurisée

Quand un projet est terminé et les appariements ne sont plus nécessaires :

```bash
# Destruction interactif (plus sûr - demande confirmation et mot de passe)
poetry run gdpr-pseudo destroy-table --db project.db

# Forcer la destruction (ignore la confirmation, vérifie toujours le mot de passe)
poetry run gdpr-pseudo destroy-table --db project.db --force
```

**Fonctionnalités de sécurité :**
- Vérification du mot de passe prévient une suppression accidentelle de mauvaise base de données
- Vérification du numéro magique SQLite prévient la suppression de fichiers non-base de données
- Protection contre les symlinks prévient les attaques par redirection
- Nettoyage sécurisé 3 passes écrase les données avant la suppression du fichier

---

## Conseils et bonnes pratiques

### Sécurité

1. **Utilisez des variables d'environnement pour les phrases de passe** plutôt que l'option `--passphrase` (qui apparaît dans l'historique du shell)
2. **Stockez les bases de données de correspondance séparément** des documents pseudonymisés — la combinaison permet la réidentification
3. **Utilisez des phrases de passe robustes** (12+ caractères, mélange de lettres, chiffres, symboles)
4. **Sauvegardez votre base de données de correspondance** avant les opérations par lot — vous ne pouvez pas inverser la pseudonymisation sans elle

### Efficacité du workflow

1. **Appuyez sur H lors de la validation** pour voir tous les raccourcis clavier (les actions groupées sont masquées par défaut)
2. **Utilisez l'acceptation/rejet groupés** (`Shift+A` / `Shift+R`) pour les types d'entités où la détection est fiable
3. **Traitez d'abord un petit fichier de test** pour vérifier les paramètres avant de lancer des tâches par lot
4. **Utilisez la même base de données** pour tous les documents connexes afin de garantir la cohérence des pseudonymes
5. **Choisissez votre thème à l'avance** — changer de thème en cours de projet crée des pseudonymes incohérents

### Organisation

1. **Une base de données par projet** — conservez des bases de données de correspondance séparées pour les projets non-connexes
2. **Utilisez `--output` ou `-o`** pour garder les fichiers pseudonymisés dans un répertoire séparé
3. **Exportez régulièrement les journaux d'audit** pour la documentation de conformité : `poetry run gdpr-pseudo export audit.json`
4. **Utilisez la commande `stats`** pour surveiller l'historique du traitement et les comptes d'entités

### Limitations connues

- **Français uniquement** — pas d'autres langues en v1.0
- **Formats texte uniquement** — `.txt` et `.md` (pas de PDF/DOCX)
- **Validation obligatoire** — chaque entité doit être examinée (détection IA ~60 % F1)
- **Le mot de passe est irrécupérable** — si perdu, les appariements existants ne peuvent pas être déchiffrés

---

## Dépannage

### Aucune entité détectée

**Cause :** Le document peut ne pas contenir de texte français reconnaissable.

**Solutions :**
1. Assurez-vous que le texte est en français avec encodage approprié (UTF-8)
2. Vérifiez la présence de noms français, de localités ou d'organisations
3. Vérifiez que le fichier est au format `.txt` ou `.md`

### Pseudonymes incohérents dans les documents

**Cause :** Utilisation de fichiers de base de données différents.

**Solution :** Spécifiez toujours la même base de données :
```bash
poetry run gdpr-pseudo process doc1.txt --db shared.db
poetry run gdpr-pseudo process doc2.txt --db shared.db
```

### L'interface de validation ne répond pas

**Cause :** Problème de compatibilité du terminal.

**Solutions :**
1. Utilisez un terminal standard (PowerShell, Terminal.app, bash)
2. Évitez d'exécuter dans des terminaux d'IDE (peuvent avoir des problèmes d'entrée)
3. Essayez `poetry shell` puis exécutez la commande directement

### Phrase de passe oubliée

**Conséquence :** Impossible d'accéder aux appariements existants ou d'inverser la pseudonymisation.

**Solution :** Créer une nouvelle base de données (les appariements précédents sont perdus) :
```bash
poetry run gdpr-pseudo init --force
```

---

## Étapes suivantes

- [Référence CLI](CLI-REFERENCE.md) - Documentation complète des commandes
- [Guide d'installation](installation.md) - Instructions de configuration détaillées
- [FAQ](faq.md) - Questions et réponses courantes
- [Guide de dépannage](troubleshooting.md) - Référence d'erreurs complète
