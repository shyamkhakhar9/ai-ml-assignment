"""MCP server: live currency conversion.

Uses Frankfurter (https://api.frankfurter.dev).
"""

from __future__ import annotations

import json
import re

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("travel-currency")

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
USER_AGENT = "NAGP-AI-Travel-Assistant/1.0 (educational assignment)"
CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")


def _normalise_code(code: str) -> str:
    value = (code or "").strip().upper()
    aliases = {"RUPEE": "INR", "RUPEES": "INR", "DOLLAR": "USD", "DOLLARS": "USD"}
    value = aliases.get(value, value)
    if not CURRENCY_RE.match(value):
        raise ValueError(f"Invalid currency code '{code}'. Use a 3-letter ISO code such as INR or SGD.")
    return value


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount between two ISO 4217 currency codes using a live rate.

    Examples: INR to SGD, SGD to INR, USD to SGD. Do not use this for
    destination facts such as attractions or neighbourhoods.
    """
    try:
        value = float(amount)
        if value < 0:
            raise ValueError("Amount must be zero or positive.")
        source = _normalise_code(from_currency)
        target = _normalise_code(to_currency)
        if source == target:
            result = {
                "ok": True,
                "source": "Frankfurter",
                "tool": "convert_currency",
                "amount": value,
                "from_currency": source,
                "to_currency": target,
                "rate": 1.0,
                "converted_amount": value,
                "date": None,
            }
            return json.dumps(result, ensure_ascii=False)

        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            response = client.get(
                FRANKFURTER_URL,
                params={"amount": value, "from": source, "to": target},
            )
            response.raise_for_status()
            payload = response.json()

        rates = payload.get("rates") or {}
        if target not in rates:
            raise ValueError(f"No rate returned for {source} -> {target}.")
        converted = rates[target]
        result = {
            "ok": True,
            "source": "Frankfurter",
            "tool": "convert_currency",
            "amount": value,
            "from_currency": payload.get("base", source),
            "to_currency": target,
            "rate": round(float(converted) / value, 6) if value else None,
            "converted_amount": converted,
            "date": payload.get("date"),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "tool": "convert_currency",
                "error": str(exc),
            },
            ensure_ascii=False,
        )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
