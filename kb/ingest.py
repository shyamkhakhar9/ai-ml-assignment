"""Load travel documents, chunk them, embed, and persist to Chroma."""

from __future__ import annotations

import json
import shutil

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from kb.embeddings import build_embeddings
from kb.paths import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    COLLECTION_NAME,
    RAW_DIR,
    ROOT,
    SOURCES_PATH,
    VECTOR_DIR,
)

HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "h1"),
        ("##", "section"),
        ("###", "subsection"),
    ],
    strip_headers=False,
)

TOKEN_SPLITTER = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=CHUNK_SIZE_TOKENS,
    chunk_overlap=CHUNK_OVERLAP_TOKENS,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
)


def load_source_catalog() -> dict:
    with SOURCES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _section_from_metadata(metadata: dict) -> str:
    for key in ("subsection", "section", "h1"):
        value = metadata.get(key)
        if value:
            return str(value)
    return "general"


def load_source_documents() -> list[Document]:
    catalog = load_source_catalog()
    documents: list[Document] = []
    missing: list[str] = []

    for source in catalog["sources"]:
        path = ROOT / source["local_path"]
        if not path.exists():
            missing.append(source["local_path"])
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            missing.append(source["local_path"])
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source_id": source["id"],
                    "source_title": source["title"],
                    "source_url": source["url"],
                    "source_path": source["local_path"],
                },
            )
        )

    if missing:
        raise FileNotFoundError(
            "Missing or empty knowledge-base files:\n- "
            + "\n- ".join(missing)
            + "\nRun: python -m kb.fetch_sources"
        )
    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    chunks: list[Document] = []
    for document in documents:
        header_docs = HEADER_SPLITTER.split_text(document.page_content)
        if not header_docs:
            header_docs = [Document(page_content=document.page_content, metadata={})]

        split_docs = TOKEN_SPLITTER.split_documents(header_docs)
        for index, chunk in enumerate(split_docs):
            content = chunk.page_content.strip()
            if len(content) < 80:
                continue
            metadata = {
                **document.metadata,
                **chunk.metadata,
                "section": _section_from_metadata({**document.metadata, **chunk.metadata}),
                "chunk_index": index,
            }
            chunks.append(Document(page_content=content, metadata=metadata))
    return chunks


def persist_chunks(chunks: list[Document]) -> Chroma:
    if VECTOR_DIR.exists():
        shutil.rmtree(VECTOR_DIR)
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=build_embeddings(),
        persist_directory=str(VECTOR_DIR),
        collection_name=COLLECTION_NAME,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return vectorstore


def ingest() -> None:
    catalog = load_source_catalog()
    print(f"Destination: {catalog['destination']}")
    print(f"Raw directory: {RAW_DIR}")
    print(f"Vector store: {VECTOR_DIR}")

    documents = load_source_documents()
    print(f"Loaded {len(documents)} source files")

    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    if not chunks:
        raise RuntimeError("No chunks produced. Check source files in data/raw/.")

    persist_chunks(chunks)
    print(f"Persisted {len(chunks)} embeddings to {VECTOR_DIR}")

    from kb.retrieve import retrieve

    sample = "What are the must-visit attractions in Singapore?"
    result = retrieve(sample)
    print(f"Sample retrieval for: {sample}")
    print(f"  hits={len(result.chunks)} sufficient={result.sufficient}")
    for chunk in result.chunks[:3]:
        print(
            f"  [{chunk.score:.3f}] {chunk.source_title} — {chunk.section[:80]}"
        )


if __name__ == "__main__":
    ingest()
