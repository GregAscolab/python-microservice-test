const CACHE_NAME = 'rockmeter-cache-v1';
const urlsToCache = [
    '/',
    '/dashboard',
    '/gps',
    '/logger',
    '/map',
    '/sensors',
    '/settings',
    '/offline',
    '/static/css/styles.css',
    '/static/js/connection.js',
    '/static/js/dashboard.js',
    '/static/js/gps.js',
    '/static/js/logger.js',
    '/static/js/map.js',
    '/static/js/sensors.js',
    '/static/js/settings.js',
    '/static/libs/jquery/jquery-3.7.1.min.js',
    '/static/libs/leaflet/leaflet.css',
    '/static/libs/leaflet/leaflet.js',
    '/static/libs/plotly/plotly-2.32.0.min.js',
    '/manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            caches.match(event.request)
                .then(response => {
                    return response || fetch(event.request)
                        .then(fetchResponse => {
                            return caches.open(CACHE_NAME).then(cache => {
                                cache.put(event.request, fetchResponse.clone());
                                return fetchResponse;
                            });
                        });
                })
                .catch(() => {
                    return caches.match('/offline');
                })
        );
    } else {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    return caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                })
                .catch(() => {
                    return caches.match(event.request);
                })
        );
    }
});
