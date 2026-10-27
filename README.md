# Korean Practice

A personal web app for learning Korean, built around my own lesson notes.

After each lesson with my tutor I paste my raw notes into the app. A language model
turns them into flashcards, corrects mistakes in my notes and asks me about anything
unclear. I review the drafts, and the app schedules practice with a spaced
repetition algorithm. Every answer I give is logged, so the app can show where my
weak spots are.

## What it does (v0.1)

- **Notes to cards.** Paste messy notes (Korean, English, half translations, typos).
  Claude drafts cards for words, sentences and grammar patterns, with corrections
  ("your notes said 언제에요; after a vowel it is 언제예요"), word by word
  breakdowns, example sentences and gap sentences. Unclear items are flagged with a
  question.
- **Review before saving.** Every draft card can be edited or dropped. Nothing is
  saved without my approval.
- **Practice in three directions.** Korean to English, English to Korean, and fill
  the gap. Reveal the answer, then rate it Again, Hard, Good or Easy.
- **Scheduling with FSRS.** The [FSRS](https://github.com/open-spaced-repetition/py-fsrs)
  algorithm predicts when I am about to forget an item and schedules it just before.
  New items are limited per day.
- **Progress.** Every review is stored with its rating and answer time, as the basis
  for a weak spots analysis (in progress).

## How it works

```
lesson notes ──► Claude API (structured output) ──► draft cards ──► my review
                                                                       │
             progress page ◄── reviews table ◄── practice ◄── FSRS ◄───┘
```

| Part | File |
|---|---|
| Pages | `app.py`, `views/` |
| AI step: prompt, output schema, API call | `korean_app/ai.py` |
| Database: SQLite schema, scheduling, queries | `korean_app/db.py` |
| Shared UI pieces | `korean_app/ui.py` |
| Tests | `tests/` |

The model must answer through a tool call whose input matches a pydantic schema, so
its output always arrives as validated, structured data.

## Run it locally

Requires Python 3.11 or newer and a [Claude API key](https://console.anthropic.com).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your key
streamlit run app.py
```

Run the tests with `python -m unittest`.

## Privacy

My lesson notes and practice history are stored in `data/korean.db`, which is
excluded from the repository. The API key lives in `.streamlit/secrets.toml`, which
is excluded too.

## Roadmap

- **v0.2** Listening practice with Korean text to speech; typing answers; follow up
  questions from the AI about what a lesson covered
- **v0.3** Related sentences and easily confused words added to cards
- Later: online version, personal website, nicer design

## Built with

Python, Streamlit, SQLite, pandas, the Claude API (Anthropic) and py-fsrs.
Developed with help from Claude as a coding assistant.
