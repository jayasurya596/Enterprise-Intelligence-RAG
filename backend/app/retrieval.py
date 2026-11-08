import logging
import math
import re
from collections import defaultdict
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.embeddings import get_embeddings
from app.models import Chunk, Document
from app.vector_index import get_vector_index

logger = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"[\w.-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def bm25_search(query: str, chunks: list[Chunk], limit: int) -> list[tuple[Chunk, float]]:
    if not chunks:
        return []
    docs = [tokenize(chunk.content) for chunk in chunks]
    qterms = tokenize(query)
    n = len(docs)
    avgdl = sum(map(len, docs)) / max(n, 1)
    doc_freq: dict[str, int] = defaultdict(int)
    for tokens in docs:
        for term in set(tokens):
            doc_freq[term] += 1
    scores: list[tuple[Chunk, float]] = []
    for chunk, tokens in zip(chunks, docs):
        counts: dict[str, int] = defaultdict(int)
        for token in tokens:
            counts[token] += 1
        score = 0.0
        for term in qterms:
            frequency = counts[term]
            if not frequency:
                continue
            df = doc_freq[term]
            inverse = math.log(1 + (n - df + 0.5) / (df + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / max(avgdl, 1))
            score += inverse * frequency * (1.5 + 1) / denominator
        if score > 0:
            scores.append((chunk, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def reciprocal_rank_fusion(dense_ids: list[str], lexical_ids: list[str], k: int) -> dict[str, float]:
    fused: dict[str, float] = defaultdict(float)
    for ranked_ids in (dense_ids, lexical_ids):
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            fused[chunk_id] += 1 / (k + rank)
    return dict(fused)


class CrossEncoderReranker:
    def __init__(self) -> None:
        self.provider = settings.reranker_provider.casefold()
        self.model = None

    def rerank(self, query: str, evidence: list[dict]) -> list[dict]:
        if self.provider in {"none", "disabled", ""} or not evidence:
            return evidence
        if self.provider != "sentence-transformers":
            logger.warning("Unknown reranker provider %s; leaving RRF order unchanged", self.provider)
            return evidence
        if self.model is None:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(settings.reranker_model)
        pairs = [(query, item["content"]) for item in evidence]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(scores, evidence), key=lambda pair: float(pair[0]), reverse=True)
        for score, item in ranked:
            item["rerank_score"] = float(score)
        return [item for _, item in ranked]


@lru_cache
def get_reranker() -> CrossEncoderReranker:
    return CrossEncoderReranker()


def search_hybrid(db: Session, query: str, owner_id: str, domains: list[str]) -> tuple[list[dict], dict]:
    # The SQL owner predicate is applied before any chunk text is loaded into lexical retrieval.
    stmt = select(Chunk).options(joinedload(Chunk.document)).join(Chunk.document).where(Chunk.owner_id == owner_id, Document.status == "ready")
    chunks = list(db.scalars(stmt).unique())
    if domains:
        wanted = {domain.casefold() for domain in domains}
        chunks = [c for c in chunks if wanted.intersection(label.casefold() for label in (c.domain_labels or []))]

    dense_hits = []
    try:
        query_vector = get_embeddings().embed_many([query])[0]
        dense_hits = get_vector_index().search(query_vector, owner_id, domains, settings.top_k_dense)
    except Exception as exc:
        logger.warning("Dense retrieval unavailable (%s); continuing with authorized lexical candidates", type(exc).__name__)
    dense_hits = [hit for hit in dense_hits if hit["score"] >= settings.min_dense_score]

    lexical = bm25_search(query, chunks, settings.top_k_bm25)
    dense_ids = [hit["id"] for hit in dense_hits]
    lexical_ids = [chunk.id for chunk, _ in lexical]
    scores = reciprocal_rank_fusion(dense_ids, lexical_ids, settings.rrf_k)
    fused: dict[str, dict] = {}
    for rank, hit in enumerate(dense_hits, start=1):
        point_id = hit["id"]
        fused.setdefault(point_id, {"id": point_id, "rrf_score": scores[point_id], "dense_rank": None, "bm25_rank": None})
        fused[point_id]["dense_rank"] = rank
        fused[point_id]["dense_score"] = hit["score"]
    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    for rank, (chunk, bm25_score) in enumerate(lexical, start=1):
        fused.setdefault(chunk.id, {"id": chunk.id, "rrf_score": scores[chunk.id], "dense_rank": None, "bm25_rank": None})
        fused[chunk.id]["bm25_rank"] = rank
        fused[chunk.id]["bm25_score"] = bm25_score
    ordered = sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)
    evidence = []
    for item in ordered[: max(settings.top_k_dense, settings.top_k_bm25)]:
        chunk = chunk_by_id.get(item["id"])
        if chunk is None:
            continue  # Never trust index payloads alone for citation resolution.
        evidence.append({"id": chunk.id, "document_id": chunk.document_id, "owner_id": chunk.owner_id, "document_name": chunk.document.source_name, "page_number": chunk.page_number, "domains": chunk.domain_labels or [], "content": chunk.content, "rrf_score": item["rrf_score"], "dense_rank": item["dense_rank"], "dense_score": item.get("dense_score"), "bm25_rank": item["bm25_rank"], "bm25_score": item.get("bm25_score")})
    reranked = get_reranker().rerank(query, evidence)[: settings.top_k_rerank]
    for position, item in enumerate(reranked, start=1):
        item["rerank_position"] = position
    diagnostics = {"dense_candidates": len(dense_hits), "bm25_candidates": len(lexical), "fused_candidates": len(evidence), "reranker": f"{settings.reranker_provider}:{settings.reranker_model}" if settings.reranker_provider == "sentence-transformers" else "disabled", "top_candidates": [{"chunk_id": item["id"], "document_name": item["document_name"], "dense_rank": item["dense_rank"], "dense_score": item["dense_score"], "bm25_rank": item["bm25_rank"], "bm25_score": item["bm25_score"], "rrf_score": item["rrf_score"], "rerank_score": item.get("rerank_score"), "rerank_position": item["rerank_position"]} for item in reranked]}
    return reranked, diagnostics

