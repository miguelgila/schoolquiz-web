import glob
import json
import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N_PATH = os.path.join(REPO_ROOT, "shared", "i18n.js")
I18N_PREFIX = "window.I18N = "
ENGINE_PATH = os.path.join(REPO_ROOT, "shared", "engine.js")
LANDING_PATH = os.path.join(REPO_ROOT, "shared", "landing.js")
JS_FILES = [ENGINE_PATH, LANDING_PATH]

EXPECTED_IT = {
    "siteTitle": "Quiz scolastici",
    "siteSub": "Ripasso per la scuola",
    "landingQuizzes": "Quiz disponibili",
    "landingDecks": "{0} mazzi · {1} domande",
    "landingOthers": "Altri quiz",
    "back": "Tutti i quiz",
    "decksAria": "Mazzo",
    "deckAll": "Tutto",
    "roundLen": "Domande per partita",
    "roundAll": "Tutte",
    "best": "Record: {0}/{1}",
    "start": "Inizia",
    "progress": "{0} / {1}",
    "check": "Verifica",
    "next": "Avanti",
    "finish": "Risultato",
    "true": "Vero",
    "false": "Falso",
    "ok": "Giusto",
    "bad": "Sbagliato",
    "correctWas": "Risposta giusta: {0}",
    "score": "{0} su {1} giuste",
    "perfect": "Perfetto! Premi \"Ricomincia\" per rigiocare.",
    "retry": "Ripassa le domande qui sotto e premi \"Ricomincia\" per riprovare.",
    "review": "Da ripassare",
    "restart": "Ricomincia",
    "matchHelp": "Per ogni voce a sinistra scegli quella giusta a destra.",
    "orderHelp": "Metti in ordine cronologico con le frecce, poi premi \"Verifica\".",
    "moveUp": "Sposta su",
    "moveDown": "Sposta giù",
    "pick": "Scegli…",
    "footCode": "Codice",
    "footLicence": "MIT",
    "coffeeQ": "Ti è utile?",
    "coffee": "Offrimi un caffè",
    "langAria": "Lingua",
}

JS_KEY_RE = re.compile(r"""\bt\(\s*(['"])([^'"]+)\1""")
HTML_KEY_RE = re.compile(r"""data-i18n(?:-aria)?=(['"])([^'"]+)\1""")


def load_i18n(path=I18N_PATH):
    """Parse the strict-JSON object after 'window.I18N = ' (a leading comment is allowed)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    start = text.find(I18N_PREFIX)
    if start < 0:
        raise ValueError("%s: no %r" % (path, I18N_PREFIX))
    text = text[start + len(I18N_PREFIX):].strip()
    if text.endswith(";"):
        text = text[:-1]
    return json.loads(text)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def html_files():
    paths = [os.path.join(REPO_ROOT, "index.html")]
    paths += sorted(glob.glob(os.path.join(REPO_ROOT, "*", "index.html")))
    return [p for p in paths if os.path.isfile(p)]


def used_keys():
    """Map each used key to the files using it, from whichever files exist."""
    used = {}
    for path in [p for p in JS_FILES if os.path.isfile(p)]:
        for match in JS_KEY_RE.finditer(_read(path)):
            used.setdefault(match.group(2), set()).add(os.path.relpath(path, REPO_ROOT))
    for path in html_files():
        for match in HTML_KEY_RE.finditer(_read(path)):
            used.setdefault(match.group(2), set()).add(os.path.relpath(path, REPO_ROOT))
    return used


class I18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i18n = load_i18n()
        cls.it = cls.i18n["ui"]["it"]

    def test_langs_is_italian_only(self):
        self.assertEqual(self.i18n["langs"], [["it", "Italiano"]])

    def test_ui_has_only_italian(self):
        self.assertEqual(list(self.i18n["ui"]), ["it"])

    def test_expected_keys_present_with_exact_strings(self):
        for key, value in EXPECTED_IT.items():
            with self.subTest(key=key):
                self.assertIn(key, self.it)
                self.assertEqual(self.it[key], value)

    def test_all_values_are_non_empty_strings(self):
        for key, value in self.it.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str)
                self.assertNotEqual(value.strip(), "")

    def test_used_keys_exist(self):
        missing = {k: sorted(v) for k, v in used_keys().items() if k not in self.it}
        self.assertEqual(missing, {}, "keys used but not defined in ui.it")

    def test_every_key_is_used(self):
        # Landing-only keys (siteSub, landingQuizzes, ...) are used by shared/landing.js,
        # so this check only makes sense once both the engine and the landing page exist.
        if not os.path.isfile(ENGINE_PATH) or not JS_KEY_RE.search(_read(ENGINE_PATH)):
            self.skipTest("shared/engine.js has no UI strings yet")
        if not os.path.isfile(LANDING_PATH):
            self.skipTest("shared/landing.js does not exist yet")
        unused = sorted(set(self.it) - set(used_keys()))
        self.assertEqual(unused, [], "keys defined in ui.it but never used")


class UsageRegexTest(unittest.TestCase):
    def test_js_regex(self):
        text = "t('start') + t(\"next\", 1) + at('nope') + t(key)"
        self.assertEqual([m.group(2) for m in JS_KEY_RE.finditer(text)], ["start", "next"])

    def test_html_regex(self):
        text = '<b data-i18n="siteTitle"></b><nav data-i18n-aria=\'decksAria\'></nav>'
        self.assertEqual([m.group(2) for m in HTML_KEY_RE.finditer(text)],
                         ["siteTitle", "decksAria"])


if __name__ == "__main__":
    unittest.main()
