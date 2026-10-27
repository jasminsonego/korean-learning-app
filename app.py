"""Entry point. Start the app with:  streamlit run app.py"""

import streamlit as st

from korean_app import db

st.set_page_config(page_title="Korean Practice", page_icon=":material/translate:", layout="centered")
db.init_db()

pages = [
    st.Page("views/practise.py", title="Practise", icon=":material/school:", default=True),
    st.Page("views/add_notes.py", title="Add lesson notes", icon=":material/edit_note:"),
    st.Page("views/cards.py", title="My cards", icon=":material/style:"),
    st.Page("views/progress.py", title="Progress", icon=":material/insights:"),
]
st.navigation(pages).run()
