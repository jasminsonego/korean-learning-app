"""Progress and weak spots.

Jasmin's part of v0.1. The data loading is done; the analysis is yours.

`reviews` below is a pandas DataFrame with one row per answer you gave:

    reviewed_at   when (UTC, text)          rating   1 Again, 2 Hard, 3 Good, 4 Easy
    seconds       time to answer            mode     ko_en, en_ko or cloze
    card_id       which card                kind     word, sentence or grammar
    korean        the card's Korean         english  the card's English
    lesson_date   which lesson it came from uncertain True if flagged for the tutor

Ideas, roughly from easy to harder (pandas works much like dplyr):
    1. Overall: how many reviews, and what share were "Again"?
    2. Success rate by direction (mode) and by type (kind). Is English -> Korean
       harder for you than Korean -> English?
    3. Your hardest cards: most "Again" answers, or slowest average answers.
    4. A chart over time: reviews per day, success rate per week.
    5. The "what should I practise most" question: combine the above into one
       recommendation shown at the top of the page.

Useful Streamlit pieces: st.metric, st.dataframe, st.bar_chart, st.line_chart.
"""

import pandas as pd
import streamlit as st

from korean_app import db

st.title("Progress")

reviews = pd.DataFrame(db.reviews_table())

if reviews.empty:
    st.info("Practise a few cards first; your progress will appear here.")
    st.stop()

reviews["reviewed_at"] = pd.to_datetime(reviews["reviewed_at"])
reviews["recalled"] = reviews["rating"] > 1  # Hard, Good and Easy all mean you remembered it

st.info("This page is still being built.", icon=":material/construction:")
st.metric("Answers so far", len(reviews))
st.dataframe(reviews.tail(20), hide_index=True)
