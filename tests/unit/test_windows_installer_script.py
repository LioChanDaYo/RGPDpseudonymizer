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

The installer also always installs into a folder of its own, named
"GDPR Pseudonymizer", and the uninstaller removes only what the installer put
there (Story 12.1). A folder typed by hand used to be wiped entirely at
uninstall, the user's own files included. The later tests run the installer's
functions and sections through a small interpreter of the NSIS commands the
script uses (``_Nsis``).
"""

import itertools
import re
from collections.abc import Iterable
from pathlib import Path

import pytest

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


# ---------------------------------------------------------------------------
# Story 12.1: the installer uses its own folder, the uninstaller removes only
# its own files.
# ---------------------------------------------------------------------------

SPEC_PATH = Path(__file__).parent.parent.parent / "gdpr-pseudo-gui.spec"

DEFAULT_FOLDER = r"C:\Program Files (x86)\GDPR Pseudonymizer"
APP_KEY = ("HKLM", r"Software\GDPR Pseudonymizer", "InstallDir")
INSTALLED_ITEMS = (
    "_internal",
    "gdpr-pseudonymizer.exe",
    "gdpr-pseudo.exe",
    "Uninstall.exe",
)

OLD_COPY_MESSAGES = {
    "ENGLISH": (
        r"GDPR Pseudonymizer is now installed in:$\r$\n$INSTDIR$\r$\n$\r$\n"
        r"The earlier version is still in:$\r$\n$OldInstDir$\r$\n"
        r"You can delete it by hand. In that folder, delete only _internal, "
        r"gdpr-pseudonymizer.exe, gdpr-pseudo.exe and Uninstall.exe.$\r$\n$\r$\n"
        r"Do not run that Uninstall.exe: it would delete everything in the "
        r"folder, your own files included."
    ),
    "FRENCH": (
        r"GDPR Pseudonymizer est maintenant installé dans :$\r$\n$INSTDIR$\r$\n"
        r"$\r$\nL'ancienne version est toujours dans :$\r$\n$OldInstDir$\r$\n"
        r"Vous pouvez la supprimer à la main. Dans ce dossier, supprimez "
        r"uniquement _internal, gdpr-pseudonymizer.exe, gdpr-pseudo.exe et "
        r"Uninstall.exe.$\r$\n$\r$\nN'exécutez pas ce fichier Uninstall.exe : "
        r"il supprimerait tout le contenu du dossier, y compris vos propres "
        r"fichiers."
    ),
}

# Fixed values for the NSIS constants the script uses (invented folders), and
# the one header define it uses that installer.nsi does not define itself.
_CONSTANTS = {
    "PROGRAMFILES": r"C:\Program Files (x86)",
    "SMPROGRAMS": r"C:\Users\u\Start Menu\Programs",
    "DESKTOP": r"C:\Users\u\Desktop",
    "HWNDPARENT": "0x100",
}
_HEADER_DEFINES = {"WM_SETTEXT": "0x000C"}  # WinMessages.nsh
_PAGE_HANDLE = "0x200"
_FIELD_HANDLE = "0x300"
_FOLDER_FIELD_ID = 1019

_SHORTCUTS = (
    r"C:\Users\u\Start Menu\Programs\GDPR Pseudonymizer\GDPR Pseudonymizer.lnk",
    r"C:\Users\u\Start Menu\Programs\GDPR Pseudonymizer\Uninstall.lnk",
    r"C:\Users\u\Desktop\GDPR Pseudonymizer.lnk",
)
_START_MENU_FOLDER = r"C:\Users\u\Start Menu\Programs\GDPR Pseudonymizer"

_IGNORED = {
    "sectionin",
    "createdirectory",
    "createshortcut",
    "writeregdword",
    "intfmt",
    "${getsize}",
    "deleteregkey",
}
_PATH_EVENTS = ("outpath", "rmdir", "delete", "copy", "uninstaller", "created")
_STEP_LIMIT = 5000
_CALL_DEPTH_LIMIT = 20
_REFERENCE = re.compile(r"\$(\{[^}]*\}|\([^)]*\)|\\.|\$|\w+)")
_ESCAPES = {"\\r": "\r", "\\n": "\n", "\\t": "\t", '\\"': '"'}


def _all_statements() -> list[list[str]]:
    """Return every statement of installer.nsi as token lists, in order."""
    lines = INSTALLER_PATH.read_text(encoding="utf-8-sig").splitlines()
    return [tokens for tokens in map(_tokens, lines) if tokens]


def _plain(statement: list[str]) -> list[str]:
    return [_unquote(token) for token in statement]


def _plain_all(statements: list[list[str]]) -> list[list[str]]:
    return [_plain(statement) for statement in statements]


def _block(kind: str, name: str) -> list[list[str]]:
    """Return the statements of ``Function <name>`` or ``Section "<name>"``.

    A section is found by its quoted name or by the index name after it
    (``Section "!${APPNAME}" SecMain``). Raises AssertionError when absent.
    """
    statements = _all_statements()
    for start, tokens in enumerate(statements):
        if tokens[0] != kind or len(tokens) < 2:
            continue
        if kind == "Function":
            found = tokens[1] == name
        else:
            found = _unquote(tokens[1]) == name or tokens[2:3] == [name]
        if not found:
            continue
        for end in range(start + 1, len(statements)):
            if statements[end][0] == f"{kind}End":
                return statements[start + 1 : end]
        raise AssertionError(f"{kind} {name} has no {kind}End in installer.nsi")
    raise AssertionError(f"{kind} {name} not found in installer.nsi")


def _defines() -> dict[str, str]:
    """Return the ``!define`` values of installer.nsi."""
    found: dict[str, str] = {}
    for tokens in _all_statements():
        if tokens[0] == "!define" and len(tokens) >= 2:
            found[tokens[1]] = _unquote(tokens[2]) if len(tokens) > 2 else ""
    return found


def _declared_vars() -> list[str]:
    return [
        tokens[-1]
        for tokens in _all_statements()
        if tokens[0] == "Var" and len(tokens) >= 2
    ]


def _attribute(name: str) -> list[str]:
    """Return the plain tokens of the one installer attribute ``name``."""
    found = [s for s in _plain_all(_all_statements()) if s[0] == name]
    assert len(found) == 1, f"expected one {name} in installer.nsi: {found}"
    return found[0]


def _key(path: str) -> str:
    return path.rstrip("\\").lower()


def _is_under(path: str, folder: str) -> bool:
    return _key(path) == _key(folder) or _key(path).startswith(_key(folder) + "\\")


def _int(text: str) -> int:
    try:
        return int(text, 0)
    except ValueError:
        raise AssertionError(f"not a number: {text!r}") from None


class _AbortedError(Exception):
    """Abort ran."""


class _Nsis:
    """A small interpreter of the NSIS subset installer.nsi uses.

    State: variables, a stack, a registry, a file tree (folders included,
    compared without regard to capitals), the directory page's folder field,
    and the list of what happened. Any command or name it does not know
    raises AssertionError, so a change to the script forces a test update.
    """

    def __init__(
        self,
        *,
        files: Iterable[str] = (),
        registry: dict[tuple[str, str, str], str] | None = None,
        dest: str | None = None,
        instdir: str | None = None,
        silent: bool = False,
    ) -> None:
        self.defines = _defines()
        self.vars: dict[str, str] = {"INSTDIR": "", "OUTDIR": ""}
        for number in range(10):
            self.vars[str(number)] = ""
            self.vars[f"R{number}"] = ""
        for name in _declared_vars():
            self.vars[name] = ""
        self.registry: dict[tuple[str, str, str], str] = {}
        for (root, key, value_name), value in (registry or {}).items():
            self.registry[self._reg(root, key, value_name)] = value
        self.tree: dict[str, str] = {}
        for path in files:
            self.add(path)
        self.silent = silent
        self.stack: list[str] = []
        self.events: list[str] = []
        self.error = True
        self.field = ""
        self.steps = 0
        self.depth = 0
        self.vars["INSTDIR"] = self._start_folder(dest, instdir)

    def _start_folder(self, dest: str | None, instdir: str | None) -> str:
        """``$INSTDIR`` as NSIS sets it before ``.onInit`` (exehead Ui.c)."""
        if instdir is not None:
            return instdir
        if dest is not None and not re.fullmatch(r"[A-Za-z]:\\*", dest):
            return dest
        _, root, key, value_name = _attribute("InstallDirRegKey")
        previous = self.registry.get(
            self._reg(root, self.expand(key), self.expand(value_name)), ""
        )
        if previous:
            return previous if previous.endswith("\\") else previous + "\\"
        return self.expand(_attribute("InstallDir")[1])

    @staticmethod
    def _reg(root: str, key: str, value_name: str) -> tuple[str, str, str]:
        return (root.upper(), key.lower(), value_name.lower())

    def registry_value(self, root: str, key: str, value_name: str) -> str | None:
        return self.registry.get(self._reg(root, key, value_name))

    # File tree -------------------------------------------------------------

    def add(self, path: str) -> None:
        parts = path.rstrip("\\").split("\\")
        for end in range(1, len(parts) + 1):
            folder = "\\".join(parts[:end])
            self.tree.setdefault(_key(folder), folder)

    def exists(self, path: str) -> bool:
        return _key(path) in self.tree

    def under(self, path: str) -> list[str]:
        prefix = _key(path) + "\\"
        return [key for key in self.tree if key.startswith(prefix)]

    # Strings -----------------------------------------------------------------

    def expand(self, token: str, depth: int = 0) -> str:
        assert depth < 10, f"defines nest too deep: {token}"

        def one(match: re.Match[str]) -> str:
            ref = match.group(1)
            if ref == "$":
                return "$"
            if ref.startswith("\\"):
                assert ref in _ESCAPES, f"unknown: ${ref}"
                return _ESCAPES[ref]
            if ref.startswith("("):
                return match.group(0)
            if ref.startswith("{"):
                name = ref[1:-1]
                if name in self.defines:
                    return self.expand(self.defines[name], depth + 1)
                assert name in _HEADER_DEFINES, f"unknown: ${{{name}}}"
                return _HEADER_DEFINES[name]
            if ref in self.vars:
                return self.vars[ref]
            assert ref in _CONSTANTS, f"unknown: ${ref}"
            return _CONSTANTS[ref]

        return _REFERENCE.sub(one, _unquote(token))

    def _var(self, token: str) -> str:
        match = re.fullmatch(r"\$(\w+)", token)
        assert match and match.group(1) in self.vars, f"not a variable: {token}"
        return match.group(1)

    # Running -----------------------------------------------------------------

    def call(self, name: str) -> None:
        """Run ``Function <name>``."""
        self._enter(_block("Function", name), name)

    def section(self, name: str) -> None:
        """Run ``Section "<name>"`` to its end, or to an Abort."""
        self._enter(_block("Section", name), name)

    def leave_directory_page(self, typed: str) -> None:
        """Click Next on the directory page with ``typed`` in the folder field.

        NSIS updates ``$INSTDIR`` with the field on every keystroke, runs the
        page's leave function, then reads the field back into ``$INSTDIR``
        without trailing backslashes and spaces (exehead Ui.c, DirProc).
        """
        statements = _plain_all(_all_statements())
        pages = [
            i
            for i, s in enumerate(statements)
            if s == ["!insertmacro", "MUI_PAGE_DIRECTORY"]
        ]
        assert len(pages) == 1, f"expected one MUI_PAGE_DIRECTORY: {pages}"
        before = statements[pages[0] - 1]
        assert before[:2] == ["!define", "MUI_PAGE_CUSTOMFUNCTION_LEAVE"] and (
            len(before) == 3
        ), f"no leave function defined right before MUI_PAGE_DIRECTORY: {before}"
        self.field = typed
        self.vars["INSTDIR"] = typed
        self.call(before[2])
        assert "abort" not in self.events, "the leave function refused the folder"
        self.vars["INSTDIR"] = self.field.rstrip("\\ ")

    def _enter(self, statements: list[list[str]], where: str) -> None:
        try:
            self._run_block(statements, where)
        except _AbortedError:
            self.events.append("abort")
        except (IndexError, KeyError, ValueError, RecursionError) as error:
            raise AssertionError(f"{where} cannot run: {error!r}") from None

    def _run_block(self, statements: list[list[str]], where: str) -> None:
        labels = _labels(statements)
        here = 0
        while here < len(statements):
            self.steps += 1
            if self.steps > _STEP_LIMIT:
                raise AssertionError(f"{where} loops forever: {self.events}")
            following = self._step(statements[here], here, labels, where)
            if following is None:
                return
            here = following

    def _step(
        self, tokens: list[str], here: int, labels: dict[str, int], where: str
    ) -> int | None:
        command = tokens[0].lower()
        args = tokens[1:]
        following = here + 1
        if len(tokens) == 1 and _LABEL.fullmatch(tokens[0]):
            pass
        elif command in _IGNORED:
            pass
        elif command == "goto":
            following = _resolve(args[0], here, labels)
        elif command == "return":
            return None
        elif command == "push":
            self.stack.append(self.expand(args[0]))
        elif command == "pop":
            assert self.stack, f"Pop on an empty stack in {where}"
            self.vars[self._var(args[0])] = self.stack.pop()
        elif command == "exch":
            assert self.stack, f"Exch on an empty stack in {where}"
            if not args:
                assert len(self.stack) >= 2, f"Exch with one item in {where}"
                self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]
            else:
                name = self._var(args[0])
                self.stack[-1], self.vars[name] = self.vars[name], self.stack[-1]
        elif command == "call":
            assert not args[0].startswith(":"), f"relative Call in {where}"
            self.depth += 1
            assert self.depth <= _CALL_DEPTH_LIMIT, f"Call nests too deep: {args[0]}"
            self._run_block(_block("Function", args[0]), args[0])
            self.depth -= 1
        elif command == "strcpy":
            self.vars[self._var(args[0])] = self._strcpy(args[1:])
        elif command == "strlen":
            self.vars[self._var(args[0])] = str(len(self.expand(args[1])))
        elif command == "intop":
            first, operator, second = args[1:4]
            assert operator in ("+", "-"), f"not modelled: {tokens}"
            left, right = _int(self.expand(first)), _int(self.expand(second))
            result = left + right if operator == "+" else left - right
            self.vars[self._var(args[0])] = str(result)
        elif command in ("strcmp", "strcmps"):
            left, right = self.expand(args[0]), self.expand(args[1])
            if command == "strcmp":
                left, right = left.lower(), right.lower()
            jumps = args[2:] + ["", ""]
            following = _resolve(jumps[0] if left == right else jumps[1], here, labels)
        elif command == "iffileexists":
            jumps = args[1:] + ["", ""]
            present = self.exists(self.expand(args[0]))
            following = _resolve(jumps[0] if present else jumps[1], here, labels)
        elif command == "readregstr":
            root, key, value_name = args[1], self.expand(args[2]), self.expand(args[3])
            value = self.registry_value(root, key, value_name)
            self.error = value is None
            self.vars[self._var(args[0])] = value or ""
        elif command == "writeregstr":
            root, key, value_name = args[0], self.expand(args[1]), self.expand(args[2])
            self.registry[self._reg(root, key, value_name)] = self.expand(args[3])
            self.events.append(f"regwrite {key}\\{value_name}")
        elif command == "messagebox":
            following = self._message_box(args, here, labels)
        elif command == "clearerrors":
            self.error = False
        elif command == "fileopen":
            path, mode = self.expand(args[1]), args[2].lower()
            if not self.exists(path):
                if mode in ("a", "w"):
                    self.events.append(f"created {path}")
                    self.add(path)
                else:
                    self.error = True
            self.vars[self._var(args[0])] = "0x400"
        elif command == "iferrors":
            jumps = args + ["", ""]
            following = _resolve(jumps[0] if self.error else jumps[1], here, labels)
            self.error = False
        elif command == "fileclose":
            pass
        elif command == "setoutpath":
            path = self.expand(args[0])
            self.vars["OUTDIR"] = path
            self.add(path)
            self.events.append(f"outpath {path}")
        elif command == "rmdir":
            recursive = [a.lower() for a in args[:-1]] == ["/r"]
            assert recursive or len(args) == 1, f"not modelled: {tokens}"
            path = self.expand(args[-1])
            self.events.append(f"rmdir /r {path}" if recursive else f"rmdir {path}")
            inside = self.under(path)
            if recursive or not inside:
                for key in inside:
                    del self.tree[key]
                self.tree.pop(_key(path), None)
        elif command == "delete":
            path = self.expand(args[0])
            self.events.append(f"delete {path}")
            if not self.under(path):
                self.tree.pop(_key(path), None)
        elif command == "file":
            assert args[0] == "/r", f"not modelled: {tokens}"
            folder = self.vars["OUTDIR"]
            assert folder, "File before any SetOutPath"
            for item in (
                r"_internal\base_library.zip",
                "gdpr-pseudonymizer.exe",
                "gdpr-pseudo.exe",
            ):
                self.add(f"{folder}\\{item}")
            self.events.append(f"copy {folder}")
        elif command == "writeuninstaller":
            path = self.expand(args[0])
            self.add(path)
            self.events.append(f"uninstaller {path}")
        elif command == "abort":
            raise _AbortedError
        elif command == "findwindow":
            window_class, title, parent = (self.expand(a) for a in args[1:4])
            assert (window_class, title, parent) == (
                "#32770",
                "",
                _CONSTANTS["HWNDPARENT"],
            ), f"not modelled: {tokens}"
            self.vars[self._var(args[0])] = _PAGE_HANDLE
        elif command == "getdlgitem":
            handle, item = self.expand(args[1]), _int(self.expand(args[2]))
            found = handle == _PAGE_HANDLE and item == _FOLDER_FIELD_ID
            self.vars[self._var(args[0])] = _FIELD_HANDLE if found else "0"
        elif command == "sendmessage":
            handle, message = self.expand(args[0]), _int(self.expand(args[1]))
            text = self.expand(args[3])
            assert (
                len(args) == 4
                and handle == _FIELD_HANDLE
                and message == _int(_HEADER_DEFINES["WM_SETTEXT"])
                and text.startswith("STR:")
            ), f"not modelled: {tokens}"
            self.field = text[len("STR:") :]
        else:
            raise AssertionError(f"not modelled: {' '.join(tokens)}")
        return following

    def _strcpy(self, args: list[str]) -> str:
        """``StrCpy`` with maxlen and start offset (NSIS manual 4.9.8.1)."""
        value = self.expand(args[0])
        maxlen = self.expand(args[1]) if len(args) > 1 else ""
        offset = self.expand(args[2]) if len(args) > 2 else ""
        if offset:
            start = _int(offset)
            if start < 0:
                start = max(len(value) + start, 0)
            value = value[start:]
        if maxlen:
            length = _int(maxlen)
            value = (
                value[: max(len(value) + length, 0)] if length < 0 else value[:length]
            )
        return value

    def _message_box(self, args: list[str], here: int, labels: dict[str, int]) -> int:
        flags, text, rest = args[0].split("|"), _unquote(args[1]), args[2:]
        self.events.append(f"prompt {text}")
        if self.silent:
            assert "/SD" in rest, f"a silent install would wait for an answer: {text}"
            answer = rest[rest.index("/SD") + 1]
        else:
            assert "MB_OK" in flags, f"no answer modelled for {args}"
            answer = "IDOK"
        checks = [t for t in rest if not t.startswith("/")]
        if "/SD" in rest:
            checks.remove(rest[rest.index("/SD") + 1])
        pairs = dict(zip(checks[0::2], checks[1::2], strict=False))
        return _resolve(pairs[answer], here, labels) if answer in pairs else here + 1


def _own_folder(folder: str) -> str:
    """Run ``OwnFolderOf`` on ``folder``; check it keeps the stack and registers."""
    nsis = _Nsis(instdir=DEFAULT_FOLDER)
    sentinels = {register: f"sentinel {register}" for register in ("0", "1", "2")}
    nsis.vars.update(sentinels)
    nsis.stack.append(folder)
    nsis.call("OwnFolderOf")
    assert len(nsis.stack) == 1, f"OwnFolderOf leaves the stack as {nsis.stack}"
    result = nsis.stack.pop()
    for register, sentinel in sentinels.items():
        assert nsis.vars[register] == sentinel, f"OwnFolderOf changes ${register}"
    return result


def _app_files(folder: str) -> list[str]:
    """The files an earlier install left in ``folder``."""
    return [
        f"{folder}\\gdpr-pseudonymizer.exe",
        f"{folder}\\gdpr-pseudo.exe",
        f"{folder}\\Uninstall.exe",
        f"{folder}\\_internal\\base_library.zip",
    ]


def _uninstall(folder: str, extra: Iterable[str] = ()) -> _Nsis:
    """Run the uninstaller from ``folder``, which holds the four items."""
    items = [
        f"{folder}\\gdpr-pseudonymizer.exe",
        f"{folder}\\gdpr-pseudo.exe",
        f"{folder}\\Uninstall.exe",
        f"{folder}\\_internal\\sub\\lib.pyd",
    ]
    nsis = _Nsis(instdir=folder, files=[*items, *extra, *_SHORTCUTS])
    nsis.section("Uninstall")
    return nsis


_OWN_FOLDER_CASES = [
    pytest.param(DEFAULT_FOLDER, DEFAULT_FOLDER, id="default"),
    pytest.param(
        "D:\\Apps\\GDPR Pseudonymizer\\",
        r"D:\Apps\GDPR Pseudonymizer",
        id="own-folder-trailing-backslash",
    ),
    pytest.param(
        r"d:\outils\gdpr pseudonymizer",
        r"d:\outils\gdpr pseudonymizer",
        id="own-folder-lower-case",
    ),
    pytest.param(r"D:\Outils", r"D:\Outils\GDPR Pseudonymizer", id="typed"),
    pytest.param(
        "D:\\Outils\\", r"D:\Outils\GDPR Pseudonymizer", id="typed-trailing-backslash"
    ),
    pytest.param(
        "D:\\Outils\\\\",
        r"D:\Outils\GDPR Pseudonymizer",
        id="typed-two-trailing-backslashes",
    ),
    pytest.param(
        r"D:\XGDPR Pseudonymizer",
        r"D:\XGDPR Pseudonymizer\GDPR Pseudonymizer",
        id="name-without-backslash",
    ),
    pytest.param(
        r"D:\GDPR Pseudonymizer Old",
        r"D:\GDPR Pseudonymizer Old\GDPR Pseudonymizer",
        id="name-then-more",
    ),
    pytest.param(
        "D:\\Apps\\GDPR Pseudonymizer ",
        r"D:\Apps\GDPR Pseudonymizer",
        id="own-folder-trailing-space",
    ),
    pytest.param(
        "D:\\Outils \\", r"D:\Outils\GDPR Pseudonymizer", id="typed-space-backslash"
    ),
    pytest.param("D:\\", r"D:\GDPR Pseudonymizer", id="drive-root"),
]


@pytest.mark.parametrize(("folder", "expected"), _OWN_FOLDER_CASES)
def test_own_folder_rule(folder: str, expected: str) -> None:
    """Any folder becomes one whose last part is "GDPR Pseudonymizer"."""
    result = _own_folder(folder)
    assert result == expected, f"{folder!r} gives {result!r}"
    assert _own_folder(result) == result, f"{result!r} changes when applied again"


_THREE = [["Push", "$INSTDIR"], ["Call", "OwnFolderOf"], ["Pop", "$INSTDIR"]]


def _find_run(statements: list[list[str]], run: list[list[str]]) -> int:
    for index in range(len(statements) - len(run) + 1):
        if statements[index : index + len(run)] == run:
            return index
    return -1


def test_own_folder_rule_runs_everywhere() -> None:
    """The rule runs in .onInit, the directory page's leave function and SecMain."""
    on_init = _plain_all(_block("Function", ".onInit"))
    assert (
        _find_run(on_init, _THREE) >= 0
    ), f".onInit does not apply the rule: {on_init}"

    statements = _plain_all(_all_statements())
    page = _find_run(statements, [["!insertmacro", "MUI_PAGE_DIRECTORY"]])
    assert page > 0, "no MUI_PAGE_DIRECTORY"
    before = statements[page - 1]
    assert before[:2] == ["!define", "MUI_PAGE_CUSTOMFUNCTION_LEAVE"] and (
        len(before) == 3
    ), f"no leave function defined right before MUI_PAGE_DIRECTORY: {before}"
    leave = _plain_all(_block("Function", before[2]))
    rule = _find_run(leave, _THREE)
    assert rule >= 0, f"the leave function does not apply the rule: {leave}"
    writes = [
        index
        for index, s in enumerate(leave)
        if len(s) == 5
        and s[0] == "SendMessage"
        and s[1].startswith("$")
        and s[2:] == ["${WM_SETTEXT}", "0", "STR:$INSTDIR"]
    ]
    assert writes and writes[0] > rule, (
        f"the leave function does not write the folder into the field after the "
        f"rule: {leave}"
    )

    main = _plain_all(_block("Section", "SecMain"))
    assert main[:1] == [["SectionIn", "RO"]], f"SecMain does not start so: {main}"
    assert main[1:4] == _THREE, f"SecMain does not apply the rule first: {main[:6]}"


