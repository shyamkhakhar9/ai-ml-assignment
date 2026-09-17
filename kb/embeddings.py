"""Embedding model used for chunk vectors."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from kb.paths import (
    EMBEDDING_PROVIDER,
    HF_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
)


@lru_cache(maxsize=1)
def build_embeddings() -> Embeddings:
    if EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)

    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=HF_EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
