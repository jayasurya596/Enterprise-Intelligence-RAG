import {
  collection,
  deleteDoc,
  doc,
  Firestore,
  getDocs,
  limit,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
  where,
  writeBatch,
} from "firebase/firestore";
import { chunkPages, extractDocumentText } from "./file-processing";

export type DocumentItem = {
  id: string;
  source_name: string;
  status: string;
  byte_size: number;
  domain_labels: string[];
  error_summary: string | null;
  created_at: string;
  chunk_count: number;
};

export type Citation = {
  marker: string;
  document_id: string;
  chunk_id: string;
  document_name: string;
  page_number: number | null;
  excerpt: string;
};

export type Message = { id: string; role: string; content: string; citations: Citation[]; created_at: string };
export type Conversation = { id: string; title: string; updated_at: string };

type SearchChunk = { id: string; document_id: string; document_name: string; page_number: number | null; text: string; domain_labels: string[] };

const MAX_WORKSPACE_CHUNKS = 1_000;
const MAX_WORKSPACE_DOCUMENTS = 50;
const MAX_CHUNKS_PER_DOCUMENT = 20;
const MAX_CONVERSATIONS_PER_WORKSPACE = 50;
const MAX_MESSAGES_PER_CONVERSATION = 100;

function slotIndex(id: string): number {
  return Number(id.slice(id.lastIndexOf("_") + 1));
}

function slotId(prefix: "document" | "chunk" | "conversation" | "message", index: number): string {
  return `${prefix}_${String(index).padStart(3, "0")}`;
}

function timestampString(value: unknown): string {
  if (value && typeof value === "object" && "toDate" in value && typeof value.toDate === "function") {
    return value.toDate().toISOString();
  }
  return new Date().toISOString();
}

function documentCollection(db: Firestore, uid: string) {
  return collection(db, "users", uid, "documents");
}

function chunkCollection(db: Firestore, uid: string, documentId: string) {
  return collection(db, "users", uid, "documents", documentId, "chunks");
}

export async function listDocuments(db: Firestore, uid: string): Promise<DocumentItem[]> {
  const result = await getDocs(query(documentCollection(db, uid), orderBy("created_at", "desc")));
  return result.docs.map((snapshot) => {
    const data = snapshot.data();
    return {
      id: snapshot.id,
      source_name: String(data.source_name ?? "Untitled document"),
      status: String(data.status ?? "ready"),
      byte_size: Number(data.byte_size ?? 0),
      domain_labels: Array.isArray(data.domain_labels) ? data.domain_labels.map(String) : [],
      error_summary: typeof data.error_summary === "string" ? data.error_summary : null,
      created_at: timestampString(data.created_at),
      chunk_count: Number(data.chunk_count ?? 0),
    };
  });
}

export async function addDocument(db: Firestore, uid: string, file: File, labels: string[]): Promise<DocumentItem> {
  const existing = await listDocuments(db, uid);
  if (existing.length >= MAX_WORKSPACE_DOCUMENTS) {
    throw new Error("This workspace has reached its 50-document free limit. Delete an older document to continue.");
  }
  const usedChunks = existing.reduce((total, item) => total + item.chunk_count, 0);
  const pages = await extractDocumentText(file);
  const chunks = chunkPages(pages);
  if (chunks.length > MAX_CHUNKS_PER_DOCUMENT) {
    throw new Error("This document needs more than 20 search chunks. Reduce its size to stay within the free prototype limit.");
  }
  if (usedChunks + chunks.length > MAX_WORKSPACE_CHUNKS) {
    throw new Error("This workspace has reached its 1,000 searchable-chunk free limit. Delete older documents to continue.");
  }

  const normalizedLabels = [...new Set(labels.map((label) => label.trim().toLowerCase().slice(0, 40)).filter(Boolean))].slice(0, 10);
  if (normalizedLabels.length === 0) normalizedLabels.push("financial");
  const occupiedDocumentIds = new Set(existing.map((item) => item.id));
  const documentSlot = Array.from({ length: MAX_WORKSPACE_DOCUMENTS }, (_, index) => index)
    .find((index) => !occupiedDocumentIds.has(slotId("document", index)));
  if (documentSlot === undefined) {
    throw new Error("This workspace has reached its 50-document free limit. Delete an older document to continue.");
  }
  const documentRef = doc(documentCollection(db, uid), slotId("document", documentSlot));
  const createdAt = serverTimestamp();
  await setDoc(documentRef, {
    source_name: file.name.slice(0, 240),
    content_type: (file.type || "application/octet-stream").slice(0, 120),
    byte_size: file.size,
    status: "processing",
    error_summary: null,
    domain_labels: normalizedLabels,
    chunk_count: chunks.length,
    created_at: createdAt,
  });

  try {
    const batch = writeBatch(db);
    for (const [index, chunk] of chunks.entries()) {
      const chunkRef = doc(chunkCollection(db, uid, documentRef.id), slotId("chunk", index));
      batch.set(chunkRef, {
        document_id: documentRef.id,
        document_name: file.name.slice(0, 240),
        page_number: chunk.pageNumber,
        text: chunk.text,
        domain_labels: normalizedLabels,
        created_at: createdAt,
      });
    }
    await batch.commit();
    await updateDoc(documentRef, { status: "ready" });
  } catch (error) {
    await removeDocument(db, uid, documentRef.id).catch(() => undefined);
    throw error;
  }

  return {
    id: documentRef.id,
    source_name: file.name,
    status: "ready",
    byte_size: file.size,
    domain_labels: normalizedLabels,
    error_summary: null,
    created_at: new Date().toISOString(),
    chunk_count: chunks.length,
  };
}

