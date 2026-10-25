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


def target(tid, side="l", ly=40, name=None):
    return {"id": tid, "name": name if name is not None else tid.capitalize(),
            "x": 200, "y": 100, "side": side, "ly": ly}


def valid_diagram():
    targets = [target("cranio", "l", 40), target("femore", "l", 120),
               target("tibia", "r", 40), target("falangi-m", "r", 100, "Falangi"),
               target("falangi-p", "r", 160, "Falangi")]
    return {"id": "diag-a", "title": "Titolo", "subtitle": "Sotto",
            "decks": [{"id": "d", "label": "Mazzo", "w": 400, "h": 300, "cw": 100,
                       "img": {"src": "img/d.svg", "x": 100, "y": 0, "w": 200, "h": 300},
                       "targets": targets}]}


def tg_of(quiz, tid):
    for t in quiz["decks"][0]["targets"]:
        if t["id"] == tid:
            return t
    raise KeyError(tid)


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


class ValidateDiagramTest(unittest.TestCase):
    def errors(self, quiz, folder="diag-a", folder_path=None):
        return cq.validate_diagram(quiz, folder, folder_path)

    def assertErrorMentions(self, errors, *needles):
        self.assertTrue(errors, "expected errors, got none")
        joined = "\n".join(errors)
        for needle in needles:
            self.assertIn(needle, joined)

    def deck(self, quiz):
        return quiz["decks"][0]

    def test_valid_diagram_has_no_errors(self):
        self.assertEqual(self.errors(valid_diagram()), [])

    def test_same_target_id_in_two_decks_is_fine(self):
        quiz = valid_diagram()
        other = copy.deepcopy(self.deck(quiz))
        other["id"] = "e"
        quiz["decks"].append(other)
        self.assertEqual(self.errors(quiz), [])

    def test_id_must_match_folder(self):
        self.assertErrorMentions(self.errors(valid_diagram(), "other"), "diag-a", "other")
        self.assertEqual(self.errors(valid_diagram(), os.path.join("x", "diag-a")), [])

    def test_needs_title_subtitle_and_decks(self):
        for field in ("title", "subtitle"):
            quiz = valid_diagram()
            quiz[field] = " "
            self.assertErrorMentions(self.errors(quiz), field)
        quiz = valid_diagram()
        quiz["decks"] = []
        self.assertErrorMentions(self.errors(quiz), "deck")
        self.assertErrorMentions(self.errors([]), "top level")

    def test_deck_id_and_label(self):
        quiz = valid_diagram()
        del self.deck(quiz)["label"]
        self.assertErrorMentions(self.errors(quiz), "label")
        quiz = valid_diagram()
        self.deck(quiz)["id"] = ""
        self.assertErrorMentions(self.errors(quiz), "deck #1", "'id'")
        quiz = valid_diagram()
        quiz["decks"].append(copy.deepcopy(self.deck(quiz)))
        self.assertErrorMentions(self.errors(quiz), "duplicate deck id")

    def test_canvas_sizes_must_be_positive_numbers(self):
        for field in ("w", "h", "cw"):
            for bad in (0, -5, "400", True, None):
                quiz = valid_diagram()
                self.deck(quiz)[field] = bad
                self.assertErrorMentions(self.errors(quiz), "'%s' must be a positive number" % field)

    def test_side_columns_must_fit(self):
        quiz = valid_diagram()
        self.deck(quiz)["cw"] = 200
        self.assertErrorMentions(self.errors(quiz), "side columns")

    def test_img_needs_src_and_box(self):
        quiz = valid_diagram()
        self.deck(quiz)["img"] = "img/d.svg"
        self.assertErrorMentions(self.errors(quiz), "'img' must be an object")
        quiz = valid_diagram()
        self.deck(quiz)["img"]["src"] = ""
        self.assertErrorMentions(self.errors(quiz), "img.src")
        for field in ("x", "y", "w", "h"):
            quiz = valid_diagram()
            self.deck(quiz)["img"][field] = "1"
            self.assertErrorMentions(self.errors(quiz), "numeric x, y, w and h")

    def test_img_inside_canvas(self):
        for field, bad in (("x", -1), ("y", -1), ("x", 201), ("h", 301), ("w", 0)):
            quiz = valid_diagram()
            self.deck(quiz)["img"][field] = bad
            self.assertErrorMentions(self.errors(quiz), "not inside the 400x300 canvas")

    def test_img_file_must_exist_when_folder_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertErrorMentions(self.errors(valid_diagram(), folder_path=tmp),
                                     "image img/d.svg not found")
            os.makedirs(os.path.join(tmp, "img"))
            with open(os.path.join(tmp, "img", "d.svg"), "w", encoding="utf-8") as f:
                f.write("<svg/>")
            self.assertEqual(self.errors(valid_diagram(), folder_path=tmp), [])

    def test_targets_need_at_least_three(self):
        quiz = valid_diagram()
        self.deck(quiz)["targets"] = self.deck(quiz)["targets"][:2]
        self.assertErrorMentions(self.errors(quiz), "at least 3 targets")
        quiz = valid_diagram()
        del self.deck(quiz)["targets"]
        self.assertErrorMentions(self.errors(quiz), "'targets'")
        quiz = valid_diagram()
        self.deck(quiz)["targets"][0] = "cranio"
        self.assertErrorMentions(self.errors(quiz), "target #1", "must be an object")

    def test_target_id_unique_and_name_non_empty(self):
        quiz = valid_diagram()
        tg_of(quiz, "femore")["id"] = "cranio"
        self.assertErrorMentions(self.errors(quiz), "duplicate target id 'cranio'")
        quiz = valid_diagram()
        tg_of(quiz, "femore")["id"] = " "
        self.assertErrorMentions(self.errors(quiz), "target #2", "'id'")
        quiz = valid_diagram()
        tg_of(quiz, "femore")["name"] = ""
        self.assertErrorMentions(self.errors(quiz), "target femore", "'name'")

    def test_target_point_numeric_and_inside_canvas(self):
        for field, bad in (("x", "200"), ("y", None), ("x", True)):
            quiz = valid_diagram()
            tg_of(quiz, "tibia")[field] = bad
            self.assertErrorMentions(self.errors(quiz), "target tibia", "must be numbers")
        for field, bad in (("x", 401), ("y", -1)):
            quiz = valid_diagram()
            tg_of(quiz, "tibia")[field] = bad
            self.assertErrorMentions(self.errors(quiz), "target tibia", "not inside")

    def test_target_side(self):
        for bad in ("left", "", None):
            quiz = valid_diagram()
            tg_of(quiz, "tibia")["side"] = bad
            self.assertErrorMentions(self.errors(quiz), "target tibia", "'side'")

    def test_target_ly_numeric_and_inside(self):
        quiz = valid_diagram()
        tg_of(quiz, "tibia")["ly"] = "40"
        self.assertErrorMentions(self.errors(quiz), "target tibia", "'ly' must be a number")
        for bad in (-1, 301):
            quiz = valid_diagram()
            tg_of(quiz, "tibia")["ly"] = bad
            self.assertErrorMentions(self.errors(quiz), "target tibia", "not inside 0..300")

    def test_slots_on_one_side_need_a_gap(self):
        quiz = valid_diagram()
        tg_of(quiz, "falangi-p")["ly"] = 139  # 39 below falangi-m at 100
        self.assertErrorMentions(self.errors(quiz), "falangi-p", "closer than 40", "side r")
        quiz = valid_diagram()
        tg_of(quiz, "falangi-p")["ly"] = 140  # exactly the minimum gap
        self.assertEqual(self.errors(quiz), [])
        # the same height on opposite sides is fine (cranio l 40, tibia r 40)
        quiz = valid_diagram()
        tg_of(quiz, "femore")["ly"] = 70  # unsorted order, still checked by height
        self.assertErrorMentions(self.errors(quiz), "femore", "closer than 40", "side l")


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
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S",
                              "decks": 1, "questions": 10}])
        self.assertEqual(self.run_main([]), (0, ""))

    def test_main_scan_reports_registry_count_mismatch(self):
        self.write_quiz("quiz-a", valid_quiz())
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S",
                              "decks": 2, "questions": 9}])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("'decks' is 2 but the quiz has 1", err)
        self.assertIn("'questions' is 9 but the quiz has 10", err)
        # missing counts are a mismatch too: the landing card shows them
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S"}])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("'decks' is None", err)

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

    def write_diagram(self, folder, quiz):
        return self.write(os.path.join(folder, "diagram.js"),
                          "window.DIAGRAM = " + json.dumps(quiz, ensure_ascii=False, indent=1) + ";\n")

    def diagram_entry(self, decks=1, questions=5):
        return {"id": "diag-a", "path": "diag-a/", "title": "T", "subtitle": "S",
                "decks": decks, "questions": questions}

    def test_main_scan_diagram_ok(self):
        self.write_quiz("quiz-a", valid_quiz())
        self.write_diagram("diag-a", valid_diagram())
        self.write("diag-a/img/d.svg", "<svg/>")
        self.write("shared/diagram.js", "const DiagramCore = {};")  # the engine, skipped
        self.write_registry([{"id": "quiz-a", "path": "quiz-a/", "title": "T", "subtitle": "S",
                              "decks": 1, "questions": 10}, self.diagram_entry()])
        self.assertEqual(self.run_main([]), (0, ""))

    def test_main_scan_diagram_count_mismatch_and_missing_image(self):
        self.write_diagram("diag-a", valid_diagram())
        self.write_registry([self.diagram_entry(2, 10)])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("'decks' is 2 but the quiz has 1", err)
        self.assertIn("'questions' is 10 but the quiz has 5", err)
        self.assertIn("image img/d.svg not found", err)

    def test_main_scan_both_files_is_an_error(self):
        quiz = valid_quiz()
        quiz["id"] = "diag-a"
        self.write_quiz("diag-a", quiz)
        self.write_diagram("diag-a", valid_diagram())
        self.write("diag-a/img/d.svg", "<svg/>")
        self.write_registry([self.diagram_entry()])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("both questions.js and diagram.js", err)
        self.assertNotIn("missing from quizzes.js", err)

    def test_main_registry_without_folder_names_both_files(self):
        self.write_registry([self.diagram_entry()])
        code, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("diag-a/questions.js or diag-a/diagram.js", err)

    def test_main_explicit_diagram_file(self):
        path = self.write_diagram("diag-a", valid_diagram())
        folder = os.path.join(self.root, "diag-a")
        code, err = self.run_main([path, folder])
        self.assertEqual(code, 1)
        self.assertIn("image img/d.svg not found", err)
        self.write("diag-a/img/d.svg", "<svg/>")
        self.assertEqual(self.run_main([path, folder]), (0, ""))
        code, err = self.run_main([path, "elsewhere"])
        self.assertEqual(code, 1)
        self.assertIn("elsewhere", err)
        path = self.write("diag-a/diagram.js", "window.QUIZ = {};")
        code, err = self.run_main([path, folder])
        self.assertEqual(code, 1)
        self.assertIn("window.DIAGRAM", err)

    def test_deck_flag_validates_bare_array(self):
        questions = valid_quiz()["decks"][0]["questions"]
        path = self.write("decks/citta.json", json.dumps(questions, ensure_ascii=False))
        self.assertEqual(self.run_main(["--deck", path]), (0, ""))
        dup = copy.deepcopy(questions)
        dup[1]["id"] = dup[0]["id"]
        path = self.write("decks/citta.json", json.dumps(dup))
        code, err = self.run_main(["--deck", path])
        self.assertEqual(code, 1)
        self.assertIn("citta", err)
        self.assertIn("duplicate", err)
        path = self.write("decks/citta.json", json.dumps(questions[:9]))
        code, err = self.run_main(["--deck", path])
        self.assertEqual(code, 1)
        self.assertIn("citta", err)
        self.assertIn("fewer than 10", err)
        path = self.write("decks/citta.json", "[{\"id\": ,]")
        code, err = self.run_main(["--deck", path])
        self.assertEqual(code, 1)
        self.assertIn("citta.json", err)
        self.assertNotIn("Traceback", err)
        code, err = self.run_main(["--deck", os.path.join(self.root, "decks", "nope.json")])
        self.assertEqual(code, 1)
        self.assertIn("nope.json", err)
        code, err = self.run_main(["--deck"])
        self.assertEqual(code, 1)
        self.assertIn("usage", err.lower())

    def test_main_bad_arg_count(self):
        code, err = self.run_main(["only-one"])
        self.assertEqual(code, 1)
        self.assertIn("usage", err.lower())


if __name__ == "__main__":
    unittest.main()
