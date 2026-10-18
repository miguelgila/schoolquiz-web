# tools

Local checks for the quiz data and code. Python 3 and node (20 or newer)
standard libraries only, no packages to install. Run everything from the repo
root, and run it before every push.

## Question file checker

```sh
python3 tools/check_questions.py
```

Scans every `<quiz-id>/questions.js` in the repo root (skipping `tools/` and
folders without a `questions.js`) and checks `quizzes.js` against the quiz
folders it found. Exits 0 when all is valid; otherwise prints one error per
line to stderr, naming the quiz, deck and question id, and exits 1.

To check a single file against a folder name (for example the test fixture,
which is not listed in `quizzes.js`):

```sh
python3 tools/check_questions.py tools/fixture/questions.js tools/fixture
```

The quiz `id` must equal the last component of the folder name.

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
- `quizzes.js`: one entry per quiz folder, each with `id`, `path` (equal to
  `id + "/"`), `title` and `subtitle`. Extra keys such as `decks` and
  `questions` counts are allowed.

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
