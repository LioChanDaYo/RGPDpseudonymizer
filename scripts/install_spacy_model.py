"""Install spaCy French language model.

This script downloads and installs the fr_core_news_lg model required
for French named entity recognition.
"""

from __future__ import annotations

import subprocess
import sys


def check_model_installed(model_name: str = "fr_core_news_lg") -> bool:
    """Check if spaCy model is already installed.

    Args:
        model_name: Name of the spaCy model to check

    Returns:
        True if model is installed, False otherwise
    """
    try:
        import spacy

        spacy.load(model_name)
        return True
    except OSError:
        return False
    except Exception as e:
        print(f"Error checking model: {e}", file=sys.stderr)
        return False


def install_model(model_name: str = "fr_core_news_lg") -> bool:
    """Install spaCy model using spaCy download command.

    Args:
        model_name: Name of the spaCy model to install

    Returns:
        True if installation successful, False otherwise
    """
    print(f"Installing spaCy model: {model_name}")
    print("This may take a few minutes (model size: ~571MB)...")
    print()

    try:
        # Run spaCy download command
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            check=True,
            capture_output=False,
        )

        if result.returncode == 0:
            print()
            print(f"[SUCCESS] Model '{model_name}' installed successfully!")
            return True
        else:
            print(
                f"[ERROR] Model installation failed with exit code {result.returncode}"
            )
            return False

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Installation failed: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point for model installation script.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    model_name = "fr_core_news_lg"

    print("=" * 70)
    print("spaCy French Language Model Installer")
    print("=" * 70)
    print()

    # Check if already installed
    if check_model_installed(model_name):
        print(f"[OK] Model '{model_name}' is already installed!")
        print()
        print("To verify installation, run:")
        print(f"  python -c \"import spacy; spacy.load('{model_name}')\"")
        return 0

    # Install model
    print(f"Model '{model_name}' is not installed.")
    print()

    success = install_model(model_name)

    if success:
        # Verify installation
        print()
        print("Verifying installation...")
        if check_model_installed(model_name):
            print("[OK] Verification successful!")
            print()
            print("You can now use the GDPR Pseudonymizer CLI:")
            print("  gdpr-pseudo process input.txt --validate")
            return 0
        else:
            print("[ERROR] Verification failed. Model may not be installed correctly.")
            print()
            print("Please try manual installation:")
            print(f"  python -m spacy download {model_name}")
            return 1
    else:
        print()
        print("Installation failed. Please check:")
        print("  1. Internet connection is available")
        print("  2. Sufficient disk space (~571MB required)")
        print("  3. spaCy is installed: pip install spacy>=3.7.0")
        print()
        print("For manual installation, run:")
        print(f"  python -m spacy download {model_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
