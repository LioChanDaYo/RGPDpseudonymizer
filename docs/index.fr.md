# GDPR Pseudonymizer

**Pseudonymisation assistée par IA pour les documents français avec vérification humaine**

Transformez vos documents français sensibles pour une analyse IA sécurisée grâce au traitement local, à la revue humaine obligatoire et à la conformité RGPD.

---

## Qu'est-ce que GDPR Pseudonymizer ?

GDPR Pseudonymizer est un **outil CLI axé sur la confidentialité** qui combine l'efficacité de l'IA avec la précision humaine pour pseudonymiser les documents textuels en français. Contrairement aux outils entièrement automatiques ou aux services cloud, il privilégie le **zéro faux négatif** et la **défendabilité juridique** grâce à des flux de validation obligatoires.

**Idéal pour :**

- **Les organisations soucieuses de la confidentialité** nécessitant une analyse IA conforme au RGPD
- **Les chercheurs universitaires** soumis à des exigences de comités d'éthique
- **Les équipes juridiques/RH** nécessitant une pseudonymisation défendable
- **Les utilisateurs de LLM** souhaitant analyser des documents confidentiels en toute sécurité

---

## Fonctionnalités clés

### Architecture axée sur la confidentialité

- **Traitement 100 % local** -- vos données ne quittent jamais votre machine
- **Aucune dépendance cloud** -- fonctionne entièrement hors ligne après l'installation
- **Tables de correspondance chiffrées** -- chiffrement AES-256-SIV, protégé par phrase de passe
- **Zéro télémétrie** -- aucune analyse ni communication externe

### IA + Vérification humaine

- **Détection hybride** -- l'IA pré-détecte environ 60 % des entités (NLP + regex + dictionnaire géographique, F1 59,97 %)
- **Validation obligatoire** -- vous vérifiez et confirmez toutes les entités (garantit une précision de 100 %)
- **Interface de validation rapide** -- raccourcis clavier, opérations par lots, moins de 2 min par document
- **Regroupement de variantes d'entités** -- les formes apparentées (« Marie Dubois », « Pr. Dubois », « Dubois ») sont fusionnées en un seul élément de validation

### Traitement par lots

- **Pseudonymes cohérents** -- même entité = même pseudonyme dans tous les documents
- **Correspondance compositionnelle** -- « Marie Dubois » et « Marie » sont résolus de manière cohérente
- **Traitement sélectif des entités** -- option `--entity-types` pour filtrer par type (PERSON, LOCATION, ORG)
- **Plus de 50 % de gain de temps** par rapport à la rédaction manuelle

### Pseudonymes thématiques

Trois thèmes intégrés : **Neutre** (prénoms français), **Star Wars** et **Le Seigneur des Anneaux**.

---

## Démarrage rapide

```bash
# Installation depuis PyPI
pip install gdpr-pseudonymizer
python -m spacy download fr_core_news_lg

# Traiter un document
gdpr-pseudo process interview.txt
```

Consultez le [Guide d'installation](installation.fr.md) pour des instructions détaillées par plateforme et le [Tutoriel](tutorial.fr.md) pour des flux de travail pas à pas.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Installation](installation.fr.md) | Configuration par plateforme (Windows, macOS, Linux, Docker) |
| [Tutoriel](tutorial.fr.md) | Tutoriels et flux de travail pas à pas |
| [Référence CLI](CLI-REFERENCE.md) | Documentation complète des commandes |
| [FAQ](faq.fr.md) | Questions fréquentes et réponses |
| [Dépannage](troubleshooting.fr.md) | Référence des erreurs et solutions |
| [Méthodologie](methodology.md) | Approche technique, conformité RGPD, citation académique |
| [Référence API](api-reference.md) | Documentation des modules pour les développeurs |

---

## Comment ça fonctionne

1. **Détecter** -- Le NLP hybride + regex identifie les entités candidates dans le texte français
2. **Valider** -- Vous vérifiez chaque entité avec son contexte environnant
3. **Pseudonymiser** -- Les entités confirmées sont remplacées par des pseudonymes thématiques
4. **Stocker** -- Les correspondances sont chiffrées dans une base de données locale pour la cohérence et la réversibilité

---

## Conformité RGPD

GDPR Pseudonymizer aide à la conformité avec les articles 4(5), 25, 30, 32 et 89 du Règlement Général sur la Protection des Données. Consultez le document [Méthodologie](methodology.md) pour la cartographie complète de conformité.

**Important :** Les données pseudonymisées restent des données personnelles au sens du RGPD. Consultez votre Délégué à la Protection des Données pour des conseils de conformité spécifiques.

---

## Statut

**Version actuelle :** v1.0.7 (février 2026)

**Pris en charge :** Python 3.10-3.12 | Windows, macOS, Linux | Formats .txt et .md | Langue française

Consultez la [FAQ](faq.fr.md) pour la feuille de route du produit.
