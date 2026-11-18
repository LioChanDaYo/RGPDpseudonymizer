# Epic 12: Windows Installer Uses Its Own Folder - Brownfield Enhancement

**Epic Goal:** The Windows installer always puts the app in a folder of its own whose name is « GDPR Pseudonymizer », and the uninstaller removes only what the installer put there, then the folder only if it is empty. Neither installing nor uninstalling can then delete a file the installer did not put there. An upgrade from an install in a hand-typed folder goes into a new subfolder, leaves the old copy untouched, and says so during the installation.

**Target Release:** the next release (none is planned). Story 12.1 lands on main first; no tag and no PyPI release without Lionel's explicit go.
**Predecessor:** v2.3.2 (Epic 11, released 2026-11-17)
**Successor:** none set. Epics 8 (v2.4) and 9 (v3.0) are unchanged.

---

## Scope Rule

One story, Story 12.1, on the Windows installer only. Nothing else. Out of scope: the macOS DMG, the Linux AppImage, and deleting old copies.

Lionel's decisions, word for word:

- Story 12.1, Lionel, 2026-11-18: a fix of the uninstaller alone (it removes only the files it installed, and the folder only if it is then empty), with the install-side case left as a known limitation, is rejected. The question asked: "Shall the BMAD agents make the uninstaller remove only the files it installed (and the folder only if it is then empty), shipped with the next release, and leave the install-side case as a known limitation?" His answer: "no, i don't want to create such a risk".
- Story 12.1, Lionel, 2026-11-18: both changes ship with the next release: the installer always uses its own « GDPR Pseudonymizer » folder, and the uninstaller removes only its own files. The question asked: "Shall the BMAD agents make both changes (the installer always uses its own « GDPR Pseudonymizer » folder, and the uninstaller removes only its own files), shipped with the next release?" His answer: "yes, but what do we do about the existing 25 windows installed programs? what will happen when they try to upgrade?"
- Story 12.1, Lionel, 2026-11-18: for an install in a hand-typed folder, the old copy is left untouched, and the sentence telling people they can delete it by hand is spelt out by the installer itself during the installation, not in the CHANGELOG. The explanation he was given first: installs in the default folder or in a folder chosen with « Parcourir » upgrade in place and receive the new uninstaller; an install in a hand-typed folder whose name is not « GDPR Pseudonymizer » upgrades into a new `<folder>\GDPR Pseudonymizer` subfolder, and the old copy is left untouched, because deleting it could recreate the install-side risk (risk (b) below). The question asked: "Shall the old copy in a hand-typed folder be left untouched, with that one CHANGELOG sentence telling people to delete it by hand?" His answer: "in case 2, i want the sentence to be not in the changelog, but in the installer itself, as in it is spelt out during the installation process".

---

## Existing System Context

- **Current relevant functionality:** v2.3.2 ships a Windows installer built with NSIS from the PyInstaller one-folder output (`installer/windows/installer.nsi`, built by the Windows job of `.github/workflows/build-executables.yaml` with `makensis /DVERSION=…`). It speaks English and French (`MUI_LANGUAGE`, `LangString MSG_APP_OPEN`). Since 2.3.2 it refuses to install while the desktop app or the command line is open, and removes `_internal` before the copy.
- **Technology stack:** NSIS 3 (MUI2, `FileFunc.nsh`), PyInstaller one-folder build from `gdpr-pseudo-gui.spec`, pytest.
- **Integration points:** `installer/windows/installer.nsi`, `tests/unit/test_windows_installer_script.py`, `gdpr-pseudo-gui.spec` (read only, for the list of installed files), `.github/workflows/build-executables.yaml`, `CHANGELOG.md`.

---

## Stories

### Story 12.1: The Windows Installer Uses Its Own Folder and the Uninstaller Removes Only Its Own Files

**Problem** (measured by the orchestrator on 2026-11-18 on origin/main `9dafd44`, `installer/windows/installer.nsi`):

- The default install folder is `C:\Program Files (x86)\GDPR Pseudonymizer`. `InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"` (l.28) makes an upgrade reuse the previous folder. The « Parcourir » button appends « GDPR Pseudonymizer » to the folder chosen. A folder typed by hand in the field is used as typed.
- At install, l.109 runs `RMDir /r "$INSTDIR\_internal"` before `File /r` (the 2.3.2 fix for the stale version number).
- At uninstall, l.158 runs `RMDir /r "$INSTDIR"`: it deletes the whole folder, including files the installer never put there.
- Risk (a): a hand-typed folder such as `D:\Outils` is wiped entirely at uninstall, the user's own files included (for example a mapping database saved there).
- Risk (b): a hand-typed folder that already holds another PyInstaller app, with its own `_internal`, loses that `_internal` at install, which breaks the other app.
- Context: the desktop app proposes new databases in the user's home folder or next to the document (`gui/widgets/passphrase_dialog.py:242`), never in the install folder. The Windows installer has 25 downloads across 8 releases. No user report.

