"""
Download full Turkish translation (Ali Ozek et al., King Fahd Complex)
from quranenc.com API identifier: turkish_shahin
"""
import urllib.request, json, sys, time
sys.stdout.reconfigure(encoding='utf-8')

AYAH_C = [7,286,200,176,120,165,206,75,129,109,123,111,43,52,99,128,111,110,98,135,
           112,78,118,64,77,227,93,88,69,60,34,30,73,54,45,83,182,88,75,85,54,53,89,
           59,37,35,38,29,18,45,60,49,62,55,78,96,29,22,24,13,14,11,11,18,12,12,30,
           52,52,44,28,28,20,56,40,31,50,40,46,42,29,19,36,25,22,17,19,26,30,20,15,
           21,11,8,8,19,5,8,8,11,11,8,3,9,5,4,7,3,6,3,5,4,5,6]

OUT = r'C:\Quran\data\tr\quran_tr.json'

def fetch_surah(s):
    url = f'https://quranenc.com/api/v1/translation/sura/turkish_shahin/{s}'
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
