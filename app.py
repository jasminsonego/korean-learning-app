import streamlit as st

st.title("Korean Practice")

# A few sample cards. Later these will come from your Preply notes.
cards = [
    {"korean": "안녕하세요", "english": "Hello"},
    {"korean": "감사합니다", "english": "Thank you"},
    {"korean": "물 주세요", "english": "Water, please"},
]

# Streamlit reruns the whole script on every click,
# so we store "which card am I on" in session_state.
if "index" not in st.session_state:
    st.session_state.index = 0

card = cards[st.session_state.index]
st.header(card["korean"])

if st.button("Show answer"):
    st.write(card["english"])

if st.button("Next card"):
    st.session_state.index = (st.session_state.index + 1) % len(cards)
    st.rerun()