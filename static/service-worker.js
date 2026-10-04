const CACHE_STATIC_NAME = 'antipid-static-v2';
const CACHE_IMAGES_NAME = 'antipid-images-v2';

const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    '/static/images/AntTipidFavicon.png',
    '/static/images/AntTipidLogo-128.png',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap',
    // Must match the URL in templates/base.html exactly, or the cache never hits.
    'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..24,400..700,0..1,0&display=block'
];

// Install Event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_STATIC_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate Event
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_STATIC_NAME && key !== CACHE_IMAGES_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Fetch Event
// Pages are network-first so balances are never served stale; a cached copy is only
// the offline fallback. Static assets and fonts are cache-first.
self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/') || url.pathname.endsWith('.csv')) return;

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).then((networkResponse) => {
                if (networkResponse && networkResponse.ok) {
                    const copy = networkResponse.clone();
                    caches.open(CACHE_STATIC_NAME).then((cache) => cache.put(request, copy));
                }
                return networkResponse;
            }).catch(() => caches.match(request))
        );
        return;
    }

    const isFont = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
    const isStatic = url.origin === self.location.origin && url.pathname.startsWith('/static/');
    if (!isFont && !isStatic) return;

    const cacheName = /\.(png|jpe?g|webp|svg|gif)$/i.test(url.pathname) ? CACHE_IMAGES_NAME : CACHE_STATIC_NAME;
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) return cachedResponse;
            return fetch(request).then((networkResponse) => {
                // Font files come back opaque/cors from gstatic; cache those too.
                if (networkResponse && (networkResponse.ok || networkResponse.type === 'opaque')) {
                    const copy = networkResponse.clone();
                    caches.open(cacheName).then((cache) => cache.put(request, copy));
                }
                return networkResponse;
            });
        })
    );
});