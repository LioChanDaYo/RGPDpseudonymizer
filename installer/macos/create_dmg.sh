#!/usr/bin/env bash
# Create a macOS .dmg from the PyInstaller .app bundle.
#
# Usage:
#   ./installer/macos/create_dmg.sh [VERSION] [ARCH]
#   ./installer/macos/create_dmg.sh 1.1.0 arm64
#
# Assumes PyInstaller has already built dist/GDPR Pseudonymizer.app

set -euo pipefail

VERSION="${1:-0.0.0}"
ARCH="${2:-$(uname -m)}"

APP_NAME="GDPR Pseudonymizer"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="gdpr-pseudonymizer-${VERSION}-macos-${ARCH}.dmg"
DMG_PATH="dist/${DMG_NAME}"
VOLUME_NAME="${APP_NAME} ${VERSION}"

echo "==> Creating DMG: ${DMG_NAME}"

# Verify .app exists
if [ ! -d "${APP_PATH}" ]; then
    echo "ERROR: ${APP_PATH} not found. Run PyInstaller first."
    exit 1
fi

# Clean up any previous DMG
rm -f "${DMG_PATH}"
rm -f "dist/tmp-${DMG_NAME}"

# Create temporary DMG
hdiutil create \
    -srcfolder "${APP_PATH}" \
    -volname "${VOLUME_NAME}" \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    -format UDRW \
    "dist/tmp-${DMG_NAME}"

# Mount the temporary DMG
MOUNT_DIR=$(hdiutil attach "dist/tmp-${DMG_NAME}" | grep '/Volumes/' | sed 's/.*\/Volumes/\/Volumes/')
echo "==> Mounted at: ${MOUNT_DIR}"

# Add symlink to /Applications for drag-and-drop install
ln -s /Applications "${MOUNT_DIR}/Applications"

# Set volume icon (use the app icon)
if [ -f "${APP_PATH}/Contents/Resources/icon_512.png" ]; then
    cp "${APP_PATH}/Contents/Resources/icon_512.png" "${MOUNT_DIR}/.VolumeIcon.icns" 2>/dev/null || true
    SetFile -c icnC "${MOUNT_DIR}/.VolumeIcon.icns" 2>/dev/null || true
    SetFile -a C "${MOUNT_DIR}" 2>/dev/null || true
fi

# Unmount
hdiutil detach "${MOUNT_DIR}" -quiet

# Convert to compressed read-only DMG
hdiutil convert \
    "dist/tmp-${DMG_NAME}" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "${DMG_PATH}"

# Clean up temporary DMG
rm -f "dist/tmp-${DMG_NAME}"

echo "==> DMG created: ${DMG_PATH}"
echo "==> Size: $(du -h "${DMG_PATH}" | cut -f1)"
