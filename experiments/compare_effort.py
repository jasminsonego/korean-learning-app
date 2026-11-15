"""Compare effort "high" (the model's default) with "medium" on the same lesson notes.

Run from the project folder, with the virtual environment active:

    python experiments/compare_effort.py

Both runs get identical input: the 27 October notes (read from the backup
database), the same tutor comment and an empty grammar list. Nothing is
written to the card database. Each answer is saved with its token count and
duration to data/experiments/ (ignored by Git, like all of data/).

Cost: two runs, each at most about 0.32 dollars (32,000 output tokens).
"""

import json
import sqlite3
import sys
import tomllib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from korean_app import ai  # noqa: E402  (needs the path above)

BACKUP_DB = ROOT / "data" / "korean-backup-before-rerun.db"
OUT_DIR = ROOT / "data" / "experiments"
TUTOR_COMMENTS = "장 is also used on its own in spoken Korean."
KNOWN_GRAMMAR: list[str] = []          # the grammar list is empty right now
EFFORTS = ["high", "medium"]


def lesson_notes() -> tuple[str, str]:
    """The 27 October notes as they were pasted into the app."""
    conn = sqlite3.connect(f"file:{BACKUP_DB}?mode=ro", uri=True)
    lesson_date, notes = conn.execute(
        "SELECT lesson_date, raw_notes FROM lessons WHERE lesson_date = '2026-10-27'").fetchone()
    conn.close()
    return lesson_date, notes


def settings() -> tuple[str, str]:
    secrets = tomllib.loads((ROOT / ".streamlit" / "secrets.toml").read_text())
    return secrets["ANTHROPIC_API_KEY"], secrets.get("ANTHROPIC_MODEL", ai.DEFAULT_MODEL)


def run(effort: str, notes: str, api_key: str, model: str) -> dict:
    print(f"\n[{effort}] running …", flush=True)
    record = {"effort": effort, "model": model, "max_output_tokens": ai.MAX_OUTPUT_TOKENS,
              "tutor_comments": TUTOR_COMMENTS, "known_grammar": KNOWN_GRAMMAR}
    try:
        lesson, stats = ai.notes_to_cards(
            notes, api_key=api_key, model=model, tutor_comments=TUTOR_COMMENTS,
            known_grammar=KNOWN_GRAMMAR, effort=effort,
            on_progress=lambda n: print(f"  writing card {n}", flush=True))
    except ai.NotesError as e:
        print(f"[{effort}] failed: {e}")
        record["error"] = str(e)
        return record
    print(f"[{effort}] done: {len(lesson.cards)} cards, {stats.describe()}")
    record |= {"output_tokens": stats.output_tokens, "seconds": round(stats.seconds, 1),
               "cards": len(lesson.cards), "lesson": lesson.model_dump()}
    return record


def main() -> None:
    lesson_date, notes = lesson_notes()
    api_key, model = settings()
    print(f"Notes from {lesson_date} ({len(notes)} characters), model {model}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    for effort in EFFORTS:
        record = run(effort, notes, api_key, model)
        path = OUT_DIR / f"effort-{stamp}-{effort}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"  saved to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
