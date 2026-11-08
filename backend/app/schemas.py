from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    email: EmailStr


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_name: str
    content_type: str
    byte_size: int
    status: str
    error_summary: str | None
    domain_labels: list[str]
    created_at: datetime
    chunk_count: int = 0


class CitationOut(BaseModel):
    marker: str
    document_id: str
    chunk_id: str
    document_name: str
    page_number: int | None
    excerpt: str


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    domains: list[str] = Field(default_factory=list, max_length=30)
    conversation_id: str | None = None


class RetrievalDiagnostics(BaseModel):
    dense_candidates: int
    bm25_candidates: int
    fused_candidates: int
    reranker: str
    top_candidates: list[dict] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    conversation_id: str
    insufficient_evidence: bool
    retrieval: RetrievalDiagnostics | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict]
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)

