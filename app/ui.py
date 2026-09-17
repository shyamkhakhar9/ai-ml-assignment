"""Streamlit chat UI for the RAG + MCP travel assistant."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.agent import AgentTurn, ChatMessage, run_turn
from app.prompts import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[1]


def _render_turn(turn: AgentTurn) -> None:
    st.markdown(turn.answer)
    if turn.tools_used:
        with st.expander("Tools used"):
            for event in turn.tools_used:
                status = "ok" if event.ok else "failed"
                st.markdown(f"- **{event.name}** ({status})")
                if not event.ok:
                    st.caption(str(event.payload.get("error") or "Tool failed."))
    if turn.sources:
        with st.expander("Sources"):
            for source in turn.sources:
                title = source.get("title") or "Source"
                url = source.get("url") or ""
                if url:
                    st.markdown(f"- [{title}]({url})")
                else:
                    st.markdown(f"- {title}")
    if not turn.used_llm:
        st.caption(
            "Answer assembled from the knowledge base and MCP tools. "
            "Set OPENAI_API_KEY to enable the LangChain tool-calling model."
        )


def main() -> None:
    st.set_page_config(page_title="AI Travel Planning Assistant", page_icon="✈️")
    st.title("AI Travel Planning Assistant")
    st.caption("Singapore")
    st.markdown("**Destination:** Singapore")
    st.info(
        "Destination facts come from the knowledge base. "
        "Weather and currency come from MCP tools. "
        "Recommendations are labelled separately from sourced facts."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for item in st.session_state.messages:
        with st.chat_message(item["role"]):
            if item["role"] == "assistant" and item.get("turn"):
                _render_turn(item["turn"])
            else:
                st.markdown(item["content"])

    query = st.chat_input(
        "Plan a trip, ask about Singapore, weather, or a currency conversion"
    )
    if query:
        st.session_state.messages.append({"role": "user", "content": query, "turn": None})
        history = [
            ChatMessage(role=item["role"], content=item["content"])
            for item in st.session_state.messages[:-1]
        ]
        with st.chat_message("user"):
            st.markdown(query)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving knowledge and current information..."):
                turn = run_turn(query, history)
            _render_turn(turn)
        st.session_state.messages.append(
            {"role": "assistant", "content": turn.answer, "turn": turn}
        )

    with st.expander("System prompt"):
        st.code(SYSTEM_PROMPT, language="markdown")
    st.caption(f"Project root: `{ROOT}`")


if __name__ == "__main__":
    main()
