# schoolquiz-web — Quiz scolastici: design

Date: 2026-10-18. Status: draft for owner approval.

## Intent

A static site at **schoolquiz.giar.dev** that hosts, over time, several
school-revision quizzes for the owner's son (3ª media in Ticino, Italian
school language, about 13 years old). The first quiz covers his history
lessons of September 2026: the return of towns and trade after the year
1000, the Alpine passes, the birth of the Swiss Confederation, and the start
of the modern age with the explorations and the conquest of America.

It is built the way the owner's two geography quizzes are built
([chgeo](https://github.com/miguelgila/chgeo), [eugeo](https://github.com/miguelgila/eugeo)):
one public GitHub repo, `miguelgila/schoolquiz-web`, served by GitHub Pages
from `main` / root, no build step, no backend, no dependencies, Italian by
default. The owner repeats the exercise for later lessons by adding a folder
with a data file; the engine and the look stay the same.

The source material is two scanned PDFs (a worksheet booklet "Storia 3ªB"
from the class, based on *La Svizzera nella storia 2*, and the boy's
handwritten notes). They were read in full on 2026-10-18 in the session that wrote this
document. Distilling them into the facts sheet
`docs/content/storia-medioevo-esplorazioni-facts.md` is the **first task of
the implementation plan**, done by that same session from the scans, before
any question is written. The PDFs themselves are **not** committed: they
contain the child's handwriting and the textbook's images.

## Goals

- A revision tool that feels like a game and matches how he will be tested:
  names, dates, places, definitions, cause and effect, and the teacher's own
  interpretation questions turned into closed questions.
- Same look, feel and conventions as chgeo/eugeo, so the owner can maintain
  all three by reading diffs: Manrope, the same palette, buttons and card
  style, **Verifica**-style feedback, a "Da ripassare" list, phone-first
  layout. There is no card tray: a round is linear, one question after the
  other, with no skipping or jumping back.
- Adding a quiz is a data task: a new folder with a `questions.js` and a line
  in the landing page's registry. No engine change.
- Every question traceable to the lesson: each one carries a one-line
  explanation and a section reference, and the facts sheet in `docs/` is the
  only ground truth used to write them.

## Non-goals

- No backend, accounts, sync, build step, package manager or bundler. The
  only tooling is a small Python checker for the data files, like eugeo's
  pipeline tests: a developer tool, not part of the site.
- No analytics, cookies, third-party scripts or widgets. Audience is a child.
  The Ko-fi link, if any, stays a plain link in the footer.
- No study/summary pages. He revises from his own worksheets; the quiz only
  explains each answer in one line.
- No other languages for the question content. The UI strings go through the
  same `i18n.js` mechanism as eugeo so the chrome can be translated later, but
  the questions are in Italian and stay so.
- No images from the textbook or the worksheets (copyright), no verbatim
  passages longer than a short phrase. Questions and explanations are
  paraphrases.

## Anti-goals (what would make it a failure)

- A wrong fact or date in a question. He would learn it wrong. Accuracy
  beats quantity: a question that cannot be grounded in the facts sheet is
  dropped, not guessed.
- Questions that are only answerable by remembering the worksheet's wording
  rather than the fact (trick questions, near-duplicate options).
- Forking so far from eugeo's structure that the owner has to learn a new
  codebase per site.

## Constraints

- Hosting: GitHub Pages, `main` / root, `.nojekyll`, `CNAME` containing
  `schoolquiz.giar.dev`. The owner adds `CNAME schoolquiz → miguelgila.github.io`
  at the `giar.dev` DNS provider and ticks *Enforce HTTPS* when the
  certificate is issued.
- Repo creation, enabling Pages and pushing are confirmed with the owner
  before they happen. Commits carry no AI or co-author lines.
- The site must work from a subfolder (`/storia-medioevo-esplorazioni/`),
  so shared assets are referenced relatively (`../shared/...`), never from `/`.
- Everything, code and question text, is MIT (`LICENSE`). The README credits
  the classroom material as the source of the facts.

## Decisions taken

Marked **(owner)** when the owner chose it, **(builder's call)** when the
builder settled a sensible default the owner may override.

### Repository layout **(owner: one repo, folder per quiz; details builder's call)**

```
index.html                     landing page: lists the quizzes from quizzes.js
quizzes.js                     window.QUIZZES registry: [{id, path, title, subtitle, decks}]
shared/
  engine.js                    the quiz engine (one IIFE), used by every quiz page
  style.css                    the shared stylesheet (palette and components from eugeo)
  i18n.js                      window.I18N: langs [['it','Italiano']], ui.it
storia-medioevo-esplorazioni/
  index.html                   thin shell: title, meta, loads ../shared/* and ./questions.js
  questions.js                 window.QUIZ = {...}   (strict JSON after the prefix)
tools/
  check_questions.py           validates every */questions.js and quizzes.js
  test_i18n.py                 every UI key used by engine.js exists in ui.it
  README.md
CNAME, .nojekyll, manifest.webmanifest, icon.svg, icon-180.png, icon-512.png
LICENSE (MIT), README.md, CLAUDE.md
docs/content/<quiz-id>-facts.md   the facts sheet each quiz is written from
docs/superpowers/specs/…, docs/superpowers/plans/…
```

A quiz page differs from another only in its `<title>`, meta description and
the `questions.js` it loads; the engine reads everything else from
`window.QUIZ`. The landing page reads `quizzes.js` and renders one card per
quiz (title, subtitle, number of decks and questions, link). It also has a
small "Altri quiz" row linking to chgeo.giar.dev and eugeo.giar.dev
**(builder's call)**.

### Data format **(builder's call)**

`questions.js` is `window.QUIZ = <JSON>;` where the JSON is strict (no
comments, no trailing commas) so the Python checker can parse it without a
JavaScript runtime. Shape:

```js
window.QUIZ = {
  "id": "storia-medioevo-esplorazioni",            // folder name
  "title": "Storia: Medioevo ed esplorazioni",
  "subtitle": "3ª media · §1 Città, mercanti e passi alpini · §2 I confini del mondo si allargano",
  "decks": [
    {"id": "citta", "label": "Città e mercanti", "questions": [ ... ]},
    ...
  ]
};
```

Question types, all with `id` (unique in the quiz, stable, e.g. `citta-07`),
`why` (one line shown after answering, in Italian) and `src` (section
reference, e.g. `"§1 · Le carte di libertà"`):

| type | fields | play |
|---|---|---|
| `mc` | `q`, `options` (3–4 strings), `answer` (index) | tap one option |
| `tf` | `q` (a statement), `answer` (true/false) | tap Vero / Falso |
| `match` | `q` (prompt), `pairs` ([[left, right], ...], 3–5) | for each left item pick the right one from a shuffled list; all must match |
| `order` | `q` (prompt), `items` (3–5 strings, in correct order) | arrange with up/down buttons (no drag); checked as a whole |

Options, pair right-hand sides and order items are shuffled at play time
(the engine makes sure a shuffled `order` never starts already correct).
A `match` or `order` question counts as one question: right only if fully
right, and the feedback shows the full correct arrangement.

Option sets are written so that the wrong ones are plausible and drawn from
the same lesson (other dates of the same deck, other cities of the same
list), never nonsense.

### Decks and size **(builder's call, from the owner's confirmed content scope)**

Five decks follow the teacher's sections. Target 25–35 questions per deck,
mixed types (roughly 60% `mc`, 20% `tf`, 10% `match`, 10% `order`):

1. **Città e mercanti** — after the year 1000: climate, population, markets,
   "un anno e un giorno", Siena's Buon Governo, Swiss towns founded by lords
   (Berna 1191, Friburgo 1157), the Neuchâtel charter of 1214 and its
   clauses, borghesi, bottega, corporazioni, women's work; long-distance
   trade (fiere della Champagne, Lega Anseatica, Venezia and Genova),
   moneta, cambiavalute, banca, lettera di cambio; the Catalan atlas of 1375.
2. **Passi alpini e commerci** — the Brünig coins (120 coins, 13th century,
   found 2014, mostly from the bishop of Basilea), soma = ~155 kg, Brennero
   4000 t in 1300, somieri and their corporations, soste, the hospice at
   2100 m; Schöllenen, Twärrenbrücke 1218–1226, Ponte del Diavolo, the
   Gottardo as Basilea–Milano link, "passo sopravvalutato" (a twentieth of
   the Brennero), cattle, cheese and mercenaries as goods, the valleys around
   the pass becoming worth controlling.
3. **Nascita della Confederazione** — Paesi forestali (Uri, Svitto,
   Untervaldo), contadini liberi, immediatezza imperiale (Enrico VII, 1309),
   balivo Werner von Homberg, Landamano, Landsgemeinde; the pact of August
   1291 (who signs, mutual aid, article 3 and 4, the crimes and penalties,
   "rinnovare un antico patto", death of Rodolfo d'Asburgo in 1291,
   "Svizzera senza fondazione"); Einsiedeln 1314, Morgarten 15 Nov 1315,
   Brunnen, Lucerna 1332, Zurigo 1351, Glarona 1352, Zugo 1352, Berna 1353,
   eight cantons, Sempach 9 Jul 1386, Dieta, thirteen cantons 1513, Ticino
   as baliaggi 1400–1515; the "piccolo popolo pacifico" myth against
   Winterthur, Etterlin, Machiavelli, Guicciardini and Wimpfeling; mercenary
   service until 1859, about a million men.
4. **Età moderna e Rinascimento** — the boy's notes: Alto Medioevo pyramid
   (oratores, bellatores, laboratores), Basso Medioevo with borghesi, the
   five breaks of the modern age, Stato vs Nazione; Giotto vs Raffaello,
   Umanesimo, Rinascimento, prospettiva, rediscovery of antiquity; Tolomeo's
   map and what it lacks; the four pushes (weak universal powers, national
   states and taxes, fall of Costantinopoli 29 May 1453 to Maometto II, cost
   of spices); the caravel and its parts.
5. **Esplorazioni e conquiste** — Portugal: Enrico il Navigatore at Sagres,
   Gil Eanes 1434, Diaz 1488, Vasco da Gama 1498, Cabral 1500, vela latina,
   "impero di punti su una linea"; Colombo: Imago mundi, 56⅔ miglia per
   degree, refused by Portugal, Granada 1492, Palos 3 Aug 1492, Bahamas
   12 Oct 1492, believes he is in Asia; Tordesillas 1494 and Brazil;
   Waldseemüller 1507 and Vespucci; Cortés 1519–1521 and Montezuma, Pizarro
   1532, horses, firearms, alliances, smallpox; Magellano 1519–1522,
   Pigafetta, 18 men back on one ship.

A sixth virtual deck **Tutto** mixes all decks.

### Play loop **(builder's call, modelled on eugeo)**

- Header: brand mark, quiz title, subtitle; a segmented control for the deck
  (as eugeo's modes); a link back to the landing page.
- A round is **10 questions** sampled at random from the chosen deck (or all
  of them if the deck has fewer; "Tutto" samples across decks). The round
  length can be changed to 20 or "tutte" with a small selector.
- One question at a time: prompt, answer controls, a **Verifica** button for
  `match`/`order` (for `mc`/`tf` the tap answers directly). Then immediate
  feedback: green/red with the correct answer highlighted, the `why` line,
  the `src` in muted text, and **Avanti**.
- Progress "3 / 10" in the toolbar, as eugeo's "piazzate" counter.
- End screen: score "7 su 10 giuste", a **Da ripassare** list with every
  missed question and its correct answer, **Ricomincia** (new random
  sample). The best score per deck is kept in `localStorage`
  (`schoolquiz.<quizId>.<deckId>.best`) and shown on the deck buttons as a
  small badge **(builder's call; drop if it clutters the phone layout)**.
- Keyboard: 1–4 pick an option, Enter advances. Touch targets ≥ 44 px.
- Zero-dependency vanilla JS, one IIFE in `shared/engine.js`, state in a
  single `S` object, `render()` on every change, as in eugeo.

### i18n **(builder's call)**

`shared/i18n.js` with `langs: [['it','Italiano']]` and `ui.it` holding every
chrome string (buttons, progress, result sentences, landing page labels),
with `{0}`/`{1}` placeholders. `t(key, ...args)` as in eugeo; the language
`<select>` is hidden while `langs` has one entry. Question text is data, not
UI, and is not keyed.

### Tooling **(builder's call)**

- `tools/check_questions.py` (Python 3, standard library only): for every
  `*/questions.js` strips the prefix and suffix, parses the JSON, and fails
  on: duplicate question ids, `answer` out of range, fewer than 3 options or
  duplicate options, `tf` answer not boolean, `match` with fewer than 3 pairs
  or duplicate sides, `order` with fewer than 3 items, missing or empty
  `why`/`src`, a deck with fewer than 10 questions, and a quiz `id` that
  does not match its folder or is missing from `quizzes.js`.
- `tools/test_i18n.py`: every `t('key'…)` used in `engine.js` and
  `index.html` files exists in `ui.it`, and every `ui.it` key is used.
- Both run locally before every push (owner rule: fix failures locally, no
  CI minutes wasted). No GitHub Actions at launch.

### Content process **(builder's call)**

`docs/content/storia-medioevo-esplorazioni-facts.md` is the facts sheet
written from the scans: one bullet per fact, grouped by section, with the
worksheet section title. It is the **only** source for writing questions.
Whoever writes a deck writes only questions whose answer and distractors
appear in the sheet; anything doubtful is left out. The writer may check a
sheet fact against general historical knowledge, and when the two disagree
does **not** silently fix either: the question is held back and the item goes
on a "da verificare" list in the plan's final report, for the owner to settle
against the originals. The owner is the final reviewer of the question bank,
since they can hold it against the worksheets.

### Hosting / ops

- **Order of work (owner):** engine, facts sheet and all five decks are
  built and checked locally first. The owner reviews the question bank
  against the worksheets. Only then is the GitHub repo created and the
  first push made, so nothing is public before the owner has seen it.
- `gh repo create miguelgila/schoolquiz-web --public --description "Quiz scolastici"`,
  initial commit on `main`, push (after owner confirmation).
- Enable Pages: `gh api -X POST repos/miguelgila/schoolquiz-web/pages -f build_type=legacy -f source[branch]=main -f source[path]=/`,
  then set the custom domain `schoolquiz.giar.dev`; enforce HTTPS once the
  certificate exists.
- Owner: DNS `CNAME schoolquiz → miguelgila.github.io`.
- PWA: `manifest.webmanifest` at the root, name "Quiz scolastici", short
  name "Schoolquiz", `start_url: "./"`, icons as eugeo. No service worker.
- Footer on every page: "Codice" link to the repo, licence, Ko-fi plain link
  as in eugeo **(builder's call: include it for consistency)**.

## What's left to the builder

- The exact visual design of the question card, the match and order
  controls, and the landing-page cards, within eugeo's palette and type.
- The icon: a simple single-colour glyph (a pencil or a checkmark in a
  square), not the geography ones.
- The split of question types per deck and the final count, within the
  ranges above.
- The text of `CLAUDE.md` and `README.md` for the new repo, modelled on
  eugeo's, including "Adding a quiz" and "Running the checks".
- How `Tutto` samples (builder's call: equal share per deck, rounded).

## Open questions resolved by default (owner may override)

- Round length 10 by default; selectable 20 / all.
- Best score per deck kept in the browser. No history beyond that.
- The folder/quiz id is `storia-medioevo-esplorazioni`.
- Question and explanation text licensed MIT with the code; the README
  states the facts come from the class worksheets based on *La Svizzera
  nella storia 2* and the student's notes, with no textbook text or images
  reproduced.
