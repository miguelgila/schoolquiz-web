import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_questions as cq  # noqa: E402


def mc(qid, answer=0, options=None):
    return {"id": qid, "type": "mc", "q": "Domanda?",
            "options": options if options is not None else ["A", "B", "C", "D"],
            "answer": answer, "why": "Perché.", "src": "§1"}


def tf(qid, answer=True):
    return {"id": qid, "type": "tf", "q": "Affermazione.", "answer": answer,
            "why": "Perché.", "src": "§1"}


def match(qid, pairs=None):
    return {"id": qid, "type": "match", "q": "Abbina.",
            "pairs": pairs if pairs is not None else [["a", "1"], ["b", "2"], ["c", "3"]],
            "why": "Perché.", "src": "§1"}


def order(qid, items=None):
    return {"id": qid, "type": "order", "q": "Ordina.",
            "items": items if items is not None else ["primo", "secondo", "terzo"],
            "why": "Perché.", "src": "§1"}


def valid_quiz():
    questions = [mc("d-01"), mc("d-02", 2), mc("d-03", 1, ["X", "Y", "Z"]),
                 mc("d-04", 3), mc("d-05"), mc("d-06"),
                 tf("d-07"), tf("d-08", False), match("d-09"), order("d-10")]
    return {"id": "quiz-a", "title": "Titolo", "subtitle": "Sotto",
            "decks": [{"id": "d", "label": "Mazzo", "questions": questions}]}


def q_of(quiz, qid):
    for deck in quiz["decks"]:
        for q in deck["questions"]:
            if q["id"] == qid:
                return q
    raise KeyError(qid)


class ValidateQuizTest(unittest.TestCase):
    def errors(self, quiz, folder="quiz-a"):
        return cq.validate_quiz(quiz, folder)

    def assertErrorMentions(self, errors, *needles):
        self.assertTrue(errors, "expected errors, got none")
        joined = "\n".join(errors)
        for needle in needles:
            self.assertIn(needle, joined)

    def test_valid_quiz_has_no_errors(self):
        self.assertEqual(self.errors(valid_quiz()), [])

    def test_extra_keys_are_tolerated(self):
        quiz = valid_quiz()
        quiz["extra"] = 1
        quiz["decks"][0]["extra"] = 1
        quiz["decks"][0]["questions"][0]["extra"] = 1
        self.assertEqual(self.errors(quiz), [])

    def test_duplicate_question_id(self):
        quiz = valid_quiz()
        q_of(quiz, "d-02")["id"] = "d-01"
        self.assertErrorMentions(self.errors(quiz), "duplicate", "d-01")

    def test_mc_answer_out_of_range(self):
        for bad in (4, -1, "0", True, 1.0):
            quiz = valid_quiz()
            q_of(quiz, "d-01")["answer"] = bad
            self.assertErrorMentions(self.errors(quiz), "d-01", "answer")

    def test_mc_fewer_than_three_or_duplicate_options(self):
        quiz = valid_quiz()
        q_of(quiz, "d-01")["options"] = ["A", "B"]
        self.assertErrorMentions(self.errors(quiz), "d-01", "options")
        quiz = valid_quiz()
        q_of(quiz, "d-01")["options"] = ["A", "B", "A"]
        self.assertErrorMentions(self.errors(quiz), "d-01", "duplicate")
        quiz = valid_quiz()
        q_of(quiz, "d-01")["options"] = ["A", "B", "C", "D", "E"]
        self.assertErrorMentions(self.errors(quiz), "d-01", "options")
        quiz = valid_quiz()
        q_of(quiz, "d-01")["options"] = ["A", "", "C"]
        self.assertErrorMentions(self.errors(quiz), "d-01", "options")

    def test_tf_answer_must_be_bool(self):
        for bad in (1, 0, "true", None):
            quiz = valid_quiz()
            q_of(quiz, "d-07")["answer"] = bad
            self.assertErrorMentions(self.errors(quiz), "d-07", "answer")

    def test_match_needs_three_unique_pairs(self):
        quiz = valid_quiz()
        q_of(quiz, "d-09")["pairs"] = [["a", "1"], ["b", "2"]]
        self.assertErrorMentions(self.errors(quiz), "d-09", "pairs")
        quiz = valid_quiz()
        q_of(quiz, "d-09")["pairs"] = [["a", "1"], ["a", "2"], ["c", "3"]]
        self.assertErrorMentions(self.errors(quiz), "d-09", "duplicate", "left")
        quiz = valid_quiz()
        q_of(quiz, "d-09")["pairs"] = [["a", "1"], ["b", "1"], ["c", "3"]]
        self.assertErrorMentions(self.errors(quiz), "d-09", "duplicate", "right")
        quiz = valid_quiz()
        q_of(quiz, "d-09")["pairs"] = [["a", "1"], ["b"], ["c", "3"]]
        self.assertErrorMentions(self.errors(quiz), "d-09", "pairs")
        quiz = valid_quiz()
        q_of(quiz, "d-09")["pairs"] = [[str(i), str(i)] for i in range(6)]
        self.assertErrorMentions(self.errors(quiz), "d-09", "pairs")

    def test_order_needs_three_items(self):
        quiz = valid_quiz()
        q_of(quiz, "d-10")["items"] = ["a", "b"]
        self.assertErrorMentions(self.errors(quiz), "d-10", "items")
        quiz = valid_quiz()
        q_of(quiz, "d-10")["items"] = ["a", "b", "a"]
        self.assertErrorMentions(self.errors(quiz), "d-10", "duplicate")
        quiz = valid_quiz()
        q_of(quiz, "d-10")["items"] = list("abcdef")
        self.assertErrorMentions(self.errors(quiz), "d-10", "items")

    def test_missing_why_or_src(self):
        for field in ("why", "src", "q"):
            quiz = valid_quiz()
            del q_of(quiz, "d-03")[field]
            self.assertErrorMentions(self.errors(quiz), "d-03", field)
            quiz = valid_quiz()
            q_of(quiz, "d-03")[field] = "  "
            self.assertErrorMentions(self.errors(quiz), "d-03", field)

    def test_unknown_type(self):
        quiz = valid_quiz()
        q_of(quiz, "d-05")["type"] = "essay"
        self.assertErrorMentions(self.errors(quiz), "d-05", "type")

    def test_deck_under_ten_questions(self):
        quiz = valid_quiz()
        quiz["decks"][0]["questions"].pop()
        self.assertErrorMentions(self.errors(quiz), "deck d", "fewer than 10")

    def test_empty_deck_does_not_crash(self):
        quiz = valid_quiz()
        quiz["decks"].append({"id": "vuoto", "label": "Vuoto", "questions": []})
        self.assertErrorMentions(self.errors(quiz), "vuoto", "fewer than 10")

    def test_quiz_needs_title_subtitle_and_decks(self):
        for field in ("title", "subtitle"):
            quiz = valid_quiz()
            del quiz[field]
            self.assertErrorMentions(self.errors(quiz), field)
        quiz = valid_quiz()
        quiz["decks"] = []
        self.assertErrorMentions(self.errors(quiz), "deck")

    def test_quiz_id_must_match_folder(self):
        self.assertErrorMentions(self.errors(valid_quiz(), "other"), "quiz-a", "other")
        # a folder path is compared by its last component
        self.assertEqual(self.errors(valid_quiz(), os.path.join("x", "quiz-a")), [])


