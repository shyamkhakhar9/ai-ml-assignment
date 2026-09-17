"""Shared paths and settings for the Singapore knowledge base."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SOURCES_PATH = ROOT / "kb" / "sources.json"
RAW_DIR = ROOT / "data" / "raw"
VECTOR_DIR = ROOT / "chroma_db"
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "singapore_travel")

CHUNK_SIZE_TOKENS = 1000
CHUNK_OVERLAP_TOKENS = 150
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.35"))

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
HF_EMBEDDING_MODEL = os.getenv(
    "HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)

USER_AGENT = (
    "NAGP-AI-Travel-Assistant/1.0 (educational assignment; "
    "https://en.wikivoyage.org/wiki/Singapore)"
)
