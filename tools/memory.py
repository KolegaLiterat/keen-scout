"""
Semantic research memory — stores query results in Chroma.
Embeddings: qwen/qwen3-embedding-8b via OpenRouter API (no local model required).
"""

import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import requests
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from dotenv import load_dotenv

load_dotenv()

MEMORY_DIR = Path(__file__).parent.parent / ".memory"
COLLECTION_NAME = "researcher"
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"

_client = None
_collection = None


class OpenRouterEmbeddingFunction(EmbeddingFunction):
    """Embeddings via OpenRouter API — Qwen3-Embedding-8B."""

    def __init__(self, model: str):
        self._model = model
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def name(self) -> str:
        return f"openrouter:{self._model}"

    def __call__(self, input: Documents) -> Embeddings:
        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers=self._headers,
            json={"model": self._model, "input": list(input)},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    MEMORY_DIR.mkdir(exist_ok=True)

    _client = chromadb.PersistentClient(path=str(MEMORY_DIR))
    ef = OpenRouterEmbeddingFunction(EMBEDDING_MODEL)

    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    return _collection


def save(query: str, result: str, sources: list[str] = None, metadata: dict = None) -> str:
    """
    Save a research result to memory.

    Args:
        query: User query
        result: Generated answer/research result
        sources: List of source URLs
        metadata: Additional metadata (e.g. category, tags)

    Returns:
        ID of the saved document
    """
    collection = _get_collection()

    doc_id = hashlib.md5(f"{query}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()

    meta = {
        "query": query[:500],
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "sources": ", ".join(sources or [])[:1000],
    }
    if metadata:
        meta.update({k: str(v)[:500] for k, v in metadata.items()})

    document = f"Query: {query}\n\nResult: {result}"

    collection.add(
        ids=[doc_id],
        documents=[document],
        metadatas=[meta],
    )

    return doc_id


def search(query: str, n_results: int = 3, min_similarity: float = 0.5) -> list[dict]:
    """
    Find semantically similar previous research.

    Args:
        query: Query to search for
        n_results: Number of results
        min_similarity: Minimum similarity threshold (0–1, default 0.5)

    Returns:
        List of dicts with query, result, sources, saved_at, similarity
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - distance
        if similarity < min_similarity:
            continue

        result_text = doc.split("Result: ", 1)[1] if "Result: " in doc else doc

        hits.append({
            "query": meta.get("query"),
            "result": result_text,
            "sources": meta.get("sources", "").split(", ") if meta.get("sources") else [],
            "saved_at": meta.get("saved_at"),
            "similarity": round(similarity, 3),
        })

    return hits


def count() -> int:
    """Return the number of stored research documents."""
    return _get_collection().count()


def clear() -> None:
    """Clear all memory."""
    global _client, _collection
    collection = _get_collection()
    _client.delete_collection(COLLECTION_NAME)
    _collection = None


if __name__ == "__main__":
    print(f"Model: {EMBEDDING_MODEL}\n")

    save(
        query="Air quality trends in major cities 2024",
        result="Air quality improved by 12% in 2024. The main remaining issue is fine particulate matter (PM2.5).",
        sources=["https://example-epa.gov/air-quality"],
    )
    save(
        query="Unemployment rate in 2024",
        result="The unemployment rate in 2024 reached 4.2%, the lowest in 30 years.",
        sources=["https://example-stats.gov/unemployment"],
    )

    print(f"In memory: {count()} documents\n")

    for q in ["smog city 2024", "air pollution", "labor market", "mountain weather"]:
        hits = search(q, n_results=2)
        print(f'Query: "{q}"')
        for h in hits:
            print(f"  [{h['similarity']}] {h['query']}")
        if not hits:
            print("  no results")
        print()
