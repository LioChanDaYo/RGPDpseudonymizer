# Foire aux questions

**GDPR Pseudonymizer** - Questions et réponses courantes

---

## Précision et détection

### Quelle précision puis-je attendre de la détection automatique ?

Le pipeline de détection hybride (NLP + regex) identifie automatiquement environ 40 à 50 % des entités dans un texte en français. Il s'agit d'une étape de pré-filtrage -- **vous examinez et confirmez chaque entité** lors du processus de validation obligatoire.

Après la validation humaine, la précision est de **100 %** car vous contrôlez la décision finale pour chaque entité.

### Pourquoi la précision de la reconnaissance d'entités nommées est-elle si faible ?

Le modèle spaCy `fr_core_news_lg` a été entraîné principalement sur des textes journalistiques, et non sur des transcriptions d'entretiens ou des documents d'entreprise. Les particularités linguistiques propres à chaque domaine (registres conversationnels, niveaux de formalité variés) réduisent la précision du modèle tel quel. Un benchmark réalisé sur 25 documents en français comportant 1 855 entités a mesuré un F1 de 29,5 % pour spaCy seul, s'améliorant à environ 40-50 % avec l'approche hybride.

Un ajustement fin à partir de données de validation réelles est prévu pour la v3.0 (objectif : 70-85 % de F1).

### Pourquoi la validation est-elle obligatoire ?

Parce que la détection par IA manque des entités. Avec un rappel d'environ 40-50 %, à peu près la moitié des entités passeraient inaperçues sans relecture humaine. Pour la conformité au RGPD, manquer ne serait-ce qu'une seule donnée personnelle pourrait constituer une violation de données. La validation obligatoire garantit **zéro faux négatif**.

### Comment traiter uniquement certains types d'entités ?

Utilisez le flag `--entity-types` avec une liste de types séparés par des virgules :

```bash
# Traiter uniquement les entités PERSON
gdpr-pseudo process doc.txt --entity-types PERSON

# Traiter PERSON et LOCATION (ignorer ORG)
gdpr-pseudo batch ./documents/ --entity-types PERSON,LOCATION
```

Les types valides sont `PERSON`, `LOCATION` et `ORG`. En l'absence de ce flag, tous les types d'entités sont traités. Ce flag fonctionne avec les commandes `process` et `batch`.

### Qu'est-ce que le regroupement de variantes d'entités ?

Le regroupement de variantes d'entités fusionne automatiquement les différentes formes d'une même entité en un seul élément de validation. Par exemple, si un document contient « Marie Dubois », « Pr. Dubois » et « Dubois », l'interface de validation les affiche comme un seul élément avec la mention « Apparaît aussi sous : » listant les formes variantes.

Cela réduit la fatigue de validation en éliminant les demandes redondantes. Le regroupement tient compte du type d'entité :

- **PERSON :** Correspondance par nom de famille après suppression du titre (« Dr. Dubois » = « Dubois »). Les prénoms différents restent séparés (« Marie Dubois » vs « Jean Dubois »).
- **LOCATION :** Suppression des prépositions françaises (« à Lyon » = « Lyon »).
- **ORG :** Correspondance insensible à la casse (« ACME Corp » = « acme corp »).

---

## Formats de documents et langues

### Quels formats de documents sont pris en charge ?

La v1.0 prend en charge :
- **Texte brut** (`.txt`)
- **Markdown** (`.md`)

Les formats PDF, DOCX, HTML et autres ne sont pas pris en charge dans la v1.0. Convertissez vos fichiers en texte brut avant le traitement.

### Puis-je utiliser cet outil pour des documents non francophones ?

Non. La v1.0 est conçue exclusivement pour les textes en français. Le modèle NLP (`fr_core_news_lg`), les expressions régulières et les bibliothèques de pseudonymes sont tous spécifiques au français.

La prise en charge multilingue (anglais, espagnol, allemand) est prévue pour la v3.0.

### Quelles langues sont prises en charge ?

