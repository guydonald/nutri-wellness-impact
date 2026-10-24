{% load static %}/* Service worker Nutri-Wellness Impact
 * - fichiers statiques (CSS, JS, images, polices) : servis depuis le telephone puis mis a jour
 *   en arriere-plan -> les pages s'affichent beaucoup plus vite apres la 1re visite ;
 * - pages : toujours demandees au serveur (donnees medicales a jour, jamais stockees),
 *   avec une page "hors connexion" si le reseau est coupe.
 * Changer VERSION pour forcer la mise a jour du cache.
 */
const VERSION = 'nutri-v1';
const STATIC_CACHE = VERSION + '-static';
const OFFLINE_URL = '{% url "pwa_offline" %}';
const STATIC_PREFIX = '{% get_static_prefix %}';
const PRECACHE = [
  OFFLINE_URL,
  '{% static "css/styles.css" %}',
  '{% static "js/bootstrap.bundle.min.js" %}',
  '{% static "js/htmx.min.js" %}',
  '{% static "img/logo.png" %}',
  '{% static "pwa/icon-192.png" %}',
];
const CDN_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.jsdelivr.net'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function staleWhileRevalidate(request) {
  return caches.open(STATIC_CACHE).then((cache) =>
    cache.match(request).then((cached) => {
      const network = fetch(request).then((response) => {
        if (response && (response.ok || response.type === 'opaque')) cache.put(request, response.clone());
        return response;
      }).catch(() => cached);
      return cached || network;
    })
  );
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Fichiers statiques du site et polices / icones des CDN
  if ((url.origin === self.location.origin && url.pathname.startsWith(STATIC_PREFIX)) ||
      CDN_HOSTS.includes(url.hostname)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Pages : reseau d'abord, page hors connexion en secours
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
  }
});
