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