_INSTALL_STARTS = [
    pytest.param(
        {"dest": r"D:\Outils"}, True, r"D:\Outils\GDPR Pseudonymizer", id="D-typed"
    ),
    pytest.param(
        {"dest": "D:\\Outils\\"},
        True,
        r"D:\Outils\GDPR Pseudonymizer",
        id="D-typed-trailing-backslash",
    ),
    pytest.param({"dest": DEFAULT_FOLDER}, True, DEFAULT_FOLDER, id="D-default"),
    pytest.param(
        {"registry": {APP_KEY: DEFAULT_FOLDER}},
        True,
        DEFAULT_FOLDER,
        id="registry-default",
    ),
    pytest.param(
        {"instdir": r"D:\Outils"},
        False,
        r"D:\Outils\GDPR Pseudonymizer",
        id="SecMain-alone",
    ),
]


@pytest.mark.parametrize(("start", "on_init", "own"), _INSTALL_STARTS)
def test_install_cleanup_only_in_own_folder(
    start: dict[str, object], on_init: bool, own: str
) -> None:
    """SecMain removes _internal and copies only inside its own folder."""
    nsis = _Nsis(silent=True, **start)
    if on_init:
        nsis.call(".onInit")
    nsis.section("SecMain")
    done = [
        e for e in nsis.events if e.split(" ", 1)[0] in ("outpath", "rmdir", "copy")
    ]
    assert done == [
        f"outpath {own}",
        f"rmdir /r {own}\\_internal",
        f"copy {own}",
    ], f"SecMain does not work in {own}: {nsis.events}"
    for item in INSTALLED_ITEMS:
        assert nsis.exists(f"{own}\\{item}"), f"{item} not installed in {own}"


