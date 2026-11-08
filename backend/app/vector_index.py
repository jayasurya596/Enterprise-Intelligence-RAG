from functools import lru_cache
from uuid import UUID

from qdrant_client import QdrantClient, models

from app.config import settings
from app.embeddings import get_embeddings

COLLECTION = "enterprise_chunks"


class VectorIndex:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None) if settings.qdrant_url else QdrantClient(":memory:")
        self.dimensions = get_embeddings().dimensions

    def ensure_collection(self) -> None:
        collections = {entry.name for entry in self.client.get_collections().collections}
        if COLLECTION not in collections:
            self.client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE))
        else:
            info = self.client.get_collection(COLLECTION)
            vector_config = info.config.params.vectors
            actual_dimensions = vector_config.size if isinstance(vector_config, models.VectorParams) else next(iter(vector_config.values())).size
            if actual_dimensions != self.dimensions:
                raise ValueError(f"Qdrant collection dimension is {actual_dimensions}; configured embedding dimension is {self.dimensions}. Recreate the collection or align the configuration.")

    def upsert(self, records: list[dict], vectors: list[list[float]]) -> None:
        if not records:
            return
        self.ensure_collection()
        points = []
        for record, vector in zip(records, vectors):
            points.append(models.PointStruct(id=str(UUID(record["id"])), vector=vector, payload={k: v for k, v in record.items() if k != "content"}))
        self.client.upsert(collection_name=COLLECTION, points=points, wait=True)

    def search(self, vector: list[float], owner_id: str, domains: list[str], limit: int) -> list[dict]:
        self.ensure_collection()
        must = [models.FieldCondition(key="owner_id", match=models.MatchValue(value=owner_id))]
        if domains:
            must.append(models.FieldCondition(key="domain_labels", match=models.MatchAny(any=domains)))
        result = self.client.query_points(collection_name=COLLECTION, query=vector, query_filter=models.Filter(must=must), limit=limit, with_payload=True)
        return [{"id": str(point.id), "score": float(point.score), "payload": point.payload or {}} for point in result.points]

    def delete_document(self, document_id: str, owner_id: str) -> None:
        self.ensure_collection()
        self.client.delete(collection_name=COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="owner_id", match=models.MatchValue(value=owner_id)), models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))])), wait=True)

    def health(self) -> bool:
        self.client.get_collections()
        return True


@lru_cache
def get_vector_index() -> VectorIndex:
    return VectorIndex()

