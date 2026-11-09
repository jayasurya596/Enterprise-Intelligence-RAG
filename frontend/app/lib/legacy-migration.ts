import { Firestore, collection, doc, getDocs, limit, orderBy, query } from "firebase/firestore";
import type { User } from "firebase/auth";
import {
  importLegacyConversation,
  importLegacyDocument,
  legacyMigrationComplete,
  markLegacyMigrationComplete,
  type Conversation,
  type LegacyDocument,
  type Message,
} from "./knowledge-store";

function dateString(value: unknown): string {
  if (value && typeof value === "object" && "toDate" in value && typeof value.toDate === "function") {
    return value.toDate().toISOString();
  }
  if (typeof value === "string" && Number.isFinite(Date.parse(value))) return new Date(value).toISOString();
  return new Date().toISOString();
}

export async function migrateLegacyFirestoreWorkspace(db: Firestore, user: User): Promise<void> {
  if (await legacyMigrationComplete(user)) return;

  const documentSnapshots = await getDocs(query(
    collection(db, "users", user.uid, "documents"),
    orderBy("created_at", "desc"),
    limit(50),
  ));
  for (const snapshot of documentSnapshots.docs) {
    const data = snapshot.data();
    const chunkSnapshots = await getDocs(collection(db, "users", user.uid, "documents", snapshot.id, "chunks"));
    const chunks = chunkSnapshots.docs.map((chunkSnapshot) => {
      const chunk = chunkSnapshot.data();
      return {
        id: chunkSnapshot.id,
        page_number: typeof chunk.page_number === "number" ? chunk.page_number : null,
        text: String(chunk.text ?? ""),
      };
    }).filter((chunk) => chunk.text.length > 0);
    if (!chunks.length) continue;
    const item: LegacyDocument = {
      id: snapshot.id,
      source_name: String(data.source_name ?? "Imported document").slice(0, 240),
      content_type: String(data.content_type ?? "application/octet-stream").slice(0, 120),
      byte_size: Math.max(0, Number(data.byte_size ?? 0)),
      domain_labels: Array.isArray(data.domain_labels) ? data.domain_labels.map(String) : ["financial"],
      created_at: dateString(data.created_at),
      chunks,
    };
    await importLegacyDocument(user, item);
  }

  const conversationSnapshots = await getDocs(query(
    collection(db, "users", user.uid, "conversations"),
    orderBy("updated_at", "desc"),
    limit(50),
  ));
  for (const snapshot of conversationSnapshots.docs) {
    const data = snapshot.data();
    const messageSnapshots = await getDocs(query(
      collection(db, "users", user.uid, "conversations", snapshot.id, "messages"),
      orderBy("created_at", "asc"),
      limit(100),
    ));
    const messages: Message[] = messageSnapshots.docs.map((messageSnapshot) => {
      const message = messageSnapshot.data();
      return {
        id: messageSnapshot.id,
        role: String(message.role ?? "assistant"),
        content: String(message.content ?? ""),
        citations: Array.isArray(message.citations) ? message.citations : [],
        created_at: dateString(message.created_at),
      };
    }).filter((message) => message.content.length > 0);
    const conversation: Conversation = {
      id: snapshot.id,
      title: String(data.title ?? "Imported conversation").slice(0, 80),
      updated_at: dateString(data.updated_at),
    };
    await importLegacyConversation(user, conversation, messages);
  }

  await markLegacyMigrationComplete(user);
}
