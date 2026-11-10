"""Tests for checking the model's answer before it becomes cards. Run with:  python -m unittest

They use fake API responses, so no API key is needed and nothing is sent."""

import unittest
from types import SimpleNamespace

import anthropic
from pydantic import TypeAdapter

from korean_app import ai

COMPLETE = ('{"summary":"Clothes","cards":[{"kind":"word","korean":"구두",'
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
        response = fake_response(CUT_OFF, stop_reason="max_tokens", output_tokens=16000)
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(response)
        self.assertIn("output limit", str(caught.exception))
        self.assertIn("16,000 of 16,000", str(caught.exception))

    def test_other_early_stop_names_the_reason(self):
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(fake_response(CUT_OFF, stop_reason="refusal"))
        self.assertIn("refusal", str(caught.exception))

    def test_broken_json_without_a_stop_reason_is_still_caught(self):
        with self.assertRaises(ai.NotesError) as caught:
            ai.parse_lesson(fake_response(CUT_OFF))
        self.assertIn("did not match the card format", str(caught.exception))
        self.assertIn("1,234 of 16,000", str(caught.exception))


class OutputFormatTests(unittest.TestCase):
    def test_schema_is_the_one_parse_used_to_send(self):
        """Switching from parse() to create() must not change what the model is asked for."""
        before = anthropic.transform_schema(TypeAdapter(ai.LessonDraft).json_schema())
        self.assertEqual(ai.OUTPUT_FORMAT, {"type": "json_schema", "schema": before})
