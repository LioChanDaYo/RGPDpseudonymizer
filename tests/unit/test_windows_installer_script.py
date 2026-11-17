"""
Unit tests for the Windows installer script (installer/windows/installer.nsi).

Installing over an earlier version copied the new files over the old ones
without removing anything, so the earlier version's files stayed in
``_internal`` next to the new ones. The desktop app then read the earlier
version's ``*.dist-info`` stamp and showed the earlier version number
(installing 2.3.2 over 2.3.1 showed "2.3.1").

The installer now removes ``_internal`` before the copy. While the desktop app
or the command line is open, their files are locked and only part of
``_internal`` could go, so the installer first asks to close them and installs
nothing until they are closed.
"""

import itertools
import re
from pathlib import Path

INSTALLER_PATH = (
    Path(__file__).parent.parent.parent / "installer" / "windows" / "installer.nsi"
)

EXECUTABLES = ("gdpr-pseudonymizer.exe", "gdpr-pseudo.exe")

MESSAGES = {
    "ENGLISH": (
        "GDPR Pseudonymizer is open. Close the app and any command window "
        "using gdpr-pseudo, then click Retry."
    ),
    "FRENCH": (
        "GDPR Pseudonymizer est ouvert. Fermez l'application et toute fenêtre "
        "de commande qui utilise gdpr-pseudo, puis cliquez sur Réessayer."
    ),
}

_TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|`[^`]*`|[;#].*|\S+')
_LABEL = re.compile(r"([A-Za-z_][\w.]*):")


def _tokens(line: str) -> list[str]:
    """Split an NSIS line into tokens, dropping a trailing comment."""
    tokens: list[str] = []
    for token in _TOKEN.findall(line):
        if token[0] in ";#":
            break
        tokens.append(token)
    return tokens


def _main_section() -> list[list[str]]:
    """Return the statements of the SecMain install section as token lists."""
    lines = INSTALLER_PATH.read_text(encoding="utf-8-sig").splitlines()
    statements: list[list[str]] = []
    inside = False
    for raw in lines:
        tokens = _tokens(raw)
        if not inside:
            if tokens[:1] == ["Section"] and "SecMain" in tokens:
                inside = True
            continue
        if tokens[:1] == ["SectionEnd"]:
            return statements
        if tokens:
            statements.append(tokens)
    raise AssertionError("SecMain section not found in installer.nsi")


def _main_section_lines() -> list[str]:
    return [" ".join(tokens) for tokens in _main_section()]


def _index_of(statements: list[str], pattern: str) -> int:
    for index, statement in enumerate(statements):
        if re.fullmatch(pattern, statement, flags=re.IGNORECASE):
            return index
    return -1


def _labels(statements: list[list[str]]) -> dict[str, int]:
    return {
        match.group(1): index
        for index, tokens in enumerate(statements)
        if len(tokens) == 1 and (match := _LABEL.fullmatch(tokens[0]))
    }


def _unquote(token: str) -> str:
    return token[1:-1] if token[:1] in "\"'`" else token


def _exe_of(path_token: str) -> str:
    path = _unquote(path_token)
    assert path.startswith("$INSTDIR\\"), f"unexpected path: {path}"
    return path[len("$INSTDIR\\") :]


def _resolve(target: str, here: int, labels: dict[str, int]) -> int:
    """Return the statement index a jump target leads to (NSIS rules)."""
    if target in ("", "0"):
        return here + 1
    assert target in labels, f"jump to an unknown or relative target: {target}"
    return labels[target]


def _run(
    statements: list[list[str]],
    exists: set[str],
    in_use: set[str],
    answers: list[str],
    silent: bool = False,
) -> list[str]:
    """Simulate SecMain up to the copy, and return what happened in order.

    ``answers`` are the user's answers to the successive message boxes:
    "cancel", "retry-closed" (closes everything, then clicks Retry) or
    "retry-open" (clicks Retry with the app still open). The error flag
    starts set, so an open without ClearErrors before it is caught.
    """
    labels = _labels(statements)
    exists, in_use, answers = set(exists), set(in_use), list(answers)
    events: list[str] = []
    error = True
    here = 0
    for _ in range(500):
        if here >= len(statements):
            raise AssertionError(f"SecMain ends without copying: {events}")
        tokens = statements[here]
        command = tokens[0].lower()
        args = tokens[1:]
        following = here + 1
        if command == "iffileexists":
            jumps = args[1:] + ["", ""]
            target = jumps[0] if _exe_of(args[0]) in exists else jumps[1]
            following = _resolve(target, here, labels)
        elif command == "clearerrors":
            error = False
        elif command == "fileopen":
            exe, mode = _exe_of(args[1]), args[2].lower()
            if exe not in exists:
                if mode in ("a", "w"):
                    events.append(f"created {exe}")
                    exists.add(exe)
                else:
                    error = True
            elif mode == "w":
                events.append(f"truncated {exe}")
            elif exe in in_use and mode != "r":
                error = True
        elif command == "iferrors":
            jumps = args + ["", ""]
            following = _resolve(jumps[0] if error else jumps[1], here, labels)
            error = False
        elif command == "goto":
            following = _resolve(args[0], here, labels)
        elif command == "messagebox":
            events.append("prompt")
            rest = args[2:]
            if silent:
                assert "/SD" in rest, "a silent install would wait for an answer"
                answer = rest[rest.index("/SD") + 1]
            else:
                assert answers, f"more prompts than expected: {events}"
                choice = answers.pop(0)
                answer = "IDCANCEL" if choice == "cancel" else "IDRETRY"
                if choice == "retry-closed":
                    in_use.clear()
            checks = [t for t in rest if t != "/SD" and not t.startswith("/")]
            if "/SD" in rest:
                checks.remove(rest[rest.index("/SD") + 1])
            pairs = dict(zip(checks[0::2], checks[1::2]))
            if answer in pairs:
                following = _resolve(pairs[answer], here, labels)
        elif command == "abort":
            events.append("abort")
            return events
        elif command == "rmdir":
            events.append(f"remove {_unquote(args[-1])}")
        elif command == "file":
            events.append("copy")
            return events
        here = following
    raise AssertionError(f"SecMain loops forever: {events}")


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


