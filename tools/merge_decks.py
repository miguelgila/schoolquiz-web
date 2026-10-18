#!/usr/bin/env python3
"""Merge decks/<id>.json files into a quiz's questions.js and refresh quizzes.js counts.

Usage: python3 tools/merge_decks.py [quiz_folder]   (default: storia-medioevo-esplorazioni)

Each deck listed in questions.js gets its questions from <quiz_folder>/decks/<deck id>.json
(a bare JSON array). A deck without a file is left as it is. The registry entry in
quizzes.js with the same id gets its "decks" and "questions" counts updated.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_prefixed(path, prefix):
    text = open(path, encoding="utf-8").read()
    if not text.startswith(prefix):
        raise SystemExit(f"{path}: does not start with {prefix!r}")
    body = text[len(prefix):].rstrip()
    if not body.endswith(";"):
        raise SystemExit(f"{path}: does not end with ';'")
    return json.loads(body[:-1])


def _dump_prefixed(path, prefix, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write(prefix + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")


def main(argv):
    folder = argv[0] if argv else "storia-medioevo-esplorazioni"
    qpath = os.path.join(ROOT, folder, "questions.js")
    quiz = _load_prefixed(qpath, "window.QUIZ = ")
    deck_dir = os.path.join(ROOT, folder, "decks")
    for deck in quiz["decks"]:
        dpath = os.path.join(deck_dir, deck["id"] + ".json")
        if os.path.exists(dpath):
            with open(dpath, encoding="utf-8") as f:
                deck["questions"] = json.load(f)
            print(f"{deck['id']}: {len(deck['questions'])} questions")
        else:
            print(f"{deck['id']}: no deck file, left unchanged ({len(deck['questions'])})")
    _dump_prefixed(qpath, "window.QUIZ = ", quiz)

    rpath = os.path.join(ROOT, "quizzes.js")
    registry = _load_prefixed(rpath, "window.QUIZZES = ")
    total = sum(len(d["questions"]) for d in quiz["decks"])
    for entry in registry:
        if entry["id"] == quiz["id"]:
            entry["decks"] = len(quiz["decks"])
            entry["questions"] = total
    _dump_prefixed(rpath, "window.QUIZZES = ", registry)
    print(f"registry: {quiz['id']} -> {len(quiz['decks'])} decks, {total} questions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
