"""Streamlit UI for searching the Singapore knowledge base."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.prompts import SYSTEM_PROMPT
from kb.retrieve import retrieve

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    st.set_page_config(page_title="AI Travel Planning Assistant", page_icon="✈️")
    st.title("AI Travel Planning Assistant")
    st.caption("Singapore")

    st.markdown("**Destination:** Singapore")
    st.info(
        "Ask a destination question to search the knowledge base. "
        "Weather and currency tools are not connected yet."
    )

    query = st.chat_input("Ask about Singapore attractions, transport, food, or itineraries")
    if query:
        with st.chat_message("user"):
            st.write(query)
        with st.chat_message("assistant"):
            try:
                result = retrieve(query)
            except FileNotFoundError as exc:
                st.error(str(exc))
                return

            if not result.sufficient:
                st.warning(result.message)
            else:
                st.write("Retrieved knowledge-base passages:")
                for index, chunk in enumerate(result.chunks, start=1):
                    st.markdown(
                        f"**[{index}] {chunk.source_title}** · score `{chunk.score:.3f}`"
                    )
                    st.caption(chunk.section)
                    st.write(chunk.content)
                with st.expander("Sources"):
                    for source in result.sources():
                        st.markdown(f"- [{source['title']}]({source['url']})")

    with st.expander("System prompt"):
        st.code(SYSTEM_PROMPT, language="markdown")
    st.caption(f"Project root: `{ROOT}`")


if __name__ == "__main__":
    main()
