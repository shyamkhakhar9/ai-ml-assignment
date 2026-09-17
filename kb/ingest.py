"""Load travel documents, chunk them, embed, and persist to the vector store."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "kb" / "sources.json"
RAW_DIR = ROOT / "data" / "raw"
VECTOR_DIR = ROOT / "chroma_db"


def load_source_catalog() -> dict:
    with SOURCES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def ingest() -> None:
    catalog = load_source_catalog()
    print(f"Destination: {catalog['destination']}")
    print(f"Configured sources: {len(catalog['sources'])}")
    print(f"Raw directory: {RAW_DIR}")
    print(f"Vector store: {VECTOR_DIR}")
    print("Add documents under data/raw/ before running ingest.")


if __name__ == "__main__":
    ingest()