**Scope (the SM writes the detailed story):**

- **Own folder (removes risk (b)).** The installer always installs into a folder whose last part is « GDPR Pseudonymizer »: if the folder chosen or typed does not end with it, the installer appends it. The default folder and a folder chosen with « Parcourir » already end with it and do not change.
- **Own files only (removes risk (a)).** The uninstaller removes only what the installer put there: `_internal`, the two executables `gdpr-pseudonymizer.exe` and `gdpr-pseudo.exe`, and `Uninstall.exe`, plus its Start Menu folder, its desktop shortcut and its registry entries. It then removes the folder only if it is empty. Anything else stays. The SM checks the exact list against `gdpr-pseudo-gui.spec` (two `EXE` with `exclude_binaries=True`, `COLLECT` into the default `_internal`) and the .nsi (`WriteUninstaller`), and confirms it against the listing of a real `dist\gdpr-pseudonymizer` build.
- **Upgrade from a hand-typed folder.** When the previous install's folder (registry `InstallDir`) does not end with « GDPR Pseudonymizer », the new version goes into the `GDPR Pseudonymizer` subfolder and the old copy is left untouched. During the installation, in English and in French, the installer tells the user where the new copy is, and that the old copy is still in the old folder and can be deleted by hand. The message is shown only in that case; silent installs skip it. The exact English and French text is proposed by the SM. **Lionel approves the French text himself before it is committed.**
- **Added by the PM (2026-11-18), for Lionel to see when he approves the text:** the old copy keeps its old `Uninstall.exe`, and an NSIS uninstaller works on the folder it runs from. Run from `D:\Outils`, it would still run the old `RMDir /r "$INSTDIR"`: it would delete all of `D:\Outils` (the user's files and the new `GDPR Pseudonymizer` subfolder included), and it would also remove the registry entries, the Start Menu folder and the desktop shortcut that now belong to the new copy. So the message names the files to delete by hand (`_internal`, `gdpr-pseudonymizer.exe`, `gdpr-pseudo.exe`, `Uninstall.exe`) and says not to run the old folder's `Uninstall.exe`.
- The 2.3.2 behaviour stays: the installer refuses to run while the desktop app or the command line is open, and removes `_internal` before the copy (now always inside a folder whose last part is « GDPR Pseudonymizer »).
- Ships with the next release (none is planned); it lands on main first.
- CHANGELOG `[Unreleased]` entry, as usual for a user-visible change. The "delete the old copy by hand" sentence is in the installer, not in the CHANGELOG (Lionel, 2026-11-18).
- Proof: tests on the .nsi script in the style of `tests/unit/test_windows_installer_script.py`. Before the release, Lionel hand-checks a build of the installer (dispatch `build-executables`):
  - install into a typed folder; the app lands in its own subfolder;
  - put a file in the app folder, uninstall, and check the file is still there;
  - upgrade from a typed-folder install; the message appears and the old copy is untouched.
- Out of scope: the macOS DMG, the Linux AppImage, and deleting old copies.

**Known limitation (recorded, not fixed):** an install that is never upgraded keeps its old uninstaller, which still deletes its whole folder. The old copy left in a hand-typed folder keeps its old uninstaller too; the message covers that case.

**Acceptance (epic level):**

1. Every install, silent installs included, ends in a folder whose last part is « GDPR Pseudonymizer » (capitals and a trailing backslash ignored in the check). A typed `D:\Outils` gives `D:\Outils\GDPR Pseudonymizer`; the default folder and a folder chosen with « Parcourir » are unchanged.
2. The uninstaller removes `_internal`, `gdpr-pseudonymizer.exe`, `gdpr-pseudo.exe` and `Uninstall.exe` (the list confirmed against the spec, the .nsi and a real build listing), its Start Menu folder, its desktop shortcut and its registry entries, then the folder only if it is empty. No `RMDir /r "$INSTDIR"` remains; any other file or folder in it stays.
3. The install-side `RMDir /r "$INSTDIR\_internal"` only ever runs inside a folder whose last part is « GDPR Pseudonymizer ».
4. Upgrade from a typed-folder install: the new copy goes into the subfolder; nothing in the old folder is changed or deleted; the message, in English and in French, says where the new copy is, that the old copy is still in the old folder and can be deleted by hand, which files to delete, and not to run the old folder's `Uninstall.exe`. It is shown only in that case; silent installs skip it. Default and « Parcourir » installs upgrade in place with no message.
5. The 2.3.2 behaviour is unchanged: the install is refused while the desktop app or the command line is open, and `_internal` is removed before the copy.
6. Tests on the .nsi script, in the style of `tests/unit/test_windows_installer_script.py`, cover 1 to 5; the existing installer tests stay green; full CI green; the `build-executables` Windows job green on the branch head.
7. The French text is approved word for word by Lionel before it is committed.
8. CHANGELOG `[Unreleased]` entry, without the "delete the old copy by hand" sentence.
9. Before the release, Lionel's hand check of a build passes its three steps (typed folder gets its own subfolder; a file put in the app folder survives the uninstall; a typed-folder upgrade shows the message and leaves the old copy untouched).

---

## Process for Every Story

- Tests first on CI: a tests-first commit and a draft PR before the fix.
- QA review.
- One read-only Codex review of the final head before merge.
- Codex only reviews. Claude BMAD agents write the code.

---

## Release

Story 12.1 lands on main with its CHANGELOG `[Unreleased]` entry and ships with the next release, none planned. Before that release, Lionel hand-checks a build of the installer (the three steps above). No tag and no PyPI release without Lionel's explicit go.

---

## Compatibility Requirements

- [ ] Installs in the default folder or in a folder chosen with « Parcourir » upgrade in place, as today, and receive the new uninstaller.
- [ ] No change to the desktop app, the CLI, the mapping database, or the macOS and Linux builds.
- [ ] Silent installs keep working, with no message.

## Risk Mitigation

- **Primary risk:** the uninstaller misses a file the installer put there (files left behind) or removes one it did not put there; the folder rule moves a default or « Parcourir » install to a new folder; a user deletes the old copy of a hand-typed install by running its old `Uninstall.exe`, which still deletes the whole folder (the user's files and the new copy included) and the new copy's registry entries and shortcuts.
- **Mitigation:** the file list checked against the spec, the .nsi and a real build listing; tests on the .nsi script; the message names the files to delete and says not to run the old `Uninstall.exe`; Lionel's hand check of a build before the release.
- **Rollback plan:** revert the story's merge commit; nothing is released until Lionel's go.

## Definition of Done

- [ ] Story 12.1 merged: every install lands in a folder whose last part is « GDPR Pseudonymizer »; the uninstaller removes only the installer's own files, shortcuts and registry entries, then the folder only if it is empty; a typed-folder upgrade goes into the subfolder, leaves the old copy untouched and says so during the installation, in English and in French, naming the files to delete and warning not to run the old `Uninstall.exe` (silent installs skip it); the 2.3.2 checks unchanged; tests on the .nsi script; CHANGELOG `[Unreleased]` entry
- [ ] French text approved word for word by Lionel before it is committed
- [ ] Tests-first commit and draft PR, QA review, read-only Codex review of the final head
- [ ] No regression in existing features (full CI green, `build-executables` Windows job green on the branch head)
- [ ] Before the next release: Lionel's hand check of an installer build passes its three steps

---

## Story Manager Handoff

"Please develop the detailed user story for this brownfield epic. Key considerations:

- This changes the Windows NSIS installer of an existing Python/Poetry CLI and PySide6 desktop app; nothing else.
- Integration points: `installer/windows/installer.nsi` (l.17 and l.27-28 for the folder, l.84-109 for the 2.3.2 checks, l.156-169 for the uninstaller), `tests/unit/test_windows_installer_script.py`, `gdpr-pseudo-gui.spec` (read only, for the installed file list), `.github/workflows/build-executables.yaml`, `CHANGELOG.md`.
- The mechanism (for example `.onVerifyInstDir` or a check after the directory page, and how the previous `InstallDir` is read) is the SM's and the dev's choice.
- Confirm the installed file list against a real `dist\gdpr-pseudonymizer` listing; the orchestrator did not list a build.
- Propose the exact English and French message; Lionel approves the French word for word before it is committed. The message names the files to delete by hand and says not to run the old folder's `Uninstall.exe`.
- The 2.3.2 checks (refusal while the app or the CLI is open, `_internal` removed before the copy) must keep working.
- The orchestrator runs `build-executables.yaml` on the branch head before merge; Lionel hand-checks a build before the release.
- Each story must include verification that existing functionality remains intact.

The epic should leave the installer unable to delete anything it did not put there, at install and at uninstall, while default installs keep upgrading in place."
