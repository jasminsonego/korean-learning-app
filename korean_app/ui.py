"""Small building blocks shared by several pages."""

import os

import streamlit as st

from korean_app.db import KINDS

KIND_LABELS = {"word": "Word", "sentence": "Sentence", "grammar": "Grammar"}
MODE_LABELS = {"ko_en": "Korean → English", "en_ko": "English → Korean",
               "cloze": "Fill the gap", "cloze_2": "Fill the gap"}


def gap_parts(card: dict, mode: str) -> tuple[str, str]:
    """The gap sentence and its answer for gap mode 'cloze' or 'cloze_2'."""
    if mode == "cloze_2":
        return card["cloze2_sentence"], card["cloze2_answer"]
    return card["cloze_sentence"], card["cloze_answer"]


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read a setting from .streamlit/secrets.toml, or from an environment
    variable with the same name. Never hard-code keys in the code."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # no secrets.toml at all
        pass
    return os.environ.get(name, default)


# ---------------------------------------------------------------- breakdown text

def breakdown_to_text(breakdown: list[dict]) -> str:
    return "\n".join(f"{g['korean']} = {g['english']}" for g in breakdown)


def text_to_breakdown(text: str) -> list[dict]:
    glosses = []
    for line in text.splitlines():
        if "=" in line:
            korean, english = line.split("=", 1)
            if korean.strip():
                glosses.append({"korean": korean.strip(), "english": english.strip()})
    return glosses


# ---------------------------------------------------------------- showing a card

def show_answer(card: dict, mode: str) -> None:
    """The back of a card: Korean first, the English a little lower down,
    then the word-by-word breakdown and any notes."""
    if mode in ("cloze", "cloze_2"):
        sentence, answer = gap_parts(card, mode)
        filled = sentence.replace("___", f"**{answer}**", 1)
        st.markdown(f"### {filled}")
        st.write("")
        st.markdown(card.get("cloze_translation") or "")
    else:
        st.markdown(f"### {card['korean']}")
        st.write("")
        st.markdown(card["english"])

    if card["breakdown"]:
        st.write("")
        st.markdown("\n".join(f"- {g['korean']} = {g['english']}" for g in card["breakdown"]))
    if card.get("note"):
        st.caption(card["note"])
    if card.get("example_korean") and mode not in ("cloze", "cloze_2"):
        st.markdown(f"Example: {card['example_korean']}  \n{card.get('example_english') or ''}")
    if card.get("original"):
        st.caption(f"Your notes said “{card['original']}”. {card.get('correction_reason') or ''}")
    if card.get("uncertain"):
        st.warning("Marked as uncertain: worth checking with your tutor.", icon=":material/help:")


# ---------------------------------------------------------------- editing a card

def card_editor(card: dict, key: str) -> dict:
    """Input fields for one card. Returns the card as currently edited.
    `key` must be unique on the page so Streamlit can tell the fields apart."""
    if card.get("uncertain") and card.get("question"):
        st.warning(card["question"], icon=":material/help:")
    if card.get("original"):
        st.caption(f"Corrected from “{card['original']}”. {card.get('correction_reason') or ''}")

    left, right = st.columns([1, 3])
    kind = left.selectbox("Type", KINDS, index=KINDS.index(card["kind"]),
                          format_func=KIND_LABELS.get, key=f"{key}_kind")
    korean = right.text_input("Korean", card["korean"], key=f"{key}_korean")
    english = st.text_input("English", card["english"], key=f"{key}_english")

    with st.expander("Details"):
        breakdown = st.text_area("Word by word (one per line: Korean = English)",
                                 breakdown_to_text(card.get("breakdown") or []), key=f"{key}_breakdown")
        note = st.text_area("Note", card.get("note") or "", key=f"{key}_note")
        example_korean = st.text_input("Example (Korean)", card.get("example_korean") or "", key=f"{key}_exko")
        example_english = st.text_input("Example (English)", card.get("example_english") or "", key=f"{key}_exen")
        cloze_sentence = st.text_input("Gap sentence (use ___ for the gap)", card.get("cloze_sentence") or "",
                                       key=f"{key}_cloze")
        cloze_answer = st.text_input("Gap answer", card.get("cloze_answer") or "", key=f"{key}_clozeans")
        cloze_translation = st.text_input("Gap sentence in English", card.get("cloze_translation") or "",
                                          key=f"{key}_clozeen")
        cloze2_sentence = st.text_input("Second gap, same sentence (sentences only)",
                                        card.get("cloze2_sentence") or "", key=f"{key}_cloze2")
        cloze2_answer = st.text_input("Second gap answer", card.get("cloze2_answer") or "", key=f"{key}_cloze2ans")
        uncertain = st.checkbox("Uncertain, check with tutor", bool(card.get("uncertain")), key=f"{key}_unc")

    return {
        **card,
        "kind": kind,
        "korean": korean.strip(),
        "english": english.strip(),
        "breakdown": text_to_breakdown(breakdown),
        "note": note.strip() or None,
        "example_korean": example_korean.strip() or None,
        "example_english": example_english.strip() or None,
        "cloze_sentence": cloze_sentence.strip() if "___" in cloze_sentence else None,
        "cloze_answer": cloze_answer.strip() or None,
        "cloze_translation": cloze_translation.strip() or None,
        "cloze2_sentence": cloze2_sentence.strip() if "___" in cloze2_sentence else None,
        "cloze2_answer": cloze2_answer.strip() or None,
        "uncertain": uncertain,
    }
