import hashlib
import math
import re
from functools import lru_cache

from app.config import settings

TOKEN_RE = re.compile(r"[\w.-]+", re.UNICODE)


def _hash_vector(text: str, dimensions: int) -> list[float]:
    tokens = [t.casefold() for t in TOKEN_RE.findall(text)]
    features = tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest[:4], "big")
        index = value % dimensions
        vector[index] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = settings.embedding_provider.strip().lower()
        self.dimensions = settings.embedding_dimensions
        self.model_name = settings.embedding_model
        self._model = None

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "hashing":
            return [_hash_vector(text, self.dimensions) for text in texts]
        if self.provider == "sentence-transformers":
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                actual = self._model.get_sentence_embedding_dimension()
                if actual != self.dimensions:
                    raise ValueError(f"Embedding dimension mismatch: configured {self.dimensions}, model returns {actual}.")
            values = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [row.astype(float).tolist() for row in values]
        raise ValueError(f"Unsupported embedding provider: {self.provider}")


@lru_cache
def get_embeddings() -> EmbeddingService:
    return EmbeddingService()

