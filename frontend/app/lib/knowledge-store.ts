import type { User } from "firebase/auth";
import { chunkPages, extractDocumentText } from "./file-processing";
import { cloudflareRequest } from "./cloudflare-client";

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
export type LegacyDocument = {
  id: string;
  source_name: string;
  content_type: string;
  byte_size: number;
  domain_labels: string[];
  created_at: string;
  chunks: Array<{ id: string; page_number: number | null; text: string }>;
};

export async function listDocuments(user: User): Promise<DocumentItem[]> {
  const result = await cloudflareRequest<{ documents: DocumentItem[] }>(user, "/api/documents");
  return result.documents;
}
export async function addDocument(user: User, file: File, labels: string[]): Promise<DocumentItem> {
  const pages = await extractDocumentText(file);
  const chunks = chunkPages(pages).map((chunk, index) => ({
    id: "chunk_" + String(index).padStart(3, "0"),
    page_number: chunk.pageNumber,
    text: chunk.text,
  }));
  const result = await cloudflareRequest<{ document: DocumentItem }>(user, "/api/documents", {
    method: "POST",
    body: JSON.stringify({
      source_name: file.name,
      content_type: file.type || "application/octet-stream",
      byte_size: file.size,
      domain_labels: labels,
      chunks,
    }),
  });
  return result.document;
}
export async function removeDocument(user: User, documentId: string): Promise<void> {
  await cloudflareRequest(user, "/api/documents", { method: "DELETE", body: JSON.stringify({ id: documentId }) });
}
export async function listConversations(user: User): Promise<Conversation[]> {
  const result = await cloudflareRequest<{ conversations: Conversation[] }>(user, "/api/conversations");
  return result.conversations;
}
export async function listMessages(user: User, conversationId: string): Promise<Message[]> {
  const result = await cloudflareRequest<{ messages: Message[] }>(user, "/api/conversations/" + encodeURIComponent(conversationId) + "/messages");
  return result.messages;
}
export async function createConversation(user: User, firstQuestion: string): Promise<string> {
  const result = await cloudflareRequest<{ id: string }>(user, "/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title: firstQuestion.trim().slice(0, 80) || "New conversation" }),
  });
  return result.id;
}
export async function saveMessage(user: User, conversationId: string, role: "user" | "assistant", content: string, citations: Citation[] = []): Promise<void> {
  await cloudflareRequest(user, "/api/conversations/" + encodeURIComponent(conversationId) + "/messages", {
    method: "POST",
    body: JSON.stringify({ role, content, citations }),
  });
}
export async function answerFromWorkspace(user: User, question: string, selectedDomains: string[]): Promise<{ answer: string; citations: Citation[] }> {
  return cloudflareRequest(user, "/api/answer", {
    method: "POST",
    body: JSON.stringify({ question, domains: selectedDomains }),
  });
}

export async function legacyMigrationComplete(user: User): Promise<boolean> {
  const result = await cloudflareRequest<{ legacy_imported: boolean }>(user, "/api/migrations/status");
  return result.legacy_imported;
}
export async function markLegacyMigrationComplete(user: User): Promise<void> {
  await cloudflareRequest(user, "/api/migrations/complete", { method: "POST", body: "{}" });
}
export async function importLegacyDocument(user: User, document: LegacyDocument): Promise<void> {
  await cloudflareRequest(user, "/api/documents", {
    method: "POST",
    body: JSON.stringify({ ...document, id: document.id }),
  });
}
export async function importLegacyConversation(user: User, conversation: Conversation, messages: Message[]): Promise<void> {
  await cloudflareRequest(user, "/api/conversations", {
    method: "POST",
    body: JSON.stringify({ id: conversation.id, title: conversation.title, created_at: conversation.updated_at, updated_at: conversation.updated_at }),
  });
  for (const message of messages) {
    await cloudflareRequest(user, "/api/conversations/" + encodeURIComponent(conversation.id) + "/messages", {
      method: "POST",
      body: JSON.stringify({
        id: message.id,
        role: message.role === "user" ? "user" : "assistant",
        content: message.content,
        citations: message.citations,
        created_at: message.created_at,
      }),
    });
  }
}
