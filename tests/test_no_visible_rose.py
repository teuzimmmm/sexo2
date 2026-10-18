"""No visible text names Rose (milestones M5 and M5b).

Scans what the user reads: the locale files, the string literals of the
enabled plugins, the texts of the Python dialogs, hints and banners, and the
installer messages. Identifiers that must keep the old name for compatibility
(data folder, plugin folders, party token prefix, CSS classes shared by the
plugins) and the credits the licence asks for are listed in ALLOWED, each with
its reason.
"""

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "Pengu Loader" / "plugins"
LOCALES = PLUGINS / "SEXO2-I18n" / "locales"

# The brand as a word: not inside identifiers such as rose_i18n or __roseBridge
BRAND = re.compile(r"(?<![A-Za-z_])(?:Rose|ROSE)(?![A-Za-z0-9_])")

# Substring -> reason. Removed from a text before it is checked.
ALLOWED = {
    "ROSE:": "prefix of the party tokens already shared between friends (party/protocol/token_codec.py)",
    "%LOCALAPPDATA%\\Rose": "real data folder, kept until the M13 migration",
    "LocalAppData\\Rose": "real data folder, kept until the M13 migration",
    "{localappdata}\\Rose": "real data folder, kept until the M13 migration",
    "SEXO2 utiliza componentes de Rose": "credit to the base project (LICENSE, MIT)",
    "Código e licença da base Rose": "credit to the base project (LICENSE, MIT)",
    "github.com/Alban1911/Rose": "credit link, and the selector that hides upstream links in the Pengu welcome screen",
    "Rose.exe": "executable of older installs, still closed and replaced by the installer and updater",
    'Name="Rose Sala.exe"': "installer still closes executables of older installs",
    "Projeto personalizado baseado em Rose": "installer publisher credit to the base project",
}

# Plugin folders (ROSE-Hub, Rose-UI...): Pengu keeps their enabled state by folder name
PLUGIN_ID = re.compile(r"(?:Rose|ROSE)-[A-Z][A-Za-z0-9]+")

# Whole texts that are identifiers, not sentences
EXACT = {
    "Rose": "name of the scheduled task created by older versions (schtasks /TN Rose)",
    "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Rose": "uninstall key of older installs",
}

# Python modules whose string literals reach dialogs, hints, notifications or banners
PYTHON_SOURCES = [
    "main/__init__.py",
    "main/core/lockfile.py",
    "main/setup/initialization.py",
    "friends/diagnostics.py",
    "friends/service.py",
    "launcher/core/launcher.py",
    "party/network/ws_relay.py",
    "party/network/private_server_config.py",
    "pengu/communication/message_handler.py",
    "injection/overlay/overlay_manager.py",
    "injection/core/injector.py",
    "injection/game/game_monitor.py",
    "utils/core/logging.py",
    "utils/core/modpkg.py",
    "utils/integration/tray_manager.py",
    "utils/integration/tray_settings.py",
    "utils/system/admin_utils.py",
]

# Disabled plugin (index.js_), never loaded by Pengu
SKIPPED_PLUGINS = {"SEXO2-Jade"}

JS_STRING = re.compile(r"""(["'`])((?:\\.|(?!\1)[^\\\n])*)\1""")


def offending(text):
    if text in EXACT:
        return False
    text = PLUGIN_ID.sub("", text)
    for allowed in ALLOWED:
        text = text.replace(allowed, "")
    return bool(BRAND.search(text))


def readable(text):
    """A sentence rather than an id, selector or log prefix"""
    return " " in text.strip() or text[:1].isupper()


def python_texts(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            yield node.lineno, node.value


def js_texts(path):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(("//", "*", "/*")):
            continue
        for match in JS_STRING.finditer(line):
            yield number, match.group(2)


# Identifiers the plugins and their tests shared under the old name (events, globals, CSS ids and
# classes, storage keys, the nav item class). They moved to SEXO2 together in M5b.
LEGACY_IDENTIFIER = re.compile(
    r"__rose|Rose[A-Z]|(?<![A-Za-z0-9_])rose[-_]|(?<![A-Za-z])rose[A-Z]|menu_item_Golden|golden_rose"
)
# Lines that are credits or the filters that hide the base project's own links
CREDIT_LINE = re.compile(r"@link|@author|github\.com|roseskins|roseapp")


class NoVisibleRoseTests(unittest.TestCase):
    def test_locales(self):
        offenders = []
        for path in sorted(LOCALES.glob("*.json")):
            for key, value in json.loads(path.read_text(encoding="utf-8")).items():
                for text in (key, value):
                    if offending(text):
                        offenders.append(f"{path.name}: {text[:80]}")
        self.assertEqual(offenders, [])

    def test_plugin_texts(self):
        offenders = []
        for path in sorted(PLUGINS.glob("*/index.js")):
            if path.parent.name in SKIPPED_PLUGINS:
                continue
            for number, text in js_texts(path):
                if readable(text) and offending(text):
                    offenders.append(f"{path.relative_to(PLUGINS)}:{number}: {text[:80]}")
        self.assertEqual(offenders, [])

    def test_python_texts(self):
        offenders = []
        for name in PYTHON_SOURCES:
            for number, text in python_texts(ROOT / name):
                if readable(text) and offending(text):
                    offenders.append(f"{name}:{number}: {text[:80]}")
        self.assertEqual(offenders, [])

    def test_installer_messages(self):
        offenders = []
        text = (ROOT / "installer-sexo2.iss").read_bytes().decode("utf-8-sig")
        for number, line in enumerate(text.splitlines(), 1):
            for literal in re.findall(r"'([^']*)'", line) + ([line] if "=" in line and "'" not in line else []):
                if offending(literal) and not line.startswith(("Type: files;", "AppMutex=")):
                    offenders.append(f"installer-sexo2.iss:{number}: {literal[:80]}")
        self.assertEqual(offenders, [])

    def test_plugins_and_browser_tests_use_the_sexo2_identifiers(self):
        offenders = []
        paths = [p for p in PLUGINS.glob("*/index.js") if p.parent.name not in SKIPPED_PLUGINS]
        paths += sorted((ROOT / "tests").glob("*.cjs"))
        for path in paths:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if LEGACY_IDENTIFIER.search(line) and not CREDIT_LINE.search(line):
                    offenders.append(f"{path.name}:{number}: {line.strip()[:80]}")
        self.assertEqual(offenders, [])

    def test_plugin_folders_carry_the_new_name(self):
        legacy = [p.name for p in PLUGINS.iterdir() if p.is_dir() and p.name.upper().startswith("ROSE-")]
        self.assertEqual(legacy, [])

    def test_the_scanner_still_sees_the_brand(self):
        self.assertTrue(offending("Restart Rose."))
        self.assertTrue(offending("Reinicie o ROSE"))
        self.assertFalse(offending("window.__sexo2Bridge"))
        self.assertTrue(LEGACY_IDENTIFIER.search("window.__roseBridge"))
        self.assertTrue(LEGACY_IDENTIFIER.search("#rose-hub"))
        self.assertIsNone(LEGACY_IDENTIFIER.search("#sexo2-hub"))
        self.assertFalse(offending("sexo2_runoverlay_*.log"))
        self.assertFalse(offending("It starts with ROSE:"))


if __name__ == "__main__":
    unittest.main()
