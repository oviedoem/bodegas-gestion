/* Service Worker — Bodegas Gestión */
const CACHE_VERSION = 'bodegas-gestion-v70';

self.addEventListener('install', e => {
  /* Activar inmediatamente — sin esperar clic del usuario */
  self.skipWaiting();
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_VERSION)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  if (url.origin !== self.location.origin) return;

  /* HTML (navegación): siempre red primero, sin caché */
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  /* JSON de datos: red primero (datos frescos), cache como fallback */
  if (url.pathname.endsWith('.json') || url.pathname.endsWith('.enc')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_VERSION).then(c => c.put(e.request, clone));
          }
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  /* Resto: cache primero */
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
