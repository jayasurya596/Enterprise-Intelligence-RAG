CREATE TABLE IF NOT EXISTS daily_ai_usage (
  usage_day TEXT PRIMARY KEY,
  embedding_chars INTEGER NOT NULL DEFAULT 0 CHECK (embedding_chars >= 0),
  generation_chars INTEGER NOT NULL DEFAULT 0 CHECK (generation_chars >= 0),
  generation_tokens INTEGER NOT NULL DEFAULT 0 CHECK (generation_tokens >= 0)
);
