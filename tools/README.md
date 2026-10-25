# tools

Local checks for the quiz data and code. Python 3 and node (20 or newer)
standard libraries only, no packages to install. Run everything from the repo
root, and run it before every push.

## Question file checker

```sh
python3 tools/check_questions.py
```

Scans every `<quiz-id>/questions.js` and `<quiz-id>/diagram.js` in the repo
root (skipping `tools/`, `shared/` and folders with neither file) and checks
`quizzes.js` against the quiz folders it found. A folder with both files is an
error. Exits 0 when all is valid; otherwise prints one error per
line to stderr, naming the quiz, deck and question id, and exits 1.

To check a single file against a folder name (for example the test fixture,
which is not listed in `quizzes.js`):

```sh
python3 tools/check_questions.py tools/fixture/questions.js tools/fixture
```

The quiz `id` must equal the last component of the folder name. A file named
`diagram.js` is checked as a diagram quiz, with its images looked up next to
it:

```sh
python3 tools/check_questions.py scienze-ossa/diagram.js scienze-ossa
```

To check a deck on its own, stored as a bare JSON array of question objects
(no `window.QUIZ` prefix), use `--deck`. The deck id is the file name without
its extension, and the same deck and question rules apply as for a full quiz:

```sh
python3 tools/check_questions.py --deck storia-medioevo-esplorazioni/decks/citta.json
```

What it checks:

- `questions.js` is `window.QUIZ = <strict JSON>;` and `quizzes.js` is
  `window.QUIZZES = <strict JSON array>;`.
- Quiz: `id` equals its folder, non-empty `title` and `subtitle`, at least
  one deck. Deck: non-empty `id` and `label`, at least 10 questions.
- Question ids are unique across the quiz. Every question has non-empty
  `id`, `type`, `q`, `why` and `src`.
- `mc`: 3-4 distinct non-empty `options`, `answer` is an integer index into
  them. `tf`: `answer` is `true` or `false`. `match`: 3-5 `[left, right]`
  `pairs` with distinct lefts and distinct rights. `order`: 3-5 distinct
  `items`, in the correct order.
- `diagram.js` (labelling board) is `window.DIAGRAM = <strict JSON>;`. Quiz:
  `id` equals its folder, non-empty `title` and `subtitle`, at least one
  deck. Deck: non-empty unique `id` and `label`, positive numbers `w`, `h`
  and `cw` with `2 * cw < w`, an `img` with a non-empty `src` (the file must
  exist in the quiz folder) and a numeric `x`, `y`, `w`, `h` box inside the
  canvas, and at least 3 `targets`. Target: `id` unique in its deck (the same
  id may appear in another deck), non-empty `name` (two targets may share
  one), numeric `x`, `y` inside the canvas, `side` `"l"` or `"r"`, numeric
  `ly` in `0..h`; slots on the same side are at least 40 units apart.
- `quizzes.js`: one entry per quiz folder, each with `id`, `path` (equal to
  `id + "/"`), `title` and `subtitle`. In the folder scan, its `decks` and
  `questions` counts must equal the real counts of that quiz (refresh them
  with `tools/merge_decks.py`); for a diagram quiz `questions` is the number
  of targets across all decks.

## Fixture quiz page

`tools/fixture/` holds a small test quiz (`"id": "fixture"`, one deck "Prova",
10 easy questions covering `mc`, `tf`, `match` and `order`) and a quiz page
(`index.html`) that loads the shared engine with `../../shared/` paths. It is
not listed in `quizzes.js`, and the checker's folder scan skips `tools/`, so
check it explicitly as shown above. Its `index.html` is the page shell every
quiz page copies.

To play it in a browser, serve the repo root and open the fixture page:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/tools/fixture/
```

Best scores and the round length are kept in `localStorage` under
`schoolquiz.fixture.*`; clear site data to reset them.

## App icons

`icon.svg` (repo root) is written by hand: a 512x512 `#1F5FA8` rounded square
with a white check mark. `rsvg-convert` is not installed on the author's Mac,
so the PNGs are exported with macOS Quick Look and `sips`, from the repo root:

```sh
qlmanage -t -s 512 -o /tmp/schoolquiz-icon icon.svg
cp /tmp/schoolquiz-icon/icon.svg.png icon-512.png
sips -s format png -z 180 180 icon-512.png --out icon-180.png
sips -g pixelWidth -g pixelHeight icon-512.png icon-180.png
```

With `rsvg-convert` available, `rsvg-convert -w 512 -h 512 icon.svg -o icon-512.png`
(and `-w 180 -h 180` for `icon-180.png`) does the same. `manifest.webmanifest`
lists all three icons.

## Test suites

Python tests (checker and other tools):

```sh
python3 -m unittest discover -s tools -p 'test_*.py' -v
```

JavaScript tests for the quiz engine, using node's built-in test runner
(no packages):

```sh
node --test tools/
```

`tools/engine.test.mjs` loads `shared/engine.js` with `node:vm` and tests the
pure `QuizCore` part: shuffling, round sampling per deck and across all decks,
the shuffled question views from `prepare`, grading with the `correctText`
formats, and the best-score helpers `readBest`/`writeBest`. It uses a seeded
random generator, so results are reproducible.

`tools/diagram.test.mjs` loads `shared/engine.js` and `shared/diagram.js` the
same way and tests the pure `DiagramCore` part of the labelling board:
`place` (moving a card, replacing a slot's card, emptying a slot, input left
untouched) and `grade` (`ok`/`bad`/`none` statuses and the count, cards with
the same name being interchangeable, unknown card ids counting as empty).
