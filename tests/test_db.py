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
SENTENCE = {"kind": "sentence", "korean": "구두 신었어요?", "english": "Did you wear dress shoes?",
            "cloze_sentence": "구두 ___?", "cloze_answer": "신었어요", "cloze_translation": "Did you wear dress shoes?"}
GRAMMAR = {"kind": "grammar", "korean": "-(으)러 가요", "english": "go (somewhere) in order to ..."}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        db.DB_PATH.unlink(missing_ok=True)
        db.init_db()

    def test_practice_directions_depend_on_card_kind(self):
        self.assertEqual(db.modes_for(WORD), ["ko_en", "en_ko"])
        self.assertEqual(db.modes_for(SENTENCE), ["ko_en", "en_ko", "cloze"])
        self.assertEqual(db.modes_for(GRAMMAR), ["ko_en"])

    def test_new_cards_are_queued_with_daily_limit(self):
        lesson = db.add_lesson("notes", "2026-10-27")
        for card in (WORD, SENTENCE, GRAMMAR):
            db.add_card(card, lesson)
        self.assertEqual(db.counts()["items"], 6)
        self.assertEqual(len(db.due_queue(new_per_day=4)), 4)

    def test_review_moves_item_into_the_future(self):
        db.add_card(WORD)
        item = db.due_queue()[0]
        due = db.record_review(item["id"], rating=3, seconds=4.2)
        self.assertGreater(due, db.now_utc())
        self.assertNotIn(item["id"], [i["id"] for i in db.due_queue()])
        self.assertEqual(db.new_items_started_today(), 1)
        rows = db.reviews_table()
        self.assertEqual((rows[0]["korean"], rows[0]["rating"], rows[0]["mode"]), ("구두", 3, "ko_en"))

    def test_editing_a_card_keeps_progress_and_updates_directions(self):
        card_id = db.add_card(WORD)
        first = db.due_queue()[0]
        db.record_review(first["id"], rating=3)
        db.update_card(card_id, {**WORD, "kind": "grammar"})  # grammar has no en_ko
        self.assertEqual(db.counts()["items"], 1)
        self.assertEqual(db.counts()["reviews"], 1)

    def test_deleting_a_card_removes_its_items_and_reviews(self):
        card_id = db.add_card(SENTENCE)
        db.record_review(db.due_queue()[0]["id"], rating=1)
        db.delete_card(card_id)
        self.assertEqual(db.counts(), {"cards": 0, "items": 0, "reviews": 0, "new": 0})


if __name__ == "__main__":
    unittest.main()
