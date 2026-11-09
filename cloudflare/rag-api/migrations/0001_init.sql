CREATE TABLE IF NOT EXISTS users (
  uid TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  email_verified INTEGER NOT NULL CHECK (email_verified IN (0, 1)),
  legacy_imported INTEGER NOT NULL DEFAULT 0 CHECK (legacy_imported IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  owner_uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK (byte_size >= 0 AND byte_size <= 5242880),
  domain_labels_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  chunk_count INTEGER NOT NULL CHECK (chunk_count BETWEEN 1 AND 20)
);
CREATE INDEX IF NOT EXISTS documents_owner_created ON documents(owner_uid, created_at DESC);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT NOT NULL,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  owner_uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
  vector_id TEXT NOT NULL UNIQUE,
  page_number INTEGER,
  text TEXT NOT NULL CHECK (length(text) <= 2000),
  created_at TEXT NOT NULL,
  PRIMARY KEY (document_id, id)
);
CREATE INDEX IF NOT EXISTS chunks_owner ON chunks(owner_uid);
CREATE INDEX IF NOT EXISTS chunks_vector ON chunks(vector_id);

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  owner_uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
  title TEXT NOT NULL CHECK (length(title) <= 80),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS conversations_owner_updated ON conversations(owner_uid, updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  owner_uid TEXT NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL CHECK (length(content) <= 10000),
  citations_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_conversation_created ON messages(owner_uid, conversation_id, created_at);
