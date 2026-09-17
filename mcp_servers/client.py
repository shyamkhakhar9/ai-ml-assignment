"""Call weather and currency MCP tools over stdio."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ToolCallResult:
    tool: str
    ok: bool
    data: dict[str, Any]
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {"tool": self.tool, "ok": self.ok, **self.data}
        if self.error:
            payload["error"] = self.error
        return payload


def _server_params(module: str) -> StdioServerParameters:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        cwd=str(ROOT),
        env=env,
    )


def _parse_tool_content(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = str(raw)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"ok": False, "error": text}


async def _call_tool(module: str, name: str, arguments: dict[str, Any]) -> ToolCallResult:
    try:
        async with stdio_client(_server_params(module)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(name, arguments)
    except Exception as exc:
        return ToolCallResult(tool=name, ok=False, data={}, error=str(exc))

    if getattr(response, "isError", False):
        return ToolCallResult(tool=name, ok=False, data={}, error="MCP tool returned an error.")

    chunks: list[str] = []
    for item in response.content:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
    payload = _parse_tool_content("".join(chunks) if chunks else {})
    ok = bool(payload.get("ok", False))
    error = None if ok else str(payload.get("error") or "Tool failed without details.")
    return ToolCallResult(tool=name, ok=ok, data=payload, error=error)


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def call_weather_forecast(location: str = "Singapore", days: int = 3) -> ToolCallResult:
    return _run(
        _call_tool(
            "mcp_servers.weather_server",
            "weather_forecast",
            {"location": location, "days": days},
        )
    )


def call_convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> ToolCallResult:
    return _run(
        _call_tool(
            "mcp_servers.currency_server",
            "convert_currency",
            {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
            },
        )
    )


def _print_result(result: ToolCallResult) -> int:
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    return 0 if result.ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Call travel MCP tools")
    sub = parser.add_subparsers(dest="command", required=True)

    weather = sub.add_parser("weather", help="Current weather and forecast")
    weather.add_argument("--location", default="Singapore")
    weather.add_argument("--days", type=int, default=3)

    convert = sub.add_parser("convert", help="Convert a currency amount")
    convert.add_argument("--amount", type=float, required=True)
    convert.add_argument("--from-currency", required=True)
    convert.add_argument("--to-currency", required=True)

    args = parser.parse_args()
    if args.command == "weather":
        result = call_weather_forecast(args.location, args.days)
    else:
        result = call_convert_currency(args.amount, args.from_currency, args.to_currency)
    raise SystemExit(_print_result(result))


if __name__ == "__main__":
    main()
