"""
build_vectors.py — Generate multilingual embeddings for all Quran translations
and upload to Supabase pgvector.

Setup:
    pip install sentence-transformers supabase python-dotenv tqdm

Environment (.env):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=your-service-role-key
"""

import os, json, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from supabase import create_client

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / 'data'

# Languages to embed — skip partial/low-quality ones if desired
LANGS = {
    'ar':  'Arabic',
    'ur':  'Urdu',
    'es':  'Spanish',
    'zh':  'Chinese',
    'far': 'Persian',
    'ind': 'Indonesian',
    'bal': 'Balochi',
    'lez': 'Lezgian',
    'ira': 'Iranouniya',
    'ku':  'Kurdish',
    'tr':  'Turkish',
    'de':  'German',
}

# Multilingual model — supports Arabic, Urdu, Persian, Chinese, Spanish, etc.
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
BATCH_SIZE = 128   # sentences per batch — tune to your RAM
EMBED_DIM  = 384   # output dimension for this model

# ── Supabase SQL (run once in Supabase SQL editor before first run) ───────────
SETUP_SQL = """
-- Enable pgvector extension
create extension if not exists vector;

-- Main table
create table if not exists verse_vectors (
  id        bigserial primary key,
  surah     smallint not null,
  ayah      smallint not null,
  lang      text     not null,
  text      text     not null,
  embedding vector(384),
  unique (surah, ayah, lang)
);

-- HNSW index for fast approximate nearest-neighbor search
create index if not exists verse_vectors_embedding_idx
  on verse_vectors
  using hnsw (embedding vector_cosine_ops);
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_verses(lang: str) -> list[dict]:
    path = DATA_DIR / lang / f'quran_{lang}.json'
    if not path.exists():
        print(f'  ⚠  {path} not found — skipping')
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        sys.exit('❌  Set SUPABASE_URL and SUPABASE_KEY in .env')

    print(f'🔗  Connecting to Supabase …')
    sb = create_client(url, key)

    print(f'📦  Loading model: {MODEL_NAME}')
    model = SentenceTransformer(MODEL_NAME)

    # Check already-uploaded languages using per-lang count
    print('Checking existing data in Supabase ...')
    done_langs = set()
    for lang in LANGS:
        try:
            res = sb.table('verse_vectors').select('id', count='exact').eq('lang', lang).execute()
            cnt = res.count or 0
            if cnt >= 6000:
                done_langs.add(lang)
                print(f'  skip {lang} — already has {cnt} rows')
        except Exception as e:
            print(f'  Could not check {lang}: {e}')

    total_inserted = 0

    for lang, lang_name in LANGS.items():
        if lang in done_langs:
            print(f'\n── {lang_name} ({lang}) — SKIPPED (already uploaded) ──')
            continue

        verses = load_verses(lang)
        if not verses:
            continue

        print(f'\n── {lang_name} ({lang}) — {len(verses)} verses ──')

        # Build text list
        texts  = [v['text'] for v in verses]
        metas  = [{'surah': v['surah'], 'ayah': v['ayah'], 'lang': lang, 'text': v['text']}
                  for v in verses]

        # Encode in batches
        embeddings = []
        for batch in tqdm(list(chunks(texts, BATCH_SIZE)), desc='  embedding'):
            embeddings.extend(model.encode(batch, show_progress_bar=False).tolist())

        # Upload in small batches with delay to avoid rate limiting
        rows = [
            {**meta, 'embedding': emb}
            for meta, emb in zip(metas, embeddings)
        ]

        inserted = 0
        for i, batch in enumerate(tqdm(list(chunks(rows, 20)), desc='  uploading')):
            for attempt in range(5):
                try:
                    sb.table('verse_vectors').upsert(batch, on_conflict='surah,ayah,lang').execute()
                    inserted += len(batch)
                    break
                except Exception as e:
                    wait = 10 * (attempt + 1)
                    print(f'  ⚠  Upload error (attempt {attempt+1}): {e} — retrying in {wait}s')
                    time.sleep(wait)
            else:
                print(f'  ✗  Batch failed after 5 attempts, skipping')
            # Small delay every batch to avoid rate limiting
            time.sleep(0.3)
            # Longer pause every 50 batches
            if (i + 1) % 50 == 0:
                time.sleep(3)

        total_inserted += inserted
        print(f'  ✅  {inserted} rows uploaded')

    print(f'\n🎉  Done — {total_inserted} total rows in Supabase')
    print('\nNext step: deploy the search API (search_api.py)')


if __name__ == '__main__':
    main()
