"""LangChain tools wrapping knowledge-base retrieval and MCP servers."""

from __future__ import annotations

import json
from typing import Any, Callable

from kb.retrieve import retrieve
from mcp_servers.client import call_convert_currency, call_weather_forecast


def format_retrieval_for_llm(query: str) -> str:
    result = retrieve(query)
    if not result.sufficient:
        return json.dumps(
            {
                "ok": False,
                "tool": "search_destination_knowledge",
                "error": result.message,
                "sources": [],
            },
            ensure_ascii=False,
        )
    passages = []
    for index, chunk in enumerate(result.chunks, start=1):
        passages.append(
            {
                "id": index,
                "source_title": chunk.source_title,
                "source_url": chunk.source_url,
                "section": chunk.section,
                "score": round(chunk.score, 3),
                "content": chunk.content,
            }
        )
    return json.dumps(
        {
            "ok": True,
            "tool": "search_destination_knowledge",
            "passages": passages,
            "sources": result.sources(),
        },
        ensure_ascii=False,
    )


def search_destination_knowledge(query: str) -> str:
    """Search the Singapore travel knowledge base for destination facts.

    Use for attractions, neighbourhoods, transport, food, culture, indoor or
    outdoor activities, and sample itineraries. Do not use for live weather
    or exchange rates.
    """
    try:
        return format_retrieval_for_llm(query)
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "tool": "search_destination_knowledge",
                "error": str(exc),
                "sources": [],
            },
            ensure_ascii=False,
        )


def weather_forecast(location: str = "Singapore", days: int = 3) -> str:
    """Get current weather and a daily forecast via the weather MCP tool.

    Use for rain, temperature, or whether indoor or outdoor activities fit
    the next few days. Default location is Singapore. days must be 1 to 7.
    """
    result = call_weather_forecast(location, days)
    return json.dumps(result.as_dict(), ensure_ascii=False)


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between currencies via the currency MCP tool.

    Use ISO codes such as INR, SGD, and USD. Do not use for destination facts.
    """
    result = call_convert_currency(amount, from_currency, to_currency)
    return json.dumps(result.as_dict(), ensure_ascii=False)


TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
    "search_destination_knowledge": search_destination_knowledge,
    "weather_forecast": weather_forecast,
    "convert_currency": convert_currency,
}


def parse_tool_payload(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"ok": False, "error": raw}
