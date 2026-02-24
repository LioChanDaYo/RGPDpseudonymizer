# Méthodologie : pseudonymisation de textes français conforme au RGPD

**GDPR Pseudonymizer** — Méthodologie technique et référence académique

**Version :** 1.0
**Date :** 2026-02-08
**Public visé :** comités d'éthique, documentation AIPD, publications académiques

---

## 1. Introduction

GDPR Pseudonymizer est un outil de pseudonymisation assisté par IA, conçu pour les documents en langue française. Il combine la reconnaissance automatique d'entités nommées (NER) avec une validation humaine obligatoire afin d'atteindre une précision de 100 % tout en préservant l'utilité des documents pour l'analyse en aval.

Ce document décrit la méthodologie technique, les procédures de validation, les contrôles qualité et la correspondance avec le RGPD, à destination de la recherche académique, des dossiers soumis aux comités d'éthique et des Analyses d'Impact relatives à la Protection des Données (AIPD).

### 1.1 Philosophie de conception

L'outil repose sur une approche à **contrôle humain** de la pseudonymisation :

1. **Pré-détection par l'IA** : identification des entités candidates par une technique hybride NLP + expressions régulières
2. **Validation humaine obligatoire** : chaque entité est vérifiée avant remplacement
3. **Pseudonymisation cohérente** : maintien de la cohérence au sein d'un corpus multi-documents
4. **Traitement intégralement local** : aucune donnée ne quitte la machine de l'utilisateur

Cette approche privilégie le **zéro faux négatif** (aucune entité oubliée) plutôt que l'automatisation complète, en reconnaissant que la précision actuelle du NLP sur les documents français (entretiens, documents professionnels) n'atteint pas le seuil requis pour une pseudonymisation sans supervision.

---

## 2. Approche technique

### 2.1 Choix de la bibliothèque NER

La bibliothèque NER a été sélectionnée par un benchmark contrôlé sur un corpus de 25 documents contenant 1 855 entités annotées manuellement (PERSON, LOCATION, ORGANIZATION), issues de transcriptions d'entretiens et de documents professionnels français.

**Résultats du benchmark (Story 1.2, 2026-01-16) :**

| Bibliothèque | Modèle | Précision | Rappel | Score F1 |
|--------------|--------|-----------|--------|----------|
| **spaCy** | `fr_core_news_lg` 3.8.0 | 27,0 % | 32,7 % | **29,5 %** |
| Stanza | `fr_default` | 10,3 % | 14,1 % | 11,9 % |

**Performance par type d'entité (spaCy) :**

| Type d'entité | Vérité terrain | Précision | Rappel | F1 |
|---------------|---------------|-----------|--------|-----|
| PERSON | 1 627 | 37,8 % | 31,3 % | 34,2 % |
| LOCATION | 123 | 29,6 % | 58,5 % | 39,3 % |
| ORGANIZATION | 105 | 3,8 % | 27,6 % | 6,7 % |

**Justification du choix :** spaCy a été retenu pour son score F1 2,5× supérieur, sa vitesse d'inférence plus rapide, sa communauté plus large et sa meilleure documentation. Les deux bibliothèques étant en deçà de l'objectif initial de 85 % de F1, une stratégie de détection hybride avec validation humaine obligatoire a été adoptée.

**Référence :** l'analyse complète du benchmark figure dans `docs/nlp-benchmark-report.md`.

### 2.2 Stratégie de détection hybride

Pour compenser les limites du NER de base, une approche hybride combine le NLP avec la détection par règles et expressions régulières (Story 1.8, 2026-01-22) :

**Pipeline de détection :**

```
Texte d'entrée
    ├── spaCy NER (fr_core_news_lg)     →  Entités détectées par NLP
    ├── Détection par expressions rég.   →  Entités détectées par règles
    │   ├── Titres français (M., Mme, Dr., Maître/Me)
    │   ├── Noms composés (Jean-Pierre, Marie-Claire)
    │   ├── Dictionnaire de noms français
    │   ├── Suffixes d'organisations (SA, SARL, SAS, Cabinet)
    │   └── Filtrage des faux positifs (titres isolés, mots-étiquettes)
    └── Déduplication                    →  Ensemble d'entités fusionné et dédupliqué
```

**Gains de performance de l'approche hybride :**

| Métrique | spaCy seul | Hybride (NLP + regex) | Amélioration |
|----------|-----------|----------------------|--------------|
| Total d'entités détectées | 2 679 | 3 625 | +35,3 % |
| Entités PERSON | 1 612 | 2 454 | +52,2 % |
| Temps de traitement par doc. | 0,07 s | 0,07 s | Pas de surcoût |

**Référence :** benchmark hybride complet dans `docs/hybrid-benchmark-report.md`.

