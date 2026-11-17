; GDPR Pseudonymizer — NSIS Installer Script
; Wraps the PyInstaller --onedir output into a single .exe installer
;
; Usage:  makensis /DVERSION=1.1.0 installer.nsi
;         (run from the repo root after PyInstaller build)

;---------------------------------------------------------------------------
; Defines
;---------------------------------------------------------------------------
!ifndef VERSION
  !define VERSION "0.0.0"
!endif

!define APPNAME "GDPR Pseudonymizer"
!define COMPANYNAME "GDPR Pseudonymizer Team"
!define EXENAME "gdpr-pseudonymizer.exe"
!define INSTALLDIR "$PROGRAMFILES\${APPNAME}"

; Source directory — PyInstaller output
!define DISTDIR "..\..\dist\gdpr-pseudonymizer"

;---------------------------------------------------------------------------
; General
;---------------------------------------------------------------------------
Name "${APPNAME} ${VERSION}"
OutFile "..\..\dist\gdpr-pseudonymizer-${VERSION}-windows-setup.exe"
InstallDir "${INSTALLDIR}"
InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Unicode true

;---------------------------------------------------------------------------
; Includes
;---------------------------------------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"

;---------------------------------------------------------------------------
; Interface settings
;---------------------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON "${DISTDIR}\_internal\gdpr_pseudonymizer\gui\resources\icons\app.ico"
!define MUI_UNICON "${DISTDIR}\_internal\gdpr_pseudonymizer\gui\resources\icons\app.ico"

;---------------------------------------------------------------------------
; Pages
;---------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;---------------------------------------------------------------------------
; Languages
;---------------------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"

; Shown when the app or the command line is open during the install.
; This file is saved as UTF-8 with a BOM so makensis reads the accented
; letters correctly whatever the build machine's code page.
LangString MSG_APP_OPEN ${LANG_ENGLISH} "GDPR Pseudonymizer is open. Close the app and any command window using gdpr-pseudo, then click Retry."
LangString MSG_APP_OPEN ${LANG_FRENCH} "GDPR Pseudonymizer est ouvert. Fermez l'application et toute fenêtre de commande qui utilise gdpr-pseudo, puis cliquez sur Réessayer."

;---------------------------------------------------------------------------
; Sections
;---------------------------------------------------------------------------
Section "!${APPNAME}" SecMain
    SectionIn RO  ; Required — cannot be deselected

    ; Refuse to install while the app or the command line is open. Their files
    ; are locked: only part of the earlier version could be removed, and the
    ; install would end with both versions' files. An executable in use cannot
    ; be opened for writing. Append mode ("a") neither changes nor truncates
    ; it, but would create it if missing, hence IfFileExists first. Nothing is
    ; changed before this check passes; Cancel (and a silent install) aborts.
    check_app_closed:
    IfFileExists "$INSTDIR\gdpr-pseudonymizer.exe" 0 check_cli_closed
    ClearErrors
    FileOpen $0 "$INSTDIR\gdpr-pseudonymizer.exe" a
    IfErrors app_open
    FileClose $0
    check_cli_closed:
    IfFileExists "$INSTDIR\gdpr-pseudo.exe" 0 app_closed
    ClearErrors
    FileOpen $0 "$INSTDIR\gdpr-pseudo.exe" a
    IfErrors app_open
    FileClose $0
    Goto app_closed
    app_open:
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(MSG_APP_OPEN)" /SD IDCANCEL IDRETRY check_app_closed
    Abort
    app_closed:

    SetOutPath "$INSTDIR"

    ; Remove the _internal folder of an earlier version first. Otherwise its
    ; version stamp (*.dist-info) and libraries stay next to the new ones, and
    ; the app shows the earlier version number. Only _internal is removed: the
    ; two top-level executables are overwritten, and the chosen folder may hold
    ; other things.
    RMDir /r "$INSTDIR\_internal"

    ; Copy entire PyInstaller output directory
    File /r "${DISTDIR}\*.*"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
    CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\${EXENAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1

    ; Calculate and write estimated size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" $0

    ; Save install dir in app registry key
    WriteRegStr HKLM "Software\${APPNAME}" "InstallDir" "$INSTDIR"
SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
SectionEnd

;---------------------------------------------------------------------------
; Section descriptions
;---------------------------------------------------------------------------
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Install ${APPNAME} (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a desktop shortcut."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;---------------------------------------------------------------------------
; Uninstaller
;---------------------------------------------------------------------------
Section "Uninstall"
    ; Remove files (entire install directory)
    RMDir /r "$INSTDIR"

    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\${APPNAME}"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APPNAME}.lnk"

    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKLM "Software\${APPNAME}"
SectionEnd
