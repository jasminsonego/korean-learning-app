"""Tests for checking the model's answer before it becomes cards. Run with:  python -m unittest

They use fake API responses, so no API key is needed and nothing is sent."""

import unittest
from types import SimpleNamespace

import anthropic
from pydantic import TypeAdapter

from korean_app import ai

LIMIT = f"{ai.MAX_OUTPUT_TOKENS:,}"
COMPLETE = ('{"summary":"Clothes","cards":[{"kind":"word","korean":"구두",'
            '"english":"dress shoes","cloze":{"sentence_with_gap":"___를 사요.",'
            '"answer":"구두","translation":"I buy dress shoes."}}]}')
NO_GAP = ('{"summary":"Clothes","cards":[{"kind":"word","korean":"구두",'
          '"english":"dress shoes"}]}')
CUT_OFF = COMPLETE[:60]  # stops in the middle of a string, like the 9 November error


def fake_response(text: str, stop_reason: str = "end_turn", output_tokens: int = 1234):
    """The parts of an API response that parse_lesson reads."""
    return SimpleNamespace(stop_reason=stop_reason,
                           usage=SimpleNamespace(output_tokens=output_tokens),
                           content=[SimpleNamespace(type="text", text=text)])


class ParseLessonTests(unittest.TestCase):
    def test_complete_answer_becomes_a_lesson(self):
        lesson = ai.parse_lesson(fake_response(COMPLETE))
        self.assertEqual(lesson.cards[0].korean, "구두")

    def test_answer_cut_off_at_the_limit_gives_a_clear_error(self):
        response = fake_response(CUT_OFF, stop_reason="max_tokens", output_tokens=ai.MAX_OUTPUT_TOKENS)
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(response)
        self.assertIn("output limit", str(caught.exception))
        self.assertIn(f"{LIMIT} of {LIMIT}", str(caught.exception))

    def test_other_early_stop_names_the_reason(self):
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(fake_response(CUT_OFF, stop_reason="refusal"))
        self.assertIn("refusal", str(caught.exception))

    def test_broken_json_without_a_stop_reason_is_still_caught(self):
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(fake_response(CUT_OFF))
        self.assertIn("did not match the card format", str(caught.exception))
        self.assertIn(f"1,234 of {LIMIT}", str(caught.exception))


    def test_card_without_a_gap_is_rejected(self):
        """Rule 9: every card has a gap. The schema enforces it."""
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(fake_response(NO_GAP))
        self.assertIn("did not match the card format", str(caught.exception))


class ProgressTests(unittest.TestCase):
    def test_counts_cards_begun_in_a_partial_answer(self):
        self.assertEqual(ai.cards_started('{"summary":"Clothes","cards":['), 0)
        self.assertEqual(ai.cards_started(COMPLETE), 1)
        self.assertEqual(ai.cards_started(COMPLETE[:-3] + ',{"kind":"sentence","korean":"구'), 2)

    def test_quoted_word_kind_inside_a_card_is_not_counted(self):
        text = '{"cards":[{"kind":"word","note":"the English word \\"kind\\" means nice"'
        self.assertEqual(ai.cards_started(text), 1)


class RunStatsTests(unittest.TestCase):
    def test_description_shows_tokens_time_and_effort(self):
        text = ai.RunStats(output_tokens=18240, seconds=161.4, effort="medium",
                           answer_chars=17429, seconds_before_answer=62.0).describe()
        self.assertIn(f"18,240 of {LIMIT} output tokens", text)
        self.assertIn("2 min 41 s", text)
        self.assertIn("first card after 1 min 2 s", text)
        self.assertIn("17,429 characters of cards", text)
        self.assertIn("effort medium", text)

    def test_cut_off_error_shows_how_much_of_the_cards_arrived(self):
        stats = ai.RunStats(output_tokens=ai.MAX_OUTPUT_TOKENS, seconds=300, effort="high",
                            answer_chars=len(CUT_OFF), seconds_before_answer=120)
        response = fake_response(CUT_OFF, stop_reason="max_tokens", output_tokens=ai.MAX_OUTPUT_TOKENS)
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(response, stats)
        self.assertIn(f"{len(CUT_OFF)} characters of cards", str(caught.exception))
        self.assertIn("first card after 2 min 0 s", str(caught.exception))


class OutputFormatTests(unittest.TestCase):
    def test_schema_is_the_one_parse_used_to_send(self):
        """Switching from parse() to create() must not change what the model is asked for."""
        before = anthropic.transform_schema(TypeAdapter(ai.LessonDraft).json_schema())
        self.assertEqual(ai.OUTPUT_FORMAT, {"type": "json_schema", "schema": before})
