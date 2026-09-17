"""Choose RAG, weather MCP, currency MCP, or a mix from the user question."""

from __future__ import annotations

import re
from dataclasses import dataclass

WEATHER_RE = re.compile(
    r"\b(weather|forecast|temperature|rain|raining|umbrella|humid|"
    r"indoor or outdoor|outdoor activities tomorrow|adjust.{0,40}weather)\b",
    re.IGNORECASE,
)
CURRENCY_RE = re.compile(
    r"\b(convert|conversion|exchange|fx|inr|sgd|usd|eur|gbp|"
    r"rupee|rupees|dollar|dollars|travel budget)\b",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(
    r"(?:(?:INR|SGD|USD|EUR|GBP)\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:INR|SGD|USD|EUR|GBP|rupees?)?",
    re.IGNORECASE,
)
PAIR_RE = re.compile(
    r"\b(INR|SGD|USD|EUR|GBP)\b.*\b(INR|SGD|USD|EUR|GBP)\b",
    re.IGNORECASE,
)
DAYS_RE = re.compile(r"\b(next\s+)?(\d+)\s+days?\b", re.IGNORECASE)


@dataclass(frozen=True)
class RoutedRequest:
    use_rag: bool
    use_weather: bool
    use_currency: bool
    weather_location: str
    weather_days: int
    amount: float | None
    from_currency: str | None
    to_currency: str | None


def _parse_currency(question: str) -> tuple[float | None, str | None, str | None]:
    pair = PAIR_RE.search(question)
    from_code = pair.group(1).upper() if pair else None
    to_code = pair.group(2).upper() if pair else None
    if from_code and to_code and from_code == to_code:
        to_code = "SGD" if from_code != "SGD" else "INR"

    amount = None
    match = AMOUNT_RE.search(question)
    if match:
        amount = float(match.group(1).replace(",", ""))

    if "to sgd" in question.lower() or "singapore dollar" in question.lower():
        to_code = to_code or "SGD"
        from_code = from_code or "INR"
    if "to inr" in question.lower() or "in inr" in question.lower():
        to_code = to_code or "INR"
        from_code = from_code or "SGD"
    if "from usd" in question.lower():
        from_code = "USD"
        to_code = to_code or "SGD"

    if amount is not None and not from_code:
        from_code = "INR"
        to_code = to_code or "SGD"
    return amount, from_code, to_code


def route_question(question: str, default_location: str = "Singapore") -> RoutedRequest:
    weather = bool(WEATHER_RE.search(question))
    currency = bool(CURRENCY_RE.search(question))
    days = 3
    days_match = DAYS_RE.search(question)
    if days_match:
        days = max(1, min(int(days_match.group(2)), 7))
    if "next week" in question.lower():
        days = max(days, 7)
    elif "three-day" in question.lower() or "3-day" in question.lower() or "3 day" in question.lower():
        days = max(days, 3)
    elif "tomorrow" in question.lower():
        days = max(days, 2)

    amount, from_code, to_code = _parse_currency(question)
    if amount is not None and from_code and to_code:
        currency = True

    use_rag = not weather and not currency
    if weather and ("itinerary" in question.lower() or "attraction" in question.lower()):
        use_rag = True
    if currency and "itinerary" in question.lower():
        use_rag = True

    return RoutedRequest(
        use_rag=use_rag,
        use_weather=weather,
        use_currency=currency,
        weather_location=default_location,
        weather_days=days,
        amount=amount,
        from_currency=from_code,
        to_currency=to_code,
    )
