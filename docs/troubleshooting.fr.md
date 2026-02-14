# Guide de dépannage

**Pseudonymiseur RGPD** - Référence des erreurs et solutions

---

## Problèmes d'installation

### `poetry: command not found`

**Cause :** Poetry n'est pas présent dans votre PATH système.

**Solution :**
1. Vérifiez le répertoire d'installation :
   - Windows : `%APPDATA%\Python\Scripts`
   - macOS/Linux : `~/.local/bin`
2. Ajoutez à votre PATH :
   - **Windows (PowerShell) :** `$env:PATH += ";$env:APPDATA\Python\Scripts"`
   - **macOS/Linux :** `export PATH="$HOME/.local/bin:$PATH"` (ajoutez à `~/.bashrc` ou `~/.zshrc`)
3. Redémarrez votre terminal
4. Alternative : utilisez `python -m poetry` à la place de `poetry`

### Version Python non prise en charge

**Erreur :** `The currently activated Python version X.Y.Z is not supported`

**Solution :**
1. Installez Python 3.10, 3.11 ou 3.12
2. Configurez Poetry pour utiliser la bonne version :
   ```bash
   poetry env use python3.11
   poetry install
   ```
3. Vérifiez avec `poetry env info` (recherchez « Python: 3.10.x », « 3.11.x » ou « 3.12.x »)

**Remarque :** Python 3.9 n'est plus pris en charge (fin de vie en octobre 2025). Python 3.13 et supérieur n'ont pas encore été testés.

### Le téléchargement du modèle spaCy échoue

**Causes possibles :** Problèmes de réseau, espace disque insuffisant (~1 Go nécessaire), pare-feu bloquant.

**Solutions :**

1. **Vérifiez l'espace disque :**
   ```bash
   # macOS/Linux
   df -h
   # Windows PowerShell
   Get-PSDrive C
   ```

2. **Installation manuelle :**
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```

3. **Réessayez avec sortie détaillée :**
   ```bash
   poetry run python -m spacy download fr_core_news_lg --verbose
   ```

4. **Derrière un pare-feu d'entreprise :** Contactez votre service informatique pour configurer un proxy ou téléchargez le paquet du modèle manuellement depuis https://github.com/explosion/spacy-models

### `poetry install` échoue avec des conflits de dépendances

**Solution :**
1. Vérifiez la version Python (doit être 3.10-3.12)
2. Supprimez l'environnement virtuel et réinstallez :
   ```bash
   poetry env remove python
   poetry install
   ```
3. Mettez à jour Poetry :
   ```bash
   poetry self update
   ```

### `gdpr-pseudo: command not found`

**Cause :** L'interface en ligne de commande requiert le préfixe `poetry run` pendant le développement.

**Solution :** Utilisez toujours `poetry run` :
```bash
# CORRECT
poetry run gdpr-pseudo --help

