"""Semantic retrieval over the Singapore travel knowledge base."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache

from langchain_chroma import Chroma

from kb.embeddings import build_embeddings
from kb.paths import (
    COLLECTION_NAME,
    RETRIEVAL_K,
    RETRIEVAL_MIN_SCORE,
    VECTOR_DIR,
)


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    score: float
    source_title: str
    source_url: str
    section: str
    source_id: str


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    chunks: list[RetrievedChunk]
    sufficient: bool
    message: str

    def sources(self) -> list[dict[str, str]]:
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for chunk in self.chunks:
            key = chunk.source_url
            if key in seen:
                continue
            seen.add(key)
            unique.append(
                {
                    "title": chunk.source_title,
                    "url": chunk.source_url,
                    "section": chunk.section,
                }
            )
        return unique


INSUFFICIENT_MESSAGE = (
    "The knowledge base does not contain enough information to answer this "
    "question reliably. Destination facts will not be invented."
)


@lru_cache(maxsize=1)
def load_vectorstore() -> Chroma:
    if not VECTOR_DIR.exists():
        raise FileNotFoundError(
            f"Vector store not found at {VECTOR_DIR}. Run: python -m kb.ingest"
        )
    return Chroma(
        persist_directory=str(VECTOR_DIR),
        embedding_function=build_embeddings(),
        collection_name=COLLECTION_NAME,
    )


def retrieve(
    query: str,
    k: int = RETRIEVAL_K,
    min_score: float = RETRIEVAL_MIN_SCORE,
) -> RetrievalResult:
    vectorstore = load_vectorstore()
    pairs = vectorstore.similarity_search_with_score(query, k=k)

    chunks: list[RetrievedChunk] = []
    for document, distance in pairs:
        score = 1.0 - float(distance)
        if score < min_score:
            continue
        metadata = document.metadata
        chunks.append(
            RetrievedChunk(
                content=document.page_content,
                score=float(score),
                source_title=metadata.get("source_title", "Unknown source"),
                source_url=metadata.get("source_url", ""),
                section=str(metadata.get("section", "general")),
                source_id=str(metadata.get("source_id", "")),
            )
        )

    sufficient = bool(chunks)
    return RetrievalResult(
        query=query,
        chunks=chunks,
        sufficient=sufficient,
        message="" if sufficient else INSUFFICIENT_MESSAGE,
    )


def format_result(result: RetrievalResult) -> str:
    lines = [f"Query: {result.query}", f"Sufficient: {result.sufficient}"]
    if not result.sufficient:
        lines.append(result.message)
        return "\n".join(lines)

    for index, chunk in enumerate(result.chunks, start=1):
        lines.append(
            f"\n[{index}] score={chunk.score:.3f} | {chunk.source_title} | {chunk.section}"
        )
        lines.append(chunk.source_url)
        preview = chunk.content.replace("\n", " ")
        lines.append(preview[:500] + ("..." if len(preview) > 500 else ""))
    lines.append("\nSources:")
    for source in result.sources():
        lines.append(f"- {source['title']} — {source['url']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the Singapore travel knowledge base")
    parser.add_argument("query", nargs="+", help="Destination question")
    parser.add_argument("--k", type=int, default=RETRIEVAL_K)
    args = parser.parse_args()
    query = " ".join(args.query)
    print(format_result(retrieve(query, k=args.k)))


if __name__ == "__main__":
    main()
