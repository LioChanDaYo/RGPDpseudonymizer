"""
Unit tests for the Windows installer script (installer/windows/installer.nsi).

Installing over an earlier version copied the new files over the old ones
without removing anything, so the earlier version's files stayed in
``_internal`` next to the new ones. The desktop app then read the earlier
version's ``*.dist-info`` stamp and showed the earlier version number
(installing 2.3.2 over 2.3.1 showed "2.3.1").
"""

import re
from pathlib import Path

INSTALLER_PATH = (
    Path(__file__).parent.parent.parent / "installer" / "windows" / "installer.nsi"
)


def _main_section_lines() -> list[str]:
    """Return the statements of the SecMain install section, comments removed."""
    lines = INSTALLER_PATH.read_text(encoding="utf-8").splitlines()
    statements: list[str] = []
    inside = False
    for raw in lines:
        line = raw.strip()
        if not inside:
            if re.match(r"Section\s+.*\bSecMain\b", line):
                inside = True
            continue
        if line.startswith("SectionEnd"):
            return statements
        # NSIS comments start with ';' or '#'; no string in this section holds one.
        line = re.split(r"\s*[;#]", line, maxsplit=1)[0].strip()
        if line:
            statements.append(line)
    raise AssertionError("SecMain section not found in installer.nsi")


def _index_of(statements: list[str], pattern: str) -> int:
    for index, statement in enumerate(statements):
        if re.fullmatch(pattern, statement, flags=re.IGNORECASE):
            return index
    return -1


def test_install_removes_previous_internal_folder_before_copy() -> None:
    """The previous _internal folder is removed before the new files are copied."""
    statements = _main_section_lines()
    copy_index = _index_of(statements, r'File\s+/r\s+"\$\{DISTDIR\}\\\*\.\*"')
    remove_index = _index_of(statements, r'RMDir\s+/r\s+"\$INSTDIR\\_internal"')

    assert copy_index >= 0, f"no File /r copy in SecMain: {statements}"
    assert (
        remove_index >= 0
    ), f'SecMain does not remove "$INSTDIR\\_internal" before copying: {statements}'
    assert (
        remove_index < copy_index
    ), f'"$INSTDIR\\_internal" is removed after the copy, not before: {statements}'


def test_install_removes_only_the_internal_folder() -> None:
    """The install never removes the chosen folder itself, which may hold other things."""
    statements = _main_section_lines()
    removals = [s for s in statements if re.match(r"(RMDir|Delete)\b", s, re.I)]

    assert removals, f"SecMain removes nothing: {statements}"
    for removal in removals:
        assert re.fullmatch(
            r'RMDir\s+/r\s+"\$INSTDIR\\_internal"', removal, flags=re.IGNORECASE
        ), f"SecMain removes more than $INSTDIR\\_internal: {removal}"


EXECUTABLES = ("gdpr-pseudonymizer.exe", "gdpr-pseudo.exe")


def _label_index(statements: list[str], label: str) -> int:
    return _index_of(statements, re.escape(label) + ":")


def test_cleanup_is_skipped_while_either_executable_is_in_use() -> None:
    """The _internal folder is kept while the desktop app or the CLI is open.

    Removing it then would delete the unlocked files only; if the user then
    cancels at the locked-file prompt of the copy, the old version is left
    broken. Each executable that exists is opened for writing (append mode,
    which neither changes nor truncates it); if that fails, the cleanup is
    skipped.
    """
    statements = _main_section_lines()
    copy_index = _index_of(statements, r'File\s+/r\s+"\$\{DISTDIR\}\\\*\.\*"')
    remove_index = _index_of(statements, r'RMDir\s+/r\s+"\$INSTDIR\\_internal"')
    assert 0 <= remove_index < copy_index, f"no cleanup before the copy: {statements}"

    for exe in EXECUTABLES:
        path = r'"\$INSTDIR\\' + re.escape(exe) + '"'
        open_index = _index_of(statements, r"FileOpen\s+(\$\w+)\s+" + path + r"\s+a")
        assert (
            0 <= open_index < remove_index
        ), f"{exe} is not opened in append mode before the cleanup: {statements}"
        handle = re.split(r"\s+", statements[open_index])[1]

        exists_index = _index_of(statements, r"IfFileExists\s+" + path + r"\s+.*")
        assert 0 <= exists_index < open_index, (
            f"{exe} is opened without checking that it exists (append mode "
            f"would create it): {statements}"
        )
        assert re.fullmatch(
            "ClearErrors", statements[open_index - 1], flags=re.IGNORECASE
        ), f"no ClearErrors right before opening {exe}: {statements}"

        check = re.fullmatch(
            r"IfErrors\s+(\w+)", statements[open_index + 1], flags=re.IGNORECASE
        )
        assert check, f"no IfErrors right after opening {exe}: {statements}"
        skip_index = _label_index(statements, check.group(1))
        assert remove_index < skip_index < copy_index, (
            f"IfErrors after opening {exe} does not jump past the cleanup: "
            f"{statements}"
        )

        assert re.fullmatch(
            r"FileClose\s+" + re.escape(handle),
            statements[open_index + 2],
            flags=re.IGNORECASE,
        ), f"{exe} is not closed after the in-use check: {statements}"
