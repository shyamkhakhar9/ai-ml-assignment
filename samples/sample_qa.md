# Sample questions and responses

Captured from the running app (`PYTHONPATH=. python -m app.agent "..."`) without `OPENAI_API_KEY`. Weather and FX values change with the MCP backends.

## RAG (destination knowledge)

**Q:** What are the must-visit attractions in Singapore?

**Tools:** `search_destination_knowledge` (ok)

**Sources:** Visit Singapore: Things to Do; Essential Travel Information; Wikivoyage Singapore Travel Guide; Sample Itineraries

**A (excerpt):** Under **Knowledge base**, retrieved passages cite Visit Singapore and Wikivoyage. Wikivoyage “See” covers Sentosa beaches, Chinatown / Little India / Geylang Serai, the colonial museum core around Bras Basah, and Mandai Wildlife Reserve (Singapore Zoo, Night Safari, Bird Paradise, River Wonders) plus the Botanic Gardens.

---

**Q:** What is the best restaurant on Mars?

**Tools:** `search_destination_knowledge` (ok, empty after score filter)

**A:** The knowledge base did not return enough destination facts. Off-topic queries are not answered with invented restaurants.

## MCP (current information)

**Q:** What is the weather in Singapore?

**Tools:** `weather_forecast` (ok)

**A (captured 2026-09-17):**

```
## MCP (weather)

Current information from the weather tool (Open-Meteo): Overcast, 29.2°C.

- 2026-09-17: Light drizzle, 24.8–32.0°C, rain 70% (indoor options preferred).
- 2026-09-18: Thunderstorm, 24.5–32.7°C, rain 83% (indoor options preferred).
- 2026-09-19: Thunderstorm, 23.4–30.0°C, rain 85% (indoor options preferred).
```

---

**Q:** Convert INR 50,000 to SGD.

**Tools:** `convert_currency` (ok)

**A (captured 2026-09-17):**

```
## MCP (currency)

Current information from the currency tool (Frankfurter): 50000.0 INR = 663.42 SGD on 2026-09-16.
```

## Combined RAG + MCP

**Q:** Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast.

**Tools:** `search_destination_knowledge` (ok, twice), `weather_forecast` (ok)

**Sources:** Visit Singapore Sample Itineraries, Essential Travel Information, Things to Do; Wikivoyage Singapore Travel Guide

**A (structure):**

1. **Knowledge base** — Visit Singapore itinerary hub (city explorer, family, 4-day, outdoor, food), climate notes, indoor/outdoor things to do, Wikivoyage climate.
2. **MCP (weather)** — Open-Meteo 7-day forecast for the following week (drizzle/thunderstorms; indoor options preferred on wet days).
3. **Recommendation** — generated day labels matching indoor-leaning days to retrieved indoor places (conservatories, museums, temples) and outdoor neighbourhoods/gardens to drier days. Marked as a generated plan, not a KB fact.

Chat history keeps a follow-up such as “Make it family-friendly.” so the next retrieval uses that preference.

## Other prompts to try in the UI

- Which neighbourhoods are suitable for cultural experiences?
- How can a tourist travel around Singapore?
- Suggest activities for a family with children.
- What indoor attractions can I visit?
- Create a three-day sightseeing itinerary.
- What is the forecast for the next three days?
- How much is 200 SGD in INR?
- I have a budget of INR 60,000. Convert it to SGD and suggest a three-day itinerary.
- Suggest outdoor attractions and replace them with indoor options if rain is expected.
