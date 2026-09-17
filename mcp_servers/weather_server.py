"""MCP server: current weather and daily forecast.

Uses Open-Meteo (no API key). Default destination is Singapore.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("travel-weather")

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "NAGP-AI-Travel-Assistant/1.0 (educational assignment)"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

DEFAULT_LOCATION = os.getenv("DESTINATION", "Singapore")
DEFAULT_LAT = float(os.getenv("DESTINATION_LAT", "1.3521"))
DEFAULT_LON = float(os.getenv("DESTINATION_LON", "103.8198"))


def _describe(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODES.get(int(code), f"Weather code {code}")


def _is_wet(code: int | None, rain_probability: float | None) -> bool:
    if rain_probability is not None and rain_probability >= 50:
        return True
    if code is None:
        return False
    return int(code) in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}


def _resolve_location(location: str) -> dict[str, Any]:
    query = (location or DEFAULT_LOCATION).strip() or DEFAULT_LOCATION
    if query.lower() in {"singapore", "sg", DEFAULT_LOCATION.lower()}:
        return {
            "name": DEFAULT_LOCATION,
            "latitude": DEFAULT_LAT,
            "longitude": DEFAULT_LON,
            "timezone": "Asia/Singapore",
        }

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20.0) as client:
        response = client.get(
            OPEN_METEO_GEOCODE,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        results = response.json().get("results") or []
    if not results:
        raise ValueError(f"Could not find coordinates for '{query}'.")
    place = results[0]
    return {
        "name": place.get("name", query),
        "country": place.get("country"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone") or "auto",
    }


@mcp.tool()
def weather_forecast(location: str = "Singapore", days: int = 3) -> str:
    """Return current conditions and a daily forecast.

    Use this for weather, rain, temperature, or whether indoor or outdoor
    activities are more suitable. Do not use it for attractions or transport.
    """
    try:
        forecast_days = max(1, min(int(days), 7))
        place = _resolve_location(location)
        params = {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": place.get("timezone") or "auto",
            "forecast_days": forecast_days,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                ]
            ),
        }
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20.0) as client:
            response = client.get(OPEN_METEO_FORECAST, params=params)
            response.raise_for_status()
            payload = response.json()

        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        current_code = current.get("weather_code")
        forecast_rows = []
        dates = daily.get("time") or []
        for index, date in enumerate(dates):
            code = (daily.get("weather_code") or [None])[index]
            rain_prob = (daily.get("precipitation_probability_max") or [None])[index]
            wet = _is_wet(code, rain_prob)
            forecast_rows.append(
                {
                    "date": date,
                    "condition": _describe(code),
                    "temp_min_c": (daily.get("temperature_2m_min") or [None])[index],
                    "temp_max_c": (daily.get("temperature_2m_max") or [None])[index],
                    "precipitation_mm": (daily.get("precipitation_sum") or [None])[index],
                    "rain_probability_pct": rain_prob,
                    "prefer_indoor": wet,
                }
            )

        result = {
            "ok": True,
            "source": "Open-Meteo",
            "tool": "weather_forecast",
            "location": place,
            "current": {
                "time": current.get("time"),
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "condition": _describe(current_code),
                "prefer_indoor": _is_wet(current_code, None),
            },
            "daily": forecast_rows,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {
                "ok": False,
                "tool": "weather_forecast",
                "error": str(exc),
            },
            ensure_ascii=False,
        )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
