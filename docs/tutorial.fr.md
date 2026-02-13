# Tutoriel d'utilisation

**GDPR Pseudonymizer** - Tutoriels pas-à-pas pour les flux de travail courants.

---

## Tutoriel 1 : Pseudonymisation d'un document unique (5 minutes)

Apprenez les bases en pseudonymisant un document en français.

### Étape 1 : Créer un document de test

Créez un fichier contenant du texte en français avec des informations personnelles :

```bash
echo "Marie Dubois travaille a Paris pour Acme SA. Elle collabore avec Jean Martin de Lyon." > interview.txt
```

**Entités présentes dans ce texte :**
- **PERSON :** Marie Dubois, Jean Martin
- **LOCATION :** Paris, Lyon
- **ORGANIZATION :** Acme SA

### Étape 2 : Définir votre phrase de passe

L'outil chiffre toutes les correspondances d'entités. Définissez une phrase de passe (12 caractères minimum) :

**Windows (PowerShell) :**
```powershell
$env:GDPR_PSEUDO_PASSPHRASE = "MySecurePassphrase123"
```

**macOS/Linux :**
```bash
export GDPR_PSEUDO_PASSPHRASE="MySecurePassphrase123"
```

**Important :** Conservez cette phrase de passe en lieu sûr. Sans elle, vous ne pourrez pas inverser la pseudonymisation.

### Étape 3 : Lancer la pseudonymisation

```bash
poetry run gdpr-pseudo process interview.txt
```

