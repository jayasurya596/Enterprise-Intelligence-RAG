import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.generation import generate_answer, validate_citations
from app.models import Conversation, Message, User
from app.retrieval import search_hybrid
from app.schemas import AskRequest, AskResponse, ConversationOut, MessageOut, RetrievalDiagnostics
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.owner_id == user.id))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    if conversation is None:
        conversation = Conversation(owner_id=user.id, title=payload.question.strip()[:100])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history = []
    if conversation.messages:
        history = [{"role": message.role, "content": message.content} for message in conversation.messages[-6:]]
    evidence, diagnostics = search_hybrid(db, payload.question, user.id, payload.domains)
    citations = []
    insufficient = not evidence
    if insufficient:
        answer = "I couldn't find enough indexed evidence to answer that question. Try uploading relevant material or selecting another domain."
    else:
        try:
            raw_answer = generate_answer(payload.question, evidence, history)
        except Exception as exc:
            logger.exception("Answer provider failed")
            raise HTTPException(status_code=503, detail="The configured answer provider is unavailable. Check provider settings and retry.") from exc
        answer, citations = validate_citations(raw_answer, evidence)
        if not citations or not answer:
            insufficient = True
            answer = "I couldn't produce a verifiable answer from the retrieved evidence. Try narrowing the question or uploading a more relevant source."
            citations = []

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question, citations=[]))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer, citations=citations))
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    response = {"answer": answer, "citations": citations, "conversation_id": conversation.id, "insufficient_evidence": insufficient, "retrieval": diagnostics if settings.app_env != "production" else None}
    return response


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversations = db.scalars(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.owner_id == user.id).order_by(Conversation.updated_at.desc()).limit(100)).all()
    return [_conversation_out(item) for item in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = db.scalar(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id, Conversation.owner_id == user.id))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return _conversation_out(conversation)


def _conversation_out(item: Conversation) -> ConversationOut:
    messages = [MessageOut(id=message.id, role=message.role, content=message.content, citations=message.citations or [], created_at=message.created_at) for message in item.messages]
    return ConversationOut(id=item.id, title=item.title, created_at=item.created_at, updated_at=item.updated_at, messages=messages)