export async function removeDocument(db: Firestore, uid: string, documentId: string): Promise<void> {
  const chunks = await getDocs(chunkCollection(db, uid, documentId));
  for (let start = 0; start < chunks.docs.length; start += 400) {
    const batch = writeBatch(db);
    for (const snapshot of chunks.docs.slice(start, start + 400)) batch.delete(snapshot.ref);
    await batch.commit();
  }
  await deleteDoc(doc(db, "users", uid, "documents", documentId));
}

export async function listConversations(db: Firestore, uid: string): Promise<Conversation[]> {
  const result = await getDocs(query(collection(db, "users", uid, "conversations"), orderBy("updated_at", "desc"), limit(50)));
  return result.docs.map((snapshot) => ({
    id: snapshot.id,
    title: String(snapshot.data().title ?? "New conversation"),
    updated_at: timestampString(snapshot.data().updated_at),
  }));
}

export async function listMessages(db: Firestore, uid: string, conversationId: string): Promise<Message[]> {
  const result = await getDocs(query(collection(db, "users", uid, "conversations", conversationId, "messages"), orderBy("created_at", "asc"), limit(100)));
  return [...result.docs].sort((left, right) => slotIndex(left.id) - slotIndex(right.id)).map((snapshot) => ({
    id: snapshot.id,
    role: String(snapshot.data().role ?? "assistant"),
    content: String(snapshot.data().content ?? ""),
    citations: Array.isArray(snapshot.data().citations) ? snapshot.data().citations as Citation[] : [],
    created_at: timestampString(snapshot.data().created_at),
  }));
}

export async function createConversation(db: Firestore, uid: string, firstQuestion: string): Promise<string> {
  const conversations = collection(db, "users", uid, "conversations");
  const existing = await getDocs(query(conversations, limit(MAX_CONVERSATIONS_PER_WORKSPACE)));
  if (existing.size >= MAX_CONVERSATIONS_PER_WORKSPACE) {
    throw new Error("This workspace has reached its 50-conversation free limit. Continue in an existing conversation.");
  }
  const occupied = new Set(existing.docs.map((snapshot) => snapshot.id));
  const conversationSlot = Array.from({ length: MAX_CONVERSATIONS_PER_WORKSPACE }, (_, index) => index)
    .find((index) => !occupied.has(slotId("conversation", index)));
  if (conversationSlot === undefined) {
    throw new Error("This workspace has reached its 50-conversation free limit. Continue in an existing conversation.");
  }
  const conversationRef = doc(conversations, slotId("conversation", conversationSlot));
  await setDoc(conversationRef, {
    title: firstQuestion.trim().slice(0, 80) || "New conversation",
    created_at: serverTimestamp(),
    updated_at: serverTimestamp(),
  });
  return conversationRef.id;
}

