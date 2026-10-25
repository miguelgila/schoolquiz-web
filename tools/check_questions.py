#!/usr/bin/env python3
"""Validate quiz data files (standard library only).

Usage:
  python3 tools/check_questions.py
      Scan every <folder>/questions.js and <folder>/diagram.js under the repo
      root (skipping tools/ and shared/) and check quizzes.js against the
      quiz folders found, including its "decks" and "questions" counts (for
      a diagram quiz, its decks and targets).
  python3 tools/check_questions.py <path/to/questions.js> <folder>
      Validate one file against the given folder name (its last component).
      quizzes.js is not read.
  python3 tools/check_questions.py <path/to/diagram.js> <folder>
      The same for a diagram (labelling board) quiz, detected by the file
      name diagram.js. The images are looked up next to the file.
  python3 tools/check_questions.py --deck <path/to/deck.json>
      Validate one deck stored as a bare JSON array of questions. The deck id
      is the file name without its extension.

Exit code 0 when everything is valid, 1 otherwise (errors go to stderr).
"""

import json
import os
import sys

QUIZ_PREFIX = "window.QUIZ = "
DIAGRAM_PREFIX = "window.DIAGRAM = "
REGISTRY_PREFIX = "window.QUIZZES = "
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"tools", "shared"}  # shared/diagram.js is the board engine, not a quiz
MIN_DECK_QUESTIONS = 10
MIN_DECK_TARGETS = 3
MIN_SLOT_GAP = 40


def _load_prefixed(path, prefix):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text.startswith(prefix):
        raise ValueError("%s: does not start with %r" % (path, prefix))
    text = text[len(prefix):].rstrip()
    if text.endswith(";"):
        text = text[:-1]
    return json.loads(text)


def load_quiz(path):
    return _load_prefixed(path, QUIZ_PREFIX)


def load_diagram(path):
    return _load_prefixed(path, DIAGRAM_PREFIX)


def load_registry(path):
    return _load_prefixed(path, REGISTRY_PREFIX)


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _distinct_texts(values):
    return all(_is_text(v) for v in values) and len(set(values)) == len(values)


def _check_question(q, where):
    errors = []
    for field in ("id", "type", "q", "why", "src"):
        if not _is_text(q.get(field)):
            errors.append("%s: missing or empty '%s'" % (where, field))
    kind = q.get("type")
    if kind == "mc":
        options = q.get("options")
        if not isinstance(options, list) or not 3 <= len(options) <= 4:
            errors.append("%s: 'options' must be a list of 3-4 strings" % where)
        elif not all(_is_text(o) for o in options):
            errors.append("%s: 'options' must be non-empty strings" % where)
        elif len(set(options)) != len(options):
            errors.append("%s: duplicate options" % where)
        answer = q.get("answer")
        size = len(options) if isinstance(options, list) else 0
        if type(answer) is not int or not 0 <= answer < size:
            errors.append("%s: 'answer' must be an option index 0..%d, got %r"
                          % (where, size - 1, answer))
    elif kind == "tf":
        if not isinstance(q.get("answer"), bool):
            errors.append("%s: 'answer' must be true or false, got %r" % (where, q.get("answer")))
    elif kind == "match":
        pairs = q.get("pairs")
        if not isinstance(pairs, list) or not 3 <= len(pairs) <= 5:
            errors.append("%s: 'pairs' must be a list of 3-5 [left, right] pairs" % where)
        elif not all(isinstance(p, list) and len(p) == 2 and _is_text(p[0]) and _is_text(p[1])
                     for p in pairs):
            errors.append("%s: every entry in 'pairs' must be [left, right] non-empty strings" % where)
        else:
            if len({p[0] for p in pairs}) != len(pairs):
                errors.append("%s: duplicate left side in 'pairs'" % where)
            if len({p[1] for p in pairs}) != len(pairs):
                errors.append("%s: duplicate right side in 'pairs'" % where)
    elif kind == "order":
        items = q.get("items")
        if not isinstance(items, list) or not 3 <= len(items) <= 5:
            errors.append("%s: 'items' must be a list of 3-5 strings" % where)
        elif not all(_is_text(i) for i in items):
            errors.append("%s: 'items' must be non-empty strings" % where)
        elif len(set(items)) != len(items):
            errors.append("%s: duplicate items" % where)
    elif _is_text(kind):
        errors.append("%s: unknown type %r (expected mc, tf, match or order)" % (where, kind))
    return errors


