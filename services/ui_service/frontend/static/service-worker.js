const CACHE_NAME = 'rockmeter-cache-v1';
const urlsToCache = [
  '/',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/js/connection_manager.js',
  '/static/libs/leaflet/leaflet.js',
  '/static/libs/plotly/plotly.min.js',
  '/static/libs/leaflet/leaflet.css',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',
  '/static/images/favicon.ico'
];

// Install a service worker
self.addEventListener('install', event => {
  // Perform install steps
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Cache and return requests
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Update a service worker
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
