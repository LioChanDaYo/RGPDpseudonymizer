> 🇬🇧 [English](README.md) | 🇫🇷 **Français**

# RGPD Pseudonymizer

[![Version PyPI](https://img.shields.io/pypi/v/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![Versions Python](https://img.shields.io/pypi/pyversions/gdpr-pseudonymizer)](https://pypi.org/project/gdpr-pseudonymizer/)
[![Licence : MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml/badge.svg)](https://github.com/LioChanDaYo/RGPDpseudonymizer/actions/workflows/ci.yaml)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://liochandayo.github.io/RGPDpseudonymizer/)

**Pseudonymisation assistée par IA pour documents francophones avec vérification humaine**

Transformez vos documents sensibles en français pour une analyse IA sécurisée grâce au traitement local, à la relecture humaine obligatoire et à la conformité RGPD.

---

## 🎯 Aperçu

RGPD Pseudonymizer est un **outil CLI axé sur la confidentialité** qui combine l'efficacité de l'IA avec la précision humaine pour pseudonymiser des documents textuels en français. Contrairement aux outils entièrement automatiques ou aux services cloud, nous privilégions le **zéro faux négatif** et la **défendabilité juridique** grâce à des flux de validation obligatoires.

**Idéal pour :**
- 🏛️ **Les organisations soucieuses de la vie privée** ayant besoin d'analyses IA conformes au RGPD
- 🎓 **Les chercheurs universitaires** soumis à des exigences de comités d'éthique
- ⚖️ **Les équipes juridiques et RH** nécessitant une pseudonymisation défendable
- 🤖 **Les utilisateurs de LLM** souhaitant analyser des documents confidentiels en toute sécurité

---

## ✨ Fonctionnalités clés

### 🔒 **Architecture axée sur la confidentialité**
- ✅ **Traitement 100 % local** — Vos données ne quittent jamais votre machine
- ✅ **Aucune dépendance cloud** — Fonctionne entièrement hors ligne après installation
- ✅ **Tables de correspondance chiffrées** — Chiffrement AES-256-SIV avec dérivation de clé PBKDF2 (210K itérations), pseudonymisation réversible protégée par phrase secrète
- ✅ **Zéro télémétrie** — Aucune collecte analytique, aucun rapport d'erreur, aucune communication externe

### 🤝 **IA + Vérification humaine**
- ✅ **Détection hybride** — L'IA pré-détecte environ 60 % des entités (NLP + regex + dictionnaire géographique)
- ✅ **Validation obligatoire** — Vous vérifiez et confirmez toutes les entités (garantit une précision de 100 %)
- ✅ **Interface de validation rapide** — Interface CLI enrichie avec raccourcis clavier, moins de 2 min par document
- ✅ **Flux intelligent** — Regroupement des entités par type (PERSON → ORG → LOCATION) avec affichage du contexte
- ✅ **Regroupement de variantes d'entités** — Les formes apparentées (« Marie Dubois », « Pr. Dubois », « Dubois ») sont fusionnées en un seul élément de validation avec un affichage « Apparaît aussi sous : »
- ✅ **Actions par lot** — Confirmation/rejet de plusieurs entités en une seule opération

### 📊 **Traitement par lot**
- ✅ **Pseudonymes cohérents** — Même entité = même pseudonyme sur 10 à 100+ documents
- ✅ **Correspondance compositionnelle** — « Marie Dubois » → « Leia Organa », « Marie » seule → « Leia »
- ✅ **Gestion intelligente des noms** — Suppression des titres (« Dr. Marie Dubois » = « Marie Dubois »), noms composés (« Jean-Pierre » traité comme unité atomique)
- ✅ **Traitement sélectif des entités** — Option `--entity-types` pour filtrer par type (ex. : `--entity-types PERSON,LOCATION`)
- ✅ **Gain de temps de 50 %+** par rapport à la rédaction manuelle (pré-détection IA + validation)

### 🎭 **Pseudonymes thématiques**
- ✅ **Résultat lisible** — Star Wars, Le Seigneur des Anneaux ou prénoms français génériques
- ✅ **Préservation du contexte** — L'analyse par LLM conserve 85 % de l'utilité du document (validé : 4,27/5,0)
- ✅ **Sensibilité au genre** — Détection automatique du genre des prénoms français à partir d'un dictionnaire de 945 prénoms et attribution de pseudonymes correspondants (prénoms féminins → pseudonymes féminins, prénoms masculins → pseudonymes masculins)
- ✅ **Prise en charge complète des entités** — Pseudonymes PERSON, LOCATION et ORGANIZATION pour tous les thèmes

---

## 🚀 Démarrage rapide

**Statut :** 🎉 **v1.0.7** (février 2026)

### Attentes réalistes pour la v1.0

**Ce que la v1.0 offre :**
- 🤖 **Détection assistée par IA** — La détection hybride NLP + regex identifie environ 60 % des entités automatiquement (F1 59,97 %)
- ✅ **Vérification humaine obligatoire** — Vous relisez et confirmez toutes les entités (2-3 min par document)
- 🔒 **Garantie de précision à 100 %** — La validation humaine assure zéro faux négatif
- ⚡ **50 %+ plus rapide que le traitement manuel** — La pré-détection fait gagner du temps par rapport à la rédaction manuelle

**Ce que la v1.0 ne propose PAS :**
- ❌ Un traitement entièrement automatique sans intervention
- ❌ Une précision IA supérieure à 85 % (actuellement : environ 60 % F1 avec l'approche hybride)
- ❌ Un mode de validation optionnel (la validation est obligatoire)

### Feuille de route

**v1.0 (MVP — T2 2026) :** CLI assisté par IA avec validation obligatoire
- Cible : Utilisateurs précoces soucieux de la vie privée, valorisant la supervision humaine
- Traitement 100 % local, tables de correspondance chiffrées, pistes d'audit

**v1.1 (T2-T3 2026) :** Améliorations rapides et conformité RGPD
- ✅ ~~Droit à l'effacement RGPD : suppression sélective d'entités (commande `delete-mapping`, article 17)~~ (Story 5.1 — terminé)
- ✅ ~~Attribution de pseudonymes sensible au genre pour les prénoms français~~ (Story 5.2 — terminé)
- ✅ ~~Améliorations de la précision NER : F1 29,74 % → 59,97 % (nettoyage des annotations, extension des regex, dictionnaire géographique)~~ (Story 5.3 — terminé)
- Corrections de bugs suite aux retours bêta et améliorations de l'expérience utilisateur

**v2.0 (T3-T4 2026) :** Interface graphique et accessibilité élargie
- Interface graphique de bureau encapsulant le noyau CLI (glisser-déposer, revue visuelle des entités)
- Exécutables autonomes (.exe pour Windows, .app pour macOS) — Python non requis
- Interface utilisateur francophone avec architecture d'internationalisation (prête pour le multilingue)
- Accessibilité WCAG AA pour les contextes professionnels et universitaires
- Cible : Utilisateurs non techniques (équipes RH, juridiques, conformité)

**v3.0 (2027+) :** Précision NLP et automatisation
- Modèle NER français affiné (objectif F1 70-85 %, contre 40-50 % actuellement)
- Option `--no-validate` pour les flux de travail à haute confiance
- Traitement automatique basé sur la confiance (objectif F1 85 %+)
- Prise en charge multilingue (anglais, espagnol, allemand)

---

## ⚙️ Installation

Consultez le [Guide d'installation](https://liochandayo.github.io/RGPDpseudonymizer/installation/) pour des instructions détaillées par plateforme.

### Prérequis
- **Python 3.10, 3.11 ou 3.12** (validé en CI/CD — 3.13+ pas encore testé)

### Installation depuis PyPI (recommandé)

```bash
pip install gdpr-pseudonymizer

# Vérifier l'installation
gdpr-pseudo --help
```

> **Remarque :** Le modèle français de spaCy (~571 Mo) se télécharge automatiquement à la première utilisation. Pour le pré-télécharger :
> ```bash
> python -m spacy download fr_core_news_lg
> ```

### Installation depuis les sources (développeur)

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
# Tester sur un document exemple
echo "Marie Dubois travaille à Paris pour Acme SA." > test.txt
gdpr-pseudo process test.txt

# Ou spécifier un fichier de sortie personnalisé
gdpr-pseudo process test.txt -o output.txt
```

Résultat attendu : "Leia Organa travaille à Coruscant pour Rebel Alliance."

### Fichier de configuration (optionnel)

Générez un modèle de configuration pour personnaliser les paramètres par défaut :

```bash
# Générer un modèle .gdpr-pseudo.yaml dans le répertoire courant
poetry run gdpr-pseudo config --init

# Afficher la configuration effective actuelle
poetry run gdpr-pseudo config
```

Exemple de `.gdpr-pseudo.yaml` :
```yaml
database:
  path: mappings.db

pseudonymization:
  theme: star_wars    # neutral, star_wars, lotr
  model: spacy

batch:
  workers: 4          # 1-8 (use 1 for interactive validation)
  output_dir: null

logging:
  level: INFO
```

**Remarque :** La phrase secrète n'est jamais stockée dans les fichiers de configuration (sécurité). Utilisez la variable d'environnement `GDPR_PSEUDO_PASSPHRASE` ou la saisie interactive. Minimum 12 caractères requis (NFR12).

---

## 📖 Documentation

**Site de documentation :** [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)

**Pour les utilisateurs :**
- 📘 [Guide d'installation](docs/installation.md) — Instructions d'installation par plateforme
- 📗 [Tutoriel d'utilisation](docs/tutorial.md) — Tutoriels pas à pas
- 📕 [Référence CLI](docs/CLI-REFERENCE.md) — Documentation complète des commandes
- 📕 [Méthodologie et citation académique](docs/methodology.md) — Approche technique et conformité RGPD
- ❓ [FAQ](docs/faq.md) — Questions fréquentes et réponses
- 🔧 [Dépannage](docs/troubleshooting.md) — Référence des erreurs et solutions

**Pour les développeurs :**
- 📚 [Référence API](docs/api-reference.md) — Documentation des modules et points d'extension
- 🏗️ [Documentation d'architecture](docs/architecture/) — Conception technique
- 📊 [Rapport de benchmark NLP](docs/nlp-benchmark-report.md) — Analyse de la précision NER
- 📊 [Rapport de performance](docs/qa/performance-stability-report.md) — Résultats de validation des performances NFR

**Pour les parties prenantes :**
- 🎨 [Positionnement et messages clés](docs/positioning-messaging-v2-assisted.md)
- 📋 [Synthèse des livrables](docs/DELIVERABLES-SUMMARY-2026-01-16.md)

---

## 🔬 Détails techniques

### Sélection de la bibliothèque NLP (Story 1.2 — Terminé)

Après un benchmark complet sur 25 documents français d'entretiens et documents professionnels (1 737 entités annotées) :

| Approche | Score F1 | Précision | Rappel | Notes |
|----------|----------|-----------|--------|-------|
| **spaCy seul** `fr_core_news_lg` | 29,5 % | 27,0 % | 32,7 % | Référence Story 1.2 |
| **Hybride** (spaCy + regex) | 59,97 % | 48,17 % | 79,45 % | Story 5.3 (actuel) |

**Trajectoire de précision :** De la référence spaCy seul à l'approche hybride avec nettoyage des annotations, extension des patterns regex et dictionnaire géographique français — le score F1 a doublé. Le rappel PERSON a atteint 82,93 %.

**Solution retenue :**
- ✅ **Approche hybride** (NLP + regex + dictionnaire géographique) atteint environ 60 % de F1
- ✅ **Validation obligatoire** garantit une précision finale de 100 %
- 📅 **Affinage du modèle** reporté à la v3.0 (objectif F1 70-85 %, nécessite des données d'entraînement issues des validations utilisateurs v1.x/v2.x)

Voir l'analyse complète : [docs/qa/ner-accuracy-report.md](docs/qa/ner-accuracy-report.md) | Référence historique : [docs/nlp-benchmark-report.md](docs/nlp-benchmark-report.md)

### Flux de validation (Story 1.7 — Terminé)

L'interface de validation offre une interface intuitive pilotée au clavier pour relire les entités détectées :

**Fonctionnalités :**
- ✅ **Regroupement par type d'entité** — Relecture PERSON → ORG → LOCATION dans un ordre logique
- ✅ **Affichage du contexte** — 10 mots avant/après chaque entité avec mise en surbrillance
- ✅ **Scores de confiance** — Code couleur de la confiance spaCy NER (vert > 80 %, jaune 60-80 %, rouge < 60 %)
- ✅ **Raccourcis clavier** — Actions à une touche : [Espace] Confirmer, [R] Rejeter, [E] Modifier, [A] Ajouter, [C] Changer le pseudonyme
- ✅ **Opérations par lot** — Accepter/rejeter toutes les entités d'un type en une fois (Maj+A/R)
- ✅ **Panneau d'aide** — Appuyez sur [H] pour la référence complète des commandes
- ✅ **Performance** — Moins de 2 minutes pour un document typique de 20-30 entités

**Étapes du flux :**
1. Écran de synthèse (décompte des entités par type)
2. Revue des entités par type avec contexte
3. Signalement des entités ambiguës pour examen attentif
4. Confirmation finale avec résumé des modifications
5. Traitement du document avec les entités validées

**Fonctionnalité de déduplication (Story 1.9) :** Les entités en double sont regroupées — validez une fois, appliquez à toutes les occurrences (réduction de 66 % du temps pour les documents volumineux).

**Regroupement de variantes d'entités (Story 4.6) :** Les formes apparentées d'une entité sont automatiquement fusionnées en un seul élément de validation. « Marie Dubois », « Pr. Dubois » et « Dubois » apparaissent comme un seul élément avec « Apparaît aussi sous : » affichant les formes variantes. Empêche le pontage transitif Union-Find pour les noms de famille ambigus partagés par des personnes différentes.

---

### Pile technologique

| Composant | Technologie | Version | Rôle |
|-----------|------------|---------|------|
| **Environnement d'exécution** | Python | 3.10-3.12 | Validé en CI/CD (3.13+ pas encore testé) |
| **Bibliothèque NLP** | spaCy | 3.8.0 | Détection d'entités en français (fr_core_news_lg) |
| **Framework CLI** | Typer | 0.9+ | Interface en ligne de commande |
| **Base de données** | SQLite | 3.35+ | Stockage local des tables de correspondance en mode WAL |
| **Chiffrement** | cryptography (AESSIV) | 44.0+ | Chiffrement AES-256-SIV pour les champs sensibles (dérivation de clé PBKDF2, protégé par phrase secrète) |
| **ORM** | SQLAlchemy | 2.0+ | Abstraction de la base de données et gestion des sessions |
| **Interface de validation** | rich | 13.7+ | Revue interactive des entités en CLI |
| **Saisie clavier** | readchar | 4.2+ | Capture de touche unique pour l'interface de validation |
| **Tests** | pytest | 7.4+ | Tests unitaires et d'intégration |
| **CI/CD** | GitHub Actions | N/A | Tests automatisés (Windows/Mac/Linux) |

---

## 🤔 Pourquoi l'assistance IA plutôt que l'automatisation complète ?

**Réponse courte :** La confidentialité et la conformité exigent une supervision humaine.

**Réponse détaillée :**
1. **Défendabilité RGPD** — La vérification humaine fournit une piste d'audit juridique
2. **Zéro faux négatif** — L'IA manque des entités, les humains les rattrapent (couverture à 100 %)
3. **Limites actuelles du NLP** — Les modèles français sur des documents d'entretiens/professionnels : 29,5 % F1 nativement (l'approche hybride atteint environ 60 %)
4. **Meilleur que les alternatives :**
   - ✅ **vs Rédaction manuelle :** 50 %+ plus rapide (pré-détection IA)
   - ✅ **vs Services cloud :** Traitement 100 % local (aucune fuite de données)
   - ✅ **vs Outils entièrement automatiques :** Précision de 100 % (vérification humaine)

**Point de vue utilisateur :**
> « Je VEUX une relecture humaine pour des raisons de conformité. L'IA me fait gagner du temps en pré-identifiant les entités, mais je garde le contrôle sur la décision finale. » — Responsable conformité

---

## 🎯 Cas d'usage

### 1. **Conformité éthique en recherche**
**Scénario :** Chercheur universitaire avec 50 transcriptions d'entretiens nécessitant l'approbation d'un comité d'éthique

**Sans RGPD Pseudonymizer :**
- ❌ Rédaction manuelle : 16-25 heures
- ❌ Détruit la cohérence du document pour l'analyse
- ❌ Sujet aux erreurs (fatigue humaine)

**Avec RGPD Pseudonymizer :**
- ✅ Pré-détection IA : environ 30 min de traitement
- ✅ Validation humaine : environ 90 min de relecture (50 docs × environ 2 min chacun)
- ✅ Total : **2-3 heures** (gain de temps de 85 %+)
- ✅ Piste d'audit pour le comité d'éthique

---

### 2. **Analyse de documents RH**
**Scénario :** Équipe RH analysant les retours des employés avec ChatGPT

**Sans RGPD Pseudonymizer :**
- ❌ Impossible d'utiliser ChatGPT (violation du RGPD — noms des employés exposés)
- ❌ Analyse manuelle uniquement (lente, perspectives limitées)

**Avec RGPD Pseudonymizer :**
- ✅ Pseudonymisation locale (noms des employés → pseudonymes)
- ✅ Envoi à ChatGPT en toute sécurité (aucune donnée personnelle exposée)
- ✅ Obtenir des analyses IA tout en restant conforme au RGPD

---

### 3. **Préparation de documents juridiques**
**Scénario :** Cabinet d'avocats préparant des dossiers pour une recherche juridique assistée par IA

**Sans RGPD Pseudonymizer :**
- ❌ Service de pseudonymisation cloud (risque tiers)
- ❌ Rédaction manuelle (heures facturables coûteuses)

**Avec RGPD Pseudonymizer :**
- ✅ Traitement 100 % local (confidentialité client)
- ✅ Précision vérifiée par l'humain (défendabilité juridique)
- ✅ Correspondances réversibles (dé-pseudonymisation possible si nécessaire)

---

## ⚖️ Conformité RGPD

### Comment RGPD Pseudonymizer soutient la conformité

| Exigence RGPD | Mise en œuvre |
|----------------|---------------|
| **Art. 25 — Protection des données dès la conception** | Traitement local, aucune dépendance cloud, stockage chiffré |
| **Art. 30 — Registre des traitements** | Journaux d'audit complets (Story 2.5) : table d'opérations suivant horodatage, fichiers traités, nombre d'entités, version du modèle, thème, succès/échec, temps de traitement ; export JSON/CSV pour le reporting de conformité |
| **Art. 32 — Mesures de sécurité** | Chiffrement AES-256-SIV avec dérivation de clé PBKDF2 (210 000 itérations), stockage protégé par phrase secrète, chiffrement au niveau des colonnes pour les champs sensibles |
| **Art. 35 — Analyse d'impact sur la protection des données** | Méthodologie transparente, approche citable pour la documentation AIPD |
| **Considérant 26 — Pseudonymisation** | Correspondance cohérente des pseudonymes, réversibilité avec phrase secrète |

### Ce que signifie la pseudonymisation (juridiquement)

**Selon l'article 4(5) du RGPD :**
> « La pseudonymisation désigne le traitement de données à caractère personnel de telle façon que celles-ci ne puissent plus être attribuées à une personne concernée précise **sans avoir recours à des informations supplémentaires**, pour autant que ces informations supplémentaires soient conservées séparément. »

**Approche de RGPD Pseudonymizer :**
- ✅ **Données personnelles remplacées :** Noms, lieux, organisations → pseudonymes
- ✅ **Stockage séparé :** Table de correspondance chiffrée avec phrase secrète (séparée des documents)
- ✅ **Réversibilité :** Les utilisateurs autorisés peuvent dé-pseudonymiser avec la phrase secrète
- ⚠️ **Note :** La pseudonymisation réduit le risque mais ne rend **PAS** les données anonymes

**Recommandation :** Consultez votre Délégué à la Protection des Données (DPD) pour des conseils de conformité spécifiques.

---

## 🛠️ État du développement

**Les 4 Epics MVP terminés + Epic 5 en cours** — v1.0.7 (février 2026).

- ✅ **Epic 1 :** Fondations et validation NLP (9 stories) — Intégration spaCy, interface de validation, détection hybride, déduplication des entités
- ✅ **Epic 2 :** Moteur de pseudonymisation principal (9 stories) — Bibliothèques de pseudonymes, chiffrement, journalisation d'audit, traitement par lot, correspondance 1:1 RGPD
- ✅ **Epic 3 :** Interface CLI et traitement par lot (7 stories) — 8 commandes CLI, suivi de progression, fichiers de configuration, traitement parallèle par lot, perfectionnement UX
- ✅ **Epic 4 :** Préparation au lancement (8 stories) — Validation de l'utilité LLM, tests multi-plateformes, documentation, suite de précision NER, validation des performances, intégration des retours bêta, refactorisation du code, préparation au lancement
- 🔄 **Epic 5 :** Améliorations rapides et conformité RGPD (3 stories terminées) — Effacement article 17 RGPD, pseudonymes sensibles au genre, améliorations de la précision NER (F1 29,74 % → 59,97 %)
- **Total :** 36 stories, 1198+ tests, 86 %+ de couverture, tous les critères qualité au vert

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour plus de détails sur :
- Les signalements de bugs et demandes de fonctionnalités
- La configuration de l'environnement de développement et les exigences de qualité du code
- Le processus de PR et le format des messages de commit

Veuillez lire notre [Code de conduite](CODE_OF_CONDUCT.md) avant de participer.

---

## 📧 Contact et support

**Responsable du projet :** Lionel Deveaux — [@LioChanDaYo](https://github.com/LioChanDaYo)

**Pour vos questions et demandes de support :**
- 💬 [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) — Questions générales, cas d'usage
- 🐛 [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues) — Signalements de bugs, demandes de fonctionnalités
- 📖 [SUPPORT.md](SUPPORT.md) — Processus de support complet et checklist d'auto-diagnostic

---

## 📜 Licence

Ce projet est distribué sous la [licence MIT](LICENSE).

---

## 🙏 Remerciements

**Construit avec :**
- [spaCy](https://spacy.io/) — Bibliothèque NLP de niveau industriel
- [Typer](https://typer.tiangolo.com/) — Framework CLI moderne
- [rich](https://rich.readthedocs.io/) — Mise en forme CLI élégante

**Inspiré par :**
- Les principes de protection de la vie privée dès la conception du RGPD
- Les exigences éthiques de la recherche universitaire
- Le besoin concret d'analyse sécurisée de documents par IA

**Méthodologie :**
- Développé avec le framework [BMAD-METHOD™](https://bmad.ai)
- Élicitation interactive et validation multi-perspectives

---

## ⚠️ Avertissement

**RGPD Pseudonymizer est un outil d'aide à la conformité RGPD. Il ne fournit PAS de conseils juridiques.**

**Notes importantes :**
- ⚠️ La pseudonymisation réduit le risque mais n'est PAS de l'anonymisation
- ⚠️ Vous restez le responsable du traitement au sens du RGPD
- ⚠️ Consultez votre DPD ou votre conseil juridique pour des orientations de conformité
- ⚠️ La validation humaine est OBLIGATOIRE — ne sautez pas les étapes de relecture
- ⚠️ Testez rigoureusement avant toute utilisation en production

**Limitations du MVP v1.0 :**
- Détection IA : environ 60 % F1 de référence (pas 85 %+)
- Validation requise pour TOUS les documents (pas optionnelle)
- Langue française uniquement (anglais, espagnol, etc. dans les versions futures)
- Formats textuels uniquement (.txt, .md — pas de PDF/DOCX en v1.0)

---

## 🧪 Tests

### Exécution des tests

Le projet comprend des tests unitaires et d'intégration complets couvrant le flux de validation, la détection NLP et les fonctionnalités principales.

**Note pour les utilisateurs Windows :** En raison de violations d'accès connues avec spaCy sous Windows ([spaCy issue #12659](https://github.com/explosion/spaCy/issues/12659)), la CI Windows n'exécute que les tests indépendants de spaCy. La suite complète de tests s'exécute sous Linux/macOS.

**Exécuter tous les tests :**
```bash
poetry run pytest -v
```

**Exécuter uniquement les tests unitaires :**
```bash
poetry run pytest tests/unit/ -v
```

**Exécuter uniquement les tests d'intégration :**
```bash
poetry run pytest tests/integration/ -v
```

**Exécuter les tests de validation de précision (nécessite le modèle spaCy) :**
```bash
poetry run pytest tests/accuracy/ -v -m accuracy -s
```

**Exécuter les tests de performance et de stabilité (nécessite le modèle spaCy) :**
```bash
# Tous les tests de performance (stabilité, mémoire, démarrage, stress)
poetry run pytest tests/performance/ -v -s -p no:benchmark --timeout=600

# Tests de benchmark uniquement (pytest-benchmark)
poetry run pytest tests/performance/ --benchmark-only -v -s
```

**Exécuter avec rapport de couverture :**
```bash
poetry run pytest --cov=gdpr_pseudonymizer --cov-report=term-missing --cov-report=html
```

**Exécuter spécifiquement les tests d'intégration du flux de validation :**
```bash
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

**Exécuter les vérifications qualité :**
```bash
# Vérification du formatage du code
poetry run black --check gdpr_pseudonymizer tests

# Formatage automatique du code
poetry run black gdpr_pseudonymizer tests

# Vérification du linting
poetry run ruff check gdpr_pseudonymizer tests

# Vérification des types
poetry run mypy gdpr_pseudonymizer
```

**Exécuter uniquement les tests compatibles Windows (excluant les tests dépendants de spaCy) :**
```bash
# Exécuter les tests unitaires sans spaCy (selon le modèle CI Windows)
poetry run pytest tests/unit/test_benchmark_nlp.py tests/unit/test_config_manager.py tests/unit/test_data_models.py tests/unit/test_file_handler.py tests/unit/test_logger.py tests/unit/test_naive_processor.py tests/unit/test_name_dictionary.py tests/unit/test_process_command.py tests/unit/test_project_config.py tests/unit/test_regex_matcher.py tests/unit/test_validation_models.py tests/unit/test_validation_stub.py -v

# Exécuter les tests d'intégration du flux de validation (compatibles Windows)
poetry run pytest tests/integration/test_validation_workflow_integration.py -v
```

### Couverture des tests

- **Tests unitaires :** 946+ tests couvrant les modèles de validation, les composants d'interface, le chiffrement, les opérations de base de données, la journalisation d'audit, le suivi de progression, la détection de genre et la logique principale
- **Tests d'intégration :** 90 tests pour les flux de bout en bout incluant la validation (Story 2.0.1), les opérations de base de données chiffrée (Story 2.4), la logique compositionnelle et la détection hybride
- **Tests de précision :** 22 tests validant la précision NER contre un corpus de référence de 25 documents (Story 4.4)
- **Tests de performance :** 15 tests validant tous les objectifs NFR — benchmarks par document (NFR1), performance par lot (NFR2), profilage mémoire (NFR4), temps de démarrage (NFR5), stabilité/taux d'erreur (NFR6), tests de stress (Story 4.5)
- **Couverture actuelle :** 86 %+ sur tous les modules (100 % pour le module de progression, 91,41 % pour AuditRepository)
- **Total des tests :** 1198+
- **CI/CD :** Tests exécutés sur Python 3.10-3.12 sous Windows, macOS et Linux
- **Critères qualité :** Tous validés (Black, Ruff, mypy, pytest)

### Scénarios clés des tests d'intégration

La suite de tests d'intégration couvre :

**Flux de validation (19 tests) :**
- ✅ Flux complet : détection d'entités → synthèse → revue → confirmation
- ✅ Actions utilisateur : confirmer (Espace), rejeter (R), modifier (E), ajouter une entité (A), changer le pseudonyme (C), navigation dans le contexte (X)
- ✅ Transitions d'état : PENDING → CONFIRMED/REJECTED/MODIFIED
- ✅ Déduplication d'entités avec revue groupée
- ✅ Cas limites : documents vides, documents volumineux (320+ entités), interruption Ctrl+C, saisie invalide
- ✅ Opérations par lot : Accepter tout le type (Maj+A), Rejeter tout le type (Maj+R) avec invites de confirmation
- ✅ Simulation d'entrée utilisateur : Simulation complète des interactions clavier et des invites

**Base de données chiffrée (9 tests) :**
- ✅ Flux de bout en bout : init → open → save → query → close
- ✅ Cohérence inter-sessions : Même phrase secrète retrouve les mêmes données
- ✅ Idempotence : Requêtes multiples retournant les mêmes résultats
- ✅ Données chiffrées au repos : Champs sensibles stockés chiffrés dans SQLite
- ✅ Intégration de la logique compositionnelle : Requêtes de composants chiffrés
- ✅ Intégration des dépôts : Tous les dépôts (correspondance, audit, métadonnées) fonctionnent avec la session chiffrée
- ✅ Lectures concurrentes : Le mode WAL permet plusieurs lecteurs simultanés
- ✅ Index de la base de données : Optimisation des performances de requête vérifiée
- ✅ Rollback de sauvegarde par lot : Intégrité transactionnelle en cas d'erreur

---

## 📊 Métriques du projet (au 2026-02-13)

| Métrique | Valeur | Statut |
|----------|--------|--------|
| **Progression du développement** | v1.0.7 | ✅ Les 4 Epics MVP + Epic 5 en cours |
| **Stories terminées** | 36 (Epic 1-5) | ✅ Epics 1-4 terminés + Stories 5.1, 5.2, 5.3 |
| **Utilité LLM (NFR10)** | 4,27/5,0 (85,4 %) | ✅ VALIDÉ (seuil : 80 %) |
| **Succès d'installation (NFR3)** | 87,5 % (7/8 plateformes) | ✅ VALIDÉ (seuil : 85 %) |
| **Première pseudonymisation (NFR14)** | 100 % en moins de 30 min | ✅ VALIDÉ (seuil : 80 %) |
| **Bugs critiques trouvés** | 1 (Story 2.8) | ✅ RÉSOLU — Epic 3 débloqué |
| **Taille du corpus de test** | 25 docs, 1 737 entités | ✅ Complet (après nettoyage) |
| **Précision NLP (référence)** | 29,5 % F1 (spaCy seul) | ✅ Mesuré (Story 1.2) |
| **Précision hybride (NLP+Regex)** | 59,97 % F1 (+30,23pp vs référence) | ✅ Story 5.3 terminé |
| **Précision finale (IA+Humain)** | 100 % (validé) | 🎯 Par conception |
| **Bibliothèques de pseudonymes** | 3 thèmes (2 426 noms + 240 lieux + 588 organisations) | ✅ Stories 2.1, 3.0, 4.6 terminées |
| **Correspondance compositionnelle** | Opérationnel (réutilisation de composants + suppression des titres + noms composés) | ✅ Stories 2.2, 2.3 terminées |
| **Traitement par lot** | Architecture validée (multiprocessing.Pool, accélération 1,17x-2,5x) | ✅ Story 2.7 terminé |
| **Stockage chiffré** | AES-256-SIV avec protection par phrase secrète (PBKDF2 210K itérations) | ✅ Story 2.4 terminé |
| **Journalisation d'audit** | Conformité article 30 RGPD (table d'opérations + export JSON/CSV) | ✅ Story 2.5 terminé |
| **Interface de validation** | Opérationnelle avec déduplication | ✅ Stories 1.7, 1.9 terminées |
| **Temps de validation** | < 2 min (20-30 entités), < 5 min (100 entités) | ✅ Objectifs atteints |
| **Performance mono-document (NFR1)** | environ 6s en moyenne pour 3,5K mots | ✅ VALIDÉ (seuil < 30s, marge de 80 %) |
| **Performance par lot (NFR2)** | environ 5 min pour 50 docs | ✅ VALIDÉ (seuil < 30min, marge de 83 %) |
| **Utilisation mémoire (NFR4)** | environ 1 Go pic mesuré par Python | ✅ VALIDÉ (seuil < 8 Go) |
| **Démarrage CLI (NFR5)** | 0,56s (help), 6,0s (démarrage à froid avec modèle) | ✅ VALIDÉ (< 5s pour le démarrage CLI) |
| **Taux d'erreur (NFR6)** | environ 0 % d'erreurs inattendues | ✅ VALIDÉ (seuil < 10 %) |
| **Couverture de test** | 1198+ tests, 86 %+ de couverture | ✅ Tous les contrôles qualité validés |
| **Critères qualité** | Ruff, mypy, pytest | ✅ Tous validés (0 problème) |
| **Langues prises en charge** | Français | 🇫🇷 v1.0 uniquement |
| **Formats pris en charge** | .txt, .md | 📝 Périmètre v1.0 |

---

## 🔗 Liens rapides

- 📘 [PRD complet](docs/.ignore/prd.md) — Exigences produit complètes
- 📊 [Rapport de benchmark](docs/nlp-benchmark-report.md) — Analyse de la précision NLP
- 🎨 [Stratégie de positionnement](docs/positioning-messaging-v2-assisted.md) — Marketing et messages clés
- 🏗️ [Documentation d'architecture](docs/architecture/) — Conception technique
- 📋 [Checklist d'approbation](docs/PM-APPROVAL-CHECKLIST.md) — Suivi des décisions PM

---

**Dernière mise à jour :** 2026-02-13 (v1.0.7 — Epic 5 en cours : effacement RGPD, pseudonymes sensibles au genre, précision NER 59,97 % F1)