def _check_decks(decks, label):
    errors = []
    deck_ids = set()
    question_ids = set()
    for d_index, deck in enumerate(decks):
        if not isinstance(deck, dict):
            errors.append("%s, deck #%d: must be an object" % (label, d_index + 1))
            continue
        deck_id = deck.get("id")
        deck_label = "%s, deck %s" % (label, deck_id if _is_text(deck_id) else "#%d" % (d_index + 1))
        if not _is_text(deck_id):
            errors.append("%s: missing or empty 'id'" % deck_label)
        elif deck_id in deck_ids:
            errors.append("%s: duplicate deck id %r" % (deck_label, deck_id))
        else:
            deck_ids.add(deck_id)
        if not _is_text(deck.get("label")):
            errors.append("%s: missing or empty 'label'" % deck_label)
        questions = deck.get("questions")
        if not isinstance(questions, list):
            errors.append("%s: 'questions' must be a list" % deck_label)
            continue
        if len(questions) < MIN_DECK_QUESTIONS:
            errors.append("%s: fewer than %d questions (%d)"
                          % (deck_label, MIN_DECK_QUESTIONS, len(questions)))
        for q_index, q in enumerate(questions):
            if not isinstance(q, dict):
                errors.append("%s, question #%d: must be an object" % (deck_label, q_index + 1))
                continue
            qid = q.get("id")
            where = "%s, question %s" % (deck_label, qid if _is_text(qid) else "#%d" % (q_index + 1))
            if _is_text(qid):
                if qid in question_ids:
                    errors.append("%s: duplicate question id %r" % (where, qid))
                question_ids.add(qid)
            errors.extend(_check_question(q, where))
    return errors


def validate_quiz(quiz, folder_name):
    folder = os.path.basename(os.path.normpath(folder_name))
    if not isinstance(quiz, dict):
        return ["quiz in %s: top level must be an object" % folder]
    quiz_id = quiz.get("id")
    label = "quiz %s" % (quiz_id if _is_text(quiz_id) else "<no id>")
    errors = []
    if quiz_id != folder:
        errors.append("%s: id %r does not match folder %r" % (label, quiz_id, folder))
    for field in ("title", "subtitle"):
        if not _is_text(quiz.get(field)):
            errors.append("%s: missing or empty '%s'" % (label, field))
    decks = quiz.get("decks")
    if not isinstance(decks, list) or not decks:
        errors.append("%s: needs at least one deck" % label)
        return errors

    return errors + _check_decks(decks, label)


def validate_deck(questions, deck_id):
    """Validate a bare question array as a deck named deck_id."""
    deck = {"id": deck_id, "label": deck_id, "questions": questions}
    return _check_decks([deck], "deck file")


def _check_image(img, w, h, deck_label, folder_path):
    if not isinstance(img, dict):
        return ["%s: 'img' must be an object" % deck_label]
    errors = []
    src = img.get("src")
    if not _is_text(src):
        errors.append("%s: missing or empty 'img.src'" % deck_label)
    elif folder_path is not None and not os.path.isfile(os.path.join(folder_path, src)):
        errors.append("%s: image %s not found in %s" % (deck_label, src, folder_path))
    box = [img.get(f) for f in ("x", "y", "w", "h")]
    if not all(_is_number(v) for v in box):
        errors.append("%s: 'img' needs numeric x, y, w and h" % deck_label)
    elif _is_number(w) and _is_number(h):
        x, y, iw, ih = box
        if iw <= 0 or ih <= 0 or x < 0 or y < 0 or x + iw > w or y + ih > h:
            errors.append("%s: 'img' box %r is not inside the %rx%r canvas"
                          % (deck_label, box, w, h))
    return errors