def test_previous_folder_read_in_on_init() -> None:
    """.onInit reads the previous folder from the key SecMain writes it to."""
    assert "OldInstDir" in _declared_vars(), "no Var OldInstDir"
    key = _attribute("InstallDirRegKey")[1:]
    on_init = _plain_all(_block("Function", ".onInit"))
    assert [
        "ReadRegStr",
        "$OldInstDir",
        *key,
    ] in on_init, f".onInit does not read {key} into $OldInstDir: {on_init}"
    main = _plain_all(_block("Section", "SecMain"))
    assert ["WriteRegStr", *key, "$INSTDIR"] in main, f"SecMain does not write {key}"


_TYPED = r"D:\Outils"
_TYPED_OWN = r"D:\Outils\GDPR Pseudonymizer"
_USER_FILES = [r"D:\Outils\ma-base.db", r"D:\Outils\Notes\n.txt"]
_TYPED_INSTALL = _app_files(_TYPED) + _USER_FILES

_PREVIOUS_INSTALLS = [
    pytest.param(None, [], None, False, DEFAULT_FOLDER, False, id="none"),
    pytest.param(
        DEFAULT_FOLDER,
        _app_files(DEFAULT_FOLDER),
        None,
        False,
        DEFAULT_FOLDER,
        False,
        id="default",
    ),
    pytest.param(
        r"D:\Apps\GDPR Pseudonymizer",
        _app_files(r"D:\Apps\GDPR Pseudonymizer"),
        None,
        False,
        r"D:\Apps\GDPR Pseudonymizer",
        False,
        id="browse",
    ),
    pytest.param(
        r"d:\outils\gdpr pseudonymizer",
        _app_files(r"d:\outils\gdpr pseudonymizer"),
        None,
        False,
        r"d:\outils\gdpr pseudonymizer",
        False,
        id="own-folder-lower-case",
    ),
    pytest.param(_TYPED, _TYPED_INSTALL, None, False, _TYPED_OWN, True, id="typed"),
    pytest.param(
        "D:\\Outils\\",
        _TYPED_INSTALL,
        None,
        False,
        _TYPED_OWN,
        True,
        id="typed-trailing-backslash",
    ),
    pytest.param(
        _TYPED, _USER_FILES, None, False, _TYPED_OWN, False, id="typed-old-copy-gone"
    ),
    pytest.param(
        _TYPED,
        _TYPED_INSTALL,
        r"E:\Autre",
        False,
        r"E:\Autre\GDPR Pseudonymizer",
        True,
        id="typed-new-folder-elsewhere",
    ),
    pytest.param(
        _TYPED, _TYPED_INSTALL, None, True, _TYPED_OWN, True, id="typed-silent"
    ),
]


