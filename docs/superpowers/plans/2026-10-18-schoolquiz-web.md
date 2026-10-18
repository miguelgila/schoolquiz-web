# schoolquiz-web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static quiz site at schoolquiz.giar.dev with a shared engine, a landing page and a first history quiz of five decks written from the student's lesson material.

**Architecture:** Plain HTML/CSS/JS, no build. `shared/engine.js` exposes a pure, testable `QuizCore` (sampling, shuffling, grading) and a DOM IIFE that renders one question at a time from `window.QUIZ`. Each quiz is a folder with a thin `index.html` and a `questions.js` holding strict JSON. A Python checker validates the data files; node's built-in test runner tests `QuizCore`.

**Tech Stack:** HTML, CSS, vanilla JS (ES2020), Python 3 standard library (`unittest`), Node ≥ 20 built-in `node:test`. No packages.

**Spec:** `docs/superpowers/specs/2026-10-18-schoolquiz-web-design.md`

## Global Constraints

- Repo root is `/Users/miguelgi/Documents/CODE/Personal/schoolquiz-web`; branch `main`; GitHub repo `miguelgila/schoolquiz-web` is created **only in Task 13**, after the owner has reviewed the questions.
- Commit messages: conventional prefix, **no AI or co-author lines, ever**.
- Shared assets are referenced relatively from quiz folders (`../shared/engine.js`), never with a leading `/`.
- Only external resource: `https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap`. No analytics, cookies, third-party scripts or widgets.
- Palette and components follow eugeo (`/Users/miguelgi/Documents/CODE/Personal/eugeo/index.html`): `--bg:#F6F6F3 --ink:#1C1C1A --muted:#5C5C57 --line:#E2E2DD --btn:#CFCFC9 --accent:#1F5FA8 --ok:#1F8A4C --bad:#C8321E --none:#D7D7D1`; buttons ≥ 44 px tall; `.panel` white, 1.5 px `--line` border, radius 16 px.
- No user-facing UI string hard-coded in HTML or `engine.js`: every chrome string is a key in `shared/i18n.js` `ui.it`. Question text is data and is not keyed.
- `questions.js` files are `window.QUIZ = <strict JSON>;` (double quotes, no comments, no trailing commas). Content in Italian.
- The only source for questions is `docs/content/storia-medioevo-esplorazioni-facts.md`. A fact that cannot be found there is not used. A fact that conflicts with general knowledge is held back and listed in the task report under "da verificare".
- The PDFs in `/Users/miguelgi/Documents/CODE/Personal/history-quiz` are never copied into the repo.
- Tests run locally before every commit: `python3 -m unittest discover -s tools -p 'test_*.py'` and `node --test tools/`.

## Review Focus

1. A deck with fewer than 10 questions, or "Tutto" with a deck smaller than its share: `sampleRound` must still return `min(n, available)` questions with no duplicates and never throw (Task 4 tests).
2. An `order` question whose shuffle happens to equal the correct order would be trivially right: `prepare` must reshuffle until it differs when items ≥ 2 (Task 4 tests).
3. A `match` with duplicate right-hand sides or an `mc` with duplicate options makes grading ambiguous: the checker rejects them (Task 2 tests).
4. Reloading the page mid-round or a corrupted `localStorage` value must not break the start screen: best-score reads are wrapped and non-numeric values ignored (Task 5 tests on `readBest`).
5. A quiz page opened from the landing page at `/storia-medioevo-esplorazioni/` (trailing slash) and without it must both load shared assets: links in `quizzes.js` end with `/` and the shell uses `../shared/` (Task 7 verification step).

---

### Task 1: Repository scaffold and facts sheet

**Owner note:** the facts sheet is written by the main session, which has the scanned pages in context. A subagent must not write it.

**Files:**
- Create: `.gitignore`, `.nojekyll`, `CNAME`, `LICENSE`, `README.md` (stub), `docs/content/storia-medioevo-esplorazioni-facts.md`

