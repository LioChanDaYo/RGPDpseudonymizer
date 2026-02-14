# Guide d'installation

**GDPR Pseudonymizer** - Pseudonymisation assistée par IA pour documents français

Ce guide couvre l'installation sur Windows, macOS et Linux.

---

## Prérequis

| Prérequis | Version | Comment vérifier |
|-------------|---------|--------------|
| **Python** | 3.10, 3.11 ou 3.12 | `python --version` |
| **Espace disque** | ~1 Go disponible | Pour le modèle spaCy français (téléchargé automatiquement au premier lancement) |
| **Connexion Internet** | Requise pour l'installation | Téléchargement du modèle : ~571 Mo |

**Important :** Python 3.10-3.12 sont validés dans les tests CI/CD. Python 3.9 n'est plus pris en charge (fin de vie en octobre 2025). Python 3.13+ n'a pas encore été testé.

---

## Installation via PyPI (recommandé)

La solution la plus simple pour les utilisateurs finaux :

```bash
pip install gdpr-pseudonymizer

# Vérifier l'installation
gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```bash
> python -m spacy download fr_core_news_lg
> ```

---

## Installation depuis les sources (contributeurs)

Pour contribuer au développement, vous aurez également besoin de [Poetry](https://python-poetry.org/) 1.7+.

### Installation rapide (toutes les plates-formes)

```bash
# 1. Cloner le dépôt
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# 2. Installer les dépendances
poetry install

# 3. Vérifier l'installation
poetry run gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

## Instructions par plate-forme

### Windows 11

#### Étape 1 : Installer Python

