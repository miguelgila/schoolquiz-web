# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`schoolquiz-web` ("Quiz scolastici") is a static, dependency-free hub of school-revision quizzes in **Italian**, written for the owner's son (3ª media in Ticino, about 13 years old). Each quiz is a folder with a thin page and a `questions.js` data file; every quiz is played by the same engine in `shared/`, and the landing page lists them from `quizzes.js`. It is hosted on GitHub Pages from `main` / root (`.nojekyll` present) at the custom domain **schoolquiz.giar.dev**, which is set by the `CNAME` file (DNS: `CNAME schoolquiz → miguelgila.github.io`). Don't remove or rename `CNAME`, or the custom domain stops working. It is also an installable PWA via `manifest.webmanifest` (no service worker).

The footer carries a "Codice" link to the repo, the licence and a plain Ko-fi donation link (`ko-fi.com/miguelgila`). Keep the link plain: no third-party widgets, scripts, analytics or cookies, since the audience is a child. Code and question text are MIT (`LICENSE`).

The site has no build step, no package manager and no linter. The only tooling is in `tools/`: a Python checker for the data files, a deck merge script and the tests. Never hard-code user-facing text in HTML or JS: add a key to `shared/i18n.js`.

It is a sibling of `eugeo` and `chgeo` (geography quizzes) and deliberately keeps their look (Manrope, palette, buttons, **Verifica**-style feedback, "Da ripassare") and their conventions (one IIFE, a single state object `S`, `render()` on every change, `t()` for strings), so the owner can maintain all three by reading diffs.

## Run locally

```sh
python3 -m http.server 8000   # then open http://localhost:8000
```

## Architecture

- **Landing page**: `index.html` (static shell with `data-i18n` attributes) loads `shared/i18n.js`, `quizzes.js` and `shared/landing.js`.
  - `quizzes.js`: `window.QUIZZES = <strict JSON array>;`, one entry per quiz: `{id, path, title, subtitle, decks, questions}`. `path` must be `id + "/"`. The `decks` and `questions` counts are shown on the card and refreshed by `tools/merge_decks.py`.
  - `shared/landing.js`: one IIFE that translates the shell and renders one `.panel.quiz` card per entry (title, subtitle, `landingDecks` count line, **Inizia** link to `path`). The "Altri quiz" row links to chgeo.giar.dev and eugeo.giar.dev.

- **`shared/i18n.js`**: `window.I18N = {langs, ui}`. `langs` is `[["it", "Italiano"]]`; `ui.it` holds every chrome string (buttons, progress, result sentences, landing labels) with `{0}`/`{1}` placeholders. After the `window.I18N = ` prefix the file is strict JSON (double quotes, no trailing commas), because `tools/test_i18n.py` parses it. Every key used must exist and every key defined must be used: the test scans `t('key'…)` calls in `shared/engine.js` and `shared/landing.js`, and `data-i18n` / `data-i18n-aria` attributes in `index.html` and `*/index.html`. Shell strings are therefore also spelled out as literal `t()` calls in each script's `shellText()`. `t(key, ...args)` looks the key up in the current language, falls back to Italian, then to the key itself, and replaces `{0}`, `{1}` with the arguments. Question text is data, not UI, and is not keyed.