- [ ] **Step 1: Init the repo**

```bash
cd /Users/miguelgi/Documents/CODE/Personal/schoolquiz-web && git init -b main
printf '.venv/\n__pycache__/\n.DS_Store\n' > .gitignore
: > .nojekyll
printf 'schoolquiz.giar.dev\n' > CNAME
```

Copy `LICENSE` from `/Users/miguelgi/Documents/CODE/Personal/eugeo/LICENSE` (MIT, year 2026, Miguel Gila). `README.md` stub: title "schoolquiz — Quiz scolastici", one line of purpose, "work in progress".

- [ ] **Step 2: Write the facts sheet**

`docs/content/storia-medioevo-esplorazioni-facts.md`: a heading per worksheet section in the order of the two PDFs (§1: Perché tornano le città; Le carte di libertà; Un ceto nuovo: la borghesia; Le strade e le merci; Il superamento delle Alpi; Una Svizzera senza fondazione; Dai tre cantoni ai tredici. Notes: Alto/Basso Medioevo; Età moderna; Stato e Nazione. §2: I confini del mondo si allargano; Il mondo prima del 1492; Le tecniche del viaggio; Colombo e l'incontro). Under each heading one bullet per fact, each self-contained (subject, fact, date/number), including the teacher's model answers to interpretation questions where the worksheet gave them, and a final "Deck mapping" section listing which headings feed which of the five decks (`citta`, `passi`, `confederazione`, `moderna`, `esplorazioni`).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: scaffold repo and add facts sheet for the first quiz"
```

---

### Task 2: Question file checker

**Files:**
- Create: `tools/check_questions.py`, `tools/test_check_questions.py`, `tools/README.md`

**Interfaces:**
- Produces: `load_quiz(path: str) -> dict` (strips `window.QUIZ = ` prefix and trailing `;`, `json.loads`), `validate_quiz(quiz: dict, folder_name: str) -> list[str]` (list of error strings, empty when valid), `validate_registry(registry: list[dict], quiz_ids: set[str]) -> list[str]`, `main(argv) -> int` (0 ok, 1 errors printed to stderr). Running `python3 tools/check_questions.py` with no args scans `*/questions.js` from the repo root and `quizzes.js` (prefix `window.QUIZZES = `).

- [ ] **Step 1: Write the failing tests** in `tools/test_check_questions.py` (`unittest`), building small quiz dicts in code:

```python
def test_valid_quiz_has_no_errors(self)      # 1 deck, 10 questions mixing all four types
def test_duplicate_question_id(self)         # error mentions the id
def test_mc_answer_out_of_range(self)
def test_mc_fewer_than_three_or_duplicate_options(self)
def test_tf_answer_must_be_bool(self)
def test_match_needs_three_unique_pairs(self) # <3 pairs, duplicate left, duplicate right
def test_order_needs_three_items(self)
def test_missing_why_or_src(self)
def test_deck_under_ten_questions(self)
def test_quiz_id_must_match_folder(self)
def test_registry_entry_missing_for_quiz(self)
def test_load_quiz_strips_prefix(self)        # writes a temp file 'window.QUIZ = {...};'
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tools.test_check_questions -v` — Expected: ImportError / failures.

- [ ] **Step 3: Implement `tools/check_questions.py`**

Valid question shapes (all need non-empty string `id`, `why`, `src`, `q`, and `type`):
- `mc`: `options` list of 3–4 distinct non-empty strings, `answer` int in range.
- `tf`: `answer` is `bool`.
- `match`: `pairs` list of 3–5 `[left, right]` with distinct lefts and distinct rights.
- `order`: `items` list of 3–5 distinct strings.
Deck needs `id`, `label`, ≥ 10 questions; quiz needs `id` == folder, `title`, `subtitle`, ≥ 1 deck; ids unique across the quiz. Registry entry: `{id, path, title, subtitle}` with `path == id + "/"` and one entry per quiz folder.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tools -p 'test_*.py' -v` — Expected: all PASS.

- [ ] **Step 5: Write `tools/README.md`** (how to run the checker and both test suites), then commit

```bash
git add tools && git commit -m "feat: add question file checker"
```

---

### Task 3: Shared i18n and its test

**Files:**
- Create: `shared/i18n.js`, `tools/test_i18n.py`

**Interfaces:**
- Produces: `window.I18N = { langs: [['it','Italiano']], ui: { it: {...} } }` with these keys (exact names, used by Tasks 4–7): `siteTitle` "Quiz scolastici", `siteSub` "Ripasso per la scuola", `landingQuizzes` "Quiz disponibili", `landingDecks` "{0} mazzi · {1} domande", `landingOthers` "Altri quiz", `back` "Tutti i quiz", `decksAria` "Mazzo", `deckAll` "Tutto", `roundLen` "Domande per partita", `roundAll` "Tutte", `best` "Record: {0}/{1}", `start` "Inizia", `progress` "{0} / {1}", `check` "Verifica", `next` "Avanti", `finish` "Risultato", `true` "Vero", `false` "Falso", `ok` "Giusto", `bad` "Sbagliato", `correctWas` "Risposta giusta: {0}", `score` "{0} su {1} giuste", `perfect` "Perfetto! Premi \"Ricomincia\" per rigiocare.", `retry` "Ripassa le domande qui sotto e premi \"Ricomincia\" per riprovare.", `review` "Da ripassare", `restart` "Ricomincia", `matchHelp` "Per ogni voce a sinistra scegli quella giusta a destra.", `orderHelp` "Metti in ordine cronologico con le frecce, poi premi \"Verifica\".", `moveUp` "Sposta su", `moveDown` "Sposta giù", `pick` "Scegli…", `footCode` "Codice", `footLicence` "MIT", `coffeeQ` "Ti è utile?", `coffee` "Offrimi un caffè", `langAria` "Lingua".
- Helper lives in `engine.js` (Task 4): `t(key, ...args)`.

- [ ] **Step 1: Write failing test** `tools/test_i18n.py`: parses `shared/i18n.js` by extracting the object literal between `window.I18N = ` and the final `;` after converting it to JSON (write `i18n.js` as strict JSON after the prefix so the test can `json.loads` it, same rule as `questions.js`); asserts every `t('key'` / `t("key"` occurrence in `shared/engine.js`, `shared/landing.js` and every `data-i18n="key"` / `data-i18n-aria="key"` in `index.html` and `*/index.html` exists in `ui.it`, and that every `ui.it` key is used somewhere (tolerate missing files before Tasks 4–7 exist by skipping absent paths, but the key list above must be present).

- [ ] **Step 2: Run to verify it fails**, **Step 3: write `shared/i18n.js`**, **Step 4: run to verify it passes** (`python3 -m unittest tools.test_i18n -v`).

- [ ] **Step 5: Commit** — `git commit -m "feat: add shared i18n strings"`

---

### Task 4: QuizCore (pure logic) with node tests

**Files:**
- Create: `shared/engine.js` (top part: `QuizCore`), `tools/engine.test.mjs`

**Interfaces:**
- Produces, on `globalThis.QuizCore` (defined with `const QuizCore = {...}; (typeof window!=='undefined'?window:globalThis).QuizCore = QuizCore;` so node can `vm`-load or `import` the file; the DOM IIFE added in Task 5 must guard `if (typeof document === 'undefined') return;`):
  - `shuffle(arr, rng = Math.random) -> newArray` (Fisher–Yates, input untouched)
  - `sampleRound(quiz, deckId, n, rng) -> question[]`: `deckId === 'all'` takes an equal share per deck (`ceil(n/decks)` each, then trims to `n`, shuffled); otherwise `min(n, deck.length)` from that deck; `n === Infinity` means all. Each returned question is a shallow copy with `deck: deckId`. No duplicates.
  - `prepare(q, rng) -> view`: `mc` → `{options: [{text, idx}]}` shuffled; `tf` → `{}`; `match` → `{lefts: [{text, idx}], rights: [{text, idx}]}` rights shuffled; `order` → `{items: [{text, idx}]}` shuffled and, when `items.length >= 2`, reshuffled until `items.map(i=>i.idx)` is not `[0,1,2…]`.
  - `grade(q, response) -> {ok: boolean, correctText: string}`: `mc` response is the original index; `tf` a boolean; `match` an object `{leftIdx: rightIdx}` (all lefts must be present and equal their own index); `order` an array of original indices (must be `[0..n-1]`). `correctText`: mc → the correct option; tf → "Vero"/"Falso" is **not** built here (UI does it with `t()`), so return the boolean as string `'true'|'false'`; match → `"A → 1 · B → 2"` joined with `" · "`; order → items joined with `" → "`.
  - `readBest(storage, key) -> number|null` (parses int, returns null on missing/NaN/throw) and `writeBest(storage, key, value)` (writes only if higher; swallows errors).

- [ ] **Step 1: Write failing tests** `tools/engine.test.mjs` (`import test from 'node:test'; import assert from 'node:assert/strict';` load the file with `vm.runInThisContext(fs.readFileSync('shared/engine.js','utf8'))` then use `globalThis.QuizCore`). Use a seeded `rng` (e.g. mulberry32) for determinism:

```js
test('shuffle keeps elements and does not mutate')
test('sampleRound returns min(n, size) without duplicates')      // deck of 7, n=10 → 7
test('sampleRound all shares across decks and respects n')       // decks 12/12/3, n=10 → 10, includes ≤3 from the small deck
test('sampleRound with Infinity returns everything')
test('prepare order never returns the identity permutation')     // 200 seeds, 3–5 items
test('prepare mc keeps original indices')
test('grade mc / tf / match / order right and wrong cases')
test('grade correctText formats')
test('readBest ignores garbage and throwing storage; writeBest keeps the max')
```

- [ ] **Step 2: Run** `node --test tools/` — Expected: FAIL (QuizCore undefined).
- [ ] **Step 3: Implement `QuizCore` in `shared/engine.js`.**
- [ ] **Step 4: Run** `node --test tools/` — Expected: all PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: add QuizCore sampling and grading"`

---

### Task 5: Engine UI, stylesheet and a fixture quiz

**Files:**
- Create: `shared/style.css`, `tools/fixture/questions.js` (one deck "Prova", 10 questions covering every type; strict JSON; **not** registered in `quizzes.js`, excluded by the checker via `tools/` path), `tools/fixture/index.html` (same shell as Task 7 but with `../../shared/` paths, used for manual testing)
- Modify: `shared/engine.js` (append the DOM IIFE)

**Interfaces:**
- Consumes: `QuizCore`, `window.I18N`, `window.QUIZ`.
- Shell markup the IIFE expects (Task 7 copies it verbatim): `<header>` with `.brand` (`.mark` + `<h1 id="qTitle">` + `<p class="sub" id="qSub">`) and `<a id="backLink" href="../" data-i18n="back">`; `<nav class="seg" id="decks" data-i18n-aria="decksAria">`; `<div class="row"><div class="tools"><label data-i18n="roundLen"></label><select id="roundLen"></select><span class="progress" id="progress"></span></div></div>`; `<main class="panel" id="card"></main>`; `<section class="result panel" id="result"></section>`; `<footer>` with code link `https://github.com/miguelgila/schoolquiz-web`, licence, Ko-fi `https://ko-fi.com/miguelgila` (plain links, `data-i18n` on their texts). `<select id="langSel" class="lang" data-i18n-aria="langAria">` hidden when `I18N.langs.length === 1`.
- Produces: state `S = {deck:'all'|deckId, n:10|20|Infinity, round:[], i:0, view:null, response:null, answered:false, results:[{q, ok, correctText}]}`; `t(key,...args)`; `localStorage` keys `schoolquiz.<quizId>.<deckId>.best` and `schoolquiz.<quizId>.n`.

- [ ] **Step 1: Write `shared/style.css`** from eugeo's palette: `.seg` deck buttons with an optional `.badge` (best score), `.card` with `.q` prompt (20 px, 800), `.options button` full-width ≥ 48 px, states `.ok`/`.bad`/`.dim`, `.tf` two buttons side by side, `.match` rows `label + select`, `.order` list rows with ▲ ▼ `.btn.icon`, `.feedback` box (`.ok` green border, `.bad` red) with `.why` and `.src` (muted, 12 px), `.result` as eugeo, `.review li` with the prompt and `correctWas`. Responsive at 360 px: single column, no horizontal scroll.
- [ ] **Step 2: Write the fixture quiz** and run `python3 tools/check_questions.py tools/fixture/questions.js tools/fixture` (checker accepts explicit `path folder` pairs) — Expected: exit 0.
- [ ] **Step 3: Implement the IIFE** in `shared/engine.js`: on load, translate `data-i18n`, fill title/subtitle, build deck buttons (`deckAll` first, then each deck label, with `best` badge when `readBest` ≠ null), round-length select (10/20/`roundAll`) persisted, start a round immediately (`setDeck()` → `fresh()` → `render()`). `render()` switches on `S.round[S.i].type`: `mc` options buttons (tap = answer, keyboard 1–4), `tf` two buttons, `match` one `<select>` per left with `pick` placeholder plus `check` button enabled when all picked, `order` list with move buttons plus `check`. After answering: mark correct/incorrect, show `.feedback` with `t('ok')`/`t('bad')`, `correctWas` (for `tf` map `'true'`→`t('true')`), `why`, `src`; the `next` button (Enter) advances; on the last question the button reads `finish` and shows `#result` with `score`, `perfect` or `retry`, the `review` list of misses, and `restart`. On finish, `writeBest` for the deck.
- [ ] **Step 4: Manual verification** `cd /Users/miguelgi/Documents/CODE/Personal/schoolquiz-web && python3 -m http.server 8000` and open `http://localhost:8000/tools/fixture/`: play a full round of each type; check with the browser at 360 px wide; no console errors. Record what was checked in the task report.
- [ ] **Step 5: Run all tests** (`python3 -m unittest discover -s tools -p 'test_*.py'`, `node --test tools/`) — Expected: PASS (i18n test now sees `engine.js`).
- [ ] **Step 6: Commit** — `git commit -m "feat: add quiz engine UI and stylesheet"`

---

### Task 6: Landing page, registry, PWA files

**Files:**
- Create: `index.html`, `quizzes.js`, `shared/landing.js`, `manifest.webmanifest`, `icon.svg`, `icon-180.png`, `icon-512.png`

**Interfaces:**
- `quizzes.js`: `window.QUIZZES = [{"id":"storia-medioevo-esplorazioni","path":"storia-medioevo-esplorazioni/","title":"Storia: Medioevo ed esplorazioni","subtitle":"3ª media · §1 Città, mercanti e passi alpini · §2 I confini del mondo si allargano","decks":5,"questions":0}];` (`decks`/`questions` are updated by Task 12).
- `shared/landing.js`: renders one `.panel` card per entry into `#quizzes` (title, subtitle, `landingDecks`, link to `path`), and the `landingOthers` row with `https://chgeo.giar.dev` and `https://eugeo.giar.dev`.

- [ ] **Step 1: Write `index.html`** (title `siteTitle`, Manrope link, `shared/style.css`, `shared/i18n.js`, `quizzes.js`, `shared/landing.js`; same footer as the quiz shell).
- [ ] **Step 2: Icon**: `icon.svg` single-colour `#1F5FA8` rounded square with a white check mark glyph; export PNGs with `rsvg-convert` or `qlmanage`/`sips` (document the command in `tools/README.md`). `manifest.webmanifest` name "Quiz scolastici", short_name "Schoolquiz", `start_url: "./"`, colours as eugeo.
- [ ] **Step 3: Verify** at `http://localhost:8000/` the card renders and links to `storia-medioevo-esplorazioni/` (404 for now is expected). Run the test suites — PASS.
- [ ] **Step 4: Commit** — `git commit -m "feat: add landing page, registry and PWA files"`

---

### Task 7: First quiz shell and empty deck skeleton

**Files:**
- Create: `storia-medioevo-esplorazioni/index.html`, `storia-medioevo-esplorazioni/questions.js`

- [ ] **Step 1: Shell**: copy the Task 5 shell with `../shared/` paths, `<title>Storia: Medioevo ed esplorazioni</title>`, meta description "Quiz di storia: città e mercanti, passi alpini, nascita della Confederazione, età moderna ed esplorazioni.", `<link rel="manifest" href="../manifest.webmanifest">`, icons `../icon.svg` / `../icon-180.png`.
- [ ] **Step 2: Skeleton `questions.js`** with the five decks in this order and ids/labels exactly: `citta` "Città e mercanti", `passi` "Passi alpini e commerci", `confederazione` "Nascita della Confederazione", `moderna` "Età moderna e Rinascimento", `esplorazioni` "Esplorazioni e conquiste", each with `"questions": []`.
- [ ] **Step 3: Verify** `python3 tools/check_questions.py` fails only with "fewer than 10 questions" for the five decks (expected until Tasks 8–12), and `http://localhost:8000/storia-medioevo-esplorazioni/` and `.../storia-medioevo-esplorazioni` (no slash: the server redirects) both load without console errors.
- [ ] **Step 4: Commit** — `git commit -m "feat: add storia quiz shell with empty decks"`

---

### Tasks 8–12: Write the five decks

Each task fills one deck in `storia-medioevo-esplorazioni/questions.js`. These five tasks are independent and may run in parallel **only if each worker edits a separate file** `storia-medioevo-esplorazioni/decks/<deckId>.json` (strict JSON array of questions) and a final step merges them into `questions.js` with a tiny script; otherwise run them sequentially editing `questions.js` directly. Decision for this plan: **parallel, one file per deck, merged in Task 12.5.**

**Rules for every deck (copy into each worker's brief):**
- Source: only `docs/content/storia-medioevo-esplorazioni-facts.md`, section(s) named in the task. Read the whole sheet once; use only the facts there. No outside facts, no invented dates. A fact that seems wrong is left out and reported under "da verificare".
- Count: 25–35 questions; types roughly 60% `mc`, 20% `tf`, 10% `match`, 10% `order`, at least 2 `match` and 2 `order` per deck.
- `id` is `<deckId>-NN` (two digits, in file order). `src` is the worksheet section title as in the sheet heading, e.g. `"§1 · Le carte di libertà"`.
- Language: Italian, addressed to a 13-year-old, plain sentences, no trick wording. Options are plausible and from the same lesson (other dates, cities or people from the sheet), 4 options for `mc` where possible, no "tutte le precedenti". `tf` statements are balanced (about half true); a false statement changes one concrete element (date, place, person).
- `why` is one sentence stating the fact (not "perché è così"). The teacher's model answers to interpretation questions are turned into `mc` with the model answer as the correct option.
- Validate with `python3 -c "import json,sys;json.load(open(sys.argv[1]))" storia-medioevo-esplorazioni/decks/<deckId>.json` and with the checker in fixture mode: wrap in a temporary quiz if needed, or run `python3 tools/check_questions.py --deck storia-medioevo-esplorazioni/decks/<deckId>.json` (add this `--deck` flag to the checker in Task 8's first step: validates a bare question array with deck id taken from the file name).
- Commit: `git add storia-medioevo-esplorazioni/decks/<deckId>.json && git commit -m "content: add <label> deck"`.

### Task 8: Deck `citta` — Città e mercanti
Sections: Perché tornano le città; Le carte di libertà; Un ceto nuovo: la borghesia; Le strade e le merci (the Catalan atlas, long-distance trade, moneta/banca parts). First add the `--deck` flag to `tools/check_questions.py` with a unit test `test_deck_flag_validates_bare_array`.

### Task 9: Deck `passi` — Passi alpini e commerci
Sections: Le strade e le merci (Brünig coins, some, Brennero); Il superamento delle Alpi.

### Task 10: Deck `confederazione` — Nascita della Confederazione
Sections: Una Svizzera senza fondazione; Dai tre cantoni ai tredici (including the "piccolo popolo pacifico" testimonies and mercenary service).

### Task 11: Deck `moderna` — Età moderna e Rinascimento
Sections: Notes (Alto/Basso Medioevo, Età moderna, Stato e Nazione); I confini del mondo si allargano (Giotto/Raffaello, Umanesimo, Rinascimento); Il mondo prima del 1492 (Tolomeo, the four pushes, Costantinopoli); the caravel diagram.

### Task 12: Deck `esplorazioni` — Esplorazioni e conquiste
Sections: Le tecniche del viaggio (Portoghesi, Waldseemüller); Colombo e l'incontro (Colombo, Tordesillas, Cortés, Pizarro, Magellano).

### Task 12.5: Merge decks and review gate

**Files:**
- Create: `tools/merge_decks.py` — reads `storia-medioevo-esplorazioni/decks/*.json` in the deck order of `questions.js`, writes them into the `questions` arrays, keeps the file strict JSON (`json.dumps(..., ensure_ascii=False, indent=1)`), and updates `decks`/`questions` counts in `quizzes.js`.

- [ ] **Step 1:** Write `tools/merge_decks.py` and run it; run `python3 tools/check_questions.py` — Expected: exit 0.
- [ ] **Step 2:** Main session (not a worker) reads every question against the scanned pages and the facts sheet, fixes or drops wrong ones, and produces the "da verificare" list for the owner.
- [ ] **Step 3:** Play one full round of each deck and of "Tutto" at `http://localhost:8000/storia-medioevo-esplorazioni/`; run both test suites.
- [ ] **Step 4:** Commit — `git commit -m "content: merge decks into the storia quiz"`.
- [ ] **Step 5: Owner review gate.** Hand the owner the question bank (a readable export: `python3 tools/merge_decks.py --print > /tmp/…` is not needed; point them at the deck JSON files and the running local site) and the "da verificare" list. **Stop here until the owner approves.**

---

### Task 13: README, CLAUDE.md, repo creation and first push

- [ ] **Step 1:** Write `README.md` (what it is, how to run locally, hosting on Pages with the `CNAME` and DNS line `CNAME schoolquiz → miguelgila.github.io`, how to add a quiz, how to run the checks, licence and source credit: "Le domande sono scritte a partire dalle schede di classe basate su *La Svizzera nella storia 2* e dagli appunti dello studente; nessun testo o immagine del libro è riprodotto.") and `CLAUDE.md` modelled on eugeo's (architecture of `shared/engine.js`, `QuizCore` API, data format, i18n rule, the checker, "Adding a quiz", "Do not" list including the PDFs and attribution lines).
- [ ] **Step 2:** Run both test suites and the checker — PASS. Commit — `git commit -m "docs: add README and CLAUDE.md"`.
- [ ] **Step 3: Ask the owner to confirm**, then:

```bash
gh repo create miguelgila/schoolquiz-web --public --description "Quiz scolastici" --source . --remote origin --push
gh api -X POST repos/miguelgila/schoolquiz-web/pages -f build_type=legacy -f source[branch]=main -f source[path]=/
gh api -X PUT repos/miguelgila/schoolquiz-web/pages -f cname=schoolquiz.giar.dev
```

- [ ] **Step 4:** Tell the owner to add the DNS record and, once the certificate is issued, run `gh api -X PUT repos/miguelgila/schoolquiz-web/pages -F https_enforced=true`. Verify `https://schoolquiz.giar.dev/storia-medioevo-esplorazioni/` loads.