export async function saveMessage(db: Firestore, uid: string, conversationId: string, role: "user" | "assistant", content: string, citations: Citation[] = []): Promise<void> {
  const messages = collection(db, "users", uid, "conversations", conversationId, "messages");
  const existing = await getDocs(query(messages, limit(MAX_MESSAGES_PER_CONVERSATION)));
  if (existing.size >= MAX_MESSAGES_PER_CONVERSATION) {
    throw new Error("This conversation has reached its 100-message free limit. Start a new conversation to continue.");
  }
  const occupied = new Set(existing.docs.map((snapshot) => snapshot.id));
  const messageSlot = Array.from({ length: MAX_MESSAGES_PER_CONVERSATION }, (_, index) => index)
    .find((index) => !occupied.has(slotId("message", index)));
  if (messageSlot === undefined) {
    throw new Error("This conversation has reached its 100-message free limit.");
  }
  const batch = writeBatch(db);
  const messageRef = doc(messages, slotId("message", messageSlot));
  batch.set(messageRef, { role, content, citations, created_at: serverTimestamp() });
  batch.update(doc(db, "users", uid, "conversations", conversationId), { updated_at: serverTimestamp() });
  await batch.commit();
}

const STOP_WORDS = new Set("a an and are as at be by for from has have in is it its of on or that the their this to was were what when where which who why with your my our about into over under how does do can could should would will not but if then than them they you we i".split(" "));

function terms(value: string): string[] {
  return value.toLowerCase().match(/[\p{L}\p{N}]{2,}/gu)?.filter((word) => !STOP_WORDS.has(word)) ?? [];
}

export async function answerFromWorkspace(db: Firestore, uid: string, questionText: string, selectedDomains: string[]): Promise<{ answer: string; citations: Citation[] }> {
  const questionTerms = [...new Set(terms(questionText))];
  const allowed = new Set(selectedDomains.map((domain) => domain.toLowerCase()));
  const documents = await listDocuments(db, uid);
  const relevantDocuments = documents.filter((document) => !allowed.size || document.domain_labels.some((label) => allowed.has(label.toLowerCase())));
  const chunkSnapshots = await Promise.all(relevantDocuments.map((document) => getDocs(query(chunkCollection(db, uid, document.id), limit(100)))));
  const candidates: Array<{ chunk: SearchChunk; score: number }> = [];

  for (const snapshotGroup of chunkSnapshots) {
    for (const snapshot of snapshotGroup.docs) {
      const data = snapshot.data();
      const labels = Array.isArray(data.domain_labels) ? data.domain_labels.map((value: unknown) => String(value).toLowerCase()) : [];
      const text = String(data.text ?? "");
      const words = terms(text);
      if (!words.length) continue;
      const counts = new Map<string, number>();
      for (const word of words) counts.set(word, (counts.get(word) ?? 0) + 1);
      const score = questionTerms.reduce((total, word) => total + Math.min(counts.get(word) ?? 0, 3), 0) / Math.sqrt(words.length);
      if (score > 0) {
        candidates.push({
          score,
          chunk: {
            id: snapshot.id,
            document_id: String(data.document_id ?? ""),
            document_name: String(data.document_name ?? "Source document"),
            page_number: typeof data.page_number === "number" ? data.page_number : null,
            text,
            domain_labels: labels,
          },
        });
      }
    }
  }
  if (candidates.length > MAX_WORKSPACE_CHUNKS) candidates.length = MAX_WORKSPACE_CHUNKS;

  candidates.sort((left, right) => right.score - left.score);
  const selected = candidates.slice(0, 3);
  if (!selected.length) return { answer: "I couldn't find matching text in your indexed documents. Try another question or upload a source that covers this topic.", citations: [] };

  const citations = selected.map(({ chunk }, index) => ({
    marker: `[S${index + 1}]`,
    document_id: chunk.document_id,
    chunk_id: chunk.id,
    document_name: chunk.document_name,
    page_number: chunk.page_number,
    excerpt: chunk.text.slice(0, 900),
  }));
  const answer = citations.map((citation) => `${citation.marker} ${citation.excerpt}`).join("\n\n") + "\n\nThese are source excerpts ranked by word overlap; review the cited documents for context.";
  return { answer, citations };
}

