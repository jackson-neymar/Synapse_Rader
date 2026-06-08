import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from settings import config
from .embedding import get_embedder

logger = logging.getLogger(__name__)

_client = None  # chromadb.PersistentClient
_collection = None  # chromadb.Collection


# ---------------------------------------------------------------------------
# ChromaDB lifecycle
# ---------------------------------------------------------------------------
def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        path = Path(config.CHROMA_PERSIST_PATH).resolve()
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        embedder = get_embedder()
        client = _get_client()
        _collection = client.get_or_create_collection(
            name="analyzed_items",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------
def index_analyzed_item(item: dict) -> None:
    """Write an analyzed item into ChromaDB."""
    embedder = get_embedder()
    collection = _get_collection()

    doc_text = " ".join([
        item.get("title", ""),
        item.get("summary_one_liner", ""),
        " ".join(item.get("summary_highlights", [])),
    ])

    embedding = embedder.embed([doc_text])[0]

    collection.upsert(
        ids=[item["id"]],
        embeddings=[embedding],
        documents=[doc_text],
        metadatas=[{
            "category_l1": item.get("category_l1", ""),
            "category_l2": item.get("category_l2", ""),
            "score_total": item.get("score_total", 0),
            "recommend_level": item.get("recommend_level", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "title": item.get("title", "")[:200],
        }],
    )


# ---------------------------------------------------------------------------
# Hybrid search (vector + BM25)
# ---------------------------------------------------------------------------
def hybrid_search(query: str, n_results: int = 5) -> list[dict]:
    embedder = get_embedder()
    collection = _get_collection()

    # Get all documents for BM25 baseline
    all_data = collection.get(include=["documents", "metadatas"])
    all_docs = all_data.get("documents", [])
    all_ids = all_data.get("ids", [])
    all_meta = all_data.get("metadatas", [])

    if not all_docs:
        return []

    # Vector search
    query_vec = embedder.embed([query])[0]
    candidate_count = min(n_results * 2, len(all_docs))
    vector_results = collection.query(
        query_embeddings=[query_vec],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    # Build BM25 on candidates and rerank
    candidate_docs = vector_results["documents"][0]
    candidate_ids = vector_results["ids"][0]
    candidate_meta = vector_results["metadatas"][0]
    candidate_distances = vector_results["distances"][0]

    # BM25 keyword score (normalized)
    tokenized_candidates = [doc.lower().split() for doc in candidate_docs]
    bm25 = BM25Okapi(tokenized_candidates)
    query_tokens = query.lower().split()
    bm25_scores = bm25.get_scores(query_tokens)
    bm25_max = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_norm = [s / bm25_max for s in bm25_scores]

    # Combine: 0.7 vector + 0.3 BM25
    # Convert cosine distance to similarity: 1 - distance
    vec_max = max(candidate_distances) if max(candidate_distances) > 0 else 1
    combined = []
    for i in range(len(candidate_ids)):
        vec_sim = 1 - (candidate_distances[i] / vec_max) if vec_max > 0 else 1
        hybrid_score = 0.7 * vec_sim + 0.3 * bm25_norm[i]
        combined.append((hybrid_score, candidate_ids[i], candidate_meta[i]))

    combined.sort(key=lambda x: x[0], reverse=True)
    top = combined[:n_results]

    return [
        {
            "id": top[i][1],
            "similarity": round(top[i][0], 4),
            "metadata": top[i][2] or {},
        }
        for i in range(len(top))
    ]
