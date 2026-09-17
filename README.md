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
- The UI currently returns retrieved passages and source links.

## Knowledge-base sources

At least three public resources (see `kb/sources.json`):

| Source | URL | Local file |
| --- | --- | --- |
| Wikivoyage Singapore Travel Guide | https://en.wikivoyage.org/wiki/Singapore | `data/raw/wikivoyage-singapore.md` |
| Visit Singapore: Essential Travel Information | https://www.visitsingapore.com/travel-guide-tips/traveller-information/ | `data/raw/visit-singapore-essential.md` |
| Visit Singapore: Sample Itineraries | https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/ | `data/raw/visit-singapore-itineraries.md` |
| Visit Singapore: Things to Do | https://www.visitsingapore.com/see-do-singapore/ | `data/raw/visit-singapore-things-to-do.md` |

Wikivoyage is downloaded via the MediaWiki API (CC BY-SA). Visit Singapore files are excerpts with original titles and URLs retained as metadata. Review STB reuse terms before redistributing those excerpts.

## RAG workflow

1. Load travel content from `data/raw/` using `kb/sources.json`.
2. Split on Markdown headings, then into ~1000-token chunks with 150-token overlap.
3. Embed with `sentence-transformers/all-MiniLM-L6-v2` (or OpenAI if `EMBEDDING_PROVIDER=openai`).
4. Store vectors in Chroma at `chroma_db/` with `source_title`, `source_url`, and `section`.
5. Retrieve the top matching chunks for each question (default `k=5`).
6. If no chunk scores above `RETRIEVAL_MIN_SCORE`, the app states that the knowledge base is insufficient instead of inventing facts.

## MCP tools

| Tool | Purpose |
| --- | --- |
| Weather | Current conditions and forecast for Singapore |
| Currency | Convert amounts (for example INR ↔ SGD) |

## Prompt and context strategy

Prompt instructions live in `app/prompts.py`. The model should use retrieved content for destination facts, MCP output for current information, keep user preferences across turns, and distinguish facts from generated recommendations.

## Project layout

```
app/                 Streamlit UI, agent, prompts
kb/                  Sources, fetch, ingest, retrieval
mcp_servers/         Weather and currency MCP servers
data/raw/            Source documents
chroma_db/           Local vector store (generated, not committed)
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
python -m kb.fetch_sources
python -m kb.ingest
python -m kb.retrieve "What are the must-visit attractions in Singapore?"
PYTHONPATH=. streamlit run app/ui.py
```

`fetch_sources` refreshes Wikivoyage. Visit Singapore Markdown is left in place unless you pass `--refresh-web`.

## Out of scope

Flight or hotel booking, payments, turn-by-turn navigation, and reservations.