# INCORRECT
gdpr-pseudo --help
```

**Alternative :** Activez l'interpréteur Poetry :
```bash
poetry shell
gdpr-pseudo --help
exit
```

---

## Problèmes de mot de passe

### `Passphrase must be at least 12 characters`

**Cause :** Exigence de sécurité -- les phrases de passe doivent contenir au moins 12 caractères.

**Solution :**
1. Utilisez un mot de passe d'au moins 12 caractères
2. Ou définissez-le via une variable d'environnement :
   ```bash
   # macOS/Linux
   export GDPR_PSEUDO_PASSPHRASE="your-secure-passphrase-here"

   # Windows PowerShell
   $env:GDPR_PSEUDO_PASSPHRASE = "your-secure-passphrase-here"
   ```

### `Incorrect passphrase`

**Erreur :** `Incorrect passphrase. Please check your passphrase and try again.`

**Solution :**
- Vérifiez que vous utilisez exactement le même mot de passe que celui utilisé lors de la création de la base de données
- Vérifiez la présence d'espaces à la fin ou de caractères invisibles
- Si vous utilisez une variable d'environnement, vérifiez : `echo $GDPR_PSEUDO_PASSPHRASE` (Linux/macOS) ou `echo $env:GDPR_PSEUDO_PASSPHRASE` (PowerShell)

### Phrase de passe oubliée

**Conséquence :** La base de données de correspondance ne peut pas être déchiffrée. Les correspondances existantes sont définitivement inaccessibles et la pseudonymisation ne peut pas être annulée.

**Récupération :** Créez une nouvelle base de données (les correspondances précédentes seront perdues) :
```bash
poetry run gdpr-pseudo init --force
```

**Prévention :** Stockez vos phrases de passe dans un gestionnaire de mots de passe sécurisé.

### `Passphrase in config file is forbidden`

**Cause :** Un champ `passphrase` a été trouvé dans `.gdpr-pseudo.yaml`. Le stockage de données d'identification en texte brut est bloqué pour des raisons de sécurité.

**Solution :** Supprimez le champ `passphrase` de votre fichier de configuration. Utilisez l'une des options suivantes :
- **Variable d'environnement :** `GDPR_PSEUDO_PASSPHRASE` (recommandée pour l'automatisation)
- **Invite interactive** (plus sûr -- comportement par défaut)
- **Option en ligne de commande :** `--passphrase` (non recommandée -- visible dans l'historique du shell)

---

## Erreurs de base de données

### `Database file not found: mappings.db`

**Cause :** Aucune base de données n'a encore été créée.

**Solution :** Initialisez une base de données :
```bash
poetry run gdpr-pseudo init
```

### `Database may be corrupted`

**Solution :**
1. Si vous disposez d'une sauvegarde, restaurez-la
2. Essayez d'exporter les données : `poetry run gdpr-pseudo export backup.json`
3. Créez une nouvelle base de données : `poetry run gdpr-pseudo init --force`

### Pseudonymes incohérents dans les documents

**Cause :** Utilisation de fichiers de base de données différents pour des documents connexes.

**Solution :** Spécifiez toujours la même base de données :
```bash
poetry run gdpr-pseudo process doc1.txt --db shared.db
poetry run gdpr-pseudo process doc2.txt --db shared.db
```

---

## Erreurs de traitement NLP

### Aucune entité détectée

**Causes possibles :**
- Le document ne contient pas de texte français reconnaissable
- L'encodage du fichier n'est pas UTF-8
- Le format de fichier n'est pas pris en charge

**Solutions :**
1. Assurez-vous que le texte est en français avec le bon encodage (UTF-8 avec accents : é, è, à)
2. Vérifiez que le document contient des noms, des lieux ou des organisations
3. Vérifiez que le fichier est au format `.txt` ou `.md`
4. Testez avec un exemple connu et valide :
   ```bash
   echo "Marie Dubois travaille a Paris pour Acme SA." > test.txt
   poetry run gdpr-pseudo process test.txt
   ```

### `Invalid theme 'xyz'`

**Solution :** Utilisez l'un des thèmes valides : `neutral`, `star_wars`, `lotr`

```bash
poetry run gdpr-pseudo process doc.txt --theme neutral
```

---

## Problèmes d'interface de validation

### L'interface de validation ne répond pas

**Cause :** Problème de compatibilité du terminal avec la capture d'entrée clavier.

**Solutions :**
1. Utilisez un terminal standard (PowerShell, Terminal.app, bash)
2. Évitez d'exécuter dans les terminaux intégrés des IDE (VS Code, PyCharm -- peuvent avoir des problèmes d'entrée)
3. Essayez `poetry shell` puis exécutez la commande directement
4. Sous Windows, essayez Windows Terminal au lieu de l'ancien cmd.exe

### Les raccourcis clavier ne fonctionnent pas

**Solution :** Appuyez sur `H` ou `?` durant le processus de validation pour voir l'aide complète avec tous les raccourcis disponibles. Certains raccourcis (opérations par lot comme `Shift+A`, `Shift+R`) sont masqués par défaut.

---

## Problèmes spécifiques à la plateforme

### Windows : violations d'accès spaCy

**Symptôme :** Crash ou erreurs de violation d'accès lors de l'exécution de spaCy sous Windows.

**Solutions :**
1. **Utilisez WSL (recommandé) :** Installez le sous-système Windows pour Linux et exécutez l'outil dedans
2. **Limitez les threads :** Définissez `OMP_NUM_THREADS=1` dans l'environnement :
   ```powershell
   $env:OMP_NUM_THREADS = 1
   ```
3. **Mettez à jour les dépendances :**
   - Mettez à jour Windows vers la dernière version
   - Mettez à jour Visual C++ Redistributable

**Remarque :** Il s'agit d'un problème connu de spaCy sous Windows ([spaCy #12659](https://github.com/explosion/spaCy/issues/12659)). L'intégration continue ignore les tests qui dépendent de spaCy sous Windows pour cette raison.

### macOS : Xcode Command Line Tools requis

**Erreur :** Erreurs de compilation lors de `poetry install`

**Solution :**
```bash
xcode-select --install
```

### macOS : Apple Silicon (M1/M2/M3)

Python 3.10+ dispose du support natif ARM. Si vous utilisez Homebrew :
```bash
brew install python@3.11
```

### Linux : Outils de compilation manquants

**Erreur :** Erreurs de compilation lors de `poetry install`

**Solution :**

Ubuntu/Debian :
```bash
sudo apt install python3-dev build-essential
```

Fedora :
```bash
sudo dnf install python3-devel gcc
```

### Erreurs de permission refusée

**Solutions :**
- **macOS/Linux :** Vérifiez les permissions des fichiers avec `ls -la`, assurez-vous d'avoir accès en écriture
- **Windows :** Exécutez PowerShell en tant qu'administrateur pour les étapes d'installation
- Assurez-vous d'avoir accès en écriture au répertoire du projet et aux chemins de sortie

---

## Problèmes de performance

### Le traitement ralentit ou plante sur de gros lots

**Solutions :**
- Traitez les fichiers par petits lots
- Réduisez le nombre de workers parallèles : `--workers 1`
- Fermez les autres applications pour libérer de la mémoire (le modèle spaCy utilise ~1,5 Go par worker)
- Surveillez l'utilisation de la mémoire -- l'outil nécessite jusqu'à 8 Go de RAM avec 4 workers

### Le chargement du modèle spaCy est lent

**Cause :** Le modèle `fr_core_news_lg` pèse environ 571 Mo et prend quelques secondes à charger lors de la première utilisation.

**Mitigation :** Le modèle est mis en cache en mémoire après le premier chargement. Les documents suivants dans une session de traitement par lot se traitent plus rapidement.

---

## Quand signaler un bug

Signalez un bug sur GitHub si vous rencontrez :

1. **Des plantages** non expliqués par les entrées de dépannage ci-dessus
2. **Une pseudonymisation incorrecte** (entité remplacée par le mauvais type de pseudonyme)
3. **Une perte de données** (corruption de base de données, correspondances manquantes)
4. **Des problèmes de sécurité** (exposition de mot de passe, problèmes de chiffrement)

**Comment signaler :**
- GitHub Issues : https://github.com/LioChanDaYo/RGPDpseudonymizer/issues
- Incluez : version du système d'exploitation, version Python, message d'erreur complet, étapes pour reproduire
- **N'incluez PAS** de données sensibles (vrais noms, contenu de documents) dans vos signalements de bugs

---

## Documentation connexe

- [Guide d'installation](installation.md) - Configuration spécifique à la plateforme
- [Référence CLI](CLI-REFERENCE.md) - Documentation complète des commandes
- [FAQ](faq.md) - Questions fréquemment posées
- [Tutoriel](tutorial.md) - Guides d'utilisation pas à pas
