# Guide de l'interface graphique

GDPR Pseudonymizer v2.0 inclut une application de bureau pour la validation visuelle des entités et le traitement de documents. Ce guide couvre toutes les fonctionnalités de l'interface graphique.

---

## Premiers pas

### Lancer l'application

**Depuis PyPI :**
```bash
pip install gdpr-pseudonymizer[gui]
gdpr-pseudo-gui
```

**Depuis les sources :**
```bash
poetry run gdpr-pseudo-gui
```

**Exécutable autonome :** Double-cliquez sur l'exécutable téléchargé (Windows .exe, macOS .dmg, Linux AppImage). Python n'est pas nécessaire.

Au premier lancement, l'application détecte automatiquement la langue de votre système (français ou anglais) et applique le thème clair par défaut.

### Écran d'accueil

L'écran d'accueil est votre point de départ :

- **Zone de glisser-déposer** — Déposez des fichiers `.txt`, `.md`, `.pdf`, `.docx`, `.xlsx` ou `.csv` pour démarrer le traitement
- **Liste des fichiers récents** — Accès rapide aux documents déjà traités
- **Carte traitement par lot** — Cliquez pour accéder au traitement par lot
- **Barre de menus** — Accédez à toutes les fonctionnalités via Fichier, Affichage, Outils et Aide

<!-- TODO: Ajouter une capture d'écran de l'écran d'accueil -->

---

## Traitement d'un document unique

### Étape 1 : Ouvrir un document

- **Glissez-déposez** un fichier sur l'écran d'accueil, ou
- Utilisez **Fichier > Ouvrir** (Ctrl+O), ou
- Cliquez sur un fichier récent dans la liste

### Étape 2 : Saisir la phrase secrète

Une boîte de dialogue apparaît pour la base de données de correspondances :

- Saisissez une phrase secrète (minimum 12 caractères)
- L'application détecte automatiquement les fichiers `.gdpr-pseudo.db` existants et mémorise la dernière base utilisée entre les sessions
- Cochez « Mémoriser » pour conserver la phrase secrète pendant la session
- Choisissez « Créer nouveau » pour démarrer une nouvelle base de données

> **Conseil :** La base de données précédemment sélectionnée est pré-sélectionnée automatiquement au prochain lancement. Votre choix est enregistré dans `.gdpr-pseudo.yaml` sous la clé `default_db_path`.

### Étape 3 : Traitement

L'écran de traitement affiche une barre de progression en 3 phases :

1. **Lecture du fichier** (0-10 %) — Chargement et analyse du document
2. **Chargement du modèle** (10-40 %) — Chargement du modèle NLP spaCy français
3. **Détection NLP** (40-100 %) — Détection des entités dans le texte

Si le modèle spaCy n'est pas installé, l'application le télécharge automatiquement avec un indicateur de progression.

### Étape 4 : Validation des entités

Après la détection, l'écran de validation s'ouvre avec une disposition en deux volets :

- **Éditeur de document** (65 %) — Votre texte avec les entités surlignées par couleur
- **Panneau d'entités** (35 %) — Barre latérale listant toutes les entités détectées, groupées par type

