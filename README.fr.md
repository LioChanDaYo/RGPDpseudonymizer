> 🇬🇧 [English](README.md) | 🇫🇷 **Français**

# GDPR Pseudonymizer

[![Version PyPI](https://img.shields.io/pypi/v/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![Versions Python](https://img.shields.io/pypi/pyversions/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![Licence : MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml/badge.svg)](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://liochandayo.github.io/RGPDpseudonymizer/)

**Pseudonymisez vos documents français grâce à l'IA, avec relecture humaine obligatoire**

Préparez vos documents sensibles pour l'analyse par IA en toute sérénité : traitement entièrement local, relecture humaine systématique, conformité RGPD.

---

## Nouveautés de la v2.0

- **Application de bureau** — Interface graphique PySide6 complète avec validation visuelle des entités, glisser-déposer et tableau de bord de progression en temps réel
- **Exécutables autonomes** — Installeur Windows (.exe), DMG macOS (arm64 + Intel) et AppImage Linux — Python non requis
- **Accessibilité WCAG 2.1 niveau AA** — Navigation au clavier, lecteurs d'écran, contrastes 4,5:1, mode contraste élevé
- **Interface française avec changement de langue** — Interface GUI FR/EN complète avec changement de langue en temps réel et détection automatique de la locale système
- **Traitement par lot avec validation par document** — Validation interactive des entités document par document avec navigation Précédent/Suivant
- **Gestion de base de données en arrière-plan** — Interface réactive avec toutes les opérations de base de données sur des threads séparés
- **Renforcement du traitement** — Assainissement des DCP dans les messages d'erreur, gestion typée des exceptions, comptage d'entités par document

<!-- TODO: Ajouter une capture d'écran de l'interface graphique -->

**Mise à jour :** `pip install --upgrade gdpr-pseudonymizer[gui]`

---

## Téléchargement — Exécutables autonomes (sans Python)

Des exécutables autonomes v2.0 pré-compilés sont disponibles pour Windows, macOS et Linux. Aucune installation de Python requise.

**[Télécharger la dernière version](https://github.com/LioChanDaYo/RGPDpseudonymizer/releases/latest)**

| Plateforme | Fichier | Notes |
|------------|---------|-------|
| **Windows** | `gdpr-pseudonymizer-2.0.0-windows-setup.exe` | Lancer l'installeur. Ajoute un raccourci au menu Démarrer. |
| **macOS (Apple Silicon)** | `gdpr-pseudonymizer-2.0.0-macos-arm64.dmg` | Ouvrir le DMG, glisser vers Applications. |
| **macOS (Intel)** | `gdpr-pseudonymizer-2.0.0-macos-x86_64.dmg` | Ouvrir le DMG, glisser vers Applications. |
| **Linux** | `gdpr-pseudonymizer-2.0.0-linux.AppImage` | `chmod +x` puis exécuter. |

### Notes par plateforme

- **Windows :** Si SmartScreen affiche « Windows a protégé votre PC », cliquez sur « Informations complémentaires » puis « Exécuter quand même ». Cela apparaît car l'exécutable n'est pas encore signé numériquement.
- **macOS :** Si Gatekeeper bloque l'application, faites un clic droit sur l'app et sélectionnez « Ouvrir ».
- **Linux :** Rendre le fichier exécutable : `chmod +x gdpr-pseudonymizer-*.AppImage`. Si le lancement échoue, installer les dépendances Qt : `sudo apt-get install libegl1 libxkbcommon0`.

### Dépannage (exécutables autonomes)

- **Faux positifs antivirus (Windows) :** Windows Defender ou Norton peuvent signaler les applications compilées avec PyInstaller. Il s'agit d'un faux positif connu.
- **Avertissements Gatekeeper (macOS) :** Faites un clic droit et « Ouvrir » pour contourner l'avertissement.
- **Premier lancement lent :** Le premier lancement peut prendre ~10-15s pendant que le système met en cache les fichiers. Les lancements suivants seront plus rapides.
- **Bibliothèques système manquantes (Linux) :** `sudo apt-get install -y libegl1 libxkbcommon0`

---

## 🎯 Présentation

GDPR Pseudonymizer est un **outil CLI et GUI conçu pour la confidentialité**. Il associe la rapidité de l'IA à la rigueur de la relecture humaine pour pseudonymiser des documents en français. Disponible en **ligne de commande (CLI)** et en **application de bureau**, avec des **exécutables autonomes** pour les utilisateurs n'ayant pas Python installé. Contrairement aux solutions entièrement automatiques ou aux services cloud, il mise sur l'**absence totale de faux négatifs** et sur la **solidité juridique** grâce à un processus de validation obligatoire.

**Pour qui ?**
- 🏛️ **Organisations sensibles à la protection des données** ayant besoin d'analyses IA conformes au RGPD
- 🎓 **Chercheurs universitaires** soumis aux exigences des comités d'éthique
- ⚖️ **Équipes juridiques et RH** qui ont besoin d'une pseudonymisation opposable
- 🤖 **Utilisateurs de LLM** souhaitant exploiter des documents confidentiels en toute sécurité

---

## ✨ Fonctionnalités principales

### 🔒 **Confidentialité au cœur de l'architecture**
- ✅ **Traitement 100 % local** — Vos données ne quittent jamais votre machine
- ✅ **Aucune dépendance cloud** — Fonctionne entièrement hors ligne après installation
- ✅ **Tables de correspondance chiffrées** — Chiffrement AES-256-SIV, dérivation de clé PBKDF2 (210 000 itérations), pseudonymisation réversible protégée par mot de passe
- ✅ **Aucune télémétrie** — Ni collecte analytique, ni rapport d'erreur, ni communication externe

### 🤝 **IA + relecture humaine**
- ✅ **Détection hybride** — L'IA repère environ 60 % des entités (NLP + expressions régulières + dictionnaire géographique)
- ✅ **Validation obligatoire** — Vous vérifiez et confirmez chaque entité (précision finale de 100 %)
- ✅ **Interface de validation rapide** — Interface CLI enrichie avec raccourcis clavier, moins de 2 min par document
- ✅ **Parcours intelligent** — Regroupement des entités par type (PERSON → ORG → LOCATION) avec affichage du contexte
- ✅ **Regroupement des variantes** — Les formes apparentées (« Marie Dubois », « Pr. Dubois », « Dubois ») sont fusionnées en un seul élément à valider, avec mention « Apparaît aussi sous : »
- ✅ **Actions groupées** — Confirmation ou rejet de plusieurs entités en une seule opération

### 📊 **Traitement par lot**
- ✅ **Pseudonymes cohérents** — Une même entité reçoit le même pseudonyme sur 10, 50 ou 100+ documents
- ✅ **Résolution par composition** — « Marie Dubois » → « Leia Organa », « Marie » seule → « Leia »
- ✅ **Gestion intelligente des noms** — Suppression des titres (« Dr. Marie Dubois » = « Marie Dubois »), noms composés (« Jean-Pierre » traité comme un tout)
- ✅ **Traitement sélectif** — Option `--entity-types` pour ne traiter que certains types (ex. : `--entity-types PERSON,LOCATION`)
- ✅ **Gain de temps de plus de 50 %** par rapport à la rédaction manuelle, grâce à la détection préalable par l'IA

### 🎭 **Pseudonymes thématiques**
- ✅ **Résultat lisible** — Thèmes Star Wars, Le Seigneur des Anneaux, prénoms français génériques ou identifiants neutres (PER-001, LOC-001)
- ✅ **Utilité préservée** — L'analyse par LLM conserve 85 % de la valeur du document (score validé : 4,27/5,0)
- ✅ **Respect du genre** — Détection automatique du genre des prénoms français à partir d'un dictionnaire de 945 prénoms, avec attribution de pseudonymes correspondants (prénom féminin → pseudonyme féminin, prénom masculin → pseudonyme masculin)
- ✅ **Tous les types d'entités couverts** — Pseudonymes PERSON, LOCATION et ORGANIZATION pour chaque thème

### 🖥️ **Fonctionnalités de l'interface graphique** (v2.0)
- ✅ **Validation visuelle des entités** — Entités colorées par type (cliquer pour accepter/rejeter), annuler/rétablir
- ✅ **Glisser-déposer** — Déposez vos fichiers sur l'écran d'accueil pour lancer le traitement
- ✅ **Traitement par lot avec tableau de bord** — Progression en temps réel, validation par document, contrôles pause/annulation
- ✅ **Thèmes clair/sombre/contraste élevé** — Préférence de thème persistante, conformité WCAG AA
- ✅ **Interface entièrement en français** — Interface FR/EN complète avec changement de langue en temps réel
- ✅ **Utilisation au clavier uniquement** — Accessibilité complète avec navigation au clavier et lecteurs d'écran

<!-- TODO: Ajouter une capture d'écran de la validation -->

---

## 🚀 Prise en main rapide

**Version actuelle :** 🎉 **v2.0.0** (mars 2026) — Interface graphique, exécutables autonomes et accessibilité

### Pour commencer

**Pour les utilisateurs non techniques (sans Python) :**
Téléchargez un exécutable autonome depuis la [section Téléchargement](#téléchargement--exécutables-autonomes-sans-python) ci-dessus et lancez-le directement.

**Pour les développeurs (PyPI) :**
```bash
# CLI uniquement
pip install gdpr-pseudonymizer

# CLI + interface graphique
pip install gdpr-pseudonymizer[gui]

# CLI + support Excel/CSV
pip install gdpr-pseudonymizer[excel]

# Tous les formats optionnels (PDF, DOCX, Excel)
pip install gdpr-pseudonymizer[formats]
```

### Ce que la v2.0 offre

- 🖥️ **Interface graphique** — Validation visuelle des entités avec glisser-déposer, tableau de bord de lot et gestion de base de données
- 📦 **Exécutables autonomes** — Installeur Windows .exe, DMG macOS (arm64 + Intel), AppImage Linux — Python non requis
- ♿ **Accessibilité WCAG 2.1 AA** — Navigation au clavier, lecteurs d'écran, mode contraste élevé
- 🌐 **Interface française** — Interface GUI FR/EN complète avec changement de langue en temps réel
- 🤖 **Détection assistée par IA** — La détection hybride NLP + regex repère environ 60 % des entités (F1 59,97 %)
- ✅ **Relecture humaine obligatoire** — Vous vérifiez toutes les entités (précision finale 100 %)
- 🔒 **Traitement 100 % local** — Vos données ne quittent jamais votre machine
- 📄 **Support PDF/DOCX** — Traitement direct des fichiers PDF et DOCX (extras optionnels)
- 📊 **Support Excel/CSV** — Traitement des fichiers .xlsx et .csv avec pseudonymisation cellule par cellule (extra optionnel : `[excel]`)

**Ce qu'elle ne propose pas :**
- ❌ Un traitement entièrement automatique sans intervention
- ❌ Une précision IA supérieure à 85 % (actuellement : environ 60 % F1 avec l'approche hybride)
- ❌ Un mode sans validation (la relecture est obligatoire)

### Feuille de route

**v1.0 (MVP — T1 2026) :** CLI assisté par IA avec validation obligatoire

**v1.1 (T1 2026) :** Effacement RGPD, pseudonymes genrés, amélioration NER, support PDF/DOCX, documentation française

**v2.0 (T1 2026) — VERSION ACTUELLE :** Interface graphique, exécutables autonomes, accessibilité WCAG AA, interface française, validation par lot, renforcement

**v3.0 (2027+) :** Précision NLP et automatisation
- Modèle NER français affiné (objectif F1 70-85 %, contre ~60 % actuellement)
- Option `--no-validate` pour les traitements à haute confiance
- Traitement automatique à partir d'un seuil de confiance (objectif F1 85 %+)
- Prise en charge multilingue (anglais, espagnol, allemand)

---

## ⚙️ Installation (Python / PyPI)

Consultez le [guide d'installation](https://liochandayo.github.io/RGPDpseudonymizer/installation/) pour des instructions détaillées selon votre plateforme.

### Prérequis
- **Python 3.10, 3.11 ou 3.12** (validé en CI/CD — 3.13+ pas encore testé)

### Depuis PyPI (recommandé)

```bash
pip install gdpr-pseudonymizer

# Vérifier l'installation
gdpr-pseudo --help
```

> **Remarque :** Le modèle français de spaCy (~571 Mo) se télécharge automatiquement à la première utilisation. Pour le pré-télécharger :
> ```bash
> python -m spacy download fr_core_news_lg
> ```

### Depuis les sources (développeurs)

```bash
# Cloner le dépôt
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# Installer les dépendances via Poetry
pip install poetry>=1.7.0
poetry install

# Vérifier l'installation
poetry run gdpr-pseudo --help
```

> **Remarque :** Le modèle français de spaCy (~571 Mo) se télécharge automatiquement à la première utilisation. Pour le pré-télécharger :
> ```bash
> poetry run python -m spacy download fr_core_news_lg
> ```

### Test rapide

```bash
# Tester sur un document d'exemple
echo "Marie Dubois travaille à Paris pour Acme SA." > test.txt
gdpr-pseudo process test.txt

# Ou préciser un fichier de sortie
gdpr-pseudo process test.txt -o output.txt
```

Résultat attendu : "Leia Organa travaille à Coruscant pour Rebel Alliance."

### Fichier de configuration (facultatif)

Générez un modèle de configuration pour personnaliser le comportement par défaut :

```bash
# Générer un modèle .gdpr-pseudo.yaml dans le répertoire courant
poetry run gdpr-pseudo config --init

# Afficher la configuration en vigueur
poetry run gdpr-pseudo config
```

Exemple de `.gdpr-pseudo.yaml` :
```yaml
database:
  path: mappings.db

pseudonymization:
  theme: star_wars    # neutral, star_wars, lotr, neutral_id
  model: spacy

batch:
  workers: 4          # 1-8 (utiliser 1 pour la validation interactive)
  output_dir: null

logging:
  level: INFO
```

**Remarque :** Le mot de passe n'est jamais stocké dans les fichiers de configuration (par sécurité). Utilisez la variable d'environnement `GDPR_PSEUDO_PASSPHRASE` ou la saisie interactive. Minimum 12 caractères requis (NFR12).

---

## 📖 Documentation

**Site de documentation :** [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)

**Pour les utilisateurs :**
- 📘 [Guide d'installation](docs/installation.fr.md) — Instructions d'installation selon votre plateforme
- 📗 [Tutoriel](docs/tutorial.fr.md) — Guides pas à pas
- 📕 [Référence CLI](docs/CLI-REFERENCE.fr.md) — Documentation complète des commandes
- 📕 [Méthodologie et citation académique](docs/methodology.fr.md) — Approche technique et conformité RGPD
- ❓ [FAQ](docs/faq.fr.md) — Questions fréquentes
- 🔧 [Dépannage](docs/troubleshooting.fr.md) — Erreurs courantes et solutions

**Pour les développeurs :**
- 📚 [Référence API](docs/api-reference.fr.md) — Documentation des modules et points d'extension
- 🏗️ [Architecture](docs/architecture/) — Conception technique
- 📊 [Rapport de benchmark NLP](docs/nlp-benchmark-report.md) — Analyse de la précision NER
- 📊 [Rapport de performance](docs/qa/performance-stability-report.md) — Résultats de validation des exigences non fonctionnelles

**Pour les parties prenantes :**
- 🎨 [Positionnement et messages clés](docs/positioning-messaging-v2-assisted.md)
- 📋 [Synthèse des livrables](docs/DELIVERABLES-SUMMARY-2026-01-16.md)

---

## 🌐 Langues de l'interface

L'interface graphique et la CLI sont disponibles en **français** (par défaut) et en **anglais**, avec changement de langue en temps réel.

### Changement de langue dans l'interface graphique

Sélectionnez votre langue dans **Paramètres > Apparence > Langue**. Le changement prend effet immédiatement — aucun redémarrage nécessaire.

### Langue de la CLI

```bash
# Aide en français (par défaut sur les systèmes francophones)
gdpr-pseudo --lang fr --help

# Aide en anglais (par défaut sur les systèmes non francophones)
gdpr-pseudo --lang en --help

# Via variable d'environnement
GDPR_PSEUDO_LANG=fr gdpr-pseudo --help
```

**Ordre de priorité pour la détection de la langue :**
1. Option `--lang` (explicite)
2. Variable d'environnement `GDPR_PSEUDO_LANG`
3. Détection automatique de la locale système
4. Anglais (défaut CLI) / Français (défaut GUI)

---

## 🔬 Détails techniques

### Choix de la bibliothèque NLP (Story 1.2 — terminé)

Après un benchmark approfondi sur 25 documents français (entretiens et documents professionnels, 1 737 entités annotées) :

| Approche | Score F1 | Précision | Rappel | Notes |
|----------|----------|-----------|--------|-------|
| **spaCy seul** `fr_core_news_lg` | 29,5 % | 27,0 % | 32,7 % | Ligne de base (Story 1.2) |
| **Hybride** (spaCy + regex) | 59,97 % | 48,17 % | 79,45 % | Story 5.3 |
| **Hybride + patterns enrichis** | 31,79 % | 19,49 % | 85,15 % | Story 7.5 (actuel) |

**Progression de la précision :** En passant de spaCy seul à l'approche hybride — avec nettoyage des annotations, enrichissement des expressions régulières et ajout d'un dictionnaire géographique français — le score F1 a doublé. Story 7.5 a ajouté 12 mots-clés de détection ORG, la désambiguïsation POS pour le dictionnaire géographique et 7 lieux internationaux — réduisant le taux de faux négatifs LOCATION de 27,42 % à 12,90 %.

**Solution retenue :**
- ✅ **Approche hybride** (NLP + regex + dictionnaire géographique + désambiguïsation POS)
- ✅ **Validation obligatoire** pour une précision finale de 100 %
- 📅 **Affinage du modèle** reporté à la v3.0 (objectif F1 70-85 %, nécessite des données d'entraînement issues des validations en v1.x/v2.x)

Analyse complète : [docs/qa/ner-accuracy-report.md](docs/qa/ner-accuracy-report.md) | Ligne de base historique : [docs/nlp-benchmark-report.md](docs/nlp-benchmark-report.md)

### Processus de validation (Story 1.7 — terminé)

L'interface de validation offre un parcours intuitif piloté au clavier pour passer en revue les entités détectées :

**Fonctionnalités :**
- ✅ **Regroupement par type** — Les entités sont présentées dans un ordre logique : PERSON → ORG → LOCATION
- ✅ **Affichage du contexte** — 10 mots avant et après chaque entité, avec mise en surbrillance
- ✅ **Scores de confiance** — Code couleur selon la confiance du modèle spaCy (vert > 80 %, jaune 60-80 %, rouge < 60 %)
- ✅ **Raccourcis clavier** — Actions à une touche : [Espace] Confirmer, [R] Rejeter, [E] Modifier, [A] Ajouter, [C] Changer le pseudonyme
- ✅ **Actions groupées** — Accepter ou rejeter toutes les entités d'un type en une fois (Maj+A/R) avec affichage du nombre d'entités traitées
- ✅ **Indicateur de défilement des contextes** — Points indicateurs (`● ○ ○ ○ ○`) montrant la position courante ; mention `[Press X to cycle]` pour faciliter la découverte de la touche X
- ✅ **Aide intégrée** — Appuyez sur [H] pour afficher tous les raccourcis
- ✅ **Performance** — Moins de 2 minutes pour un document type de 20-30 entités

**Étapes du processus :**
1. Écran récapitulatif (nombre d'entités par type)
2. Revue des entités type par type, avec contexte
3. Signalement des entités ambiguës pour examen attentif
4. Confirmation finale avec résumé des modifications
5. Traitement du document avec les entités validées

**Déduplication (Story 1.9) :** Les entités en double sont regroupées — vous validez une fois, la décision s'applique à toutes les occurrences (réduction de 66 % du temps pour les documents longs).

**Regroupement des variantes (Story 4.6) :** Les différentes formes d'une même entité sont automatiquement fusionnées en un seul élément à valider. « Marie Dubois », « Pr. Dubois » et « Dubois » apparaissent comme un seul élément, avec la mention « Apparaît aussi sous : ». Ce regroupement évite le pontage transitif Union-Find lorsque des noms de famille sont partagés par des personnes différentes.

---

### Technologies utilisées

| Composant | Technologie | Version | Rôle |
|-----------|------------|---------|------|
| **Environnement d'exécution** | Python | 3.10-3.12 | Validé en CI/CD (3.13+ pas encore testé) |
| **Bibliothèque NLP** | spaCy | 3.8.0 | Détection d'entités en français (fr_core_news_lg) |
| **CLI** | Typer | 0.9+ | Interface en ligne de commande |
| **Base de données** | SQLite | 3.35+ | Stockage local des tables de correspondance (mode WAL) |
| **Chiffrement** | cryptography (AESSIV) | 44.0+ | Chiffrement AES-256-SIV des champs sensibles (dérivation PBKDF2, protégé par mot de passe) |
| **ORM** | SQLAlchemy | 2.0+ | Couche d'abstraction base de données et gestion des sessions |
| **Interface graphique** | PySide6 | 6.7+ | Application de bureau (optionnel : `pip install gdpr-pseudonymizer[gui]`) |
| **Interface de validation** | rich | 13.7+ | Revue interactive des entités en CLI |
| **Saisie clavier** | readchar | 4.2+ | Capture de touche unique pour la validation |
| **Tests** | pytest | 7.4+ | Tests unitaires et d'intégration |
| **CI/CD** | GitHub Actions | N/A | Tests automatisés (Windows/Mac/Linux) |

---

## 🤔 Pourquoi une assistance IA plutôt qu'une automatisation complète ?

**En bref :** La confidentialité et la conformité exigent un contrôle humain.

**En détail :**
1. **Solidité juridique au regard du RGPD** — La relecture humaine fournit une piste d'audit opposable
2. **Aucun faux négatif** — L'IA laisse passer des entités ; l'humain les rattrape (couverture à 100 %)
3. **Limites actuelles du NLP** — Les modèles français sur des documents d'entretiens ou professionnels : 29,5 % F1 de base (l'approche hybride atteint environ 60 %)
4. **Mieux que les alternatives :**
   - ✅ **vs rédaction manuelle :** Plus de 50 % de temps gagné grâce à la détection préalable
   - ✅ **vs services cloud :** Traitement 100 % local, aucune fuite de données
   - ✅ **vs outils entièrement automatiques :** Précision de 100 % grâce à la relecture humaine

**Témoignage :**
> « Je TIENS à la relecture humaine pour des raisons de conformité. L'IA me fait gagner du temps en repérant les entités à l'avance, mais c'est moi qui garde la main sur la décision finale. » — Responsable conformité

---

## 🎯 Exemples d'utilisation

### 1. **Recherche universitaire et conformité éthique**
**Contexte :** Un chercheur doit pseudonymiser 50 transcriptions d'entretiens pour obtenir l'aval de son comité d'éthique.

**Sans GDPR Pseudonymizer :**
- ❌ Rédaction manuelle : 16-25 heures
- ❌ Perte de la cohérence du document pour l'analyse
- ❌ Risque d'erreur dû à la fatigue

**Avec GDPR Pseudonymizer :**
- ✅ Détection préalable par l'IA : environ 30 min de traitement
- ✅ Relecture humaine : environ 90 min (50 documents × environ 2 min chacun)
- ✅ Total : **2-3 heures** (plus de 85 % de temps gagné)
- ✅ Journal d'audit pour le comité d'éthique

---

### 2. **Analyse de documents RH**
**Contexte :** Une équipe RH souhaite analyser les retours de ses collaborateurs avec ChatGPT.

**Sans GDPR Pseudonymizer :**
- ❌ Impossible d'utiliser ChatGPT (violation du RGPD — les noms des employés seraient exposés)
- ❌ Analyse manuelle uniquement (lente, perspectives limitées)

**Avec GDPR Pseudonymizer :**
- ✅ Pseudonymisation en local (noms des employés → pseudonymes)
- ✅ Transmission à ChatGPT en toute sécurité (aucune donnée personnelle exposée)
- ✅ Analyses IA obtenues dans le respect du RGPD

---

### 3. **Préparation de documents juridiques**
**Contexte :** Un cabinet d'avocats prépare des pièces pour une recherche juridique assistée par IA.

**Sans GDPR Pseudonymizer :**
- ❌ Service de pseudonymisation cloud (risque lié au tiers)
- ❌ Rédaction manuelle (heures facturées coûteuses)

**Avec GDPR Pseudonymizer :**
- ✅ Traitement 100 % local (secret professionnel préservé)
- ✅ Précision vérifiée par l'humain (solidité juridique)
- ✅ Correspondances réversibles (dé-pseudonymisation possible si nécessaire)

---

## ⚖️ Conformité RGPD

### Comment GDPR Pseudonymizer contribue à la conformité

| Exigence RGPD | Mise en œuvre |
|----------------|---------------|
| **Art. 25 — Protection des données dès la conception** | Traitement local, aucune dépendance cloud, stockage chiffré |
| **Art. 30 — Registre des traitements** | Journaux d'audit complets (Story 2.5) : table d'opérations traçant horodatage, fichiers traités, nombre d'entités, version du modèle, thème, succès/échec, durée de traitement ; export JSON/CSV pour le reporting de conformité |
| **Art. 32 — Mesures de sécurité** | Chiffrement AES-256-SIV avec dérivation de clé PBKDF2 (210 000 itérations), stockage protégé par mot de passe, chiffrement au niveau des colonnes pour les champs sensibles |
| **Art. 35 — Analyse d'impact** | Méthodologie transparente, approche citable pour la documentation d'une AIPD |
| **Considérant 26 — Pseudonymisation** | Correspondance cohérente des pseudonymes, réversibilité par mot de passe |

### Ce que signifie la pseudonymisation au sens juridique

**Selon l'article 4(5) du RGPD :**
> « La pseudonymisation désigne le traitement de données à caractère personnel de telle façon que celles-ci ne puissent plus être attribuées à une personne concernée précise **sans avoir recours à des informations supplémentaires**, pour autant que ces informations supplémentaires soient conservées séparément. »

**L'approche de GDPR Pseudonymizer :**
- ✅ **Remplacement des données personnelles :** Noms, lieux, organisations → pseudonymes
- ✅ **Stockage séparé :** Table de correspondance chiffrée par mot de passe, distincte des documents
- ✅ **Réversibilité :** Les utilisateurs autorisés peuvent dé-pseudonymiser grâce au mot de passe
- ⚠️ **Attention :** La pseudonymisation réduit le risque mais ne rend **pas** les données anonymes

**Recommandation :** Consultez votre délégué à la protection des données (DPD) pour des conseils de conformité adaptés à votre situation.

---

## 🛠️ État du développement

**Epics 1-6 terminés** — v2.0.0 (mars 2026). Interface graphique avec exécutables autonomes et accessibilité WCAG AA.

- ✅ **Epic 1 :** Fondations et validation NLP (9 stories) — Intégration spaCy, interface de validation, détection hybride, déduplication des entités
- ✅ **Epic 2 :** Moteur de pseudonymisation (9 stories) — Bibliothèques de pseudonymes, chiffrement, journaux d'audit, traitement par lot, correspondance 1:1 RGPD
- ✅ **Epic 3 :** Interface CLI et traitement par lot (7 stories) — 8 commandes CLI, suivi de progression, fichiers de configuration, traitement parallèle, perfectionnement UX
- ✅ **Epic 4 :** Préparation au lancement (8 stories) — Validation de l'utilité LLM, tests multi-plateformes, documentation, suite de précision NER, validation des performances, intégration des retours bêta, refactorisation, préparation au lancement
- ✅ **Epic 5 :** Améliorations et conformité RGPD (7 stories) — Effacement article 17 RGPD, pseudonymes tenant compte du genre, amélioration de la précision NER (F1 29,74 % → 59,97 %), traduction française de la documentation, support PDF/DOCX, perfectionnement CLI et benchmarks, release v1.1
- ✅ **Epic 6 :** v2.0 Interface graphique et accessibilité (9 stories) — Application de bureau PySide6, validation visuelle, traitement par lot GUI, i18n, WCAG AA, exécutables autonomes
  - ✅ Story 6.1 : Architecture UX et sélection du framework GUI
  - ✅ Story 6.2 : Fondations de l'application GUI (fenêtre principale, thèmes, écran d'accueil, paramètres, 77 tests GUI)
  - ✅ Story 6.3 : Workflow de traitement de documents (dialogue de phrase secrète, worker de traitement, écran de résultats, 45 nouveaux tests GUI)
  - ✅ Story 6.4 : Interface visuelle de validation des entités (éditeur d'entités, panneau latéral, état de validation avec annuler/rétablir, 72 nouveaux tests GUI)
  - ✅ Story 6.5 : Traitement par lot et gestion de configuration (écran de traitement par lot, gestion de la base de données, améliorations des paramètres, 40 nouveaux tests)
  - ✅ Story 6.6 : Internationalisation et interface française (i18n double voie : Qt Linguist + gettext, 267 chaînes GUI, ~50 chaînes CLI, changement de langue en temps réel, 53 nouveaux tests)
  - ✅ Story 6.7 : Accessibilité (WCAG 2.1 niveau AA) — navigation au clavier, support des lecteurs d'écran, mode contraste élevé, palette adaptée au daltonisme, mise à l'échelle DPI, 33 tests d'accessibilité
  - ✅ Story 6.7.1 : Renforcement du traitement et sécurité — Assainissement des DCP dans les messages d'erreur, gestion typée des exceptions, refactorisation DRY, comptage d'entités par document (correctif DATA-001), 26 nouveaux tests
  - ✅ Story 6.7.2 : Opérations base de données en arrière-plan — DatabaseWorker (QRunnable) pour les opérations liste/recherche/suppression/export, stratégie d'annulation-remplacement, recherche anti-rebond 300 ms, routage par seuil, indicateur de chargement, 38 nouveaux tests
  - ✅ Story 6.7.3 : Validation par document en lot — Validation interactive des entités par document en mode lot, navigation Précédent/Suivant, annulation avec affichage des statuts, 21 nouveaux tests
  - ✅ Story 6.8 : Exécutables autonomes et distribution — Builds PyInstaller, installeur NSIS (Windows), DMG (macOS), AppImage (Linux), workflow CI
  - ✅ Story 6.9 : Préparation de la version v2.0 — Bump de version, CHANGELOG, mises à jour de la documentation, coordination de la publication
- **Total :** 53 stories, 1 800+ tests, 86 %+ de couverture, tous les contrôles qualité au vert

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour en savoir plus sur :
- Les signalements de bugs et demandes de fonctionnalités
- La mise en place de l'environnement de développement et les exigences qualité
- Le processus de pull request et le format des messages de commit

Merci de lire notre [code de conduite](CODE_OF_CONDUCT.md) avant de participer.

---

## 📧 Contact et support

**Responsable du projet :** Lionel Deveaux — [@LioChanDaYo](https://github.com/LioChanDaYo)

**Pour vos questions et demandes de support :**
- 💬 [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) — Questions générales, retours d'expérience
- 🐛 [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues) — Signalements de bugs, suggestions de fonctionnalités
- 📖 [SUPPORT.md](SUPPORT.md) — Processus de support et aide au diagnostic

---

## 📜 Licence

Ce projet est distribué sous la [licence MIT](LICENSE).

---

## 🙏 Remerciements

**Construit avec :**
- [spaCy](https://spacy.io/) — Bibliothèque NLP de niveau industriel
- [Typer](https://typer.tiangolo.com/) — Framework CLI moderne
- [rich](https://rich.readthedocs.io/) — Mise en forme élégante en terminal

**Sources d'inspiration :**
- Les principes de protection des données dès la conception du RGPD
- Les exigences éthiques de la recherche universitaire
- Le besoin concret d'analyser des documents par IA sans compromettre la confidentialité

**Méthodologie :**
- Développé avec le framework [BMAD-METHOD™](https://bmad.ai)
- Élicitation interactive et validation multi-perspectives

---

## ⚠️ Avertissement

**GDPR Pseudonymizer est un outil d'aide à la conformité RGPD. Il ne constitue en aucun cas un conseil juridique.**

**Points importants :**
- ⚠️ La pseudonymisation réduit le risque mais n'est pas une anonymisation
- ⚠️ Vous restez responsable du traitement au sens du RGPD
- ⚠️ Consultez votre DPD ou votre conseil juridique pour toute question de conformité
- ⚠️ La relecture humaine est OBLIGATOIRE — ne sautez pas les étapes de validation
- ⚠️ Testez rigoureusement avant toute mise en production

**Limitations actuelles :**
- Détection IA : environ 60 % F1 (pas 85 %+)
- Validation requise pour TOUS les documents (pas facultative)
- Documents en français uniquement (anglais, espagnol, etc. dans les versions futures)
- Formats supportés : .txt, .md, .pdf, .docx, .xlsx, .csv (PDF/DOCX/Excel nécessitent des extras optionnels : `pip install gdpr-pseudonymizer[formats]`)
- Les formules Excel sont lues comme valeurs affichées en cache ; les chaînes de formule ne sont pas préservées dans la sortie pseudonymisée
- Le format binaire .xls (Excel 97-2003) n'est pas supporté — enregistrez d'abord au format .xlsx

---

## 🧪 Tests

### Lancer les tests

Le projet comprend des tests unitaires et d'intégration couvrant le processus de validation, la détection NLP et les fonctionnalités principales.

**Note pour les utilisateurs Windows :** En raison de violations d'accès connues avec spaCy sous Windows ([spaCy issue #12659](https://github.com/explosion/spaCy/issues/12659)), la CI Windows n'exécute que les tests indépendants de spaCy. La suite complète tourne sous Linux/macOS.

**Lancer tous les tests :**
```bash
poetry run pytest -v
```

**Tests unitaires uniquement :**
```bash
poetry run pytest tests/unit/ -v
```

**Tests d'intégration uniquement :**
```bash
poetry run pytest tests/integration/ -v
```

**Tests de validation de la précision (nécessite le modèle spaCy) :**
```bash
poetry run pytest tests/accuracy/ -v -m accuracy -s
```

**Tests de performance et de stabilité (nécessite le modèle spaCy) :**
```bash
# Tous les tests de performance (stabilité, mémoire, démarrage, stress)
poetry run pytest tests/performance/ -v -s -p no:benchmark --timeout=600

# Tests de benchmark uniquement (pytest-benchmark)
poetry run pytest tests/performance/ --benchmark-only -v -s
```

**Avec rapport de couverture :**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=term-missing --cov-report=html
```

**Tests d'intégration du processus de validation :**
```bash
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

**Contrôles qualité :**
```bash
# Vérification du formatage
poetry run black --check gdpr_pseudonymizer tests

# Formatage automatique
poetry run black gdpr_pseudonymizer tests

# Vérification du linting
poetry run ruff check gdpr_pseudonymizer tests

# Vérification des types
poetry run mypy gdpr_pseudonymizer
```

**Tests compatibles Windows uniquement (sans dépendance à spaCy) :**
```bash
# Tests unitaires sans spaCy (reproduit la CI Windows)
poetry run pytest tests/unit/test_benchmark_nlp.py tests/unit/test_config_manager.py tests/unit/test_data_models.py tests/unit/test_file_handler.py tests/unit/test_logger.py tests/unit/test_naive_processor.py tests/unit/test_name_dictionary.py tests/unit/test_process_command.py tests/unit/test_project_config.py tests/unit/test_regex_matcher.py tests/unit/test_validation_models.py tests/unit/test_validation_stub.py -v

# Tests d'intégration du processus de validation (compatibles Windows)
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

### Couverture des tests

- **Tests unitaires :** 977+ tests couvrant les modèles de validation, les composants d'interface, le chiffrement, les opérations de base de données, les journaux d'audit, le suivi de progression, la détection de genre, l'indicateur de défilement des contextes et la logique métier
- **Tests d'intégration :** 90 tests couvrant les parcours de bout en bout, dont la validation (Story 2.0.1), les opérations sur base chiffrée (Story 2.4), la logique de composition et la détection hybride
- **Tests de précision :** 22 tests mesurant la précision NER sur un corpus de référence de 25 documents (Story 4.4)
- **Tests de performance :** 19 tests validant toutes les exigences non fonctionnelles — benchmarks par document (NFR1), benchmarks de détection d'entités, traitement par lot (NFR2), profilage mémoire (NFR4), temps de démarrage (NFR5), stabilité et taux d'erreur (NFR6), tests de charge (Story 4.5)
- **Couverture actuelle :** 86 %+ sur l'ensemble des modules (100 % pour le module de progression, 91,41 % pour AuditRepository)
- **Total :** 1 800+ tests
- **CI/CD :** Tests exécutés sur Python 3.10-3.12, sous Windows, macOS et Linux
- **Contrôles qualité :** Tous validés (Black, Ruff, mypy, pytest)

### Principaux scénarios des tests d'intégration

La suite de tests d'intégration couvre :

**Processus de validation (19 tests) :**
- ✅ Parcours complet : détection des entités → récapitulatif → revue → confirmation
- ✅ Actions utilisateur : confirmer (Espace), rejeter (R), modifier (E), ajouter une entité (A), changer le pseudonyme (C), parcourir les contextes (X)
- ✅ Transitions d'état : PENDING → CONFIRMED/REJECTED/MODIFIED
- ✅ Déduplication des entités avec revue groupée
- ✅ Cas limites : documents vides, documents volumineux (320+ entités), interruption Ctrl+C, saisie invalide
- ✅ Actions groupées : Accepter tout le type (Maj+A), Rejeter tout le type (Maj+R), avec demande de confirmation
- ✅ Simulation d'interactions : simulation complète des saisies clavier et des invites

**Base de données chiffrée (9 tests) :**
- ✅ Parcours complet : init → open → save → query → close
- ✅ Cohérence inter-sessions : une même mot de passe retrouve les mêmes données
- ✅ Idempotence : des requêtes multiples retournent les mêmes résultats
- ✅ Données chiffrées au repos : les champs sensibles sont stockés chiffrés dans SQLite
- ✅ Logique de composition intégrée : requêtes sur les composants chiffrés
- ✅ Intégration des dépôts : tous les dépôts (correspondance, audit, métadonnées) fonctionnent avec la session chiffrée
- ✅ Lectures concurrentes : le mode WAL permet plusieurs lecteurs simultanés
- ✅ Index : vérification de l'optimisation des performances de requête
- ✅ Rollback en traitement par lot : intégrité transactionnelle en cas d'erreur

---

## 📊 Métriques du projet (au 2026-03-03)

| Métrique | Valeur | Statut |
|----------|--------|--------|
| **Avancement** | v2.0.0 | ✅ Epics 1-6 terminés |
| **Stories terminées** | 52 (Epics 1-6) | ✅ Tous les epics terminés |
| **Utilité LLM (NFR10)** | 4,27/5,0 (85,4 %) | ✅ VALIDÉ (seuil : 80 %) |
| **Succès d'installation (NFR3)** | 87,5 % (7/8 plateformes) | ✅ VALIDÉ (seuil : 85 %) |
| **Première pseudonymisation (NFR14)** | 100 % en moins de 30 min | ✅ VALIDÉ (seuil : 80 %) |
| **Bugs critiques trouvés** | 1 (Story 2.8) | ✅ RÉSOLU — Epic 3 débloqué |
| **Corpus de test** | 25 documents, 1 737 entités | ✅ Complet (après nettoyage) |
| **Précision NLP (ligne de base)** | 29,5 % F1 (spaCy seul) | ✅ Mesuré (Story 1.2) |
| **Précision hybride (NLP+Regex)** | 59,97 % F1 (+30,23 pp vs ligne de base) | ✅ Story 5.3 terminé |
| **Précision finale (IA+Humain)** | 100 % (validé) | 🎯 Par conception |
| **Bibliothèques de pseudonymes** | 3 thèmes (2 426 noms + 240 lieux + 588 organisations) | ✅ Stories 2.1, 3.0, 4.6 terminées |
| **Résolution par composition** | Opérationnelle (réutilisation des composants + suppression des titres + noms composés) | ✅ Stories 2.2, 2.3 terminées |
| **Traitement par lot** | Architecture validée (multiprocessing.Pool, accélération 1,17x-2,5x) | ✅ Story 2.7 terminé |
| **Stockage chiffré** | AES-256-SIV avec protection par mot de passe (PBKDF2 210 000 itérations) | ✅ Story 2.4 terminé |
| **Journaux d'audit** | Conformité article 30 RGPD (table d'opérations + export JSON/CSV) | ✅ Story 2.5 terminé |
| **Interface de validation** | Opérationnelle avec déduplication | ✅ Stories 1.7, 1.9 terminées |
| **Temps de validation** | < 2 min (20-30 entités), < 5 min (100 entités) | ✅ Objectifs atteints |
| **Performance mono-document (NFR1)** | environ 6 s en moyenne pour 3 500 mots | ✅ VALIDÉ (seuil < 30 s, marge de 80 %) |
| **Performance par lot (NFR2)** | environ 5 min pour 50 documents | ✅ VALIDÉ (seuil < 30 min, marge de 83 %) |
| **Utilisation mémoire (NFR4)** | environ 1 Go de pic mesuré par Python | ✅ VALIDÉ (seuil < 8 Go) |
| **Démarrage CLI (NFR5)** | 0,56 s (help), 6,0 s (démarrage à froid avec modèle) | ✅ VALIDÉ (< 5 s pour le démarrage CLI) |
| **Taux d'erreur (NFR6)** | environ 0 % d'erreurs inattendues | ✅ VALIDÉ (seuil < 10 %) |
| **Couverture de test** | 1 800+ tests (dont 393 GUI), 86 %+ de couverture | ✅ Tous les contrôles qualité validés |
| **Contrôles qualité** | Ruff, mypy, pytest | ✅ Tous validés (0 problème) |
| **Langues GUI/CLI** | Français (défaut), Anglais | 🌐 Changement en temps réel (Story 6.6) |
| **Langues de documents** | Français | 🇫🇷 v1.0 uniquement |
| **Formats** | .txt, .md, .pdf, .docx, .xlsx, .csv | 📝 PDF/DOCX/Excel via extras optionnels |

---

## 🔗 Liens rapides

- 📘 [PRD complet](docs/.ignore/prd.md) — Exigences produit détaillées
- 📊 [Rapport de benchmark](docs/nlp-benchmark-report.md) — Analyse de la précision NLP
- 🎨 [Positionnement](docs/positioning-messaging-v2-assisted.md) — Stratégie marketing et messages clés
- 🏗️ [Architecture](docs/architecture/) — Conception technique
- 📋 [Checklist d'approbation](docs/PM-APPROVAL-CHECKLIST.md) — Suivi des décisions PM

---

**Dernière mise à jour :** 2026-03-13 (v2.0.0+ — Interface graphique, exécutables autonomes, accessibilité WCAG AA, interface française, support Excel/CSV, 1 800+ tests au total)
