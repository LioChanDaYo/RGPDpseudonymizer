# GDPR Pseudonymizer

**Pseudonymisez vos documents français grâce à l'IA, avec relecture humaine obligatoire**

Préparez vos documents sensibles pour l'analyse par IA en toute sérénité : traitement entièrement local, relecture humaine systématique, conformité RGPD.

---

## Qu'est-ce que GDPR Pseudonymizer ?

GDPR Pseudonymizer est un **outil en ligne de commande conçu pour la confidentialité**. Il associe la rapidité de l'IA à la rigueur de la relecture humaine pour pseudonymiser des documents en français. Contrairement aux solutions entièrement automatiques ou aux services cloud, il mise sur l'**absence totale de faux négatifs** et sur la **solidité juridique** grâce à un processus de validation obligatoire.

**Pour qui ?**

- **Organisations sensibles à la protection des données** ayant besoin d'analyses IA conformes au RGPD
- **Chercheurs universitaires** soumis aux exigences des comités d'éthique
- **Équipes juridiques et RH** qui ont besoin d'une pseudonymisation opposable
- **Utilisateurs de LLM** souhaitant exploiter des documents confidentiels en toute sécurité

---

## Fonctionnalités principales

### Confidentialité au cœur de l'architecture

- **Traitement 100 % local** — vos données ne quittent jamais votre machine
- **Aucune dépendance cloud** — fonctionne entièrement hors ligne après installation
- **Tables de correspondance chiffrées** — chiffrement AES-256-SIV, protégé par mot de passe
- **Aucune télémétrie** — ni collecte analytique, ni communication externe

### IA + relecture humaine

- **Détection hybride** — l'IA repère environ 60 % des entités (NLP + expressions régulières + dictionnaire géographique, F1 59,97 %)
- **Validation obligatoire** — vous vérifiez et confirmez chaque entité (précision finale de 100 %)
- **Interface de validation rapide** — raccourcis clavier, actions groupées, moins de 2 min par document
- **Regroupement des variantes** — les formes apparentées (« Marie Dubois », « Pr. Dubois », « Dubois ») sont fusionnées en un seul élément à valider

### Traitement par lot

- **Pseudonymes cohérents** — une même entité reçoit le même pseudonyme dans tous les documents
- **Résolution par composition** — « Marie Dubois » et « Marie » sont résolus de façon cohérente
- **Traitement sélectif** — option `--entity-types` pour ne traiter que certains types (PERSON, LOCATION, ORG)
- **Plus de 50 % de temps gagné** par rapport à la rédaction manuelle

### Pseudonymes thématiques

Trois thèmes intégrés : **Neutre** (prénoms français), **Star Wars** et **Le Seigneur des Anneaux**.

---

## Prise en main rapide

```bash
# Installer depuis PyPI
pip install gdpr-pseudonymizer
python -m spacy download fr_core_news_lg

# Traiter un document
gdpr-pseudo process interview.txt
```

Consultez le [guide d'installation](installation.fr.md) pour des instructions détaillées selon votre plateforme et le [tutoriel](tutorial.fr.md) pour des guides pas à pas.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Installation](installation.fr.md) | Instructions selon votre plateforme (Windows, macOS, Linux, Docker) |
| [Tutoriel](tutorial.fr.md) | Guides pas à pas |
| [Référence CLI](CLI-REFERENCE.md) | Documentation complète des commandes |
| [FAQ](faq.fr.md) | Questions fréquentes |
| [Dépannage](troubleshooting.fr.md) | Erreurs courantes et solutions |
| [Méthodologie](methodology.md) | Approche technique, conformité RGPD, citation académique |
| [Référence API](api-reference.md) | Documentation des modules pour les développeurs |

---

## Comment ça marche

1. **Détecter** — Le NLP hybride + expressions régulières repère les entités candidates dans le texte français
2. **Valider** — Vous passez en revue chaque entité avec son contexte
3. **Pseudonymiser** — Les entités confirmées sont remplacées par des pseudonymes thématiques
4. **Stocker** — Les correspondances sont chiffrées dans une base locale pour assurer la cohérence et la réversibilité

---

## Conformité RGPD

GDPR Pseudonymizer contribue à la conformité avec les articles 4(5), 25, 30, 32 et 89 du Règlement général sur la protection des données. Consultez le document [Méthodologie](methodology.md) pour la correspondance complète avec le RGPD.

**Important :** Les données pseudonymisées restent des données personnelles au sens du RGPD. Consultez votre délégué à la protection des données pour des conseils de conformité adaptés.

---

## Statut

**Version actuelle :** v1.0.7 (février 2026)

**Environnements pris en charge :** Python 3.10-3.12 | Windows, macOS, Linux | Formats .txt et .md | Français

Consultez la [FAQ](faq.fr.md) pour la feuille de route du produit.
