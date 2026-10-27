"""Practise due cards: see the front, think of the answer, reveal, rate."""

import time
from datetime import datetime

import streamlit as st

from korean_app import db
from korean_app.ui import KIND_LABELS, MODE_LABELS, show_answer

NEW_PER_DAY = 15
RATINGS = [(1, "Again"), (2, "Hard"), (3, "Good"), (4, "Easy")]

st.title("Practise")

queue = db.due_queue(new_per_day=NEW_PER_DAY)

if not queue:
    totals = db.counts()
    if totals["cards"] == 0:
        st.info("No cards yet. Add your first lesson notes to get started.", icon=":material/edit_note:")
        st.page_link("views/add_notes.py", label="Add lesson notes", icon=":material/arrow_forward:")
    else:
        st.success("All done for now.", icon=":material/check_circle:")
        next_due = db.next_due_time()
        if next_due:
            when = datetime.fromisoformat(next_due).astimezone()
            st.caption(f"Next card is due {when:%d.%m.%Y at %H:%M}.")
        if totals["new"]:
            st.caption(f"{totals['new']} new items are waiting; up to {NEW_PER_DAY} new ones are introduced per day.")
    st.stop()

item = queue[0]
card = db.get_card(item["card_id"])

# Remember when this item was first shown, to measure how long the answer took.
if st.session_state.get("current_item") != item["id"]:
    st.session_state.current_item = item["id"]
    st.session_state.shown_at = time.time()
    st.session_state.revealed = False

new_count = sum(i["is_new"] for i in queue)
st.caption(f"{len(queue) - new_count} to review · {new_count} new")


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
        st.header(card["cloze_sentence"], anchor=False)
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
