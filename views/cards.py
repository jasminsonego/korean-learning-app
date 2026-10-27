"""Browse, search, fix and add cards by hand."""

from datetime import datetime

import pandas as pd
import streamlit as st

from korean_app import db
from korean_app.ui import KIND_LABELS, card_editor

st.title("My cards")

if message := st.session_state.pop("cards_message", None):
    st.success(message, icon=":material/check_circle:")

cards = db.list_cards()

# ---------------------------------------------------------------- add by hand

with st.expander("Add a card by hand"):
    with st.form("manual", clear_on_submit=True):
        new_card = card_editor({"kind": "word", "korean": "", "english": ""}, key="manual")
        if st.form_submit_button("Add card"):
            if new_card["korean"] and new_card["english"]:
                db.add_card(new_card)
                st.session_state.cards_message = f"Added “{new_card['korean']}”."
                st.rerun()
            else:
                st.error("A card needs both Korean and English.")

if not cards:
    st.info("No cards yet.")
    st.stop()

# ---------------------------------------------------------------- table

search = st.text_input("Search", placeholder="Korean or English").strip().lower()
shown = [c for c in cards if search in c["korean"].lower() or search in c["english"].lower()]


def flag(card: dict) -> str:
    if card["uncertain"]:
        return "check with tutor"
    if card.get("original"):
        return "corrected"
    return ""


def due_label(iso_time: str | None) -> str:
    if not iso_time:
        return ""
    return f"{datetime.fromisoformat(iso_time).astimezone():%d.%m.%Y %H:%M}"


table = pd.DataFrame({
    "Korean": [c["korean"] for c in shown],
    "English": [c["english"] for c in shown],
    "Type": [KIND_LABELS[c["kind"]] for c in shown],
    "Lesson": [c["lesson_date"] or "by hand" for c in shown],
    "Next due": [due_label(c["next_due"]) for c in shown],
    "Flag": [flag(c) for c in shown],
})
st.caption(f"{len(shown)} of {len(cards)} cards. Click a row to edit it.")
event = st.dataframe(table, hide_index=True, on_select="rerun", selection_mode="single-row")

# ---------------------------------------------------------------- edit selected

if event.selection.rows:
    card = shown[event.selection.rows[0]]
    st.subheader(f"Edit “{card['korean']}”", anchor=False)
    with st.form(f"edit_{card['id']}"):
        edited = card_editor(card, key=f"edit_{card['id']}")
        save = st.form_submit_button("Save changes", type="primary")
    if save:
        db.update_card(card["id"], edited)
        st.session_state.cards_message = "Card updated. Your learning progress on it was kept."
        st.rerun()

    confirm = st.checkbox("I want to delete this card and its practice history", key=f"confirm_{card['id']}")
    if st.button("Delete card", disabled=not confirm):
        db.delete_card(card["id"])
        st.session_state.cards_message = f"Deleted “{card['korean']}”."
        st.rerun()
