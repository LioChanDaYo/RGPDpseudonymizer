# Questions fréquemment posées

**GDPR Pseudonymizer** - Réponses aux questions les plus courantes

---

## Précision et détection

### Quelle précision puis-je attendre de la détection automatique ?

Le pipeline hybride de détection (NLP + expressions régulières) identifie automatiquement environ 60 % des entités dans un texte français. Cette étape sert de pré-filtrage -- **vous vérifiez et validez chaque entité** au cours du processus de validation obligatoire.

Après validation humaine, la précision atteint **100 %** puisque vous contrôlez la décision finale pour chaque entité.

### Pourquoi la précision du NER est-elle si faible ?

Le modèle spaCy `fr_core_news_lg` a été entraîné principalement sur des textes journalistiques, pas sur des transcriptions d'entretiens ou des documents commerciaux. Les modèles linguistiques spécifiques à un domaine (registres conversationnels, formalité mixte) réduisent la précision en utilisation directe. Un test d'évaluation portant sur 25 documents français contenant 1 855 entités a mesuré un F1 de 29,5 % pour spaCy seul, amélioré à environ 60 % (F1 59,97 %) avec l'approche hybride.

Un affinage basé sur des données de validation du monde réel est prévu pour la v3.0 (ciblant un F1 de 70-85 %).

### Pourquoi la validation est-elle obligatoire ?

Parce que la détection IA rate des entités. Avec un rappel d'environ 80 %, environ un cinquième des entités ne seraient pas détectées sans examen humain. Pour la conformité RGPD, manquer ne serait-ce qu'une entité de données personnelles pourrait constituer une violation de données. La validation obligatoire garantit **aucun faux négatif**.

### Comment traiter uniquement certains types d'entités ?

Utilisez l'option `--entity-types` avec une liste de types séparés par des virgules :

```bash
# Traiter uniquement les entités PERSON
gdpr-pseudo process doc.txt --entity-types PERSON

# Traiter PERSON et LOCATION (ignorer ORG)
gdpr-pseudo batch ./documents/ --entity-types PERSON,LOCATION
```

Les types valides sont `PERSON`, `LOCATION` et `ORG`. Quand cette option n'est pas spécifiée, tous les types d'entités sont traités. Elle fonctionne avec les commandes `process` et `batch`.

### Qu'est-ce que le regroupement des variantes d'entités ?

Le regroupement des variantes fusionne automatiquement les formes connexes d'une même entité en un seul élément de validation. Par exemple, si un document contient « Marie Dubois », « Pr. Dubois » et « Dubois », l'interface de validation les montre comme un seul élément avec « Apparaît aussi sous : » listant les formes variantes.

Cela réduit la fatigue de validation en éliminant les demandes redondantes. Le regroupement est de type conscient :

- **PERSON :** Correspondance du nom de famille sans titre (« Dr. Dubois » = « Dubois »). Les prénoms différents restent séparés (« Marie Dubois » vs « Jean Dubois »).
- **LOCATION :** Suppression des prépositions françaises (« à Lyon » = « Lyon »).
- **ORG :** Correspondance insensible à la casse (« ACME Corp » = « acme corp »).

---

## Formats de documents et langues

### Quels formats de documents sont pris en charge ?

La v1.0 prend en charge :
- **Texte brut** (`.txt`)
- **Markdown** (`.md`)

Les formats PDF, DOCX, HTML et autres ne sont pas pris en charge dans la v1.0. Convertissez les fichiers en texte brut avant le traitement.

### Puis-je utiliser cet outil pour des documents non français ?

Non. La v1.0 est conçue exclusivement pour le texte en langue française. Le modèle NLP (`fr_core_news_lg`), les expressions régulières et les bibliothèques de pseudonymes sont tous spécifiques au français.

La prise en charge multilingue (anglais, espagnol, allemand) est prévue pour la v3.0.

### Quelles langues sont prises en charge ?

