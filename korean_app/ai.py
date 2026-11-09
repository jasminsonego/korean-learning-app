"""Turn raw lesson notes into draft flashcards with the Claude API.

The request uses structured outputs: the API is given the LessonDraft
schema below and the model's answer is constrained to match it. The answer
therefore always arrives as structured data rather than free text, and the
SDK turns it straight into a LessonDraft object.
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


class GrammarPoint(BaseModel):
    form: str = Field(description="The ending, particle or pattern, e.g. -(으)ㄹ (modifier)")
    explanation: str = Field(description="One short sentence: what it does")


class CardDraft(BaseModel):
    kind: Literal["word", "sentence", "grammar"]
    korean: str = Field(description="Correct, standard Korean. Word parts start with a hyphen (-화)")
    english: str = Field(description="Natural English meaning; '(guess) ...' if unsure")
    breakdown: list[Gloss] = Field(
        default_factory=list, description="Glosses in order; particles as separate entries (rule 6)")
    note: str | None = Field(None, description="Short usage or grammar explanation, colloquial variants")
    original: str | None = Field(
        None, description="The Korean or the meaning as written in the notes, only if it was wrong (rule 1)")
    correction_reason: str | None = Field(None, description="Why it was wrong, one short sentence")
    example_korean: str | None = None
    example_english: str | None = None
    cloze: Cloze | None = None
    second_cloze: Cloze | None = Field(
        None, description="Sentences only: the same sentence with a different gap (rule 9)")
    uncertain: bool = Field(False, description="True if you are not sure what the notes meant")
    question: str | None = Field(None, description="Short question to the learner when uncertain")


class LessonDraft(BaseModel):
    summary: str = Field(description="One or two sentences: what this lesson practised")
    cards: list[CardDraft]
    new_grammar: list[GrammarPoint] = Field(
        default_factory=list, description="Grammar explained in this lesson that was not on the known list (rule 7)")


# ---------------------------------------------------------------- prompt

SYSTEM_PROMPT = """You turn a Korean learner's raw lesson notes into flashcards.

The learner is an adult beginner taking one-to-one lessons with a Korean tutor. The tutor \
writes the notes quickly during the lesson; her English is not native. The notes mix Korean, \
English, "=" glosses, arrows, abbreviations, typos and fragments. Translations are often \
missing or loose.

You receive:
- <notes>: the raw lesson notes.
- <tutor_comments> (optional): things the tutor said that are not in the notes, written down \
by the learner. Treat them as reliable. If they disagree with your general knowledge, follow \
them and do not mark them as uncertain.
- <known_grammar>: grammar the learner has already had explained. It may be empty.

Make one card per learnable item:
- kind "word": vocabulary, including compounds and set phrases (있잖아요).
- kind "sentence": full sentences and questions from the lesson.
- kind "grammar": patterns and endings (for example -(으)러 가요), and word parts (rule 4).
Include items that appear only in passing, such as a word with no translation.

