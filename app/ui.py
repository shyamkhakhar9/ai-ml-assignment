"""Streamlit chat UI for the travel assistant."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.prompts import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    st.set_page_config(page_title="AI Travel Planning Assistant", page_icon="✈️")
    st.title("AI Travel Planning Assistant")
    st.caption("Singapore")

    st.markdown("**Destination:** Singapore")
    st.markdown(f"**Project root:** `{ROOT}`")

    with st.expander("System prompt"):
        st.code(SYSTEM_PROMPT, language="markdown")

    st.chat_input("Ask a travel question", disabled=True)


if __name__ == "__main__":
    main()