class RegistryTest(unittest.TestCase):
    def entry(self, qid="quiz-a"):
        return {"id": qid, "path": qid + "/", "title": "T", "subtitle": "S",
                "decks": 1, "questions": 10}

    def test_valid_registry(self):
        self.assertEqual(cq.validate_registry([self.entry()], {"quiz-a"}), [])

    def test_registry_entry_missing_for_quiz(self):
        errors = cq.validate_registry([self.entry()], {"quiz-a", "quiz-b"})
        self.assertTrue(any("quiz-b" in e for e in errors), errors)

    def test_registry_entry_without_folder(self):
        errors = cq.validate_registry([self.entry(), self.entry("ghost")], {"quiz-a"})
        self.assertTrue(any("ghost" in e for e in errors), errors)

    def test_registry_bad_path_and_missing_fields(self):
        bad = self.entry()
        bad["path"] = "quiz-a"
        del bad["title"]
        errors = cq.validate_registry([bad], {"quiz-a"})
        joined = "\n".join(errors)
        self.assertIn("path", joined)
        self.assertIn("title", joined)

    def test_registry_duplicate_entry(self):
        errors = cq.validate_registry([self.entry(), self.entry()], {"quiz-a"})
        self.assertTrue(any("duplicate" in e for e in errors), errors)


class LoadAndMainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def write_quiz(self, folder, quiz):
        return self.write(os.path.join(folder, "questions.js"),
                          "window.QUIZ = " + json.dumps(quiz, ensure_ascii=False, indent=1) + ";\n")

    def write_registry(self, entries):
        self.write("quizzes.js", "window.QUIZZES = " + json.dumps(entries) + ";\n")

    def test_load_quiz_strips_prefix(self):
        quiz = valid_quiz()
        path = self.write_quiz("quiz-a", quiz)
        self.assertEqual(cq.load_quiz(path), quiz)

    def test_load_quiz_rejects_bad_prefix(self):
        path = self.write("quiz-a/questions.js", "var QUIZ = {};")
        with self.assertRaises(ValueError):
            cq.load_quiz(path)

    def run_main(self, argv):
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            code = cq.main(argv, root=self.root)
        return code, err.getvalue()

    def test_main_scan_ok(self):
        self.write_quiz("quiz-a", valid_quiz())
        os.makedirs(os.path.join(self.root, "shared"))
        broken = copy.deepcopy(valid_quiz())
        broken["id"] = "fixture"
        broken["decks"][0]["questions"] = []
        self.write_quiz("tools/fixture", broken)  # skipped by the scan
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S"}])
        self.assertEqual(self.run_main([]), (0, ""))

    def test_main_scan_reports_errors(self):
        quiz = valid_quiz()
        quiz["decks"][0]["questions"] = []
        self.write_quiz("quiz-a", quiz)
        self.write_registry([])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("fewer than 10", err)
        self.assertIn("quiz-a", err)

    def test_main_missing_registry(self):
        self.write_quiz("quiz-a", valid_quiz())
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("quizzes.js", err)

    def test_main_invalid_json(self):
        self.write("quiz-a/questions.js", "window.QUIZ = {\"id\": \"quiz-a\",};")
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S"}])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("questions.js", err)

    def test_main_explicit_file(self):
        quiz = valid_quiz()
        quiz["id"] = "fixture"
        path = self.write_quiz("tools/fixture", quiz)
        self.assertEqual(self.run_main([path, os.path.join(self.root, "tools", "fixture")]), (0, ""))
        code, err = self.run_main([path, "elsewhere"])
        self.assertEqual(code, 1)
        self.assertIn("elsewhere", err)

    def test_main_bad_arg_count(self):
        code, err = self.run_main(["only-one"])
        self.assertEqual(code, 1)
        self.assertIn("usage", err.lower())


if __name__ == "__main__":
    unittest.main()
