CREATE TABLE documents_scoped (
  id TEXT NOT NULL,
  owner_uid TEXT NOT NULL,
  source_name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK (byte_size >= 0 AND byte_size <= 5242880),
  domain_labels_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  chunk_count INTEGER NOT NULL CHECK (chunk_count BETWEEN 1 AND 20),
  PRIMARY KEY (owner_uid, id),
  FOREIGN KEY (owner_uid) REFERENCES users(uid) ON DELETE CASCADE
);
INSERT INTO documents_scoped (id, owner_uid, source_name, content_type, byte_size, domain_labels_json, created_at, chunk_count)
SELECT id, owner_uid, source_name, content_type, byte_size, domain_labels_json, created_at, chunk_count FROM documents;

CREATE TABLE chunks_scoped (
  id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  owner_uid TEXT NOT NULL,
  vector_id TEXT NOT NULL UNIQUE,
  page_number INTEGER,
  text TEXT NOT NULL CHECK (length(text) <= 2000),
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_uid, document_id, id),
  FOREIGN KEY (owner_uid, document_id) REFERENCES documents_scoped(owner_uid, id) ON DELETE CASCADE,
  FOREIGN KEY (owner_uid) REFERENCES users(uid) ON DELETE CASCADE
);
INSERT INTO chunks_scoped (id, document_id, owner_uid, vector_id, page_number, text, created_at)
SELECT id, document_id, owner_uid, vector_id, page_number, text, created_at FROM chunks;

CREATE TABLE conversations_scoped (
  id TEXT NOT NULL,
  owner_uid TEXT NOT NULL,
  title TEXT NOT NULL CHECK (length(title) <= 80),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (owner_uid, id),
  FOREIGN KEY (owner_uid) REFERENCES users(uid) ON DELETE CASCADE
);
INSERT INTO conversations_scoped (id, owner_uid, title, created_at, updated_at)
SELECT id, owner_uid, title, created_at, updated_at FROM conversations;

CREATE TABLE messages_scoped (
  id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  owner_uid TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL CHECK (length(content) <= 10000),
  citations_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_uid, conversation_id, id),
  FOREIGN KEY (owner_uid, conversation_id) REFERENCES conversations_scoped(owner_uid, id) ON DELETE CASCADE,
  FOREIGN KEY (owner_uid) REFERENCES users(uid) ON DELETE CASCADE
);
INSERT INTO messages_scoped (id, conversation_id, owner_uid, role, content, citations_json, created_at)
SELECT id, conversation_id, owner_uid, role, content, citations_json, created_at FROM messages;

DROP TABLE messages;
DROP TABLE conversations;
DROP TABLE chunks;
DROP TABLE documents;

ALTER TABLE documents_scoped RENAME TO documents;
ALTER TABLE chunks_scoped RENAME TO chunks;
ALTER TABLE conversations_scoped RENAME TO conversations;
ALTER TABLE messages_scoped RENAME TO messages;

CREATE INDEX documents_owner_created ON documents(owner_uid, created_at DESC);
CREATE INDEX chunks_owner ON chunks(owner_uid);
CREATE INDEX chunks_vector ON chunks(vector_id);
CREATE INDEX conversations_owner_updated ON conversations(owner_uid, updated_at DESC);
CREATE INDEX messages_conversation_created ON messages(owner_uid, conversation_id, created_at);