@pytest.mark.parametrize(
    ("previous", "files", "dest", "silent", "installed", "message"), _PREVIOUS_INSTALLS
)
def test_previous_install_cases(
    previous: str | None,
    files: list[str],
    dest: str | None,
    silent: bool,
    installed: str,
    message: bool,
) -> None:
    """Upgrades: the old copy stays as it was; a typed folder gets the message."""
    nsis = _Nsis(
        files=files,
        registry={APP_KEY: previous} if previous else None,
        dest=dest,
        silent=silent,
    )
    nsis.call(".onInit")
    nsis.section("SecMain")
    events = nsis.events

    assert "abort" not in events, f"the install stopped: {events}"
    copies = [e for e in events if e.startswith("copy ")]
    assert copies == [f"copy {installed}"], f"not installed in {installed}: {events}"
    assert nsis.registry_value(*APP_KEY) == installed, "InstallDir not the new folder"
    prompts = [e for e in events if e.startswith("prompt ")]
    if message:
        assert prompts == ["prompt $(MSG_OLD_COPY)"], f"expected the message: {events}"
        shown = events.index(prompts[0])
        write = f"regwrite {APP_KEY[1]}\\{APP_KEY[2]}"
        assert write in events, f"InstallDir never written: {events}"
        assert shown > events.index(copies[0]) and shown > events.index(
            write
        ), f"the message comes before the copy or the InstallDir write: {events}"
    else:
        assert prompts == [], f"no message expected: {events}"

    for event in events:
        kind, _, rest = event.partition(" ")
        if kind in _PATH_EVENTS:
            path = rest.removeprefix("/r ")
            assert _is_under(path, installed), f"outside {installed}: {event}"
    for path in files:
        if not _is_under(path, installed):
            assert nsis.exists(path), f"{path} was removed"


