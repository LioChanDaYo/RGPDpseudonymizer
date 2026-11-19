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
; A folder typed on this page gets its own "GDPR Pseudonymizer" subfolder.
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE OwnFolderLeave
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

; The previous install's folder, read in .onInit before anything writes it.
; Declared before the LangStrings that show it.
Var OldInstDir

; Shown when the app or the command line is open during the install.
; This file is saved as UTF-8 with a BOM so makensis reads the accented
; letters correctly whatever the build machine's code page.
LangString MSG_APP_OPEN ${LANG_ENGLISH} "GDPR Pseudonymizer is open. Close the app and any command window using gdpr-pseudo, then click Retry."
LangString MSG_APP_OPEN ${LANG_FRENCH} "GDPR Pseudonymizer est ouvert. Fermez l'application et toute fenêtre de commande qui utilise gdpr-pseudo, puis cliquez sur Réessayer."

; Shown after an upgrade from a folder typed by hand: the new copy is in its
; own subfolder and the earlier one is still where it was (Story 12.1).
LangString MSG_OLD_COPY ${LANG_ENGLISH} "GDPR Pseudonymizer is now installed in:$\r$\n$INSTDIR$\r$\n$\r$\nThe earlier version is still in:$\r$\n$OldInstDir$\r$\nYou can delete it by hand. In that folder, delete only _internal, gdpr-pseudonymizer.exe, gdpr-pseudo.exe and Uninstall.exe.$\r$\n$\r$\nDo not run that Uninstall.exe: it would delete everything in the folder, your own files included."
LangString MSG_OLD_COPY ${LANG_FRENCH} "GDPR Pseudonymizer est maintenant installé dans :$\r$\n$INSTDIR$\r$\n$\r$\nL'ancienne version est toujours dans :$\r$\n$OldInstDir$\r$\nVous pouvez la supprimer à la main. Dans ce dossier, supprimez uniquement _internal, gdpr-pseudonymizer.exe, gdpr-pseudo.exe et Uninstall.exe.$\r$\n$\r$\nN'exécutez pas ce fichier Uninstall.exe : il supprimerait tout le contenu du dossier, y compris vos propres fichiers."

;---------------------------------------------------------------------------
; Functions: the install folder always ends in \GDPR Pseudonymizer
;---------------------------------------------------------------------------

; In: a folder on the stack. Out: the same folder without trailing
; backslashes or spaces.
Function TrimFolder
    Exch $0
    Push $1
    trim_loop:
    StrCpy $1 $0 1 -1
    StrCmp $1 "\" trim_one
    StrCmp $1 " " trim_one trim_done
    trim_one:
    StrCpy $0 $0 -1
    Goto trim_loop
    trim_done:
    Pop $1
    Exch $0
FunctionEnd

; In: a folder on the stack. Out: that folder, trimmed, ending in
; \GDPR Pseudonymizer (capitals ignored): the folder itself when it already
; ends so, otherwise its « GDPR Pseudonymizer » subfolder. The last 19
; characters are compared, backslash included, so D:\XGDPR Pseudonymizer
; still gets the subfolder.
Function OwnFolderOf
    Call TrimFolder
    Exch $0
    Push $1
    Push $2
    StrLen $2 "\${APPNAME}"   ; 19
    IntOp $1 0 - $2           ; -19
    StrCpy $1 $0 $2 $1        ; the last 19 characters
    StrCmp $1 "\${APPNAME}" own_done
    StrCpy $0 "$0\${APPNAME}"
    own_done:
    Pop $2
    Pop $1
    Exch $0
FunctionEnd

; $INSTDIR holds the /D= folder or the registry folder here, so a silent
; install and the directory page both start from the final folder.
Function .onInit
    ReadRegStr $OldInstDir HKLM "Software\${APPNAME}" "InstallDir"
    Push $INSTDIR
    Call OwnFolderOf
    Pop $INSTDIR
FunctionEnd

; NSIS reads the folder field back into $INSTDIR after this function, so
; the result is also written into the field (control 1019).
Function OwnFolderLeave
    Push $1
    Push $INSTDIR
    Call OwnFolderOf
    Pop $INSTDIR
    FindWindow $1 "#32770" "" $HWNDPARENT
    GetDlgItem $1 $1 1019
    SendMessage $1 ${WM_SETTEXT} 0 "STR:$INSTDIR"
    Pop $1
FunctionEnd

; After an upgrade from a folder typed by hand, the earlier copy stays where it
; was. Tell where both are, which files to delete by hand, and not to run the
; earlier Uninstall.exe: it would delete its whole folder (Story 12.1).
Function OldCopyMessage
    Push $0
    StrCmp $OldInstDir "" old_done
    Push $OldInstDir
    Call TrimFolder
    Pop $OldInstDir
    Push $OldInstDir
    Call OwnFolderOf
    Pop $0
    StrCmp $0 $OldInstDir old_done
    IfFileExists "$OldInstDir\gdpr-pseudonymizer.exe" 0 old_done
    MessageBox MB_OK|MB_ICONINFORMATION "$(MSG_OLD_COPY)" /SD IDOK
    old_done:
    Pop $0
FunctionEnd

;---------------------------------------------------------------------------
; Sections
;---------------------------------------------------------------------------
Section "!${APPNAME}" SecMain
    SectionIn RO  ; Required — cannot be deselected

    ; Install only into a folder of its own, whatever set $INSTDIR (the
    ; directory page, /D=, the registry): the cleanup below then never runs
    ; in a folder the user chose for other things.
    Push $INSTDIR
    Call OwnFolderOf
    Pop $INSTDIR

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

    ; Last, so the message is true when shown and an aborted install never
    ; shows it.
    Call OldCopyMessage
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
    ; Remove only what the installer put there, then the folder if it is
    ; empty. Anything else in it stays (Story 12.1).
    Delete "$INSTDIR\gdpr-pseudonymizer.exe"
    Delete "$INSTDIR\gdpr-pseudo.exe"
    RMDir /r "$INSTDIR\_internal"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove Start Menu shortcuts, then their folder if it is empty
    Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
    Delete "$SMPROGRAMS\${APPNAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APPNAME}"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APPNAME}.lnk"

    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
    DeleteRegKey HKLM "Software\${APPNAME}"
SectionEnd
