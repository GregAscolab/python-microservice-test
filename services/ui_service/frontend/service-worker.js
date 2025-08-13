const CACHE_NAME = 'rockmeter-cache-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
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
    '/manifest.json',
    '/templates/index.html',
    '/templates/dashboard.html',
    '/templates/gps.html',
    '/templates/logger.html',
    '/templates/map.html',
    '/templates/sensors.html',
    '/templates/settings.html',
    '/templates/header.html',
    '/templates/footer.html',
    '/templates/sidebar.html'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});