### 2.3 Algorithme de pseudonymisation

Le moteur de pseudonymisation repose sur une **approche par composition** pour garantir la cohérence interne :

**Principes fondamentaux :**

1. **Résolution par composants :** les noms complets sont décomposés en composants (par ex. « Marie Dubois » → [« Marie », « Dubois »]), chacun associé à un composant de pseudonyme. Les références partielles (« Marie » seul) sont résolues vers le même composant de pseudonyme (« Leia »).

2. **Bibliothèques de pseudonymes à thème :** trois bibliothèques fournissent des ensembles de pseudonymes culturellement distincts :
   - **Neutral :** noms à consonance française, vraies villes françaises, noms d'entreprises réalistes
   - **Star Wars :** personnages, planètes et factions de l'univers Star Wars
   - **Le Seigneur des Anneaux :** personnages et lieux de la Terre du Milieu de Tolkien

3. **Couverture par type d'entité :**
   - PERSON : prénom + nom de famille avec prise en compte du genre (lorsque le NER fournit la classification)
   - LOCATION : villes, régions, pays
   - ORGANIZATION : entreprises, institutions, organismes

4. **Prétraitement des noms français :**
   - Suppression des titres : « Dr. Marie Dubois » → « Marie Dubois » (le titre est conservé dans le document de sortie)
   - Noms composés : « Jean-Pierre » traité comme unité indivisible
   - Déduplication : les entités identiques sont validées une seule fois et le remplacement s'applique à toutes les occurrences

### 2.4 Schéma de chiffrement

Les correspondances sont stockées dans une base de données SQLite chiffrée à l'aide de primitives cryptographiques conformes aux standards :

| Composant | Implémentation | Standard |
|-----------|----------------|----------|
| **Chiffrement** | AES-256-SIV (AEAD déterministe) | RFC 5297, approuvé NIST |
| **Dérivation de clé** | PBKDF2-HMAC-SHA256 | NIST SP 800-132 |
| **Itérations** | 210 000 | Recommandation OWASP 2023 |
| **Sel** | 32 octets, aléatoire cryptographique | Unique par base de données |

**Choix du chiffrement déterministe :** AES-256-SIV permet d'effectuer des recherches sur les champs chiffrés (par ex. vérifier si une correspondance existe déjà pour la résolution par composition). C'est un compromis standard utilisé par AWS DynamoDB, Google Tink et MongoDB pour les champs chiffrés interrogeables.

**Modèle de sécurité :** la base de données est exclusivement locale (aucune exposition réseau). Un attaquant devrait à la fois accéder physiquement à la machine et connaître le mot de passe pour déchiffrer les correspondances.

---

## 3. Procédures de validation et contrôles qualité

### 3.1 Processus de validation interactive

Chaque document fait l'objet d'une validation humaine obligatoire avant que la pseudonymisation ne soit appliquée :

1. **Détection des entités :** le pipeline hybride NLP + regex identifie les entités candidates
2. **Écran de synthèse :** le validateur voit le nombre d'entités par type (PERSON, LOCATION, ORG)
3. **Révision entité par entité :** chaque entité est présentée avec :
   - Le contexte environnant (10 mots avant et après, avec mise en surbrillance)
   - Le type d'entité et la source de détection (NLP ou regex)
   - Le score de confiance (code couleur : vert >80 %, jaune 60-80 %, rouge <60 %)
   - Le pseudonyme proposé depuis la bibliothèque à thème
4. **Actions du validateur :** accepter, rejeter (faux positif), modifier le texte de l'entité, ajouter une entité non détectée, changer le pseudonyme
5. **Actions groupées :** accepter ou rejeter toutes les entités d'un type donné
6. **Confirmation finale :** récapitulatif de toutes les décisions avant traitement

**Temps de validation :** moins de 2 minutes pour un document type (20-30 entités). La déduplication des entités réduit la durée de validation d'environ 66 % pour les documents volumineux contenant des entités répétées.

### 3.2 Métriques de précision NER

| Étape | Taux de détection | Faux positifs | Remarques |
|-------|-------------------|---------------|-----------|
| spaCy de base | 29,5 % F1 | Élevé | Pré-entraîné sur du texte d'actualité |
| Hybride (NLP + regex) | ~40-50 % F1 | Modéré | Rappel amélioré de +35,3 % |
| Après validation | 100 % de précision | 0 % | La vérification humaine détecte toutes les erreurs |

### 3.3 Conservation de l'utilité pour les LLM

L'utilité des documents pseudonymisés a été validée en aval selon la méthodologie « LLM comme juge » (Story 4.1, 2026-02-06) :

