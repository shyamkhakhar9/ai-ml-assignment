"""Streamlit UI for knowledge-base search and MCP weather/currency tools."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.intent import route_question
from app.prompts import SYSTEM_PROMPT
from mcp_servers.client import call_convert_currency, call_weather_forecast

ROOT = Path(__file__).resolve().parents[1]


def _render_weather(result) -> None:
    st.markdown("**MCP tool: weather**")
    if not result.ok:
        st.warning(
            "The weather tool failed or is unavailable. "
            "Current conditions will not be guessed."
        )
        st.caption(result.error or "Unknown error")
        return
    data = result.data
    location = data.get("location") or {}
    current = data.get("current") or {}
    st.write(
        f"Current information from the weather tool for "
        f"{location.get('name', 'the destination')} ({data.get('source', 'MCP')})."
    )
    st.write(
        f"Now: {current.get('condition')}, {current.get('temperature_c')}°C, "
        f"humidity {current.get('humidity_pct')}%."
    )
    daily = data.get("daily") or []
    if daily:
        st.table(
            [
                {
                    "Date": row.get("date"),
                    "Condition": row.get("condition"),
                    "Min °C": row.get("temp_min_c"),
                    "Max °C": row.get("temp_max_c"),
                    "Rain %": row.get("rain_probability_pct"),
                    "Prefer indoor": "Yes" if row.get("prefer_indoor") else "No",
                }
                for row in daily
            ]
        )


def _render_currency(result) -> None:
    st.markdown("**MCP tool: currency**")
    if not result.ok:
        st.warning(
            "The currency tool failed or is unavailable. "
            "An exchange rate will not be guessed."
        )
        st.caption(result.error or "Unknown error")
        return
    data = result.data
    st.write(f"Current information from the currency tool ({data.get('source', 'MCP')}).")
    st.write(
        f"{data.get('amount')} {data.get('from_currency')} = "
        f"{data.get('converted_amount')} {data.get('to_currency')} "
        f"(rate {data.get('rate')} on {data.get('date')})."
    )


def _render_rag(query: str) -> None:
    st.markdown("**Knowledge base**")
    try:
        from kb.retrieve import retrieve

        result = retrieve(query)
    except FileNotFoundError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Knowledge-base retrieval is unavailable: {exc}")
        return
    if not result.sufficient:
        st.warning(result.message)
        return
    for index, chunk in enumerate(result.chunks, start=1):
        st.markdown(f"**[{index}] {chunk.source_title}** · score `{chunk.score:.3f}`")
        st.caption(chunk.section)
        st.write(chunk.content)
    with st.expander("Sources"):
        for source in result.sources():
            st.markdown(f"- [{source['title']}]({source['url']})")


def main() -> None:
    st.set_page_config(page_title="AI Travel Planning Assistant", page_icon="✈️")
    st.title("AI Travel Planning Assistant")
    st.caption("Singapore")

    st.markdown("**Destination:** Singapore")
    st.info(
        "Destination facts come from the knowledge base. "
        "Weather and currency come from MCP tools. "
        "Failed tools are reported instead of inventing values."
    )

    query = st.chat_input(
        "Ask about Singapore, weather, or a currency conversion"
    )
    if query:
        with st.chat_message("user"):
            st.write(query)
        with st.chat_message("assistant"):
            routed = route_question(query)
            called_tool = False
            if routed.use_weather:
                weather = call_weather_forecast(
                    routed.weather_location, routed.weather_days
                )
                _render_weather(weather)
                called_tool = True
            if routed.use_currency:
                if routed.amount is None or not routed.from_currency or not routed.to_currency:
                    st.warning(
                        "A currency conversion was requested, but the amount "
                        "or currency pair could not be read. No rate was invented."
                    )
                else:
                    fx = call_convert_currency(
                        routed.amount, routed.from_currency, routed.to_currency
                    )
                    _render_currency(fx)
                called_tool = True
            if routed.use_rag or not called_tool:
                _render_rag(query)

    with st.expander("System prompt"):
        st.code(SYSTEM_PROMPT, language="markdown")
    st.caption(f"Project root: `{ROOT}`")


if __name__ == "__main__":
    main()
