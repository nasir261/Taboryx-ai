const CACHE_NAME = 'medistock-ai-web-v3';
const APP_SHELL = ['/', '/index.html', '/styles.css', '/app.js', '/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  if (request.url.startsWith(self.location.origin + '/api/')) return;
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((networkResponse) => {
      if (networkResponse.ok && request.mode === 'navigate') {
        const copy = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      }
      return networkResponse;
    }))
  );
});