- **`shared/engine.js`**: two parts in one file.
  - **`QuizCore`**: pure logic, no DOM, assigned to `window.QuizCore` (or `globalThis` in node). Every random function takes an optional `rng` (default `Math.random`) so tests can seed it.
    - `shuffle(arr, rng)`: Fisher-Yates on a copy.
    - `sampleRound(quiz, deckId, n, rng)`: `n` questions from one deck (all of them if the deck is smaller), or for `deckId === 'all'` an equal share per deck (`ceil(n / decks)`), shuffled and cut to `n`; `n === Infinity` returns every question. Each question is a shallow copy tagged with `deck`. An unknown deck returns `[]`.
    - `prepare(q, rng)`: the shuffled view. `mc` → `{options: [{text, idx}]}`; `match` → `{lefts: [{text, idx}], rights: [{text, idx}] shuffled}`; `order` → `{items: [{text, idx}]}`, reshuffled (up to 50 tries) so it never starts already solved; `tf` → `{}`. `idx` is always the original position.
    - `grade(q, response)` → `{ok, correctText}`. Response shapes: `mc` the original option index (number, compared strictly); `tf` a boolean; `match` an object `{leftIdx: rightIdx}` whose values may be numeric strings (from `<select>`), right only when it has exactly one entry per pair and every left maps to its own index; `order` an array of original indices, right only when it is `[0, 1, …]`. `correctText`: `mc` the right option, `tf` the string `'true'`/`'false'` (the UI translates it), `match` `left → right · left → right`, `order` `item → item → item`.
    - `readBest(storage, key)`: the stored best as an integer, or `null` when missing, not a plain digit string, or when storage is unavailable or throws. `writeBest(storage, key, value)`: stores `value` only when it beats the stored best; errors are swallowed.
  - **DOM IIFE**: returns immediately when `typeof document === 'undefined'`, so node can load the file for `tools/engine.test.mjs`. It expects `window.I18N` and `window.QUIZ` loaded first and a page shell with these ids: `qTitle`, `qSub`, `backLink`, `langSel`, `decks`, `roundLen`, `progress`, `card`, `result` (see `tools/fixture/index.html`).
    - **State `S`**: `{deck, n, round, i, view, response, answered, results}`. `deck` starts at `'all'` (Tutto); `n` is 10, 20 or `Infinity`. `fresh()` samples a new round and resets the rest; `setDeck()` rebuilds the deck buttons, calls `fresh()` and `render()`.
    - **`render(focus)`** draws the current question into `#card`: it calls `prepare()`, resets `response`/`answered`, updates the progress `{0} / {1}` and dispatches to `renderMc`, `renderTf`, `renderMatch` (one `<select>` per left item, **Verifica** enabled once all are chosen) or `renderOrder` (up/down buttons, no drag, **Verifica** always enabled). `mc` and `tf` answer on tap.
    - **Feedback** (`answer()` → `markAnswer()` + `showFeedback()`): options turn `ok` / `bad` / `dim`, match rows and order rows `ok` / `bad`, controls are disabled. The feedback box shows **Giusto** or **Sbagliato**; the `correctWas` line ("Risposta giusta: …") appears **only on a wrong answer**, since on a right one the highlighted option already shows it. Then the `why` line, the `src` in muted text and **Avanti** (**Risultato** on the last question).
    - **End screen** (`finish()`): score `{0} su {1} giuste`, a perfect or retry sentence, a **Da ripassare** list with every missed question and its correct answer, and **Ricomincia** (new random sample).
    - **Keyboard**: `1`–`4` pick an `mc` option, `1`/`2` answer `tf` (Vero/Falso); `Enter` presses **Verifica** for match/order when enabled, and **Avanti** after answering. Shortcuts are ignored with Alt/Ctrl/Meta, and digits are ignored while focus is in a `select` or input; `Enter` on a focused button or link is left to the browser.
    - **localStorage** (every access wrapped in try/catch): `schoolquiz.<quizId>.<deckId>.best` holds the best score per deck, including `all`, recorded **only for 10-question rounds** so every badge reads "best / 10"; it is shown as a `.badge` on the deck button. `schoolquiz.<quizId>.n` holds the round length (`10`, `20` or `all`).
    - The language `<select>` is hidden while `langs` has one entry. Changing it re-translates and starts a fresh round.

- **`shared/style.css`**: the shared stylesheet, palette and components from eugeo. Colours are the `:root` variables `--bg`, `--ink`, `--muted`, `--line`, `--btn`, `--accent` (`#1F5FA8`, also the `theme-color` and the icon), `--ok`, `--bad`, `--none`, `--okBg`, `--badBg`. Touch targets are at least 44 px. Use the variables, don't add new colours inline.

- **A quiz folder** (`storia-medioevo-esplorazioni/`):
  - `index.html`: the page shell, copied from an existing quiz (originally from `tools/fixture/index.html`, with the paths changed from `../../` to `../`). Only the `<title>` and the meta description differ between quizzes; the manifest and icon links point to `../`. Shared assets are always referenced relatively (`../shared/...`), never from `/`, because the page lives in a subfolder.
  - `questions.js`: `window.QUIZ = <strict JSON>;` with `{id, title, subtitle, decks: [{id, label, questions: [...]}]}`. `id` equals the folder name. Question types `mc`, `tf`, `match`, `order`, each with `id`, `q`, `why`, `src`; see `README.md` for the fields and examples. The help line under every `order` question (`orderHelp`) only explains the arrows, so the prompt itself must say what is being ordered and in which direction.
  - `decks/<deck id>.json`: when present, the **editable source** of each deck as a bare JSON array. `python3 tools/merge_decks.py <folder>` copies them into `questions.js` (rewritten with one-space indentation) and refreshes the `decks`/`questions` counts in `quizzes.js`. A deck without a file is left as it is.

