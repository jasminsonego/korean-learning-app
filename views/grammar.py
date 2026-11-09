"""Grammar list: everything that has been explained to you.

The AI receives this list with every lesson and only explains grammar
that isn't on it. New forms are added when you save a lesson; you can also
add or remove forms here by hand."""

import streamlit as st

from korean_app import db

st.title("Grammar list")
st.caption("Grammar on this list is not explained again when you add new lesson notes.")

if message := st.session_state.pop("grammar_message", None):
    st.success(message, icon=":material/check_circle:")

with st.expander("Add a form by hand"):
    with st.form("add_grammar", clear_on_submit=True):
        form = st.text_input("Form", placeholder="-아요/-어요 (present tense, polite)")
        explanation = st.text_input("Short explanation (optional)")
        if st.form_submit_button("Add"):
            if not form.strip():
                st.error("Enter a form first.")
            elif db.add_grammar(form, explanation):
                st.session_state.grammar_message = f"Added {form.strip()}."
                st.rerun()
            else:
                st.warning(f"{form.strip()} is already on the list.")

grammar = db.list_grammar()
if not grammar:
    st.info("The list is empty. Forms are added when you save lesson notes.")
    st.stop()

st.caption(f"{len(grammar)} forms")
for g in grammar:
    left, right = st.columns([6, 1], vertical_alignment="center")
    source = f"lesson {g['lesson_date']}" if g["lesson_date"] else "added by hand"
    lines = [f"**{g['form']}**", g["explanation"], f":gray[{source}]"]
    left.markdown("  \n".join(line for line in lines if line))
    if right.button("Remove", key=f"remove_{g['id']}"):
        db.delete_grammar(g["id"])
        st.session_state.grammar_message = f"Removed {g['form']}."
        st.rerun()