1. Téléchargez Python 3.11 depuis [python.org](https://www.python.org/downloads/)
2. Lancez le programme d'installation et cochez **« Add Python to PATH »**
3. Vérifiez en ouvrant PowerShell et en exécutant :
   ```powershell
   python --version
   # Attendu : Python 3.11.x
   ```

#### Étape 2 : Installer Poetry

Ouvrez PowerShell et exécutez :
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Ajoutez Poetry au PATH s'il n'est pas trouvé :
```powershell
# À ajouter à votre profil PowerShell ou à exécuter à chaque session
$env:PATH += ";$env:APPDATA\Python\Scripts"
```

Vérifiez :
```powershell
poetry --version
# Attendu : Poetry (version 1.7.0 ou supérieure)
```

#### Étape 3 : Cloner et installer

```powershell
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Étape 4 : Vérifier l'installation

```powershell
poetry run gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```powershell
> poetry run python scripts/install_spacy_model.py
> ```

**Remarque Windows :** L'interface en ligne de commande peut apparaître sous la forme `gdpr-pseudo.cmd`. C'est un comportement normal de Poetry.

---

### macOS (Intel & Apple Silicon)

#### Étape 1 : Installer Python

**Option A : Via Homebrew (recommandé)**
```bash
brew install python@3.11
```

**Option B : Depuis python.org**
Téléchargez depuis [python.org](https://www.python.org/downloads/macos/)

Vérifiez :
```bash
python3 --version
# Attendu : Python 3.11.x
```

**Apple Silicon (M1/M2/M3) :** Python 3.9+ bénéficie d'un support ARM natif.

#### Étape 2 : Installer les outils de ligne de commande Xcode

Nécessaires pour compiler certaines dépendances :
```bash
xcode-select --install
```

#### Étape 3 : Installer Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Ajoutez au PATH (à ajouter à `~/.zshrc` de façon permanente) :
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Vérifiez :
```bash
poetry --version
```

#### Étape 4 : Cloner et installer

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Étape 5 : Vérifier l'installation

```bash
poetry run gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Linux (Ubuntu 22.04 / Debian)

#### Étape 1 : Installer Python et les outils de compilation

```bash
sudo apt update
sudo apt install python3.11 python3.11-dev python3-pip build-essential
```

Vérifiez :
```bash
python3.11 --version
# Attendu : Python 3.11.x
```

#### Étape 2 : Installer Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Ajoutez au PATH (à ajouter à `~/.bashrc` de façon permanente) :
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Vérifiez :
```bash
poetry --version
```

#### Étape 3 : Cloner et installer

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Étape 4 : Vérifier l'installation

```bash
poetry run gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Linux (Fedora 39+)

#### Étape 1 : Installer Python et les outils de compilation

```bash
sudo dnf install python3.11 python3.11-devel gcc git curl
```

Vérifiez :
```bash
python3.11 --version
# Attendu : Python 3.11.x
```

#### Étape 2 : Installer Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Ajoutez au PATH (à ajouter à `~/.bashrc` de façon permanente) :
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Vérifiez :
```bash
poetry --version
```

#### Étape 3 : Cloner et installer

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Étape 4 : Vérifier l'installation

```bash
poetry run gdpr-pseudo --help
```

> **Note :** Le modèle spaCy français (~571 Mo) se télécharge automatiquement au premier lancement. Pour le pré-télécharger :
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Docker (alternative)

Docker offre une méthode d'installation indépendante de la plate-forme. Un Dockerfile ne figure pas encore dans le dépôt (prévu après la version MVP), mais vous pouvez exécuter l'outil dans un conteneur Docker manuellement.

#### Configuration rapide avec Docker

```bash
# Démarrer un conteneur Python interactif
docker run -it --rm -v "$(pwd)/documents:/data" python:3.11 bash

# À l'intérieur du conteneur :
pip install poetry
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry config virtualenvs.create false
poetry install
python -m spacy download fr_core_news_lg

# Traiter un document du répertoire monté /data
gdpr-pseudo process /data/input.txt -o /data/output.txt
```

#### Remarques

- Montez votre répertoire de documents avec `-v` pour que les fichiers de sortie persistent après la fermeture du conteneur
- Utilisez `poetry config virtualenvs.create false` pour installer directement dans le conteneur (pas besoin d'environnement virtuel dans Docker)
- L'option `--rm` nettoie le conteneur après sa fermeture. Omettez-la si vous souhaitez réutiliser le conteneur
- **Testé sur :** Docker Desktop 29.2.0 (Windows), conteneur Ubuntu 24.04, conteneur Debian 12, conteneur Fedora 39

#### Améliorations prévues

Un Dockerfile pré-construit et une image Docker publiée sont prévus pour une version future, ce qui simplifiera l'utilisation à ceci :

```bash
# Version future (pas encore disponible)
docker run -v "$(pwd):/data" gdpr-pseudonymizer process /data/input.txt
```

---

## Utilisation de la ligne de commande

### Installation via pip

Si vous avez installé avec `pip install gdpr-pseudonymizer`, les commandes fonctionnent directement :

```bash
gdpr-pseudo --help
gdpr-pseudo process input.txt
gdpr-pseudo batch ./documents/
```

### Installation depuis les sources (Poetry)

Si vous avez cloné le dépôt, préfixez les commandes avec `poetry run` :

```bash
poetry run gdpr-pseudo --help
poetry run gdpr-pseudo process input.txt
poetry run gdpr-pseudo batch ./documents/
```

**Alternative :** Activez le shell Poetry pour la session :
```bash
poetry shell
gdpr-pseudo --help  # Fonctionne dans ce shell
exit                # Retourner au shell normal
```

---

## Configuration (optionnelle)

Générez un fichier de configuration modèle :

```bash
poetry run gdpr-pseudo config --init
```

Cela crée `.gdpr-pseudo.yaml` dans le répertoire courant :

```yaml
database:
  path: mappings.db

pseudonymization:
  theme: neutral    # neutral | star_wars | lotr
  model: spacy

batch:
  workers: 4        # 1-8 (utiliser 1 pour la validation interactive)
  output_dir: null

logging:
  level: INFO
```

Afficher la configuration actuelle effective :
```bash
poetry run gdpr-pseudo config
```

**Remarque de sécurité :** La mot de passe n'est jamais stockée dans les fichiers de configuration. Utilisez :
- Variable d'environnement : `GDPR_PSEUDO_PASSPHRASE`
- Invite interactive (par défaut)

---

## Dépannage

### `poetry: command not found`

**Cause :** Poetry n'est pas dans le PATH.

**Solution :**
1. Vérifiez l'emplacement d'installation :
   - Windows : `%APPDATA%\Python\Scripts`
   - macOS/Linux : `~/.local/bin`
2. Ajoutez au PATH (voir les instructions spécifiques à votre plate-forme ci-dessus)
3. Redémarrez votre terminal
4. Alternative : utilisez `python -m poetry` à la place de `poetry`

---

### Version Python non prise en charge

**Erreur :** `The currently activated Python version X.Y.Z is not supported`

**Solution :**
1. Installez Python 3.10, 3.11 ou 3.12
2. Configurez Poetry pour utiliser la bonne version :
   ```bash
   poetry env use python3.11
   poetry install
   ```

**Note :** Si votre système a Python 3.13+ mais que Poetry utilise 3.10-3.12, l'outil fonctionne correctement. Poetry gère son propre environnement virtuel indépendamment de Python au niveau système. Vérifiez avec :
```bash
poetry env info
# Recherchez « Virtualenv Python: 3.11.x » (doit être 3.10-3.12)
```

---

### Exigences de mot de passe

**Erreur :** `Passphrase must be at least 12 characters`

**Cause :** Exigence de sécurité. Les phrases de passe doivent comporter au moins 12 caractères.

**Solution :**
1. Utilisez une mot de passe d'au moins 12 caractères
2. Ou définissez-la via une variable d'environnement :
   ```bash
   export GDPR_PSEUDO_PASSPHRASE="votre-phrase-de-passe-securisee"
   ```

---

### Échec du téléchargement du modèle spaCy

**Causes possibles :**
- Problèmes réseau
- Espace disque insuffisant (~1 Go requis)
- Pare-feu bloquant le téléchargement

**Solutions :**

1. **Vérifiez l'espace disque :**
   ```bash
   # macOS/Linux
   df -h

   # Windows
   dir
   ```

2. **Installation manuelle :**
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```

3. **Derrière un pare-feu d'entreprise :** Contactez votre équipe informatique pour la configuration du proxy

4. **Réessayez avec sortie détaillée :**
   ```bash
   poetry run python -m spacy download fr_core_news_lg --verbose
   ```

---

### `poetry install` échoue avec des conflits de dépendances

**Solution :**
1. Vérifiez la version Python (doit être 3.10-3.12)
2. Videz l'environnement virtuel et réinstallez :
   ```bash
   poetry env remove python
   poetry install
   ```
3. Mettez à jour Poetry :
   ```bash
   poetry self update
   ```

---

### La commande CLI ne fonctionne pas

**Erreur :** `gdpr-pseudo: command not found`

**Solution :** Utilisez toujours le préfixe `poetry run` :
```bash
# CORRECT
poetry run gdpr-pseudo --help

# INCORRECT
gdpr-pseudo --help
```

---

### Windows : violations d'accès spaCy

**Symptôme :** Crash ou erreurs de violation d'accès lors de l'exécution de spaCy.

**Solutions :**
1. Utilisez Windows Subsystem for Linux (WSL) à la place
2. Limitez les threads : définissez la variable d'environnement `OMP_NUM_THREADS=1`
3. Mettez à jour Windows et Visual C++ Redistributable

---

### Erreurs de permission refusée

**Cause :** Permissions de fichiers insuffisantes.

**Solutions :**
- **macOS/Linux :** Vérifiez les permissions avec `ls -la`
- **Windows :** Lancez PowerShell en tant qu'administrateur pour l'installation
- Assurez-vous d'avoir accès en écriture au répertoire du projet

---

## Vérifier l'installation complète

Exécutez ces commandes pour vérifier que tout fonctionne :

```bash
# 1. Vérifier l'interface en ligne de commande
poetry run gdpr-pseudo --help

# 2. Vérifier la version
poetry run gdpr-pseudo --version

# 3. Test de traitement (crée un fichier de test)
echo "Marie Dubois travaille a Paris." > test_install.txt
poetry run gdpr-pseudo process test_install.txt

# 4. Vérifier le résultat
cat test_install_pseudonymized.txt

# 5. Nettoyage
rm test_install.txt test_install_pseudonymized.txt mappings.db
```

---

## Étapes suivantes

Après l'installation :

1. **Prise en main rapide :** [tutorial.md](tutorial.md) - Votre première pseudonymisation en 5 minutes
2. **Référence CLI :** [CLI-REFERENCE.md](CLI-REFERENCE.md) - Documentation complète des commandes
3. **FAQ :** [faq.md](faq.md) - Questions fréquemment posées et réponses

---

## Obtenir de l'aide

**Problèmes d'installation :**
- Problèmes GitHub : https://github.com/LioChanDaYo/RGPDpseudonymizer/issues
- Incluez : version de l'OS, version de Python, message d'erreur complet

**Documentation :**
- [Référence CLI](CLI-REFERENCE.md)
- [Tutoriel](tutorial.md)
- [FAQ](faq.md)
- [Dépannage](troubleshooting.md)
