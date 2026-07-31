"""
Download full Japanese translation (Saeed Sato / Yoichi Sato)
from quranenc.com API identifier: japanese_saeedsato
"""
import urllib.request, json, sys, time, os
sys.stdout.reconfigure(encoding='utf-8')

OUT = r'C:\Quran\data\ja\quran_ja.json'
os.makedirs(r'C:\Quran\data\ja', exist_ok=True)

def fetch_surah(s):
    url = f'https://quranenc.com/api/v1/translation/sura/japanese_saeedsato/{s}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())['result']
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep((attempt+1) * 3)

verses = []
gid = 0
for s in range(1, 115):
    ayahs = fetch_surah(s)
    for item in ayahs:
        gid += 1
        text = item.get('translation', '').strip()
        verses.append({'id': gid, 'surah': s, 'ayah': int(item['aya']), 'text': text})
    print(f'S{s}: {len(ayahs)} ayahs | total so far: {len(verses)}', flush=True)
    time.sleep(0.3)

print(f'\nTotal: {len(verses)}/6236')
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(verses, f, ensure_ascii=False, indent=2)
print(f'Saved -> {OUT}')
