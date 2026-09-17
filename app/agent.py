"""LangChain agent: destination retrieval, MCP tools, and chat memory."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

from app.intent import route_question
from app.prompts import SYSTEM_PROMPT
from app.tools import (
    convert_currency,
    parse_tool_payload,
    search_destination_knowledge,
    weather_forecast,
)
from kb.paths import ROOT

load_dotenv(ROOT / ".env")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOOL_ROUNDS = 6
MEMORY_TURNS = 8


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ToolEvent:
    name: str
    ok: bool
    payload: dict[str, Any]


@dataclass
class AgentTurn:
    answer: str
    sources: list[dict[str, str]] = field(default_factory=list)
    tools_used: list[ToolEvent] = field(default_factory=list)
    used_llm: bool = False


def llm_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _record_tool(name: str, raw: str, events: list[ToolEvent], sources: list[dict[str, str]]) -> None:
    payload = parse_tool_payload(raw)
    events.append(ToolEvent(name=name, ok=bool(payload.get("ok")), payload=payload))
    for source in payload.get("sources") or []:
        if source not in sources:
            sources.append(source)


def _build_langchain_tools():
    from langchain_core.tools import StructuredTool

    return [
        StructuredTool.from_function(
            search_destination_knowledge,
            name="search_destination_knowledge",
            description=(
                "Search the Singapore travel knowledge base for attractions, "
                "neighbourhoods, transport, food, culture, and itineraries."
            ),
        ),
        StructuredTool.from_function(
            weather_forecast,
            name="weather_forecast",
            description=(
                "MCP weather tool. Current conditions and a daily forecast. "
                "Arguments: location (default Singapore), days (1-7)."
            ),
        ),
        StructuredTool.from_function(
            convert_currency,
            name="convert_currency",
            description=(
                "MCP currency tool. Convert amount between ISO codes such as "
                "INR, SGD, USD. Arguments: amount, from_currency, to_currency."
            ),
        ),
    ]


def _run_with_llm(question: str, history: list[ChatMessage]) -> AgentTurn:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_openai import ChatOpenAI

    tools = _build_langchain_tools()
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0).bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    recent = history[-(MEMORY_TURNS * 2) :]
    for item in recent:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=question))

    events: list[ToolEvent] = []
    sources: list[dict[str, str]] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = llm.invoke(messages)
        messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            answer = (response.content or "").strip()
            if not answer:
                answer = "I could not produce an answer from the available tools."
            return AgentTurn(answer=answer, sources=sources, tools_used=events, used_llm=True)
        for call in tool_calls:
            name = call["name"]
            args = call.get("args") or {}
            tool = tool_map.get(name)
            if tool is None:
                raw = json.dumps({"ok": False, "error": f"Unknown tool '{name}'."})
            else:
                raw = tool.invoke(args)
            _record_tool(name, str(raw), events, sources)
            messages.append(
                ToolMessage(content=str(raw), tool_call_id=call["id"], name=name)
            )

    return AgentTurn(
        answer="Stopped after the maximum number of tool calls without a final answer.",
        sources=sources,
        tools_used=events,
        used_llm=True,
    )


def _fallback_answer(question: str, history: list[ChatMessage]) -> AgentTurn:
    routed = route_question(question)
    events: list[ToolEvent] = []
    sources: list[dict[str, str]] = []
    sections: list[str] = []

    if any("family" in item.content.lower() for item in history if item.role == "user"):
        question = f"{question} (keep this family-friendly based on earlier preference)"

    if routed.use_rag or (not routed.use_weather and not routed.use_currency):
        queries = [question]
        if routed.use_weather:
            queries.append(
                "Singapore indoor attractions museums conservatories temples "
                "and outdoor gardens neighbourhoods itinerary"
            )
        seen_passages: list[dict] = []
        for query in queries:
            raw = search_destination_knowledge(query)
            _record_tool("search_destination_knowledge", raw, events, sources)
            payload = parse_tool_payload(raw)
            if payload.get("ok"):
                seen_passages.extend(payload.get("passages") or [])
        sections.append("## Knowledge base")
        if not seen_passages:
            sections.append("The knowledge base did not return enough destination facts.")
        else:
            for passage in seen_passages[:8]:
                sections.append(
                    f"[{passage['id']}] {passage['source_title']} "
                    f"({passage['source_url']})\n{passage['content']}"
                )

    weather_payload = None
    if routed.use_weather:
        raw = weather_forecast(routed.weather_location, routed.weather_days)
        _record_tool("weather_forecast", raw, events, sources)
        weather_payload = parse_tool_payload(raw)
        sections.append("## MCP (weather)")
        if not weather_payload.get("ok"):
            sections.append(
                "The weather tool failed. A forecast will not be invented. "
                f"{weather_payload.get('error') or ''}"
            )
        else:
            current = weather_payload.get("current") or {}
            sections.append(
                f"Current information from the weather tool "
                f"({weather_payload.get('source')}): {current.get('condition')}, "
                f"{current.get('temperature_c')}°C."
            )
            for day in weather_payload.get("daily") or []:
                indoor = "indoor options preferred" if day.get("prefer_indoor") else "outdoor options suitable"
                sections.append(
                    f"- {day.get('date')}: {day.get('condition')}, "
                    f"{day.get('temp_min_c')}–{day.get('temp_max_c')}°C, "
                    f"rain {day.get('rain_probability_pct')}% ({indoor})."
                )

    if routed.use_currency:
        sections.append("## MCP (currency)")
        if routed.amount is None or not routed.from_currency or not routed.to_currency:
            sections.append(
                "A conversion was requested, but the amount or currency pair "
                "could not be read. No rate was invented."
            )
        else:
            raw = convert_currency(routed.amount, routed.from_currency, routed.to_currency)
            _record_tool("convert_currency", raw, events, sources)
            fx = parse_tool_payload(raw)
            if not fx.get("ok"):
                sections.append(
                    "The currency tool failed. A rate will not be invented. "
                    f"{fx.get('error') or ''}"
                )
            else:
                sections.append(
                    f"Current information from the currency tool ({fx.get('source')}): "
                    f"{fx.get('amount')} {fx.get('from_currency')} = "
                    f"{fx.get('converted_amount')} {fx.get('to_currency')} "
                    f"on {fx.get('date')}."
                )

    if weather_payload and weather_payload.get("ok") and any(
        event.name == "search_destination_knowledge" and event.ok for event in events
    ):
        sections.append("## Recommendation")
        sections.append(
            "Generated plan: match retrieved indoor places (conservatories, "
            "museums, temples) to days marked prefer-indoor in the forecast, "
            "and outdoor neighbourhoods, gardens, or parks to drier days. "
            "This itinerary is a suggestion built from the knowledge base and "
            "the MCP forecast, not a booked schedule."
        )
        for day in weather_payload.get("daily") or []:
            kind = "indoor-leaning" if day.get("prefer_indoor") else "outdoor-leaning"
            sections.append(f"- {day.get('date')}: {kind} day because of {day.get('condition')}.")

    answer = "\n\n".join(section.strip() for section in sections if section.strip())
    return AgentTurn(answer=answer, sources=sources, tools_used=events, used_llm=False)


def run_turn(question: str, history: list[ChatMessage] | None = None) -> AgentTurn:
    history = history or []
    if llm_configured():
        return _run_with_llm(question, history)
    return _fallback_answer(question, history)


def get_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_agent():
    if not llm_configured():
        raise RuntimeError(
            "Set OPENAI_API_KEY in .env to build the LangChain tool-calling agent. "
            "Without a key, run_turn() still answers using retrieval and MCP tools."
        )
    return _build_langchain_tools()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the travel assistant")
    parser.add_argument("question", nargs="+")
    args = parser.parse_args()
    question = " ".join(args.question)
    turn = run_turn(question)
    print(turn.answer)
    if turn.tools_used:
        print("\nTools:")
        for event in turn.tools_used:
            print(f"- {event.name}: {'ok' if event.ok else 'failed'}")
    if turn.sources:
        print("\nSources:")
        for source in turn.sources:
            print(f"- {source.get('title')} — {source.get('url')}")


if __name__ == "__main__":
    main()
