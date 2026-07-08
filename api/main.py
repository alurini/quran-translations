"""
Quran Semantic Search API
Deploy on Render.com as a Python web service.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from supabase import create_client

load_dotenv()

app = FastAPI(title='Quran Semantic Search', version='1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)

MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_db():
    return create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))


def embed(text: str) -> list[float]:
    return get_model().encode(text).tolist()


def fmt(rows: list[dict]) -> list[dict]:
    return [
        {
            'surah': r['surah'],
            'ayah':  r['ayah'],
            'lang':  r['lang'],
            'text':  r['text'],
            'score': round(1 - r.get('distance', 0), 4),
        }
        for r in rows
    ]


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/search')
def search(
    q:     str        = Query(..., description='Search query (any language)'),
    lang:  str | None = Query(None, description='Language code: ar, ur, es, zh, far, ind, bal, lez, ira, ku, tr, de'),
    limit: int        = Query(5, ge=1, le=20),
):
    """Find verses closest in meaning to the query."""
    vector = embed(q)
    fn     = 'search_verses_lang' if lang else 'search_verses'
    params = {'query_embedding': vector, 'match_count': limit}
    if lang:
        params['filter_lang'] = lang
    result = get_db().rpc(fn, params).execute()
    return {'query': q, 'lang': lang, 'results': fmt(result.data)}


@app.get('/similar')
def similar(
    surah: int = Query(..., ge=1, le=114),
    ayah:  int = Query(..., ge=1),
    lang:  str = Query('ar'),
    limit: int = Query(5, ge=1, le=20),
):
    """Find verses similar to a given verse."""
    db  = get_db()
    row = (db.table('verse_vectors')
             .select('embedding')
             .eq('surah', surah).eq('ayah', ayah).eq('lang', lang)
             .single().execute())
    if not row.data:
        return {'error': f'{lang} {surah}:{ayah} not found'}
    result = db.rpc('search_verses', {
        'query_embedding': row.data['embedding'],
        'match_count': limit + 1
    }).execute()
    results = [r for r in result.data if not (r['surah'] == surah and r['ayah'] == ayah)][:limit]
    return {'surah': surah, 'ayah': ayah, 'lang': lang, 'similar': fmt(results)}