**Protocole :** comparaison A/B des réponses de LLM sur les versions originales et pseudonymisées de 10 documents représentatifs (5 transcriptions d'entretiens, 5 documents professionnels).

**Dimensions évaluées (échelle de 1 à 5) :**

| Dimension | Score moyen | Interprétation |
|-----------|------------|----------------|
| Fidélité thématique | 4,27/5,0 | Thèmes intégralement préservés |
| Cohérence relationnelle | 4,27/5,0 | Relations entre entités maintenues |
| Préservation des faits | 4,27/5,0 | Faits correctement extraits |
| **Utilité globale** | **4,27/5,0 (85,4 %)** | **Dépasse le seuil de 80 %** |

**Conclusion :** les documents pseudonymisés conservent une utilité suffisante pour l'analyse par LLM (résumé, extraction de thèmes, cartographie des relations).

**Référence :** rapport de validation complet dans `docs/llm-validation-report.md`.

---

## 4. Limites et cas particuliers

### 4.1 Précision du NER

- La précision de base du NER est de 29,5 % F1 (en deçà de l'objectif de 85 % pour un traitement sans supervision)
- La détection hybride améliore le score à ~40-50 % F1, mais la validation humaine reste obligatoire
- La détection d'ORG est particulièrement faible (3,8 % de précision = 96 % de faux positifs)
- Les modèles pré-entraînés sont optimisés pour le texte d'actualité, pas pour les entretiens ni les documents professionnels
- L'affinage avec les données de validation des utilisateurs est prévu pour la v3.0

### 4.2 Limites de langue et de format

- **Français uniquement** en v1.0 (anglais, espagnol, allemand prévus pour les versions suivantes)
- **Formats texte uniquement :** `.txt` et `.md` (pas de prise en charge des PDF, DOCX ou HTML en v1.0)
- Le texte doit utiliser l'encodage UTF-8 avec les accents français (é, è, à, etc.)

### 4.3 Cas particuliers de détection

- Les **noms français peu courants**, absents des données d'entraînement de spaCy, peuvent ne pas être détectés par le NLP (mais seront repérés lors de la validation)
- Les **noms composés** (« Jean-Pierre ») sont traités comme des unités indivisibles
- Les **titres** (« Dr. », « Maître », « Me ») sont supprimés pour la recherche de correspondance, mais conservés dans le document de sortie
- Les **abréviations** peuvent ne pas être détectées par le NLP ni par les expressions régulières
- L'**attribution de pseudonymes selon le genre** n'est pas encore disponible pour tous les cas (FE-007, prévue pour la v1.1)

### 4.4 Contraintes opérationnelles

- **Le mot de passe est irrécupérable :** en cas d'oubli, les correspondances ne peuvent pas être déchiffrées et la pseudonymisation ne peut pas être inversée
- **Cohérence des thèmes :** changer de thème en cours de projet produit des pseudonymes incohérents
- **Conçu pour un seul utilisateur :** pas de gestion d'accès multi-utilisateurs en v1.0 (SQLite en mode WAL permet les lectures concurrentes)

---

## 5. Correspondance avec le RGPD

### 5.1 Définition de la pseudonymisation (article 4(5))

> « La pseudonymisation désigne le traitement de données à caractère personnel de telle façon que celles-ci ne puissent plus être attribuées à une personne concernée précise sans avoir recours à des informations supplémentaires, pour autant que ces informations supplémentaires soient conservées séparément et soumises à des mesures techniques et organisationnelles afin de garantir que les données à caractère personnel ne sont pas attribuées à une personne physique identifiée ou identifiable. »
>
> — RGPD, article 4(5)

**Conformité de GDPR Pseudonymizer :**

| Exigence | Mise en œuvre |
|----------|-------------|
| Données personnelles remplacées par des pseudonymes | Les entités PERSON, LOCATION et ORG sont remplacées par des pseudonymes à thème |
| Informations supplémentaires conservées séparément | La base de correspondances est stockée séparément des documents pseudonymisés |
| Mesures techniques de séparation | Chiffrement AES-256-SIV avec protection par mot de passe |
| Réversibilité | Les utilisateurs autorisés peuvent lever la pseudonymisation à l'aide du mot de passe correct |

### 5.2 Pseudonymisation et anonymisation

**Distinction importante :** les données pseudonymisées restent des données personnelles au sens du RGPD (considérant 26). La table de correspondances permet la ré-identification, ce qui implique :

- Les obligations RGPD continuent de s'appliquer aux données pseudonymisées
- La base de correspondances doit être protégée par des mesures de sécurité appropriées
- La pseudonymisation est une **mesure de réduction des risques**, et non une exemption du RGPD

L'**anonymisation** (suppression irréversible de toute information identifiante) sort du périmètre de cet outil. GDPR Pseudonymizer préserve volontairement la réversibilité pour les cas d'usage qui le nécessitent (recherche académique, procédures judiciaires, exigences d'audit).

### 5.3 Matrice de conformité aux articles du RGPD

| Article RGPD | Exigence | Mise en œuvre | Statut |
|-------------|----------|--------------|--------|
| **Art. 4(5)** | Définition de la pseudonymisation | Remplacement cohérent avec correspondance chiffrée séparée | Conforme |
| **Art. 25** | Protection des données dès la conception | Traitement 100 % local, aucune dépendance cloud, stockage chiffré | Conforme |
| **Art. 32** | Sécurité du traitement | Chiffrement AES-256-SIV, dérivation de clé PBKDF2 (210 000 itérations), protection par mot de passe | Conforme |
| **Art. 30** | Registre des traitements | Journaux d'audit complets (horodatage, nombre d'entités, version du modèle, résultat) ; export JSON/CSV | Conforme |
| **Art. 35** | Analyse d'impact | Méthodologie transparente (ce document), pipeline de traitement auditable | Contribue à l'AIPD |
| **Art. 89** | Garanties pour la recherche | Pseudonymisation comme garantie technique à des fins de recherche ou de statistiques | Conforme |
| **Considérant 26** | Portée des données pseudonymisées | La documentation indique clairement que les données pseudonymisées restent des données personnelles | Reconnu |
| **Considérant 28** | Garantie technique | Pseudonymisation appliquée comme mesure technique et organisationnelle | Conforme |

### 5.4 Traçabilité (journal d'audit)

Chaque opération de pseudonymisation est enregistrée dans une table d'opérations :

| Champ | Description |
|-------|-------------|
| Horodatage | Date et heure de l'opération |
| Type d'opération | PROCESS, BATCH, IMPORT, etc. |
| Fichier(s) d'entrée | Chemin(s) du ou des documents sources |
| Nombre d'entités | Nombre d'entités traitées |
| Version du modèle | Modèle NLP utilisé (version de spaCy fr_core_news_lg) |
| Thème | Thème de la bibliothèque de pseudonymes |
| Résultat | Succès ou échec |
| Durée | Temps de traitement en secondes |

Les journaux d'audit peuvent être exportés au format JSON ou CSV pour les rapports de conformité :

```bash
poetry run gdpr-pseudo export audit_log.json
```

---

## 6. Citation académique

### 6.1 Comment citer cet outil

Pour référencer cet outil dans des publications académiques, des dossiers soumis à un comité d'éthique ou des AIPD :

> Deveaux, L. (2026). *GDPR Pseudonymizer: AI-Assisted Pseudonymization for French Documents with Human Verification* (Version 1.0) [Logiciel]. GitHub. https://github.com/LioChanDaYo/RGPDpseudonymizer

**BibTeX :**

```bibtex
@software{deveaux2026gdpr,
  author = {Deveaux, Lionel},
  title = {{GDPR Pseudonymizer: AI-Assisted Pseudonymization for French Documents with Human Verification}},
  year = {2026},
  version = {1.0},
  url = {https://github.com/LioChanDaYo/RGPDpseudonymizer}
}
```

### 6.2 Références

1. Parlement européen et Conseil. (2016). *Règlement (UE) 2016/679 (Règlement Général sur la Protection des Données)*. Journal officiel de l'Union européenne, L 119, 1-88.

2. Honnibal, M. et Montani, I. (2017). *spaCy 2: Natural language understanding with Bloom embeddings, convolutional neural networks and incremental parsing*. https://spacy.io

3. Harkins, P. (2023). *RFC 5297: Synthetic Initialization Vector (SIV) Authenticated Encryption Using the Advanced Encryption Standard (AES)*. IETF.

4. OWASP Foundation. (2023). *Password Storage Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

5. NIST. (2010). *SP 800-132: Recommendation for Password-Based Key Derivation*. National Institute of Standards and Technology.

---

## 7. Documents associés

- [Rapport de benchmark NLP](nlp-benchmark-report.md) — Évaluation complète des bibliothèques NER
- [Rapport de détection hybride](hybrid-benchmark-report.md) — Analyse des performances de l'approche hybride
- [Rapport de validation LLM](llm-validation-report.md) — Tests de conservation de l'utilité
- [Guide d'installation](installation.md) — Instructions d'installation
- [Référence de la ligne de commande](CLI-REFERENCE.md) — Documentation des commandes
- [FAQ](faq.md) — Questions fréquentes

---

**Avertissement :** cet outil contribue à la conformité RGPD mais ne constitue pas un avis juridique. Consultez votre Délégué à la Protection des Données (DPO) ou votre conseil juridique pour des orientations de conformité adaptées à votre contexte.
