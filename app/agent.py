"""LangChain agent for retrieval, MCP tools, and chat memory."""

from __future__ import annotations

from app.prompts import SYSTEM_PROMPT


def build_agent():
    raise NotImplementedError("Agent orchestration is not implemented yet.")


def get_system_prompt() -> str:
    return SYSTEM_PROMPT
