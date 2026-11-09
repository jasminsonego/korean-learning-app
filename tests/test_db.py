"""Tests for the database layer. Run with:  python -m unittest

They use a temporary database, so your real data is never touched."""

import os
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ["KOREAN_APP_DB"] = str(Path(_tmp.name) / "test.db")

from korean_app import db  # noqa: E402  (must come after setting the env var)

WORD = {"kind": "word", "korean": "구두", "english": "dress shoes",
        "breakdown": [{"korean": "구두", "english": "dress shoes"}]}
SENTENCE = {"kind": "sentence", "korean": "구두 신었어요?", "english": "Are you wearing dress shoes?",
            "cloze_sentence": "구두 ___?", "cloze_answer": "신었어요", "cloze_translation": "Are you wearing dress shoes?"}
TWO_GAPS = {**SENTENCE, "cloze2_sentence": "___ 신었어요?", "cloze2_answer": "구두"}
GRAMMAR = {"kind": "grammar", "korean": "-(으)러 가요", "english": "go (somewhere) in order to ..."}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        db.DB_PATH.unlink(missing_ok=True)
        db.init_db()

    def test_practice_directions_depend_on_card_kind(self):
        self.assertEqual(db.modes_for(WORD), ["ko_en", "en_ko"])
        self.assertEqual(db.modes_for(SENTENCE), ["ko_en", "en_ko", "cloze"])
        self.assertEqual(db.modes_for(GRAMMAR), ["ko_en"])
        self.assertEqual(db.modes_for(TWO_GAPS), ["ko_en", "en_ko", "cloze", "cloze_2"])
        self.assertEqual(db.modes_for({**TWO_GAPS, "kind": "word"}), ["ko_en", "en_ko", "cloze"])

    def test_grammar_list_ignores_duplicates_and_survives_lesson_deletion(self):
        lesson = db.add_lesson("notes", "2026-11-09", tutor_comments="장 is used alone")
        self.assertTrue(db.add_grammar("-(으)ㄹ (modifier)", "makes a verb describe a noun", lesson))
        self.assertFalse(db.add_grammar("-(으)ㄹ (modifier)"))
        self.assertEqual(db.known_grammar_forms(), ["-(으)ㄹ (modifier)"])
        with db.connect() as conn:
            conn.execute("DELETE FROM lessons WHERE id = ?", (lesson,))
        self.assertEqual(db.list_grammar()[0]["lesson_id"], None)
        db.delete_grammar(db.list_grammar()[0]["id"])
        self.assertEqual(db.list_grammar(), [])

    def test_new_cards_wait_until_a_batch_is_started(self):
        lesson = db.add_lesson("notes", "2026-10-27")
        for card in (WORD, SENTENCE, GRAMMAR):
            db.add_card(card, lesson)
        self.assertEqual(db.counts()["items"], 6)
        self.assertEqual(db.due_queue(), [])
        self.assertEqual(db.waiting_new_count(), 6)
        self.assertEqual(db.start_batch(4), 4)
        queue = db.due_queue()
        self.assertEqual(len(queue), 4)
        self.assertEqual([i["mode"] for i in queue[:3]], ["ko_en"] * 3)  # Korean -> English first
        self.assertEqual(db.waiting_new_count(), 2)

    def test_items_coming_back_later_today_can_be_practised_early(self):
        db.add_card(WORD)
        db.start_batch(1)
        item = db.due_queue()[0]
        db.record_review(item["id"], rating=3)  # a new item comes back in about 10 minutes
        count, _first = db.later_today()
        if count == 0:
            self.skipTest("run just before midnight: the item comes back tomorrow")
        self.assertEqual(count, 1)
        self.assertEqual(db.due_queue(), [])
        self.assertEqual([i["id"] for i in db.due_queue(include_later_today=True)], [item["id"]])

    def test_settings_have_defaults_and_can_be_changed(self):
        self.assertEqual(db.get_setting("batch_size"), "15")
        db.set_setting("batch_size", 40)
        db.set_setting("batch_size", 25)
        self.assertEqual(db.get_setting("batch_size"), "25")

    def test_old_database_gets_the_batch_column(self):
        db.DB_PATH.unlink()
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH)
        conn.executescript(db.SCHEMA.replace("    batch_started TEXT,       -- when this new item was put into a batch; NULL = still waiting\n", ""))
        conn.close()
        db.init_db()
        db.add_card(WORD)
        self.assertEqual(db.start_batch(5), 2)

    def test_review_moves_item_into_the_future(self):
        db.add_card(WORD)
        db.start_batch(15)
        item = db.due_queue()[0]
        due = db.record_review(item["id"], rating=3, seconds=4.2)
        self.assertGreater(due, db.now_utc())
        self.assertNotIn(item["id"], [i["id"] for i in db.due_queue()])
        rows = db.reviews_table()
        self.assertEqual((rows[0]["korean"], rows[0]["rating"], rows[0]["mode"]), ("구두", 3, "ko_en"))

    def test_editing_a_card_keeps_progress_and_updates_directions(self):
        card_id = db.add_card(WORD)
        db.start_batch(15)
        first = db.due_queue()[0]
        db.record_review(first["id"], rating=3)
        db.update_card(card_id, {**WORD, "kind": "grammar"})  # grammar has no en_ko
        self.assertEqual(db.counts()["items"], 1)
        self.assertEqual(db.counts()["reviews"], 1)

    def test_deleting_a_card_removes_its_items_and_reviews(self):
        card_id = db.add_card(SENTENCE)
        db.start_batch(15)
        db.record_review(db.due_queue()[0]["id"], rating=1)
        db.delete_card(card_id)
        self.assertEqual(db.counts(), {"cards": 0, "items": 0, "reviews": 0, "new": 0})


if __name__ == "__main__":
    unittest.main()
