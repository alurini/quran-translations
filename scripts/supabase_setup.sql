-- ════════════════════════════════════════════════════════════════
-- Run this once in Supabase → SQL Editor before build_vectors.py
-- ════════════════════════════════════════════════════════════════

-- 1. Enable pgvector
create extension if not exists vector;

-- 2. Main table
create table if not exists verse_vectors (
  id        bigserial primary key,
  surah     smallint not null,
  ayah      smallint not null,
  lang      text     not null,
  text      text     not null,
  embedding vector(384),
  unique (surah, ayah, lang)
);

-- 3. HNSW index — fast cosine similarity search
create index if not exists verse_vectors_hnsw_idx
  on verse_vectors
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- ── Search functions ──────────────────────────────────────────────

-- Search across ALL languages
create or replace function search_verses(
  query_embedding vector(384),
  match_count     int default 5
)
returns table (
  surah    smallint,
  ayah     smallint,
  lang     text,
  text     text,
  distance float
)
language sql stable as $$
  select
    surah, ayah, lang, text,
    embedding <=> query_embedding as distance
  from verse_vectors
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- Search within a specific language
create or replace function search_verses_lang(
  query_embedding vector(384),
  filter_lang     text,
  match_count     int default 5
)
returns table (
  surah    smallint,
  ayah     smallint,
  lang     text,
  text     text,
  distance float
)
language sql stable as $$
  select
    surah, ayah, lang, text,
    embedding <=> query_embedding as distance
  from verse_vectors
  where lang = filter_lang
  order by embedding <=> query_embedding
  limit match_count;
$$;