def _check_targets(targets, w, h, deck_label):
    if not isinstance(targets, list) or len(targets) < MIN_DECK_TARGETS:
        return ["%s: 'targets' must be a list of at least %d targets" % (deck_label, MIN_DECK_TARGETS)]
    errors = []
    ids = set()
    slots = {"l": [], "r": []}
    sized = _is_number(w) and _is_number(h)
    for t_index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append("%s, target #%d: must be an object" % (deck_label, t_index + 1))
            continue
        tid = target.get("id")
        where = "%s, target %s" % (deck_label, tid if _is_text(tid) else "#%d" % (t_index + 1))
        if not _is_text(tid):
            errors.append("%s: missing or empty 'id'" % where)
        elif tid in ids:
            errors.append("%s: duplicate target id %r" % (where, tid))
        else:
            ids.add(tid)
        if not _is_text(target.get("name")):
            errors.append("%s: missing or empty 'name'" % where)
        x, y = target.get("x"), target.get("y")
        if not _is_number(x) or not _is_number(y):
            errors.append("%s: 'x' and 'y' must be numbers" % where)
        elif sized and not (0 <= x <= w and 0 <= y <= h):
            errors.append("%s: point (%r, %r) is not inside the %rx%r canvas" % (where, x, y, w, h))
        side = target.get("side")
        if side not in slots:
            errors.append("%s: 'side' must be \"l\" or \"r\", got %r" % (where, side))
        ly = target.get("ly")
        if not _is_number(ly):
            errors.append("%s: 'ly' must be a number" % where)
        elif sized and not 0 <= ly <= h:
            errors.append("%s: 'ly' %r is not inside 0..%r" % (where, ly, h))
        elif side in slots:
            slots[side].append((ly, where))
    for side in sorted(slots):
        ordered = sorted(slots[side], key=lambda s: s[0])
        for (ly_a, _), (ly_b, where) in zip(ordered, ordered[1:]):
            if ly_b - ly_a < MIN_SLOT_GAP:
                errors.append("%s: slot at ly %r is closer than %d to the one at ly %r (side %s)"
                              % (where, ly_b, MIN_SLOT_GAP, ly_a, side))
    return errors


def validate_diagram(quiz, folder_name, folder_path=None):
    """Validate a loaded diagram quiz; with folder_path, its images must exist there."""
    folder = os.path.basename(os.path.normpath(folder_name))
    if not isinstance(quiz, dict):
        return ["diagram in %s: top level must be an object" % folder]
    quiz_id = quiz.get("id")
    label = "diagram %s" % (quiz_id if _is_text(quiz_id) else "<no id>")
    errors = []
    if quiz_id != folder:
        errors.append("%s: id %r does not match folder %r" % (label, quiz_id, folder))
    for field in ("title", "subtitle"):
        if not _is_text(quiz.get(field)):
            errors.append("%s: missing or empty '%s'" % (label, field))
    decks = quiz.get("decks")
    if not isinstance(decks, list) or not decks:
        errors.append("%s: needs at least one deck" % label)
        return errors

    deck_ids = set()
    for d_index, deck in enumerate(decks):
        if not isinstance(deck, dict):
            errors.append("%s, deck #%d: must be an object" % (label, d_index + 1))
            continue
        deck_id = deck.get("id")
        deck_label = "%s, deck %s" % (label, deck_id if _is_text(deck_id) else "#%d" % (d_index + 1))
        if not _is_text(deck_id):
            errors.append("%s: missing or empty 'id'" % deck_label)
        elif deck_id in deck_ids:
            errors.append("%s: duplicate deck id %r" % (deck_label, deck_id))
        else:
            deck_ids.add(deck_id)
        if not _is_text(deck.get("label")):
            errors.append("%s: missing or empty 'label'" % deck_label)
        w, h, cw = deck.get("w"), deck.get("h"), deck.get("cw")
        for field, value in (("w", w), ("h", h), ("cw", cw)):
            if not _is_number(value) or value <= 0:
                errors.append("%s: '%s' must be a positive number, got %r" % (deck_label, field, value))
        if all(_is_number(v) and v > 0 for v in (w, h, cw)) and 2 * cw >= w:
            errors.append("%s: two side columns (2 x cw = %r) do not fit in w %r" % (deck_label, 2 * cw, w))
        if not (_is_number(w) and w > 0 and _is_number(h) and h > 0):
            w = h = None
        errors.extend(_check_image(deck.get("img"), w, h, deck_label, folder_path))
        errors.extend(_check_targets(deck.get("targets"), w, h, deck_label))
    return errors


def validate_registry(registry, quiz_ids):
    if not isinstance(registry, list):
        return ["quizzes.js: must be an array"]
    errors = []
    seen = set()
    for index, entry in enumerate(registry):
        if not isinstance(entry, dict):
            errors.append("quizzes.js entry #%d: must be an object" % (index + 1))
            continue
        entry_id = entry.get("id")
        label = "quizzes.js entry %s" % (entry_id if _is_text(entry_id) else "#%d" % (index + 1))
        for field in ("id", "path", "title", "subtitle"):
            if not _is_text(entry.get(field)):
                errors.append("%s: missing or empty '%s'" % (label, field))
        if not _is_text(entry_id):
            continue
        if entry.get("path") != entry_id + "/":
            errors.append("%s: path must be %r, got %r" % (label, entry_id + "/", entry.get("path")))
        if entry_id in seen:
            errors.append("%s: duplicate entry" % label)
        seen.add(entry_id)
        if entry_id not in quiz_ids:
            errors.append("%s: no quiz folder %s/questions.js or %s/diagram.js"
                          % (label, entry_id, entry_id))
    for quiz_id in sorted(set(quiz_ids) - seen):
        errors.append("quiz %s: missing from quizzes.js" % quiz_id)
    return errors