Le français uniquement dans la v1.0. L'outil utilise le modèle `fr_core_news_lg` de spaCy entraîné spécifiquement sur du texte français.

---

## Conformité RGPD

### Cet outil est-il conforme au RGPD ?

GDPR Pseudonymizer **facilite** la conformité RGPD mais ne la garantit pas à lui seul. L'outil implémente :

- **Article 4(5) :** Pseudo-anonymisation avec stockage séparé chiffré de la table de correspondance
- **Article 25 :** Protection des données dès la conception (traitement 100 % local, stockage chiffré)
- **Article 32 :** Mesures de sécurité (chiffrement AES-256-SIV, dérivation de clé PBKDF2)
- **Article 30 :** Registres de traitement (journalisation d'audit complète avec export)

**Important :** Les données pseudo-anonymisées restent des données personnelles au sens du RGPD (Considérant 26). Vous restez responsable du traitement et devez consulter votre Délégué à la protection des données pour des conseils de conformité spécifiques.

Consultez la [Méthodologie](methodology.md) pour la cartographie complète de conformité RGPD.

### La pseudo-anonymisation est-elle la même chose que l'anonymisation ?

Non. La **pseudo-anonymisation** remplace les informations d'identification par des pseudonymes mais reste réversible (avec la table de correspondance et le mot de passe). Les données pseudo-anonymisées restent des données personnelles au sens du RGPD.

L'**anonymisation** supprime de manière irréversible toute information d'identification afin que la ré-identification soit impossible. Le RGPD ne s'applique pas aux données véritablement anonymes.

GDPR Pseudonymizer effectue la pseudo-anonymisation, non l'anonymisation. C'est intentionnel -- de nombreux cas d'usage nécessitent la réversibilité (suivi de recherche académique, procédures judiciaires, exigences d'audit).

### Mes données quittent-elles ma machine ?

Non. Tout le traitement se fait localement. Il n'y a aucune dépendance cloud, appels API, télémétrie ou communication réseau. Après l'installation initiale (téléchargement du modèle spaCy), l'outil fonctionne complètement hors ligne.

---

## Comparaison avec les alternatives

### Comment cela se compare-t-il au caviardage manuel ?

| Aspect | Caviardage manuel | GDPR Pseudonymizer |
|--------|------------------|--------------------|
| **Temps par document** | 15-30 minutes | 2-5 minutes (détection préalable IA + validation) |
| **Précision** | Sujette à erreur humaine | 100 % (validation obligatoire) |
| **Cohérence** | Difficile entre documents | Garantie (même entité = même pseudonyme) |
| **Réversibilité** | Impossible | Oui (table de correspondance chiffrée) |
| **Piste d'audit** | Journalisation manuelle | Automatique (journalisation des opérations, export JSON/CSV) |
| **Coût pour 50 documents** | 16-25 heures | 2-3 heures |

### Comment cela se compare-t-il aux services cloud de pseudo-anonymisation ?

| Aspect | Services cloud | GDPR Pseudonymizer |
|--------|----------------|---------------------|
| **Localisation des données** | Serveurs tiers | 100 % local |
| **Risque de confidentialité** | Exposition des données au fournisseur | Zéro (aucun réseau) |
| **Coût** | Par document ou abonnement | Gratuit (open source) |
| **Précision** | Varie (souvent pas de validation) | 100 % (validation obligatoire) |
| **Personnalisation** | Limitée | Complète (pseudonymes thématiques, fichiers de configuration) |
| **Internet requis** | Toujours | Uniquement pour l'installation |

### Comment cela se compare-t-il aux outils entièrement automatiques ?

