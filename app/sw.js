const CACHE_NAME = 'quran-v1';
const SHELL_URLS = ['./', './index.html', './manifest.json'];

// JSON files — relative paths (works both locally and on GitHub Pages)
const DATA_BASE = self.registration.scope.includes('github.io')
  ? 'https://raw.githubusercontent.com/alurini/quran-translations/main/data/'
  : '../data/';

const LANG_FILES = {
  ur:  DATA_BASE + 'ur/quran_ur.json',
  bal: DATA_BASE + 'bal/quran_bal.json',
  lez: DATA_BASE + 'lez/quran_lez.json',
  ira: DATA_BASE + 'ira/quran_ira.json',
  far: DATA_BASE + 'far/quran_far.json',
  ind: DATA_BASE + 'ind/quran_ind.json',
};

// Install — cache app shell only
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => c.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

// Activate — clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch — cache-first for JSON, network-first for shell
self.addEventListener('fetch', e => {
  const url = e.request.url;

  // JSON data files — cache first, fetch on miss
  const isData = Object.values(LANG_FILES).some(f => url.includes(f) || url.endsWith('.json'));
  if (isData) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        if (cached) return cached;
        return fetch(e.request).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  // App shell — cache first
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});

// Message: cache a specific language file
self.addEventListener('message', e => {
  if (e.data?.type === 'CACHE_LANG') {
    const url = LANG_FILES[e.data.lang];
    if (!url) return;
    caches.open(CACHE_NAME).then(c =>
      c.match(url).then(hit => {
        if (!hit) fetch(url).then(res => res.ok && c.put(url, res));
      })
    );
  }
  if (e.data?.type === 'GET_CACHED_LANGS') {
    caches.open(CACHE_NAME).then(c => c.keys()).then(keys => {
      const cached = Object.entries(LANG_FILES)
        .filter(([, url]) => keys.some(k => k.url === url || k.url.includes(url)))
        .map(([lang]) => lang);
      e.source.postMessage({ type: 'CACHED_LANGS', langs: cached });
    });
  }
});