def quiz_counts(quiz):
    """(decks, questions) of a loaded quiz, or None when its decks are malformed."""
    decks = quiz.get("decks") if isinstance(quiz, dict) else None
    if not isinstance(decks, list) or not all(
            isinstance(d, dict) and isinstance(d.get("questions"), list) for d in decks):
        return None
    return len(decks), sum(len(d["questions"]) for d in decks)


def diagram_counts(quiz):
    """(decks, targets) of a loaded diagram quiz, or None when its decks are malformed."""
    decks = quiz.get("decks") if isinstance(quiz, dict) else None
    if not isinstance(decks, list) or not all(
            isinstance(d, dict) and isinstance(d.get("targets"), list) for d in decks):
        return None
    return len(decks), sum(len(d["targets"]) for d in decks)


def validate_registry_counts(registry, counts):
    """Compare each entry's decks/questions with counts {quiz id: (decks, questions)}."""
    if not isinstance(registry, list):
        return []
    errors = []
    for entry in registry:
        if not isinstance(entry, dict) or entry.get("id") not in counts:
            continue
        label = "quizzes.js entry %s" % entry["id"]
        for field, real in zip(("decks", "questions"), counts[entry["id"]]):
            if entry.get(field) != real:
                errors.append("%s: '%s' is %r but the quiz has %d (run tools/merge_decks.py)"
                              % (label, field, entry.get(field), real))
    return errors


def _check_file(path, folder):
    try:
        if os.path.basename(path) == "diagram.js":
            return validate_diagram(load_diagram(path), folder, os.path.dirname(path))
        return validate_quiz(load_quiz(path), folder)
    except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
        return ["%s: cannot load: %s" % (path, exc)]


def _check_deck_file(path):
    deck_id = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8") as f:
            questions = json.load(f)
    except (OSError, ValueError) as exc:
        return ["%s: cannot load: %s" % (path, exc)]
    if not isinstance(questions, list):
        return ["%s: deck %s: top level must be an array" % (path, deck_id)]
    return validate_deck(questions, deck_id)


def _scan(root):
    errors = []
    quiz_ids = set()
    counts = {}
    for name in sorted(os.listdir(root)):
        if name in SKIP_DIRS or name.startswith("."):
            continue
        folder_path = os.path.join(root, name)
        quiz_path = os.path.join(folder_path, "questions.js")
        diagram_path = os.path.join(folder_path, "diagram.js")
        has_quiz, has_diagram = os.path.isfile(quiz_path), os.path.isfile(diagram_path)
        if not has_quiz and not has_diagram:
            continue
        quiz_ids.add(name)
        if has_quiz and has_diagram:
            errors.append("%s: has both questions.js and diagram.js, keep only one" % folder_path)
            continue
        path = diagram_path if has_diagram else quiz_path
        try:
            quiz = load_diagram(path) if has_diagram else load_quiz(path)
        except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
            errors.append("%s: cannot load: %s" % (path, exc))
            continue
        if has_diagram:
            errors.extend(validate_diagram(quiz, name, folder_path))
            real = diagram_counts(quiz)
        else:
            errors.extend(validate_quiz(quiz, name))
            real = quiz_counts(quiz)
        if real is not None:
            counts[name] = real
    registry_path = os.path.join(root, "quizzes.js")
    try:
        registry = load_registry(registry_path)
    except (OSError, ValueError) as exc:
        errors.append("%s: cannot load: %s" % (registry_path, exc))
    else:
        errors.extend(validate_registry(registry, quiz_ids))
        errors.extend(validate_registry_counts(registry, counts))
    return errors


def main(argv, root=REPO_ROOT):
    """argv excludes the program name. Returns the process exit code."""
    if len(argv) == 0:
        errors = _scan(root)
    elif len(argv) == 2 and argv[0] == "--deck":
        errors = _check_deck_file(argv[1])
    elif len(argv) == 2:
        errors = _check_file(argv[0], argv[1])
    else:
        print("usage: check_questions.py [<path/to/questions.js|diagram.js> <folder> | --deck <path/to/deck.json>]",
              file=sys.stderr)
        return 1
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
