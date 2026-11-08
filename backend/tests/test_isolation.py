from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.retrieval as retrieval
from app.db import Base
from app.models import Chunk, Document, User


class FakeIndex:
    def __init__(self, point_ids):
        self.point_ids = point_ids

    def search(self, vector, owner_id, domains, limit):
        return [{"id": item, "score": 0.9, "payload": {"owner_id": "untrusted-payload"}} for item in self.point_ids]


def test_foreign_dense_result_cannot_become_citation_evidence(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        first = User(id="user-a", email="a@example.test", password_hash="unused")
        second = User(id="user-b", email="b@example.test", password_hash="unused")
        db.add_all([first, second])
        db.flush()
        doc_a = Document(id="doc-a", owner_id=first.id, source_name="mine.txt", storage_name="a.txt", content_type="text/plain", byte_size=20, status="ready", domain_labels=[])
        doc_b = Document(id="doc-b", owner_id=second.id, source_name="theirs.txt", storage_name="b.txt", content_type="text/plain", byte_size=20, status="ready", domain_labels=[])
        db.add_all([doc_a, doc_b])
        db.flush()
        own_chunk = Chunk(id="chunk-a", document_id=doc_a.id, owner_id=first.id, chunk_order=0, page_number=None, domain_labels=[], content="renewal period is thirty days")
        foreign_chunk = Chunk(id="chunk-b", document_id=doc_b.id, owner_id=second.id, chunk_order=0, page_number=None, domain_labels=[], content="renewal period is one year")
        db.add_all([own_chunk, foreign_chunk])
        db.commit()
        monkeypatch.setattr(retrieval, "get_vector_index", lambda: FakeIndex([foreign_chunk.id, own_chunk.id]))
        evidence, _ = retrieval.search_hybrid(db, "renewal period", first.id, [])
        assert evidence
        assert all(item["owner_id"] == first.id for item in evidence)
        assert foreign_chunk.id not in {item["id"] for item in evidence}
    engine.dispose()

