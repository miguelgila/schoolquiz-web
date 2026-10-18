# schoolquiz — Quiz scolastici

A static hub of school-revision quizzes in Italian, hosted at [schoolquiz.giar.dev](https://schoolquiz.giar.dev). Each quiz lives in its own folder with a thin page and a data file, and every quiz is played by the same shared engine in `shared/`. The landing page lists the quizzes from `quizzes.js`. There is no build step, no backend and no third-party script: only plain HTML, CSS and JavaScript, plus the Manrope font stylesheet from Google Fonts.

## Quizzes

| Quiz | Folder | Decks | Questions |
|---|---|---|---|
| Storia: Medioevo ed esplorazioni | `storia-medioevo-esplorazioni/` | 5: Città e mercanti, Passi alpini e commerci, Nascita della Confederazione, Età moderna e Rinascimento, Esplorazioni e conquiste | 168 |
| Contesto Socioeconomico 2026 | `contesto-socioeconomico-2026/` | 5: Settori economici, I tre pilastri, Lavoro, turismo e commercio, Società e innovazione, Ambiente e politica | 168 |

Every quiz also has a **Tutto** deck that mixes all its decks, with an equal share from each.

## How to play

Pick a deck and a round length (10, 20 or all questions), then answer one question at a time: the feedback shows right or wrong, the correct answer, a one-line explanation and the lesson section. At the end the score comes with a **Da ripassare** list of the missed questions; the best score per deck is kept in the browser, for 10-question rounds only.

## Run locally

Any static file server works, e.g.

```sh
python3 -m http.server 8000
```

then open <http://localhost:8000>.

## Hosting on GitHub Pages

Settings → Pages → *Deploy from a branch* → `main` / root. `.nojekyll` is present so the files are served as they are.

The site uses the custom domain `schoolquiz.giar.dev`: the `CNAME` file in the repo root contains it. At the DNS provider, add a `CNAME` record `schoolquiz` → `miguelgila.github.io`. GitHub provisions the TLS certificate automatically; tick *Enforce HTTPS* once it is issued.

Quiz pages live in subfolders, so every shared asset is referenced relatively (`../shared/...`), never from `/`. The site is an installable PWA through `manifest.webmanifest` (no service worker).

## Checks

The checks use the Python 3 and node (20 or newer) standard libraries only, with nothing to install. Run them from the repo root, locally, before every push:

```sh
python3 tools/check_questions.py                      # validates every */questions.js and quizzes.js
python3 -m unittest discover -s tools -p 'test_*.py'  # checker tests and the i18n key check
node --test tools/                                    # tests for the engine's pure logic
```

See [tools/README.md](tools/README.md) for what the checker validates, its single-file and `--deck` modes, the fixture quiz page and the icon export.

## Adding a quiz

1. Create a folder named after the quiz id, e.g. `geografia-ticino/`.
2. Copy `index.html` from an existing quiz into it and change only the `<title>` and the meta description. The page reads everything else from its data file.
3. Write `questions.js` as `window.QUIZ = <JSON>;`. The JSON must be strict (double quotes, no comments, no trailing commas) so the Python checker can parse it. Its `id` must equal the folder name; it needs a `title`, a `subtitle` and a list of `decks`, each with `id`, `label` and at least 10 `questions`.
4. Add a line to `quizzes.js`: `{"id", "path": "<id>/", "title", "subtitle", "decks", "questions"}`.
5. Optionally keep each deck as a bare JSON array in `<folder>/decks/<deck id>.json`, which is easier to edit and to check on its own (`python3 tools/check_questions.py --deck <file>`). Then run `python3 tools/merge_decks.py <folder>` to copy the decks into `questions.js` and refresh the counts of the existing `quizzes.js` entry (the merge does not add a missing entry).
6. Run the checks above.

## Question format

Every question has an `id` that is unique in the quiz and stable (e.g. `citta-07`), a `type`, a prompt `q`, a one-line explanation `why` shown after answering, and a section reference `src`. Options, the right-hand side of pairs and order items are shuffled at play time.

**`mc`**, multiple choice: 3 or 4 `options`, `answer` is the index of the right one.

```json
{"id": "confederazione-01", "type": "mc",
 "q": "Come si chiamano in tedesco i Paesi forestali (Uri, Svitto e Untervaldo)?",
 "options": ["Landsgemeinde", "Landamano", "Waldstätte", "Dieta"], "answer": 2,
 "why": "I Paesi forestali, cioè Uri, Svitto e Untervaldo, in tedesco si chiamano Waldstätte.",
 "src": "§1 · Una Svizzera senza fondazione"}
```

**`tf`**, true or false: `q` is a statement, `answer` is `true` or `false`.

```json
{"id": "confederazione-04", "type": "tf",
 "q": "In cambio dell'immediatezza imperiale, l'imperatore manda un rappresentante, il balivo, a fare giustizia.",
 "answer": true,
 "why": "L'imperatore garantisce diritti e privilegi e invia un balivo a fare giustizia.",
 "src": "§1 · Una Svizzera senza fondazione"}
```

**`match`**: 3 to 5 `pairs` of `[left, right]`. For each left item the player picks the right one from a shuffled list; the question is right only if every pair matches.

```json
{"id": "confederazione-15", "type": "match",
 "q": "Abbina ogni reato del patto del 1291 alla sua pena.",
 "pairs": [["Omicidio premeditato", "Morte (o bando se il colpevole è fuggito)"],
           ["Incendio doloso", "Esclusione dalla comunità"],
           ["Furto o danno", "Sequestro dei beni"]],
 "why": "Il patto punisce l'omicidio premeditato con la morte o il bando, l'incendio doloso con l'esclusione e il furto o danno con il sequestro dei beni.",
 "src": "§1 · Una Svizzera senza fondazione"}
```

**`order`**: 3 to 5 `items`, written in the correct order. The player arranges them with up and down buttons; the question is right only if the whole order is.

```json
{"id": "confederazione-26", "type": "order",
 "q": "Metti in ordine cronologico.",
 "items": ["Patto federale", "Immediatezza imperiale concessa da Enrico VII",
           "Battaglia del Morgarten", "Lucerna entra nell'alleanza", "Battaglia di Sempach"],
 "why": "1291, 1309, 1315, 1332, 1386.",
 "src": "§1 · Dai tre cantoni ai tredici"}
```

## Content

Le domande sono scritte a partire dalle schede di classe basate su *La Svizzera nella storia 2* e dagli appunti dello studente; nessun testo o immagine del libro è riprodotto.

Le domande di *Contesto Socioeconomico 2026* sono scritte a partire da appunti di studio sul contesto socioeconomico svizzero e ticinese; nessun testo originale è riprodotto.

The facts sheet each quiz is written from is in [docs/content/](docs/content/). It is the only source used for the questions; the scanned worksheets and notes are not part of the repo.

## License

[MIT](LICENSE), for the code and for the question and explanation text.

The footer has a plain Ko-fi link. There are no analytics, cookies or third-party scripts, because the audience is schoolchildren.
