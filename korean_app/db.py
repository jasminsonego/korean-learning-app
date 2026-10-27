"""Database layer: everything the app stores lives in one SQLite file.

Tables
------
lessons   one row per pasted set of lesson notes
cards     one learnable thing: a word, a sentence or a grammar pattern
items     one way of practising a card (Korean -> English, English -> Korean,
          or a gap sentence). Each item has its own spaced-repetition state.
reviews   one row per answer you give. This is the raw data for the
          progress page.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fsrs import Card as FsrsCard
from fsrs import Rating, Scheduler

# The database lives in data/, which .gitignore keeps off GitHub.
# KOREAN_APP_DB lets the tests use a throwaway database instead.
DB_PATH = Path(os.environ.get("KOREAN_APP_DB", Path(__file__).parent.parent / "data" / "korean.db"))

KINDS = ("word", "sentence", "grammar")
MODES = ("ko_en", "en_ko", "cloze")

# FSRS decides when each item comes back. 0.9 means: schedule the next
# review for when you are predicted to still remember it 90% of the time.
scheduler = Scheduler(desired_retention=0.9)

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id          INTEGER PRIMARY KEY,
    lesson_date TEXT NOT NULL,
    raw_notes   TEXT NOT NULL,
    summary     TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cards (
    id                INTEGER PRIMARY KEY,
    lesson_id         INTEGER REFERENCES lessons(id),
    kind              TEXT NOT NULL CHECK (kind IN ('word', 'sentence', 'grammar')),
    korean            TEXT NOT NULL,
    english           TEXT NOT NULL,
    breakdown         TEXT NOT NULL DEFAULT '[]',  -- JSON list of {korean, english}
    note              TEXT,
    original          TEXT,   -- how it was written in the notes, if the AI corrected it
    correction_reason TEXT,
    example_korean    TEXT,
    example_english   TEXT,
    cloze_sentence    TEXT,   -- Korean sentence with ___ for the gap
    cloze_answer      TEXT,
    cloze_translation TEXT,
    uncertain         INTEGER NOT NULL DEFAULT 0,
    question          TEXT,
    created_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id        INTEGER PRIMARY KEY,
    card_id   INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    mode      TEXT NOT NULL CHECK (mode IN ('ko_en', 'en_ko', 'cloze')),
    fsrs_card TEXT NOT NULL,  -- FSRS state as JSON
    due       TEXT NOT NULL,  -- ISO time in UTC, copied out of fsrs_card for fast queries
    UNIQUE (card_id, mode)
);
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY,
    item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    rating      INTEGER NOT NULL,  -- 1 Again, 2 Hard, 3 Good, 4 Easy
    seconds     REAL,              -- time from showing the card to rating it
    reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_due ON items(due);
CREATE INDEX IF NOT EXISTS idx_reviews_item ON reviews(item_id);
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """Times are stored as text in one fixed format, so that comparing
    the text also compares the times correctly."""
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


@contextmanager
def connect():
    """Open the database, commit if everything worked, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["korean"]
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------- saving

def add_lesson(raw_notes: str, lesson_date: str, summary: str | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO lessons (lesson_date, raw_notes, summary, created_at) VALUES (?, ?, ?, ?)",
            (lesson_date, raw_notes, summary, iso(now_utc())),
        )
        return cur.lastrowid


def modes_for(card: dict) -> list[str]:
    """Which practice directions make sense for this card."""
    modes = ["ko_en"]
    if card["kind"] in ("word", "sentence"):
        modes.append("en_ko")
    if card.get("cloze_sentence") and card.get("cloze_answer"):
        modes.append("cloze")
    return modes


def _new_item_row(card_id: int, mode: str) -> tuple:
    fsrs_card = FsrsCard()
    return (card_id, mode, fsrs_card.to_json(), iso(fsrs_card.due))


CARD_FIELDS = (
    "kind", "korean", "english", "note", "original", "correction_reason",
    "example_korean", "example_english", "cloze_sentence", "cloze_answer",
    "cloze_translation", "uncertain", "question",
)


def add_card(card: dict, lesson_id: int | None = None) -> int:
    """Save one card and create its practice items. Returns the card id."""
    values = [card.get(f) for f in CARD_FIELDS]
    values[CARD_FIELDS.index("uncertain")] = int(bool(card.get("uncertain")))
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO cards (lesson_id, breakdown, created_at, {', '.join(CARD_FIELDS)}) "
            f"VALUES (?, ?, ?, {', '.join('?' * len(CARD_FIELDS))})",
            [lesson_id, json.dumps(card.get("breakdown") or [], ensure_ascii=False), iso(now_utc()), *values],
        )
        card_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO items (card_id, mode, fsrs_card, due) VALUES (?, ?, ?, ?)",
            [_new_item_row(card_id, m) for m in modes_for(card)],
        )
        return card_id


