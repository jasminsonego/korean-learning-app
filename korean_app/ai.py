"""Turn raw lesson notes into draft flashcards with the Claude API.

The model is forced to answer by "calling a tool" whose input must match
the LessonDraft schema below. That way the answer always arrives as
structured data rather than free text, and pydantic checks it.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

DEFAULT_MODEL = "claude-sonnet-5-5"


# ---------------------------------------------------------------- output shape

class Gloss(BaseModel):
    korean: str
    english: str


class Cloze(BaseModel):
    sentence_with_gap: str = Field(description="Korean sentence with exactly one ___ where the answer goes")
    answer: str = Field(description="The Korean word or ending that fills the gap")
    translation: str = Field(description="English translation of the full sentence")


class CardDraft(BaseModel):
    kind: Literal["word", "sentence", "grammar"]
    korean: str = Field(description="Corrected, standard Korean")
    english: str = Field(description="Natural English meaning")
    breakdown: list[Gloss] = Field(default_factory=list, description="Word-by-word glosses, in order")
    note: str | None = Field(None, description="Short usage or grammar explanation, colloquial variants")
    original: str | None = Field(None, description="Exactly how it appeared in the notes, only if you changed it")
    correction_reason: str | None = Field(None, description="Why you changed it, one short sentence")
    example_korean: str | None = None
    example_english: str | None = None
    cloze: Cloze | None = None
    uncertain: bool = Field(False, description="True if you are not sure what the notes meant")
    question: str | None = Field(None, description="Short question to the learner when uncertain")


class LessonDraft(BaseModel):
    summary: str = Field(description="One or two sentences: what this lesson practised")
    cards: list[CardDraft]


# ---------------------------------------------------------------- prompt

SYSTEM_PROMPT = """You turn a Korean learner's raw lesson notes into flashcards.

The learner is an adult beginner taking one-to-one lessons with a tutor. The notes are \
written quickly during or after the lesson. They mix Korean, English, "=" glosses, \
arrows, abbreviations, typos and fragments. Translations are often missing or loose.

Make one card per learnable item:
- kind "word": vocabulary, including compounds and set phrases (있잖아요).
- kind "sentence": full sentences and questions from the lesson.
- kind "grammar": patterns and endings (for example -(으)러 가요).
Include items that appear only in passing, such as a word with no translation.

Rules:
1. Correct mistakes. If the Korean spelling, grammar or the English meaning in the notes is \
wrong or non-standard, the card gets the correct version. Put the text exactly as written \
in "original" and one short sentence in "correction_reason". If a form is colloquial \
(for example 꽁짜), use the standard form and mention the colloquial one in "note".
2. Never guess silently. If you cannot tell what something means or why it is in the notes \
(abbreviations, unclear fragments), still make the card, set "uncertain" to true and ask one \
short question in "question".
3. "breakdown": for sentences and grammar, gloss every word or ending in order. For \
compound words, split them when that helps (요가복 = 요가 + 복).
4. For words and grammar, add one short, natural beginner-level example sentence in polite \
해요 style with its English translation.
5. "cloze": for sentences, and for the example sentence of words and grammar, blank out the \
one most useful word or ending with ___.
6. Do not add vocabulary or topics that are not in the notes. Example sentences are the only \
new material.
7. Write all translations and explanations in English. Keep explanations short.
"""

TOOL = {
    "name": "save_lesson_cards",
    "description": "Save the flashcards made from the lesson notes.",
}


def _inline_refs(schema: dict) -> dict:
    """pydantic puts nested models under $defs and points to them with $ref.
    Replace every $ref with the definition itself, so the schema is
    self-contained and simple."""
    defs = schema.get("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].split("/")[-1]])
            return {k: resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


TOOL["input_schema"] = _inline_refs(LessonDraft.model_json_schema())


# ---------------------------------------------------------------- the call

class NotesError(Exception):
    """Something went wrong turning notes into cards; the message is shown to the user."""


def notes_to_cards(notes: str, api_key: str, model: str = DEFAULT_MODEL) -> LessonDraft:
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=[TOOL],
            tool_choice={"type": "tool", "name": TOOL["name"]},
            messages=[{"role": "user", "content": f"<notes>\n{notes}\n</notes>"}],
        )
    except anthropic.AuthenticationError as e:
        raise NotesError("The API key was rejected. Check ANTHROPIC_API_KEY in .streamlit/secrets.toml.") from e
    except anthropic.APIStatusError as e:
        raise NotesError(f"The Claude API returned an error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise NotesError("Could not reach the Claude API. Check your internet connection.") from e

    if response.stop_reason == "max_tokens":
        raise NotesError("The notes were too long to process in one go. Try pasting them in two parts.")

    tool_calls = [block for block in response.content if block.type == "tool_use"]
    if not tool_calls:
        raise NotesError("The model did not return any cards. Please try again.")
    return LessonDraft.model_validate(tool_calls[0].input)


def draft_to_card(draft: CardDraft) -> dict:
    """Flatten a CardDraft into the dict shape the database expects."""
    card = draft.model_dump(exclude={"cloze"})
    card["breakdown"] = [g.model_dump() for g in draft.breakdown]
    card["cloze_sentence"] = draft.cloze.sentence_with_gap if draft.cloze else None
    card["cloze_answer"] = draft.cloze.answer if draft.cloze else None
    card["cloze_translation"] = draft.cloze.translation if draft.cloze else None
    return card