def test_old_copy_message_box() -> None:
    """The message is an OK box a silent install skips, shown last in SecMain."""
    function = _plain_all(_block("Function", "OldCopyMessage"))
    boxes = [s for s in function if s[0] == "MessageBox"]
    assert boxes == [
        ["MessageBox", "MB_OK|MB_ICONINFORMATION", "$(MSG_OLD_COPY)", "/SD", "IDOK"]
    ], f"unexpected message box: {boxes}"
    main = _plain_all(_block("Section", "SecMain"))
    assert main[-1:] == [["Call", "OldCopyMessage"]], f"SecMain ends with {main[-1:]}"


def test_old_copy_message_text() -> None:
    """The message exists in English and French, word for word as approved."""
    raw = INSTALLER_PATH.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "installer.nsi has no UTF-8 BOM"
    lines = raw.decode("utf-8-sig").splitlines()
    found: dict[str, str] = {}
    last_language = -1
    declared = -1
    for index, line in enumerate(lines):
        if re.match(r"\s*!insertmacro\s+MUI_LANGUAGE\b", line):
            last_language = index
        if re.fullmatch(r"\s*Var\s+(/GLOBAL\s+)?OldInstDir\s*(;.*)?", line):
            declared = index
        match = re.fullmatch(
            r'\s*LangString\s+MSG_OLD_COPY\s+\$\{LANG_(\w+)\}\s+"([^"]*)"\s*', line
        )
        if match:
            assert index > last_language >= 0, "MSG_OLD_COPY before MUI_LANGUAGE"
            assert index > declared >= 0, "MSG_OLD_COPY before Var OldInstDir"
            found[match.group(1)] = match.group(2)
    assert found == OLD_COPY_MESSAGES
    for language, text in found.items():
        for item in INSTALLED_ITEMS + ("$INSTDIR", "$OldInstDir"):
            assert item in text, f"{language}: {item} missing"
        assert text.count("Uninstall.exe") >= 2, f"{language}: Uninstall.exe once"
        fixed = text.replace("$INSTDIR", "").replace("$OldInstDir", "")
        fixed = fixed.replace("$\\r$\\n", "\r\n")
        assert len(fixed) <= 500, f"{language}: {len(fixed)} characters"
    assert found["FRENCH"] != found["ENGLISH"]


