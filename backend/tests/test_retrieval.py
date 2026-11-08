from types import SimpleNamespace

from uuid import uuid4

from app.embeddings import get_embeddings
from app.retrieval import CrossEncoderReranker, bm25_search, reciprocal_rank_fusion
from app.vector_index import VectorIndex


def test_bm25_ranks_exact_term_match_first():
    chunks = [
        SimpleNamespace(id="a", content="Operational overview and delivery schedule"),
        SimpleNamespace(id="b", content="Invoice identifier ZX-449 payment due date"),
    ]
    ranked = bm25_search("ZX-449", chunks, limit=5)
    assert ranked[0][0].id == "b"
    assert ranked[0][1] > 0


def test_rrf_rewards_consensus_across_retrievers():
    scores = reciprocal_rank_fusion(["shared", "dense-only"], ["shared", "bm25-only"], k=60)
    assert scores["shared"] == 2 / 61
    assert scores["shared"] > scores["dense-only"]


def test_cross_encoder_scores_reorder_candidates(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "reranker_provider", "sentence-transformers")
    ranker = CrossEncoderReranker()
    ranker.model = type("FakeModel", (), {"predict": lambda self, pairs: [0.1, 0.9]})()
    evidence = [{"id": "first", "content": "low relevance"}, {"id": "second", "content": "high relevance"}]
    assert [item["id"] for item in ranker.rerank("question", evidence)] == ["second", "first"]


def test_qdrant_dense_search_applies_owner_and_domain_filters():
    index = VectorIndex()
    first_id, second_id = str(uuid4()), str(uuid4())
    records = [
        {"id": first_id, "owner_id": "user-a", "document_id": "doc-a", "domain_labels": ["finance"]},
        {"id": second_id, "owner_id": "user-b", "document_id": "doc-b", "domain_labels": ["finance"]},
    ]
    vector = get_embeddings().embed_many(["payment terms"])[0]
    index.upsert(records, [vector, vector])
    hits = index.search(vector, "user-a", ["finance"], 5)
    assert [hit["id"] for hit in hits] == [first_id]