Voir [Validation des entités](#validation-des-entites) ci-dessous pour les instructions détaillées.

### Étape 5 : Résultats et sauvegarde

Après la finalisation, l'écran de résultats affiche :

- Aperçu du document pseudonymisé avec les pseudonymes surlignés
- Répartition par type d'entité (PERSON, LOCATION, ORG avec indicateurs de couleur)
- Bouton **« Enregistrer sous... »** pour sauvegarder le document pseudonymisé

---

## Validation des entités

L'écran de validation est l'endroit où vous passez en revue et confirmez toutes les entités détectées.

### Couleurs des entités

Les entités sont colorées par type (conçues pour être accessibles aux daltoniens) :

| Type | Thème clair | Thème sombre |
|------|-------------|--------------|
| **PERSON** | Fond bleu | Fond bleu |
| **LOCATION** | Fond orange | Fond orange |
| **ORG** | Fond violet | Fond violet |
| **Rejeté** | Rouge barré | Rouge barré |

### Icônes de statut (barre latérale)

| Icône | Signification |
|-------|---------------|
| ○ | En attente (pas encore vérifié) |
| ✓ | Confirmé / Ajouté |
| ✗ | Rejeté |
| ✎ | Modifié |

Les entités connues (déjà dans la base) affichent un badge « déjà connu ».

### Passer en revue les entités

**À la souris :**

1. **Cliquez sur une entité** dans l'éditeur pour la sélectionner et la mettre en surbrillance dans la barre latérale
2. **Cliquez sur une entité** dans la barre latérale pour y défiler dans l'éditeur
3. **Clic droit sur une entité** dans l'éditeur pour le menu contextuel :
   - Accepter
   - Rejeter
   - Modifier le texte...
   - Changer le pseudonyme
   - Changer le type (PERSON, LOCATION, ORG)
4. **Clic droit sur du texte sélectionné** pour l'ajouter comme nouvelle entité

**Au clavier (mode navigation) :**

1. Appuyez sur **Entrée** pour entrer en mode navigation (focus sur la première entité en attente)
2. Utilisez **Tab** / **Maj+Tab** pour vous déplacer entre les entités (uniquement actifs en mode navigation)
3. Appuyez sur **Entrée** pour accepter l'entité courante
4. Appuyez sur **Suppr** pour rejeter l'entité courante
5. Appuyez sur **Maj+F10** ou la **touche Menu** pour ouvrir le menu contextuel
6. Appuyez sur **Échap** pour quitter le mode navigation

> **Remarque :** Tab et Maj+Tab ne naviguent entre les entités que lorsque le mode navigation est actif. En dehors de ce mode, ils suivent la navigation de focus standard. Appuyez sur **F1** pour ouvrir la fenêtre d'aide des raccourcis clavier.

### Actions groupées

**Via la barre latérale :**

- Cochez plusieurs entités avec les cases à cocher
- Cliquez sur **« Accepter la sélection »** ou **« Rejeter la sélection »**
- Cliquez sur **« Tout accepter : PERSONNES »** (ou LOCATIONS/ORGANISATIONS) pour accepter toutes les entités en attente d'un type
- Cliquez sur **« Accepter les déjà connues »** pour accepter toutes les entités connues

**Raccourcis clavier :**

| Raccourci | Action |
|-----------|--------|
| Ctrl+Maj+A | Accepter toutes les entités en attente |
| Ctrl+Maj+R | Rejeter toutes les entités en attente |
| Ctrl+Z | Annuler la dernière action |
| Ctrl+Maj+Z / Ctrl+Y | Rétablir |
| Ctrl+F | Focus sur le champ de filtre |

### Filtrer les entités

Utilisez le champ de filtre en haut de la barre latérale pour rechercher des entités par texte. Tapez pour filtrer en temps réel ; utilisez le bouton d'effacement pour réinitialiser.

### Masquer les rejetés / Masquer les validées

- Cochez **« Masquer les rejetés »** pour cacher les entités rejetées barrées dans l'éditeur.
- Cochez **« Masquer les validées »** pour cacher les entités déjà acceptées et connues, vous permettant de vous concentrer sur les entités en attente.

### Finaliser

Lorsque toutes les entités ont été vérifiées (le compteur affiche « Toutes vérifiées ») :

1. Cliquez sur **« Finaliser »** en bas de l'écran
2. Un dialogue de résumé confirme vos modifications
3. Le document est pseudonymisé et l'écran de résultats apparaît

---

## Traitement par lot

### Étape 1 : Sélectionner les fichiers

1. Depuis l'écran d'accueil, cliquez sur la carte traitement par lot, ou utilisez **Fichier > Ouvrir un dossier** (Ctrl+Maj+O)
2. Choisissez un dossier ou sélectionnez plusieurs fichiers
3. L'application découvre tous les fichiers supportés (`.txt`, `.md`, `.pdf`, `.docx`, `.xlsx`, `.csv`), en excluant les fichiers déjà pseudonymisés (`*_pseudonymized*`)
4. Définissez le répertoire de sortie (par défaut : `{entrée}/_pseudonymized/`)
5. Activez optionnellement **« Valider les entités par document »** pour vérifier les entités document par document

### Étape 2 : Tableau de bord de traitement

L'écran de lot affiche :

- **Barre de progression globale** avec pourcentage
- **Tableau par document** avec transitions de statut : En attente → En cours → Traité / Erreur
- **Temps restant estimé**
- Contrôles **Pause/Reprise** et **Annulation**

### Étape 3 : Validation par document (optionnel)

Si la validation est activée, le traitement se met en pause après la détection des entités de chaque document :

- Un indicateur « Document X de Y » montre votre position
- Utilisez les boutons **Précédent/Suivant** pour naviguer entre les documents
- Vérifiez et validez les entités comme en mode document unique
- Cliquez sur **« Valider et continuer »** pour passer au document suivant
- Cliquez sur **« Valider et terminer »** sur le dernier document
- Cliquez sur **« Annuler le lot »** pour annuler les documents restants

### Étape 4 : Résumé et export

Après le traitement de tous les documents :

- Cartes récapitulatives : documents traités, entités détectées, pseudonymes nouveaux/réutilisés, erreurs
- Tableau de résultats par document avec statut
- Bouton **« Exporter »** pour sauvegarder un rapport de lot en `.txt`

---

## Gestion de la base de données

Accès via **Outils > Gestion de la base de données** dans la barre de menus.

### Consultation des entités

- Parcourez toutes les correspondances d'entités stockées
- Filtrez par type (PERSON, LOCATION, ORG)
- Recherchez par nom d'entité
- Colonnes : identifiant, type, nom complet, pseudonyme, date de première détection

### Suppression d'entités (RGPD article 17)

1. Sélectionnez des entités avec les cases à cocher
2. Cliquez sur **« Supprimer »**
3. Confirmez dans la boîte de dialogue
4. Une entrée d'audit ERASURE est créée pour la conformité

### Export

Cliquez sur **« Exporter CSV »** pour exporter la liste des entités au format CSV avec les colonnes : entity_id, entity_type, full_name, pseudonym_full, first_seen.

### Bases récentes

L'application mémorise les 5 dernières bases ouvertes (affichées dans un menu déroulant). Les informations de la base affichent : date de création, nombre d'entités, dernière opération.

---

## Paramètres

Accès via **Outils > Paramètres** (Ctrl+,).

### Apparence

- **Thème :** Clair, Sombre ou Contraste élevé
- **Langue :** Français ou Anglais (le changement s'applique immédiatement, sans redémarrage)

### Traitement par défaut

- **Thème de pseudonymes :** Neutre, Star Wars ou Le Seigneur des Anneaux
- **Modèle NLP :** spaCy (par défaut)
- **Répertoire de sortie par défaut**

### Options de traitement par lot

- **Workers :** 1 à 8 traitements parallèles (utilisez 1 pour la validation interactive)
- **Thème par défaut :** Thème de pseudonymes pour le traitement par lot

---

## Référence des raccourcis clavier

### Raccourcis globaux

| Raccourci | Action |
|-----------|--------|
| Ctrl+O | Ouvrir un fichier |
| Ctrl+Maj+O | Ouvrir un dossier (lot) |
| Ctrl+Q | Quitter l'application |
| Ctrl+, | Ouvrir les paramètres |
| F1 | Aide raccourcis clavier |
| F11 | Basculer en plein écran |

### Écran de validation

| Raccourci | Action |
|-----------|--------|
| Entrée | Entrer en mode navigation / Accepter l'entité |
| Tab | Entité suivante |
| Maj+Tab | Entité précédente |
| Suppr | Rejeter l'entité |
| Échap | Quitter le mode navigation |
| Ctrl+Z | Annuler |
| Ctrl+Maj+Z / Ctrl+Y | Rétablir |
| Ctrl+F | Filtrer les entités |
| Ctrl+Maj+A | Accepter toutes les entités en attente |
| Ctrl+Maj+R | Rejeter toutes les entités en attente |
| Maj+F10 / Touche Menu | Menu contextuel de l'entité |

### Éditeur

| Raccourci | Action |
|-----------|--------|
| Ctrl++ | Zoom avant |
| Ctrl+- | Zoom arrière |

---

## Fonctionnalités d'accessibilité

GDPR Pseudonymizer v2.0 respecte les normes d'accessibilité **WCAG 2.1 niveau AA**.

### Navigation au clavier

Tous les éléments interactifs sont accessibles au clavier. Des indicateurs de focus (contour solide de 2 px) sont visibles sur tous les contrôles. En mode contraste élevé, les indicateurs sont renforcés (3 px gras jaune).

### Lecteurs d'écran

L'application est compatible avec les lecteurs d'écran (NVDA sous Windows, VoiceOver sous macOS) :

- Tous les boutons et contrôles ont des noms et descriptions accessibles
- L'éditeur d'entités annonce : type, texte et statut pour chaque entité
- Le panneau d'entités annonce : type, texte, statut connu, statut de validation et pseudonyme

### Mode contraste élevé

- Détection automatique des paramètres de contraste élevé du système
- Sélection manuelle via **Affichage > Contraste élevé**
- Rapport de contraste 21:1 pour les éléments critiques
- Polices en gras pour une meilleure lisibilité
- Indicateurs de focus jaune vif sur fond noir pur

### Accessibilité pour les daltoniens

Les couleurs des entités sont choisies pour être distinguables sans dépendre du contraste rouge/vert :
- Bleu (PERSON), Orange (LOCATION), Violet (ORG)

### Mise à l'échelle DPI

L'application prend en charge la mise à l'échelle de l'affichage de 100 % à 200 %. De légers ajustements de mise en page peuvent survenir à 200 % (limitation connue UI-001), mais toutes les fonctionnalités restent accessibles.