Vous entrerez dans le **flux de validation interactif** — voir la section [Présentation de l'interface de validation](#presentation-de-linterface-de-validation) ci-dessous.

### Étape 4 : Examiner le résultat

Après la validation, consultez le fichier pseudonymisé :

```bash
cat interview_pseudonymized.txt
```

**Exemple de sortie (avec le thème neutre) :**
```
Sophie Martin travaille a Marseille pour TechnoPlus SARL. Elle collabore avec Pierre Laurent de Bordeaux.
```

### Étape 5 : Consulter la base de correspondances

Affichez les correspondances d'entités stockées dans la base de données chiffrée :

```bash
poetry run gdpr-pseudo list-mappings
```

---

## Tutoriel 2 : Traitement par lots de plusieurs documents

Traitez plusieurs documents avec des pseudonymes cohérents entre tous les fichiers.

### Étape 1 : Créer les documents de test

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

Saisissez une phrase de passe lorsque demandé (ou utilisez la variable d'environnement).

### Étape 3 : Traiter tous les documents

```bash
poetry run gdpr-pseudo batch documents/ --db project.db -o output/
```

**Ce qui se passe :**
- Chaque document entre dans le flux de validation
- Les mêmes entités reçoivent les **mêmes pseudonymes** dans tous les documents
- Une barre de progression affiche l'état d'avancement

### Étape 4 : Vérifier la cohérence

```bash
cat output/doc1_pseudonymized.txt
cat output/doc2_pseudonymized.txt
cat output/doc3_pseudonymized.txt
```

« Marie Dubois » devrait avoir le même pseudonyme dans les trois documents.

### Étape 5 : Afficher les statistiques

```bash
poetry run gdpr-pseudo stats --db project.db
```

Affiche le nombre d'entités, les thèmes utilisés et l'historique de traitement.

### Filtrage par type d'entité

Si vous n'avez besoin de pseudonymiser que certains types d'entités, utilisez l'option `--entity-types` :

```bash
# Traiter uniquement les entités PERSON (ignorer LOCATION et ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON

# Traiter les entités PERSON et LOCATION (ignorer ORG)
poetry run gdpr-pseudo batch documents/ --db project.db --entity-types PERSON,LOCATION
```

Cela est utile lorsque :
- Vous souhaitez uniquement anonymiser les noms de personnes tout en conservant les vrais lieux
- Vous voulez traiter les types d'entités en passes séparées pour faciliter la relecture
- Vos documents contiennent de nombreuses détections d'ORG non pertinentes que vous souhaitez ignorer

L'option `--entity-types` fonctionne également avec la commande `process` pour les documents individuels.

---

## Tutoriel 3 : Utiliser les fichiers de configuration

Créez un fichier de configuration pour définir les options par défaut.

### Étape 1 : Générer un modèle de configuration

```bash
poetry run gdpr-pseudo config --init
```

Cela crée le fichier `.gdpr-pseudo.yaml` dans le répertoire courant.

### Étape 2 : Modifier la configuration

Ouvrez `.gdpr-pseudo.yaml` et personnalisez-le :

```yaml
database:
  path: project_mappings.db

pseudonymization:
  theme: star_wars    # neutral | star_wars | lotr
  model: spacy

batch:
  workers: 4          # 1-8 (utiliser 1 pour la validation interactive)
  output_dir: pseudonymized_output

logging:
  level: INFO
```

### Étape 3 : Afficher la configuration effective

```bash
poetry run gdpr-pseudo config
```

Affiche la configuration fusionnée de toutes les sources.

### Étape 4 : Modifier la configuration via la CLI

Modifiez les paramètres sans éditer le fichier :

```bash
# Changer le thème
poetry run gdpr-pseudo config set pseudonymization.theme lotr

# Changer le chemin de la base de données
poetry run gdpr-pseudo config set database.path my_mappings.db

# Afficher la configuration mise à jour
poetry run gdpr-pseudo config
```

### Priorité de la configuration

Les paramètres sont appliqués dans cet ordre (de la priorité la plus haute à la plus basse) :

1. Options de la CLI (ex. : `--theme star_wars`)
2. Fichier de configuration personnalisé (`--config /path/to/config.yaml`)
3. Configuration du projet (`./.gdpr-pseudo.yaml`)
4. Configuration du répertoire personnel (`~/.gdpr-pseudo.yaml`)
5. Valeurs par défaut

**Exemple :** Une option de la CLI prend le pas sur le fichier de configuration :
```bash
# Utilise le thème lotr même si la configuration indique neutral
poetry run gdpr-pseudo process doc.txt --theme lotr
```

---

## Tutoriel 4 : Choisir un thème de pseudonymes

Comparez les trois thèmes disponibles pour choisir celui qui convient le mieux à votre cas d'utilisation.

### Comparaison des thèmes

| Type d'entité | Neutre | Star Wars | Le Seigneur des Anneaux |
|---------------|--------|-----------|--------------------------|
| **PERSON** | Sophie Martin | Leia Organa | Arwen Evenstar |
| **LOCATION** | Marseille | Coruscant | Rivendell |
| **ORGANIZATION** | TechnoPlus SARL | Rebel Alliance | House of Elrond |

### Thème neutre (par défaut)

Idéal pour : documents professionnels, conformité juridique, rendu réaliste.

```bash
poetry run gdpr-pseudo process doc.txt --theme neutral
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Sortie :  Sophie Martin travaille a Marseille pour TechnoPlus SARL.
```

**Caractéristiques :**
- Noms à consonance française
- Vraies villes et régions françaises
- Noms d'entreprises réalistes avec les suffixes appropriés (SA, SARL, SAS)

### Thème Star Wars

Idéal pour : identification facile du contenu pseudonymisé, tests ludiques.

```bash
poetry run gdpr-pseudo process doc.txt --theme star_wars
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Sortie :  Leia Organa travaille a Coruscant pour Rebel Alliance.
```

**Caractéristiques :**
- Noms de personnages emblématiques de Star Wars
- Planètes et lieux de l'univers Star Wars
- Factions et organisations (Rebel Alliance, Galactic Empire, etc.)

### Thème Le Seigneur des Anneaux

Idéal pour : projets littéraires, pseudonymisation distinctive, passionnés de fantasy.

```bash
poetry run gdpr-pseudo process doc.txt --theme lotr
```

**Exemple de transformation :**
```
Entrée :  Marie Dubois travaille a Paris pour Acme SA.
Sortie :  Arwen Evenstar travaille a Rivendell pour House of Elrond.
```

**Caractéristiques :**
- Personnages de la Terre du Milieu de Tolkien
- Lieux : Rivendell, Gondor, The Shire, etc.
- Organisations : royaumes, maisons et alliances

### Changer de thème

**Important :** Une fois que vous avez traité des documents avec un thème, conservez-le pour garantir la cohérence. Changer de thème en cours de projet entraîne des pseudonymes incohérents.

Si vous devez changer :
```bash
# Créer une nouvelle base de données pour le nouveau thème
poetry run gdpr-pseudo init --db star_wars_project.db --force
poetry run gdpr-pseudo batch documents/ --db star_wars_project.db --theme star_wars
```

---

## Présentation de l'interface de validation

Chaque document passe par une validation interactive pour garantir une précision de 100 %.

### L'écran de validation

Lorsque vous traitez un document, vous verrez :

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
|--------|--------|-------------|
| `Space` | Accepter | Confirmer l'entité et le pseudonyme |
| `R` | Rejeter | Marquer comme faux positif (conserver l'original) |
| `E` | Éditer | Modifier le texte de l'entité |
| `A` | Ajouter | Ajouter manuellement une entité manquée |
| `C` | Changer | Choisir un autre pseudonyme |

**Navigation :**
| Touche | Action | Description |
|--------|--------|-------------|
| `N` / `Right Arrow` | Suivant | Aller à l'entité suivante |
| `P` / `Left Arrow` | Précédent | Aller à l'entité précédente |
| `X` | Parcourir les contextes | Afficher les autres occurrences de l'entité |
| `Q` | Quitter | Quitter la validation (avec confirmation) |

**Opérations par lots (masquées — appuyez sur H pour les afficher) :**
| Touche | Action | Description |
|--------|--------|-------------|
| `Shift+A` | Accepter tout le type | Accepter toutes les entités du type courant |
| `Shift+R` | Rejeter tout le type | Rejeter toutes les entités du type courant |

**Aide :**
| Touche | Action |
|--------|--------|
| `H` / `?` | Afficher le panneau d'aide (affiche tous les raccourcis, y compris les opérations par lots) |

### Regroupement des variantes d'entités

L'interface de validation regroupe automatiquement les formes apparentées d'une entité en un seul élément de validation. Par exemple, si un document contient « Marie Dubois », « Pr. Dubois » et « Dubois », ceux-ci sont affichés comme un seul élément :

```
Entity: Marie Dubois
Type: PERSON
Also appears as: Pr. Dubois, Dubois
```

Accepter ou rejeter cet élément applique la décision à toutes les formes variantes. Cela réduit la fatigue de validation lorsque les documents utilisent plusieurs formes pour désigner la même personne (titres, noms de famille, abréviations).

### Flux de validation

1. **Écran récapitulatif :** Nombre d'entités par type (PERSON, LOCATION, ORG)
2. **Examen des entités :** Passage en revue de chaque entité avec son contexte (variantes regroupées)
3. **Prise de décisions :** Accepter, rejeter, éditer ou changer le pseudonyme
4. **Confirmation finale :** Résumé des modifications apportées
5. **Traitement du document :** Application de la pseudonymisation

### Conseils pour une validation efficace

1. **Appuyez sur H pour voir tous les raccourcis :** De nombreux raccourcis (comme Shift+A/Shift+R) ne sont pas affichés sur l'écran principal
2. **Utilisez les opérations par lots :** Appuyez sur `Shift+A` pour accepter toutes les entités PERSON si elles semblent correctes
3. **Parcourez les contextes :** Appuyez sur `X` pour voir toutes les occurrences d'une entité avant de décider
4. **Faites confiance aux scores élevés :** Les entités avec un score de confiance > 90 % sont généralement correctes
5. **Examinez les scores faibles :** Les scores de confiance en jaune ou rouge nécessitent un examen attentif

---

## Flux de travail courants

### Recherche universitaire : transcriptions d'entretiens

```bash
# Mise en place du projet
export GDPR_PSEUDO_PASSPHRASE="AcademicResearch2026!"
poetry run gdpr-pseudo init --db research_project.db

# Traiter tous les entretiens
poetry run gdpr-pseudo batch interviews/ --db research_project.db -o anonymized/

# Exporter le journal d'audit pour le comité d'éthique
poetry run gdpr-pseudo export audit_log.json --db research_project.db

# Partager les fichiers anonymisés (gardez le fichier mappings.db en sécurité !)
```

### Analyse RH : retours d'employés

```bash
# Pseudonymiser pour une analyse par ChatGPT
poetry run gdpr-pseudo process feedback_report.txt --theme star_wars

# Téléverser la version pseudonymisée vers ChatGPT
# Analyser le résultat (références à "Luke Skywalker" au lieu des vrais noms)
# Retrouver les correspondances via list-mappings
poetry run gdpr-pseudo list-mappings --search "Luke"
```

### Juridique : préparation de documents pour un dossier

```bash
# Initialiser avec une phrase de passe robuste
poetry run gdpr-pseudo init --db case_12345.db

# Traiter les documents du dossier
poetry run gdpr-pseudo batch case_documents/ --db case_12345.db --theme neutral

# Exporter les correspondances pour référence
poetry run gdpr-pseudo list-mappings --db case_12345.db --export mappings.csv
```

---

## Tutoriel 5 : Gestion des correspondances

Consultez et gérez vos correspondances entité-pseudonyme.

### Valider les correspondances existantes

Passez en revue les correspondances stockées sans traiter de documents :

```bash
# Afficher toutes les correspondances avec les métadonnées
poetry run gdpr-pseudo validate-mappings

# Mode de révision interactif
poetry run gdpr-pseudo validate-mappings --interactive

# Filtrer par type d'entité
poetry run gdpr-pseudo validate-mappings --type PERSON
```

### Importer des correspondances depuis un autre projet

Combinez les correspondances de plusieurs bases de données :

```bash
# Importer de l'ancien projet vers le nouveau
poetry run gdpr-pseudo import-mappings old_project.db --db new_project.db

# Demander confirmation pour chaque doublon (au lieu de l'ignorer automatiquement)
poetry run gdpr-pseudo import-mappings old_project.db --prompt-duplicates
```

### Détruire une base de données de manière sécurisée

Lorsqu'un projet est terminé et que les correspondances ne sont plus nécessaires :

```bash
# Destruction interactive (le plus sûr — demande confirmation et phrase de passe)
poetry run gdpr-pseudo destroy-table --db project.db

# Destruction forcée (saute la confirmation, vérifie toujours la phrase de passe)
poetry run gdpr-pseudo destroy-table --db project.db --force
```

**Fonctionnalités de sécurité :**
- Vérification de la phrase de passe pour éviter la suppression accidentelle de la mauvaise base de données
- Vérification du nombre magique SQLite pour empêcher la suppression de fichiers qui ne sont pas des bases de données
- Protection contre les liens symboliques pour prévenir les attaques par redirection
- Effacement sécurisé en 3 passes : les données sont écrasées avant la suppression du fichier

---

## Conseils et bonnes pratiques

### Sécurité

1. **Utilisez des variables d'environnement pour les phrases de passe** plutôt que l'option `--passphrase` (qui apparaît dans l'historique du shell)
2. **Stockez les bases de correspondances séparément** des documents pseudonymisés — la combinaison des deux permet la ré-identification
3. **Utilisez des phrases de passe robustes** (12 caractères minimum, mélange de lettres, chiffres et symboles)
4. **Sauvegardez votre base de correspondances** avant les opérations par lots — vous ne pouvez pas inverser la pseudonymisation sans elle

### Efficacité du flux de travail

1. **Appuyez sur H pendant la validation** pour voir tous les raccourcis clavier (les opérations par lots sont masquées par défaut)
2. **Utilisez les acceptations/rejets par lots** (`Shift+A` / `Shift+R`) pour les types d'entités où la détection est fiable
3. **Traitez d'abord un petit fichier de test** pour vérifier les paramètres avant de lancer un traitement par lots
4. **Utilisez la même base de données** pour tous les documents liés afin de garantir des pseudonymes cohérents
5. **Choisissez votre thème dès le départ** — changer de thème en cours de projet entraîne des pseudonymes incohérents

### Organisation

1. **Une base de données par projet** — conservez des bases de correspondances séparées pour les projets sans lien entre eux
2. **Utilisez `--output` ou `-o`** pour placer les fichiers pseudonymisés dans un répertoire distinct
3. **Exportez régulièrement les journaux d'audit** pour la documentation de conformité : `poetry run gdpr-pseudo export audit.json`
4. **Utilisez la commande `stats`** pour suivre l'historique de traitement et le nombre d'entités

### Limitations connues

- **Français uniquement** — aucune autre langue dans la version 1.0
- **Formats texte uniquement** — `.txt` et `.md` (pas de PDF/DOCX)
- **La validation est obligatoire** — chaque entité doit être examinée (le rappel de la détection IA est d'environ 40-50 %)
- **La phrase de passe est irrécupérable** — en cas de perte, les correspondances existantes ne peuvent pas être déchiffrées

---

## Dépannage

### Aucune entité détectée

**Cause :** Le document ne contient peut-être pas de texte en français reconnaissable.

**Solutions :**
1. Vérifiez que le texte est en français avec un encodage correct (UTF-8)
2. Vérifiez la présence de noms français, de lieux ou d'organisations
3. Assurez-vous que le fichier est au format `.txt` ou `.md`

### Pseudonymes incohérents entre les documents

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
2. Évitez l'exécution dans les terminaux intégrés aux IDE (ils peuvent avoir des problèmes de saisie)
3. Essayez `poetry shell` puis lancez la commande directement

### Phrase de passe oubliée

**Conséquence :** Impossible d'accéder aux correspondances existantes ou d'inverser la pseudonymisation.

**Solution :** Créez une nouvelle base de données (les correspondances précédentes sont perdues) :
```bash
poetry run gdpr-pseudo init --force
```

---

## Étapes suivantes

- [Référence CLI](CLI-REFERENCE.md) - Documentation complète des commandes
- [Guide d'installation](installation.fr.md) - Instructions détaillées de mise en place
- [FAQ](faq.fr.md) - Questions fréquentes et réponses
- [Guide de dépannage](troubleshooting.fr.md) - Référence complète des erreurs
