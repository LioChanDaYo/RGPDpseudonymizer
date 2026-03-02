#!/usr/bin/env bash
# Create a Linux AppImage from the PyInstaller --onedir output.
#
# Usage:
#   ./installer/linux/create_appimage.sh [VERSION]
#   ./installer/linux/create_appimage.sh 1.1.0
#
# Prerequisites:
#   - PyInstaller has already built dist/gdpr-pseudonymizer/
#   - appimagetool is available (downloaded by this script if missing)

set -euo pipefail

VERSION="${1:-0.0.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
PYINSTALLER_OUTPUT="${DIST_DIR}/gdpr-pseudonymizer"
APPDIR="${DIST_DIR}/gdpr-pseudonymizer.AppDir"
APPIMAGE_NAME="gdpr-pseudonymizer-${VERSION}-linux.AppImage"

echo "==> Building AppImage: ${APPIMAGE_NAME}"

# Verify PyInstaller output exists
if [ ! -d "${PYINSTALLER_OUTPUT}" ]; then
    echo "ERROR: ${PYINSTALLER_OUTPUT} not found. Run PyInstaller first."
    exit 1
fi

# Clean up previous AppDir
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}"

# Copy PyInstaller output into AppDir
cp -r "${PYINSTALLER_OUTPUT}" "${APPDIR}/gdpr-pseudonymizer"

# Copy AppRun entry point
cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"

# Copy desktop entry
cp "${SCRIPT_DIR}/gdpr-pseudonymizer.desktop" "${APPDIR}/gdpr-pseudonymizer.desktop"

# Copy icon (use 256px PNG as the AppImage icon)
ICON_SRC="${PYINSTALLER_OUTPUT}/gdpr_pseudonymizer/gui/resources/icons/icon_256.png"
if [ -f "${ICON_SRC}" ]; then
    cp "${ICON_SRC}" "${APPDIR}/gdpr-pseudonymizer.png"
else
    echo "WARNING: Icon not found at ${ICON_SRC}, AppImage will have no icon"
fi

# Download appimagetool if not available
APPIMAGETOOL="appimagetool"
if ! command -v "${APPIMAGETOOL}" &>/dev/null; then
    echo "==> Downloading appimagetool..."
    APPIMAGETOOL="${DIST_DIR}/appimagetool"
    curl -fsSL -o "${APPIMAGETOOL}" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
fi

# Build AppImage
cd "${DIST_DIR}"
ARCH=x86_64 "${APPIMAGETOOL}" "${APPDIR}" "${APPIMAGE_NAME}"

echo "==> AppImage created: ${DIST_DIR}/${APPIMAGE_NAME}"
echo "==> Size: $(du -h "${DIST_DIR}/${APPIMAGE_NAME}" | cut -f1)"
