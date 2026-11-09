"""Practise due cards: see the front, think of the answer, reveal, rate."""

import time
from datetime import datetime

import streamlit as st

from korean_app import db
from korean_app.ui import KIND_LABELS, MODE_LABELS, gap_parts, show_answer

RATINGS = [(1, "Again"), (2, "Hard"), (3, "Good"), (4, "Easy")]


def local_time(iso_time: str) -> datetime:
    return datetime.fromisoformat(iso_time).astimezone()


# ---------------------------------------------------------------- batch size setting

with st.sidebar:
    batch_size = st.number_input(
        "New cards per batch", min_value=1, max_value=1000, step=5,
        value=int(db.get_setting("batch_size")),
        help="How many new items you start at once. The next batch is offered "
             "when the current one is done for today.",
    )
    if batch_size != int(db.get_setting("batch_size")):
        db.set_setting("batch_size", batch_size)

st.title("Practise")

# "Continue now" sets this, so items scheduled for later today show up immediately.
early = st.session_state.get("early", False)
queue = db.due_queue(include_later_today=early)

# ---------------------------------------------------------------- nothing to practise right now

if not queue:
    st.session_state.early = False
    totals = db.counts()
    later_count, later_first = db.later_today()
    waiting = db.waiting_new_count()

    if totals["cards"] == 0:
        st.info("No cards yet. Add your first lesson notes to get started.", icon=":material/edit_note:")
        st.page_link("views/add_notes.py", label="Add lesson notes", icon=":material/arrow_forward:")

    elif later_count:
        st.info(
            f"{later_count} {'card comes' if later_count == 1 else 'cards come'} back later today, "
            f"the next at {local_time(later_first):%H:%M}.",
            icon=":material/schedule:",
        )
        if st.button("Continue now", type="primary"):
            st.session_state.early = True
            st.rerun()

    elif waiting:
        if totals["reviews"]:
            st.success("Batch done: everything you practised is scheduled for another day.",
                       icon=":material/check_circle:")
        next_size = min(batch_size, waiting)
        if st.button(f"Start next batch ({next_size} new)", type="primary"):
            db.start_batch(next_size)
            st.rerun()
        st.caption(f"{waiting} new items waiting in total.")

    else:
        st.success("All done for now.", icon=":material/check_circle:")
        next_due = db.next_due_time()
        if next_due:
            st.caption(f"Next card is due {local_time(next_due):%d.%m.%Y at %H:%M}.")
    st.stop()

item = queue[0]
card = db.get_card(item["card_id"])

# Remember when this item was first shown, to measure how long the answer took.
if st.session_state.get("current_item") != item["id"]:
    st.session_state.current_item = item["id"]
    st.session_state.shown_at = time.time()
    st.session_state.revealed = False

new_count = sum(i["is_new"] for i in queue)
st.caption(f"{len(queue) - new_count} to review · {new_count} new in this batch")


def rate(item_id: int, rating: int) -> None:
    seconds = round(time.time() - st.session_state.shown_at, 1)
    db.record_review(item_id, rating, seconds)
    st.session_state.current_item = None


# ---------------------------------------------------------------- front

with st.container(border=True):
    st.caption(f"{MODE_LABELS[item['mode']]} · {KIND_LABELS[card['kind']]}" + (" · new" if item["is_new"] else ""))
    if item["mode"] == "ko_en":
        st.header(card["korean"], anchor=False)
    elif item["mode"] == "en_ko":
        st.header(card["english"], anchor=False)
    else:
        st.header(gap_parts(card, item["mode"])[0], anchor=False)
        st.caption(card.get("cloze_translation") or "")

    if not st.session_state.revealed:
        if st.button("Show answer", type="primary", width="stretch"):
            st.session_state.revealed = True
            st.rerun()
    else:
        st.divider()
        show_answer(card, item["mode"])

# ---------------------------------------------------------------- rating

if st.session_state.revealed:
    st.caption("How well did you know it?")
    for column, (value, label) in zip(st.columns(4), RATINGS):
        column.button(label, key=f"rate_{value}", on_click=rate, args=(item["id"], value), width="stretch")