def update_card(card_id: int, card: dict) -> None:
    """Overwrite a card's content. Learning progress is kept; practice
    directions are added or removed if the card changed shape."""
    values = [card.get(f) for f in CARD_FIELDS]
    values[CARD_FIELDS.index("uncertain")] = int(bool(card.get("uncertain")))
    with connect() as conn:
        conn.execute(
            f"UPDATE cards SET breakdown = ?, {', '.join(f + ' = ?' for f in CARD_FIELDS)} WHERE id = ?",
            [json.dumps(card.get("breakdown") or [], ensure_ascii=False), *values, card_id],
        )
        wanted = set(modes_for(card))
        existing = {r["mode"] for r in conn.execute("SELECT mode FROM items WHERE card_id = ?", (card_id,))}
        for mode in existing - wanted:
            conn.execute("DELETE FROM items WHERE card_id = ? AND mode = ?", (card_id, mode))
        conn.executemany(
            "INSERT INTO items (card_id, mode, fsrs_card, due) VALUES (?, ?, ?, ?)",
            [_new_item_row(card_id, m) for m in wanted - existing],
        )


def delete_card(card_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))


# ---------------------------------------------------------------- reading

def _card_from_row(row: sqlite3.Row) -> dict:
    card = dict(row)
    card["breakdown"] = json.loads(card["breakdown"] or "[]")
    card["uncertain"] = bool(card["uncertain"])
    return card


def get_card(card_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return _card_from_row(row) if row else None


def list_cards() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT c.*, l.lesson_date,
                      (SELECT MIN(due) FROM items i WHERE i.card_id = c.id) AS next_due
               FROM cards c LEFT JOIN lessons l ON l.id = c.lesson_id
               ORDER BY c.id DESC"""
        ).fetchall()
    return [_card_from_row(r) for r in rows]


def _local_midnight_utc() -> str:
    """Start of today on this computer's clock, expressed in UTC."""
    local_now = datetime.now().astimezone()
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return iso(midnight.astimezone(timezone.utc))


def new_items_started_today() -> int:
    with connect() as conn:
        return conn.execute(
            """SELECT COUNT(*) FROM (
                   SELECT item_id, MIN(reviewed_at) AS first FROM reviews GROUP BY item_id
               ) WHERE first >= ?""",
            (_local_midnight_utc(),),
        ).fetchone()[0]


def due_queue(new_per_day: int = 15) -> list[dict]:
    """Items to practise now: reviews that are due first, then a limited
    number of brand-new items so a big lesson doesn't flood one day."""
    now = iso(now_utc())
    new_left = max(0, new_per_day - new_items_started_today())
    with connect() as conn:
        seen = conn.execute(
            """SELECT i.*, 0 AS is_new FROM items i
               WHERE i.due <= ? AND EXISTS (SELECT 1 FROM reviews r WHERE r.item_id = i.id)
               ORDER BY i.due""",
            (now,),
        ).fetchall()
        new = conn.execute(
            """SELECT i.*, 1 AS is_new FROM items i
               WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.item_id = i.id)
               -- all Korean -> English first, so you never see a card's
               -- answer right before being asked the reverse direction
               ORDER BY CASE i.mode WHEN 'ko_en' THEN 0 WHEN 'en_ko' THEN 1 ELSE 2 END, i.card_id
               LIMIT ?""",
            (new_left,),
        ).fetchall()
    return [dict(r) for r in seen] + [dict(r) for r in new]


def next_due_time() -> str | None:
    with connect() as conn:
        row = conn.execute(
            """SELECT MIN(due) FROM items i
               WHERE EXISTS (SELECT 1 FROM reviews r WHERE r.item_id = i.id)"""
        ).fetchone()
    return row[0]


def counts() -> dict:
    with connect() as conn:
        return {
            "cards": conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0],
            "items": conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
            "reviews": conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
            "new": conn.execute(
                "SELECT COUNT(*) FROM items i WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.item_id = i.id)"
            ).fetchone()[0],
        }


# ---------------------------------------------------------------- practising

def record_review(item_id: int, rating: int, seconds: float | None = None) -> datetime:
    """Store your answer and let FSRS schedule the item's next review.
    Returns when the item is due next."""
    reviewed_at = now_utc()
    with connect() as conn:
        row = conn.execute("SELECT fsrs_card FROM items WHERE id = ?", (item_id,)).fetchone()
        fsrs_card = FsrsCard.from_json(row["fsrs_card"])
        fsrs_card, _log = scheduler.review_card(fsrs_card, Rating(rating), review_datetime=reviewed_at)
        conn.execute(
            "UPDATE items SET fsrs_card = ?, due = ? WHERE id = ?",
            (fsrs_card.to_json(), iso(fsrs_card.due), item_id),
        )
        conn.execute(
            "INSERT INTO reviews (item_id, rating, seconds, reviewed_at) VALUES (?, ?, ?, ?)",
            (item_id, rating, seconds, iso(reviewed_at)),
        )
    return fsrs_card.due


def reviews_table() -> list[dict]:
    """Every answer you have given, joined with what was being practised.
    One row per review: the starting point for the progress page."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT r.id AS review_id, r.reviewed_at, r.rating, r.seconds,
                      i.id AS item_id, i.mode,
                      c.id AS card_id, c.kind, c.korean, c.english, c.uncertain,
                      l.lesson_date
               FROM reviews r
               JOIN items i ON i.id = r.item_id
               JOIN cards c ON c.id = i.card_id
               LEFT JOIN lessons l ON l.id = c.lesson_id
               ORDER BY r.reviewed_at"""
        ).fetchall()
    return [dict(r) for r in rows]
