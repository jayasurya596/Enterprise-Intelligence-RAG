from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
import app.routes_documents as documents_routes
import app.retrieval as retrieval


class FakeIndex:
    def __init__(self):
        self.points = {}

    def upsert(self, records, vectors):
        for record, vector in zip(records, vectors):
            self.points[record["id"]] = (record, vector)

    def search(self, vector, owner_id, domains, limit):
        from math import sqrt
        candidates = []
        for point_id, (record, stored_vector) in self.points.items():
            if record["owner_id"] != owner_id:
                continue
            if domains and not set(domains).intersection(record["domain_labels"]):
                continue
            score = sum(a * b for a, b in zip(vector, stored_vector)) / (sqrt(sum(a*a for a in vector)) * sqrt(sum(b*b for b in stored_vector)) or 1)
            candidates.append({"id": point_id, "score": score, "payload": record})
        return sorted(candidates, key=lambda item: item["score"], reverse=True)[:limit]

    def delete_document(self, document_id, owner_id):
        self.points = {key: value for key, value in self.points.items() if not (value[0]["document_id"] == document_id and value[0]["owner_id"] == owner_id)}

    def health(self):
        return True


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        with TestSession() as session:
            yield session

    fake_index = FakeIndex()
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(documents_routes, "get_vector_index", lambda: fake_index)
    monkeypatch.setattr(retrieval, "get_vector_index", lambda: fake_index)
    monkeypatch.setattr("app.main.settings.upload_dir", tmp_path / "uploads")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def make_account(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/register", json={"email": email, "password": "LongEnough!Pass123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_upload_without_domain_uses_financial_default(client: TestClient, monkeypatch):
    monkeypatch.setattr(documents_routes.settings, "default_domain", "financial")
    token = make_account(client, "finance@example.com")
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("statement.txt", b"Revenue for the period was 120000 USD.", "text/plain")},
    )
    assert response.status_code == 201
    assert response.json()["domain_labels"] == ["financial"]


def test_upload_ask_citations_and_owner_isolation(client: TestClient):
    owner_token = make_account(client, "owner@example.com")
    other_token = make_account(client, "other@example.com")
    owner = {"Authorization": f"Bearer {owner_token}"}
    other = {"Authorization": f"Bearer {other_token}"}

    upload = client.post("/api/documents", headers=owner, files={"file": ("risk.txt", b"The main operational risk is delayed delivery.", "text/plain")}, data={"domains": "operations"})
    assert upload.status_code == 201
    document = upload.json()
    assert document["status"] == "ready"
    assert document["chunk_count"] == 1

    answer = client.post("/api/chat/ask", headers=owner, json={"question": "What is the main operational risk?", "domains": ["operations"]})
    assert answer.status_code == 200
    body = answer.json()
    assert "delayed delivery" in body["answer"]
    assert body["citations"][0]["document_id"] == document["id"]
    assert body["citations"][0]["page_number"] is None

    assert client.get(f"/api/documents/{document['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/documents/{document['id']}", headers=other).status_code == 404
    assert client.get("/api/documents", headers=other).json() == []
    conversation_id = body["conversation_id"]
    assert client.get(f"/api/chat/conversations/{conversation_id}", headers=other).status_code == 404

    deleted = client.delete(f"/api/documents/{document['id']}", headers=owner)
    assert deleted.status_code == 204
    assert client.get(f"/api/documents/{document['id']}", headers=owner).status_code == 404
    after_delete = client.post(f"/api/chat/ask", headers=owner, json={"question": "What is the main operational risk?", "domains": ["operations"], "conversation_id": conversation_id})
    assert after_delete.status_code == 200
    assert after_delete.json()["insufficient_evidence"] is True
    assert after_delete.json()["citations"] == []