def test_uninstaller_keeps_other_files() -> None:
    """The uninstaller leaves other files, and so the folder, in place."""
    folder = _TYPED_OWN
    nsis = _uninstall(folder, [f"{folder}\\ma-base.db", f"{folder}\\Notes\\n.txt"])
    for kept in ("ma-base.db", "Notes", "Notes\\n.txt"):
        assert nsis.exists(f"{folder}\\{kept}"), f"{kept} was removed: {nsis.events}"
    for item in INSTALLED_ITEMS:
        assert not nsis.exists(f"{folder}\\{item}"), f"{item} left behind"
        assert not nsis.under(f"{folder}\\{item}"), f"{item} not emptied"
    assert nsis.exists(folder), "the folder was removed with a file of the user in it"


def test_uninstaller_list_matches_installer() -> None:
    """The uninstaller removes exactly the items the build and installer create."""
    spec = SPEC_PATH.read_text(encoding="utf-8")
    calls = re.findall(r"\bEXE\((.*?)\n\)", spec, flags=re.DOTALL)
    names = [re.findall(r'\bname="([^"]+)"', call) for call in calls]
    assert len(names) == 2 and all(len(n) == 1 for n in names), names
    collect = re.findall(r"\bCOLLECT\((.*?)\n\)", spec, flags=re.DOTALL)
    assert len(collect) == 1 and "contents_directory" not in collect[0], collect
    writes = [s for s in _plain_all(_all_statements()) if s[0] == "WriteUninstaller"]
    assert len(writes) == 1 and writes[0][1].startswith("$INSTDIR\\"), writes
    expected = sorted(
        ["_internal", writes[0][1][len("$INSTDIR\\") :]]
        + [n[0] + ".exe" for n in names]
    )

    removed = []
    for statement in _plain_all(_block("Section", "Uninstall")):
        if statement[0] in ("Delete", "RMDir") and statement[-1].startswith(
            "$INSTDIR\\"
        ):
            removed.append(statement[-1][len("$INSTDIR\\") :])
    assert sorted(removed) == expected, f"removes {removed}, expected {expected}"


