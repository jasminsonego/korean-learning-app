"""Paste lesson notes, let Claude draft cards, review them, save."""

import uuid
from datetime import date

import streamlit as st

from korean_app import ai, db
from korean_app.ui import card_editor, get_secret

st.title("Add lesson notes")

if message := st.session_state.pop("saved_message", None):
    st.success(message, icon=":material/check_circle:")

api_key = get_secret("ANTHROPIC_API_KEY")
model = get_secret("ANTHROPIC_MODEL", ai.DEFAULT_MODEL)

if not api_key:
    st.info(
        "To turn notes into cards, add your Claude API key: copy "
        "`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, "
        "paste your key into it and restart the app.",
        icon=":material/key:",
    )

draft = st.session_state.get("draft")

# ---------------------------------------------------------------- step 1: paste

if draft is None:
    with st.form("paste"):
        lesson_date = st.date_input("Lesson date", value=date.today(), format="DD.MM.YYYY")
        notes = st.text_area("Your notes, exactly as they are", height=300,
                             placeholder="오늘은 할 일이 많아요! 구두 = heel ...")
        submitted = st.form_submit_button("Turn into cards", type="primary", disabled=not api_key)

    if submitted:
        if not notes.strip():
            st.warning("Paste some notes first.")
        else:
            with st.spinner("Reading your notes and making cards. This takes up to a minute…"):
                try:
                    result = ai.notes_to_cards(notes, api_key=api_key, model=model)
                except ai.NotesError as e:
                    st.error(str(e))
                    st.stop()
            st.session_state.draft = {
                "id": uuid.uuid4().hex[:8],
                "notes": notes,
                "date": lesson_date.isoformat(),
                "summary": result.summary,
                "cards": [ai.draft_to_card(c) for c in result.cards],
            }
            st.rerun()
    st.stop()

# ---------------------------------------------------------------- step 2: review

st.markdown(f"**What this lesson practised:** {draft['summary']}")
uncertain = sum(c["uncertain"] for c in draft["cards"])
corrected = sum(bool(c.get("original")) for c in draft["cards"])
st.caption(
    f"{len(draft['cards'])} cards drafted · {corrected} corrected from your notes · "
    f"{uncertain} need your answer. Check each one, untick what you don't want, then save."
)

with st.form("review"):
    edited = []
    for i, card in enumerate(draft["cards"]):
        with st.container(border=True):
            keep = st.checkbox("Keep this card", value=True, key=f"{draft['id']}_{i}_keep")
            edited.append((keep, card_editor(card, key=f"{draft['id']}_{i}")))
    save = st.form_submit_button("Save cards", type="primary")

if st.button("Discard these drafts"):
    del st.session_state.draft
    st.rerun()

if save:
    to_save = [card for keep, card in edited if keep]
    incomplete = [c for c in to_save if not c["korean"] or not c["english"]]
    if incomplete:
        st.error("Every card you keep needs both Korean and English.")
        st.stop()
    lesson_id = db.add_lesson(draft["notes"], draft["date"], draft["summary"])
    for card in to_save:
        db.add_card(card, lesson_id)
    del st.session_state.draft
    st.session_state.saved_message = f"Saved {len(to_save)} cards. They are waiting for you under Practise."
    st.rerun()