Uniquement le français dans la v1.0. L'outil utilise le modèle spaCy `fr_core_news_lg`, entraîné spécifiquement sur des textes en français.

---

## Conformité au RGPD

### Cet outil est-il conforme au RGPD ?

GDPR Pseudonymizer **facilite** la conformité au RGPD mais ne la garantit pas à lui seul. L'outil met en œuvre :

- **Article 4(5) :** Pseudonymisation avec stockage séparé et chiffré de la table de correspondance
- **Article 25 :** Protection des données dès la conception (traitement 100 % local, stockage chiffré)
- **Article 32 :** Mesures de sécurité (chiffrement AES-256-SIV, dérivation de clé PBKDF2)
- **Article 30 :** Registre des traitements (journalisation d'audit complète avec export)

**Important :** Les données pseudonymisées restent des données personnelles au sens du RGPD (considérant 26). Vous demeurez le responsable du traitement et devriez consulter votre Délégué à la Protection des Données pour des recommandations de conformité spécifiques.

Voir [Méthodologie](methodology.md) pour la correspondance complète avec le RGPD.

### La pseudonymisation est-elle identique à l'anonymisation ?

Non. La **pseudonymisation** remplace les informations identifiantes par des pseudonymes, mais reste réversible (grâce à la table de correspondance et à la phrase de passe). Les données pseudonymisées restent des données personnelles au sens du RGPD.

L'**anonymisation** supprime de manière irréversible toute information identifiante, rendant la ré-identification impossible. Le RGPD ne s'applique pas aux données véritablement anonymes.

GDPR Pseudonymizer effectue une pseudonymisation, et non une anonymisation. C'est un choix de conception -- de nombreux cas d'usage nécessitent la réversibilité (suivi de recherches universitaires, procédures judiciaires, exigences d'audit).

### Mes données quittent-elles ma machine ?

Non. Tout le traitement s'effectue en local. Il n'y a aucune dépendance cloud, aucun appel API, aucune télémétrie ni aucune communication réseau. Après l'installation initiale (téléchargement du modèle spaCy), l'outil fonctionne entièrement hors ligne.

---

## Comparaison avec les alternatives

### Comment cet outil se compare-t-il à la rédaction manuelle ?

| Aspect | Rédaction manuelle | GDPR Pseudonymizer |
|--------|-------------------|---------------------|
| **Temps par document** | 15-30 minutes | 2-5 minutes (pré-détection IA + validation) |
| **Précision** | Sujette à l'erreur humaine | 100 % (validation obligatoire) |
| **Cohérence** | Difficile entre documents | Garantie (même entité = même pseudonyme) |
| **Réversibilité** | Impossible | Oui (table de correspondance chiffrée) |
| **Piste d'audit** | Journalisation manuelle | Automatique (journalisation des opérations, export JSON/CSV) |
| **Coût pour 50 documents** | 16-25 heures | 2-3 heures |

### Comment cet outil se compare-t-il aux services de pseudonymisation en cloud ?

| Aspect | Services cloud | GDPR Pseudonymizer |
|--------|---------------|---------------------|
| **Localisation des données** | Serveurs tiers | 100 % local |
| **Risque pour la vie privée** | Exposition des données au prestataire | Nul (aucun réseau) |
| **Coût** | Au document ou par abonnement | Gratuit (open source) |
| **Précision** | Variable (souvent sans validation) | 100 % (validation obligatoire) |
| **Personnalisation** | Limitée | Complète (pseudonymes thématiques, fichiers de configuration) |
| **Connexion Internet requise** | En permanence | Uniquement pour l'installation |

### Comment cet outil se compare-t-il aux outils entièrement automatiques ?

| Aspect | Outils automatiques | GDPR Pseudonymizer |
|--------|---------------------|---------------------|
| **Supervision humaine** | Aucune | Obligatoire |
| **Précision** | Dépend du NLP (souvent 70-90 %) | 100 % (validé par un humain) |
| **Rapidité** | Plus rapide (pas de validation) | Plus lent mais plus précis |
| **Défendabilité RGPD** | Plus faible (pas de piste d'audit humaine) | Plus forte (relecture humaine documentée) |
| **Faux négatifs** | Possibles | Zéro (par conception) |

---

## Feuille de route

### Quelles sont les évolutions prévues ?

**v1.0 (Actuelle - T2 2026) :** CLI assisté par IA avec validation obligatoire
- Traitement 100 % local, tables de correspondance chiffrées, pistes d'audit
- Langue française, formats .txt/.md

**v1.1 (T2-T3 2026) :** Améliorations rapides et conformité RGPD
- Droit à l'effacement (RGPD) : suppression sélective d'entités (commande `delete-mapping`, article 17)
- Attribution de pseudonymes tenant compte du genre pour les noms français
- Corrections de bugs et améliorations UX issues des retours bêta

**v2.0 (T3-T4 2026) :** Interface graphique de bureau
- Interface graphique encapsulant le noyau CLI (glisser-déposer, revue visuelle des entités)
- Exécutables autonomes (.exe, .app) -- aucune installation de Python requise
- Interface en français avec architecture d'internationalisation

**v3.0 (2027+) :** Précision NLP et automatisation
- Modèle de reconnaissance d'entités nommées affiné pour le français (objectif : 70-85 % de F1)
- Flag optionnel `--no-validate` pour les flux de travail à haute confiance
- Prise en charge multilingue (anglais, espagnol, allemand)

### Y aura-t-il une version avec interface graphique ?

Oui. La v2.0 (prévue T3-T4 2026) inclura une interface graphique de bureau avec traitement de documents par glisser-déposer, revue visuelle des entités et exécutables autonomes ne nécessitant pas l'installation de Python. Le public cible est constitué d'utilisateurs non techniques (équipes RH, juridiques, conformité).

### Puis-je contribuer ?

Pas encore. Le projet est en phase de pré-lancement. Après le lancement du MVP v1.0, les contributions seront les bienvenues : signalements de bugs, améliorations de la documentation, traductions et suggestions de fonctionnalités.

GitHub : https://github.com/LioChanDaYo/RGPDpseudonymizer

---

## Questions techniques

### Quel modèle NLP est utilisé ?

spaCy `fr_core_news_lg` (version 3.8.0), un grand modèle de langue française (~571 Mo). Il a été retenu après un benchmark comparatif avec Stanza, obtenant un score F1 2,5 fois supérieur sur le corpus de test.

### Comment la base de correspondance est-elle chiffrée ?

AES-256-SIV (chiffrement authentifié déterministe selon la RFC 5297) avec dérivation de clé PBKDF2-HMAC-SHA256 (210 000 itérations). Chaque base de données possède un sel aléatoire cryptographiquement sûr de 32 octets. La phrase de passe n'est jamais stockée sur le disque.

### Que se passe-t-il si j'oublie ma phrase de passe ?

La base de correspondance ne peut pas être déchiffrée sans la phrase de passe correcte. Cela signifie :
- Les correspondances de pseudonymes existantes sont définitivement inaccessibles
- Vous ne pouvez pas inverser la pseudonymisation des documents déjà traités
- Vous devez créer une nouvelle base de données (`poetry run gdpr-pseudo init --force`)

**Recommandation :** Conservez votre phrase de passe dans un gestionnaire de mots de passe sécurisé.

### Puis-je utiliser différents thèmes pour un même projet ?

Techniquement oui, mais ce n'est pas recommandé. Des thèmes différents produisent des pseudonymes différents pour une même entité, créant des incohérences. Si vous devez changer de thème, utilisez une base de données distincte pour chaque thème.

---

## Documentation associée

- [Guide d'installation](installation.md) - Instructions de mise en place
- [Tutoriel d'utilisation](tutorial.md) - Tutoriels pas à pas
- [Référence CLI](CLI-REFERENCE.md) - Documentation complète des commandes
- [Méthodologie](methodology.md) - Approche technique et conformité au RGPD
- [Dépannage](troubleshooting.md) - Référence des erreurs et solutions
