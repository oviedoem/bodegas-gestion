/* Service Worker — Bodegas Gestión */
/* VERSIÓN: cambiar este string en cada deploy para forzar refresh en todos los dispositivos */
const CACHE_VERSION = 'bodegas-gestion-v27';

self.addEventListener('install', e => {
  /* No llamar skipWaiting() aqui — el banner en index.html controla cuando activar */
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('activate', e => {
  /* Borrar todos los caches de versiones anteriores */
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_VERSION)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim()) /* tomar control de todas las tabs abiertas */
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  /* Solo manejar mismo origen */
  if (url.origin !== self.location.origin) return;

  /* HTML (navegación): siempre red primero, sin caché */
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  /* JSON de datos: red primero (para tener datos frescos), cache como fallback */
  if (url.pathname.endsWith('.json')) {
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