- **`tools/`**: full documentation in `tools/README.md`.
  - `check_questions.py`: no arguments scans every `<folder>/questions.js` (skipping `tools/` and dot folders) and checks `quizzes.js` against the folders found; `check_questions.py <path/to/questions.js> <folder>` checks one file against a folder name without reading `quizzes.js`; `check_questions.py --deck <deck.json>` checks one bare deck array, with the file name as deck id. It enforces the shape rules (3–4 distinct `mc` options and an index `answer`, boolean `tf`, 3–5 `match` pairs with distinct sides, 3–5 distinct `order` items, non-empty `id`/`type`/`q`/`why`/`src`, unique question ids, at least 10 questions per deck, quiz `id` equal to the folder, registry `path` equal to `id + "/"`, registry `decks`/`questions` equal to the real counts in the no-argument scan). Errors go to stderr, exit code 1.
  - `fixture/`: a small test quiz (`id` `fixture`, one deck of 10 easy questions of every type) and the reference page shell, playable at `http://localhost:8000/tools/fixture/`. It is not in `quizzes.js`; check it with `python3 tools/check_questions.py tools/fixture/questions.js tools/fixture`.
  - `engine.test.mjs`: node's built-in test runner; loads `shared/engine.js` with `node:vm` and tests `QuizCore` with a seeded generator.
  - `test_check_questions.py` and `test_i18n.py`: unittest suites for the checker and the i18n keys.
  - Icons: `icon.svg` is hand-written; the PNGs are exported with `qlmanage` and `sips` (commands in `tools/README.md`).

```sh
python3 tools/check_questions.py
python3 -m unittest discover -s tools -p 'test_*.py'
node --test tools/
```

All three run locally before every push (owner rule: fix failures locally, no CI minutes wasted). There are no GitHub Actions.

## Content rules

- The facts sheet `docs/content/<quiz-id>-facts.md` is the **only** source for writing questions. The answer and the distractors of every question must appear in it; anything doubtful is left out, not guessed. A wrong fact is the worst failure.
- Questions and explanations are in Italian, worded for a 13-year-old. Distractors are plausible and drawn from the same lesson (other dates, other cities of the same deck), never nonsense or trick near-duplicates.
- No textbook text or images: questions and explanations are paraphrases, at most a short phrase verbatim.
- Lines marked "DA VERIFICARE" in the facts sheet are off limits. If a sheet fact seems to disagree with general knowledge, don't fix either silently: hold the question back and report it to the owner.
- The source PDFs (class worksheets and the student's handwritten notes) live outside the repo and are never committed.

## Adding a quiz

1. Write the facts sheet `docs/content/<quiz-id>-facts.md`.
2. Create `<quiz-id>/`, copy `index.html` from an existing quiz, and change only `<title>` and the meta description.
3. Write the decks in `<quiz-id>/decks/<deck id>.json` and check each with `python3 tools/check_questions.py --deck <file>`.
4. Write `<quiz-id>/questions.js` with `id`, `title`, `subtitle` and the decks (`id`, `label`, empty `questions`), add the registry line to `quizzes.js`, then run `python3 tools/merge_decks.py <quiz-id>`.
5. Run the three checks above.

## Adding a language

Add `[code, name]` to `langs` in `shared/i18n.js` and a `ui.<code>` block with every key of `ui.it` and the same placeholders. The language selector unhides itself once `langs` has more than one entry, so no HTML change is needed. `tools/test_i18n.py` currently asserts Italian only (`test_langs_is_italian_only`, `test_ui_has_only_italian`), so update those tests and extend them to check every key in the new block. The question text stays Italian.

## Do not

- Hand-edit `questions.js` of a quiz that has a `decks/` folder without editing the deck file and re-running `tools/merge_decks.py`; the next merge overwrites the hand edit.
- Hard-code UI text in HTML or JS.
- Remove or rename `CNAME`.
- Add third-party scripts, widgets, analytics or cookies. The only external resource is the Manrope stylesheet from Google Fonts; don't add more.
- Commit the source PDFs or any image from the textbook or worksheets.
- Add AI or co-author attribution lines to commits.
