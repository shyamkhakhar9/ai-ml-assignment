# AI Travel Planning Assistant

A travel assistant for **Singapore** that combines a document knowledge base (RAG) with current weather and currency data from MCP tools.

## Architecture

```
User (Streamlit)
        │
        ▼
LangChain agent (prompts + chat memory)
        │
        ├── RAG retriever → Chroma (chunk embeddings + title/URL metadata)
        └── MCP tools
              ├── weather_forecast
              └── convert_currency
```

- Destination facts come only from retrieved documents.
- Weather and exchange rates come only from MCP tools.
- Combined questions use both sources.
- The UI should label knowledge-base sources, MCP results, and model suggestions separately.

## Knowledge-base sources

At least three public resources (see `kb/sources.json`):

| Source | URL |
| --- | --- |
| Wikivoyage Singapore Travel Guide | https://en.wikivoyage.org/wiki/Singapore |
| Visit Singapore: Essential Travel Information | https://www.visitsingapore.com/travel-guide-tips/traveller-information/ |
| Visit Singapore: Sample Itineraries | https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/ |
| Visit Singapore: Things to Do | https://www.visitsingapore.com/see-do-singapore/ |

Place downloaded files under `data/raw/` before ingest. Keep original titles and URLs as metadata. Review reuse terms before redistributing extracted content.

## RAG workflow

1. Load travel content from `data/raw/`.
2. Split into meaningful chunks.
3. Embed chunks and store them in Chroma (`chroma_db/`).
4. Retrieve relevant chunks for each question.
5. Generate grounded answers with source title and link.
6. If the knowledge base is insufficient, say so instead of inventing facts.

## MCP tools

| Tool | Purpose |
| --- | --- |
| Weather | Current conditions and forecast for Singapore |
| Currency | Convert amounts (for example INR ↔ SGD) |

Tools must not answer destination questions already covered by the knowledge base. Failed or unavailable tools must not produce fabricated values.

## Prompt and context strategy

Prompt instructions live in `app/prompts.py`. The model should use retrieved content for destination facts, MCP output for current information, keep user preferences across turns, and distinguish facts from generated recommendations.

## Project layout

```
app/                 Streamlit UI, agent, prompts
kb/                  Source catalog and ingest script
mcp_servers/         Weather and currency MCP servers
data/raw/            Downloaded source documents
data/processed/      Optional processed files
samples/             Sample questions and captured responses
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

```bash
python -m kb.ingest
PYTHONPATH=. streamlit run app/ui.py
```

## Out of scope

Flight or hotel booking, payments, turn-by-turn navigation, and reservations.