| Aspect | Outils automatiques | GDPR Pseudonymizer |
|--------|---------------------|---------------------|
| **Supervision humaine** | Aucune | Obligatoire |
| **Précision** | Dépend du NLP (souvent 70-90 %) | 100 % (validation humaine) |
| **Vitesse** | Plus rapide (pas de validation) | Plus lent mais plus précis |
| **Solidité juridique RGPD** | Plus faible (pas de piste d'audit humain) | Plus forte (révision humaine documentée) |
| **Faux négatifs** | Possibles | Zéro (par conception) |

---

## Feuille de route

### Qu'est-ce qui est prévu pour les versions futures ?

**v1.0 (Actuelle - Q2 2026) :** CLI assistée par IA avec validation obligatoire
- Traitement 100 % local, tables de correspondance chiffrées, pistes d'audit
- Langue française, formats .txt/.md

**v1.1 (Q2-Q3 2026) :** Améliorations rapides et conformité RGPD
- Droit à l'oubli RGPD : suppression sélective des entités (commande `delete-mapping`, Article 17)
- Attribution de pseudonymes consciente du genre pour les noms français
- Correctifs de commentaires bêta et améliorations UX

**v2.0 (Q3-Q4 2026) :** Interface graphique de bureau
- Interface graphique enveloppant le noyau CLI (glisser-déposer, révision visuelle des entités)
- Exécutables autonomes (.exe, .app) -- Python non requis
- Interface prioritairement en français avec architecture d'internationalisation

**v3.0 (2027+) :** Précision NLP et automation
- Modèle NER français affinage (cible F1 de 70-85 %)
- Option `--no-validate` facultative pour les workflows haute confiance
- Prise en charge multilingue (anglais, espagnol, allemand)

### Aura-t-il une version avec interface graphique ?

Oui. La v2.0 (prévue pour Q3-Q4 2026) inclura une interface graphique de bureau avec traitement de documents par glisser-déposer, révision visuelle des entités et exécutables autonomes qui ne nécessitent pas l'installation de Python. Le public cible est constitué d'utilisateurs non techniques (RH, juridique, conformité).

### Puis-je contribuer ?

Pas encore. Le projet est en développement pré-lancement. Après le lancement de la v1.0 MVP, les contributions seront bienvenues pour les rapports de bogues, les améliorations de documentation, les traductions et les suggestions de fonctionnalités.

GitHub : https://github.com/LioChanDaYo/RGPDpseudonymizer

---

## Questions techniques

### Quel modèle NLP est utilisé ?

spaCy `fr_core_news_lg` (version 3.8.0), un grand modèle de langue française (~571 Mo). Il a été sélectionné après un test d'évaluation par rapport à Stanza, réalisant un score F1 2,5 fois meilleur sur le corpus de test.

### Comment la base de données de correspondance est-elle chiffrée ?

AES-256-SIV (chiffrement authentifié déterministe selon RFC 5297) avec dérivation de clé PBKDF2-HMAC-SHA256 (210 000 itérations). Chaque base de données possède un salt aléatoire cryptographiquement unique de 32 octets. Le mot de passe n'est jamais stocké sur le disque.

### Que se passe-t-il si j'oublie mon mot de passe ?

La base de données de correspondance ne peut pas être déchiffrée sans le mot de passe correct. Cela signifie :
- Les mappings de pseudonymes existants sont définitivement inaccessibles
- Vous ne pouvez pas inverser la pseudo-anonymisation sur les documents précédemment traités
- Vous devez créer une nouvelle base de données (`poetry run gdpr-pseudo init --force`)

**Recommandation :** Stockez votre mot de passe dans un gestionnaire de mots de passe sécurisé.

### Puis-je utiliser différents thèmes pour le même projet ?

Techniquement oui, mais ce n'est pas recommandé. Les différents thèmes produisent différents pseudonymes pour la même entité, créant des incohérences. Si vous devez changer de thème, utilisez une base de données séparée pour chaque thème.

---

## Documentation connexe

- [Guide d'installation](installation.md) - Instructions de configuration
- [Tutoriel d'utilisation](tutorial.md) - Tutoriels pas à pas
- [Référence CLI](CLI-REFERENCE.md) - Documentation complète des commandes
- [Méthodologie](methodology.md) - Approche technique et conformité RGPD
- [Dépannage](troubleshooting.md) - Référence d'erreurs et solutions