def test_only_recursive_removal_is_internal() -> None:
    """In the whole script, only "$INSTDIR\\_internal" is removed with its content."""
    recursive = [
        tokens
        for tokens in _all_statements()
        if tokens[0].lower() == "rmdir" and "/r" in [t.lower() for t in tokens[1:-1]]
    ]
    assert recursive, "no RMDir /r at all"
    for tokens in recursive:
        assert tokens[-1] == '"$INSTDIR\\_internal"', f"removes more: {tokens}"


def test_uninstaller_removes_its_shortcuts_and_registry() -> None:
    """The uninstaller deletes its shortcuts, an empty Start Menu folder, its keys."""
    shortcuts = [
        s[1] for s in _plain_all(_all_statements()) if s[0] == "CreateShortCut"
    ]
    assert len(shortcuts) == 3, f"expected three shortcuts: {shortcuts}"
    uninstall = _plain_all(_block("Section", "Uninstall"))
    start_menu = ["RMDir", "$SMPROGRAMS\\${APPNAME}"]
    assert start_menu in uninstall, f"no {start_menu} without /r: {uninstall}"
    folder_removed = uninstall.index(start_menu)
    for shortcut in shortcuts:
        assert ["Delete", shortcut] in uninstall, f"{shortcut} not deleted"
        if shortcut.startswith("$SMPROGRAMS\\${APPNAME}\\"):
            assert (
                uninstall.index(["Delete", shortcut]) < folder_removed
            ), f"{shortcut} deleted after its folder"
    for key in (
        "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}",
        "Software\\${APPNAME}",
    ):
        assert ["DeleteRegKey", "HKLM", key] in uninstall, f"{key} not deleted"

    nsis = _uninstall(_TYPED_OWN)
    for path in _SHORTCUTS:
        assert not nsis.exists(path), f"{path} left behind"
    assert not nsis.exists(_START_MENU_FOLDER), "the Start Menu folder stays"
    assert nsis.exists(_CONSTANTS["SMPROGRAMS"]), "Programs was removed"