Rules:
1. Corrections. If the Korean (spelling, spacing, grammar, word choice) or the meaning given \
in the notes is wrong, the card gets the correct version: put what the notes said in \
"original" and one short sentence in "correction_reason". Use "original" only for these real \
mistakes. Fix English typos, grammar, capitals and punctuation silently, without "original". \
If the notes were right but incomplete, add the missing information in "note" instead. If a \
form is colloquial (for example 꽁짜), use the standard form and mention the colloquial one in \
"note".
2. Uncertainty. If you cannot tell what something means or why it is in the notes \
(abbreviations, unclear fragments), still make the card, keep the Korean as written, write \
your best guess as the English starting with "(guess) ", set "uncertain" to true and ask one \
short question in "question". Do not mark it as a correction.
3. Translations. Translate as a native speaker would understand the Korean in context. For \
example, with verbs of wearing the past tense usually describes what someone has on now: \
구두 신었어요? = Are you wearing dress shoes?
4. Word parts. When the notes explain part of a word (for example 화 in 운동화, 복 in 한복):
- If the part is also used as a word on its own in everyday Korean with that meaning, make a \
normal kind "word" card.
- If it only appears inside compounds, make a kind "grammar" card with a hyphen (-화), the \
English as "<meaning> (in compounds)", and list common compounds in "note". Mention in "note" \
if the same syllable means something else on its own (화 alone = anger).
5. Telling cards apart. The English side is also used as a prompt to answer in Korean. If two \
cards from these notes have the same or nearly the same English meaning (무료 and 공짜 both \
"free"), add a short hint in brackets so each has exactly one right answer: \
"free of charge (formal)", "free (casual)".
6. "breakdown", for sentences and grammar, in order:
- Write particles as their own entry with a hyphen and their function, never glued to the \
noun: 오늘 = today, -은 = topic marker, 일 = thing(s), work, -이 = subject marker.
- For conjugated verbs and adjectives, put the dictionary form in brackets after the Korean: \
"많아요 (많다)" = there are many; "할 (하다)" = to do.
- For compound words, split them when that helps (요가복 = 요가 + 복).
7. Grammar explanations. For every ending, conjugation or pattern used in the cards that is \
not on <known_grammar> (treat variants such as -아요/-어요 as the same form), explain once in \
this lesson, in the "note" of the first card where it appears: what the form does and why it \
is used here, in one or two short sentences. Example for 할 일: "-(으)ㄹ turns 하다 into a \
describing form for the noun: 할 일 = things to do." Add each such form to "new_grammar". Do \
not explain forms that are on <known_grammar>, and do not explain the same form twice.
8. Examples. For words and grammar, add one short, natural beginner-level example sentence in \
polite 해요 style with its English translation. It must show the most typical real situation \
for the item. For expressions whose use depends on the situation (있잖아요, 잘됐다), say in \
"note" when people use it.
9. Gaps. "cloze": for sentences, blank out the most useful word or ending with ___. If a \
second part of the same sentence is equally worth practising, add "second_cloze": the same \
sentence with that other part blanked. For words and grammar, use the example sentence and \
blank out the card's own word, part or ending, never another word; no second_cloze.
10. Look-alikes. If part of a word looks like something the learner may already know but is \
something else, explain it in "note". Example: in 년도 (年度, a counted or calendar year) the \
도 is part of the Sino-Korean word, not the particle 도 (also); at the start of a word it is \
written 연도.
11. Do not add vocabulary or topics that are not in the notes. Example sentences are the only \
new material.
12. Write all translations and explanations in English. Keep explanations short.
"""


def build_user_message(notes: str, tutor_comments: str, known_grammar: list[str]) -> str:
    """Everything the model needs for one lesson, in clearly labelled parts."""
    known = "\n".join(f"- {form}" for form in known_grammar) or "(empty)"
    parts = [f"<notes>\n{notes}\n</notes>"]
    if tutor_comments.strip():
        parts.append(f"<tutor_comments>\n{tutor_comments}\n</tutor_comments>")
    parts.append(f"<known_grammar>\n{known}\n</known_grammar>")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- the call

class NotesError(Exception):
    """Something went wrong turning notes into cards; the message is shown to the user."""


def notes_to_cards(notes: str, api_key: str, model: str = DEFAULT_MODEL,
                   tutor_comments: str = "", known_grammar: list[str] | None = None) -> LessonDraft:
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": build_user_message(notes, tutor_comments, known_grammar or [])}],
            output_format=LessonDraft,
        )
    except anthropic.AuthenticationError as e:
        raise NotesError("The API key was rejected. Check ANTHROPIC_API_KEY in .streamlit/secrets.toml.") from e
    except anthropic.APIStatusError as e:
        raise NotesError(f"The Claude API returned an error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise NotesError("Could not reach the Claude API. Check your internet connection.") from e

    if response.stop_reason == "max_tokens":
        raise NotesError("The notes were too long to process in one go. Try pasting them in two parts.")
    if response.parsed_output is None:
        raise NotesError(f"The model did not return any cards (stop reason: {response.stop_reason}). Please try again.")
    return response.parsed_output


def draft_to_card(draft: CardDraft) -> dict:
    """Flatten a CardDraft into the dict shape the database expects."""
    card = draft.model_dump(exclude={"cloze", "second_cloze"})
    card["breakdown"] = [g.model_dump() for g in draft.breakdown]
    card["cloze_sentence"] = draft.cloze.sentence_with_gap if draft.cloze else None
    card["cloze_answer"] = draft.cloze.answer if draft.cloze else None
    card["cloze_translation"] = draft.cloze.translation if draft.cloze else None
    second = draft.second_cloze if draft.kind == "sentence" else None
    card["cloze2_sentence"] = second.sentence_with_gap if second else None
    card["cloze2_answer"] = second.answer if second else None
    return card