def test_app_open_check_jumps() -> None:
    """Each executable is checked only if present; in use leads to the prompt."""
    statements = _main_section()
    lines = _main_section_lines()
    labels = _labels(statements)
    prompt_index = _index_of(lines, r"MessageBox\s+.*")
    remove_index = _index_of(lines, r'RMDir\s+/r\s+"\$INSTDIR\\_internal"')
    copy_index = _index_of(lines, r'File\s+/r\s+"\$\{DISTDIR\}\\\*\.\*"')
    assert prompt_index >= 0, f"no MessageBox in SecMain: {lines}"

    first_check = -1
    for exe in EXECUTABLES:
        path = r'"\$INSTDIR\\' + re.escape(exe) + '"'
        exists_index = _index_of(lines, r"IfFileExists\s+" + path + r"(\s+\S+){1,2}")
        open_index = _index_of(lines, r"FileOpen\s+\$\w+\s+" + path + r"\s+a")
        assert 0 <= exists_index < open_index < prompt_index, (
            f"{exe}: no IfFileExists then FileOpen in append mode before the "
            f"prompt: {lines}"
        )
        first_check = exists_index if first_check < 0 else first_check
        assert lines[open_index - 1] == "ClearErrors", f"{exe}: no ClearErrors"

        jumps = statements[exists_index][2:] + ["", ""]
        when_present = _resolve(jumps[0], exists_index, labels)
        when_missing = _resolve(jumps[1], exists_index, labels)
        assert (
            when_present == open_index - 1
        ), f"{exe}: IfFileExists does not lead to the open when it exists"
        assert (
            when_missing > open_index + 2
        ), f"{exe}: IfFileExists does not jump past the open when it is missing"

        errors = statements[open_index + 1]
        assert errors[0] == "IfErrors", f"{exe}: no IfErrors right after the open"
        in_use = _resolve(errors[1], open_index + 1, labels)
        between = statements[in_use:prompt_index]
        assert in_use < prompt_index and all(
            len(s) == 1 and _LABEL.fullmatch(s[0]) for s in between
        ), f"{exe}: IfErrors does not lead to the prompt"
        assert statements[open_index + 2][0] == "FileClose", f"{exe}: no FileClose"

    prompt = statements[prompt_index]
    assert "MB_RETRYCANCEL" in prompt[1].split("|"), f"no Retry/Cancel: {prompt}"
    assert prompt[2] == '"$(MSG_APP_OPEN)"', f"unexpected prompt text: {prompt}"
    assert prompt[3:5] == ["/SD", "IDCANCEL"], f"no /SD IDCANCEL: {prompt}"
    assert prompt[5] == "IDRETRY", f"no IDRETRY jump: {prompt}"
    retry = _resolve(prompt[6], prompt_index, labels)
    assert retry <= first_check, f"Retry does not go back before both checks: {prompt}"
    assert lines[prompt_index + 1] == "Abort", "the prompt is not followed by Abort"
    assert (
        prompt_index + 1 < remove_index < copy_index
    ), f"the cleanup is not after the check and before the copy: {lines}"


def test_app_open_check_behaviour() -> None:
    """Simulated runs: install only once both executables are closed."""
    statements = _main_section()
    done = ["remove $INSTDIR\\_internal", "copy"]
    states = [set(c) for n in range(3) for c in itertools.combinations(EXECUTABLES, n)]

    for exists in states:
        assert _run(statements, exists, set(), []) == done, f"closed, {exists}"
        for in_use in (s for s in states if s and s <= exists):
            case = f"present {sorted(exists)}, open {sorted(in_use)}"
            assert _run(statements, exists, in_use, ["cancel"]) == [
                "prompt",
                "abort",
            ], f"Cancel: {case}"
            assert _run(statements, exists, in_use, [], silent=True) == [
                "prompt",
                "abort",
            ], f"silent: {case}"
            assert (
                _run(statements, exists, in_use, ["retry-closed"]) == ["prompt"] + done
            ), f"Retry once closed: {case}"
            assert _run(statements, exists, in_use, ["retry-open", "cancel"]) == [
                "prompt",
                "prompt",
                "abort",
            ], f"Retry while still open: {case}"


def test_app_open_message_in_both_languages() -> None:
    """The prompt text exists in English and French, after the languages load."""
    raw = INSTALLER_PATH.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), (
        "installer.nsi has no UTF-8 BOM: makensis would read the accented "
        "letters of the French text in the build machine's code page"
    )
    lines = raw.decode("utf-8-sig").splitlines()
    found: dict[str, str] = {}
    last_language = -1
    for index, line in enumerate(lines):
        if re.match(r"\s*!insertmacro\s+MUI_LANGUAGE\b", line):
            last_language = index
        match = re.fullmatch(
            r'\s*LangString\s+MSG_APP_OPEN\s+\$\{LANG_(\w+)\}\s+"([^"]*)"\s*', line
        )
        if match:
            assert index > last_language >= 0, "LangString before MUI_LANGUAGE"
            found[match.group(1)] = match.group(2)
    assert found == MESSAGES