_DIRECTORY_PAGE_CASES = [
    pytest.param(r"D:\Outils", r"D:\Outils\GDPR Pseudonymizer", id="typed"),
    pytest.param(
        r"D:\Apps\GDPR Pseudonymizer", r"D:\Apps\GDPR Pseudonymizer", id="own-folder"
    ),
    pytest.param(
        "D:\\Apps\\GDPR Pseudonymizer ",
        r"D:\Apps\GDPR Pseudonymizer",
        id="own-folder-trailing-space",
    ),
]


@pytest.mark.parametrize(("typed", "expected"), _DIRECTORY_PAGE_CASES)
def test_directory_page_leave_keeps_own_folder(typed: str, expected: str) -> None:
    """Next on the directory page keeps the own folder, in $INSTDIR and the field."""
    nsis = _Nsis(instdir=DEFAULT_FOLDER)
    nsis.vars["1"] = "sentinel 1"
    nsis.leave_directory_page(typed)
    assert nsis.vars["INSTDIR"] == expected, f"{typed!r} gives {nsis.vars['INSTDIR']!r}"
    assert nsis.field == expected, f"the field shows {nsis.field!r}"
    assert nsis.vars["1"] == "sentinel 1", "the leave function changes $1"
    assert nsis.stack == [], f"the leave function leaves the stack as {nsis.stack}"


def test_uninstaller_removes_an_empty_folder() -> None:
    """With only the installer's items in it, the folder goes too."""
    nsis = _uninstall(_TYPED_OWN)
    assert not nsis.exists(_TYPED_OWN), f"the folder stays: {nsis.events}"
    assert not nsis.under(_TYPED_OWN), "something stays in the folder"
    assert nsis.exists(_TYPED), "the parent folder was removed"


def test_default_and_browse_folder_unchanged() -> None:
    """The default folder and the registry folder of an upgrade are unchanged."""
    statements = _plain_all(_all_statements())
    assert ["!define", "INSTALLDIR", "$PROGRAMFILES\\${APPNAME}"] in statements
    assert ["InstallDir", "${INSTALLDIR}"] in statements
    key = ["HKLM", "Software\\${APPNAME}", "InstallDir"]
    assert ["InstallDirRegKey", *key] in statements
    main = _plain_all(_block("Section", "SecMain"))
    assert ["WriteRegStr", *key, "$INSTDIR"] in main
