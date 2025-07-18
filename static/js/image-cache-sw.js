// Service Worker for persistent image caching
// This will cache images across browser sessions for faster loading

const CACHE_NAME = 'pokemon-tcg-images-v1';
const MAX_CACHE_SIZE = 50; // Maximum number of images to cache
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

// Install event - set up the cache
self.addEventListener('install', event => {
    console.log('Image cache service worker installing...');
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('Image cache opened');
            return cache;
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Image cache service worker activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event - intercept image requests
self.addEventListener('fetch', event => {
    const request = event.request;
    
    // Only cache proxy image requests
    if (request.url.includes('/api/proxy-image')) {
        event.respondWith(handleImageRequest(request));
    }
});

async function handleImageRequest(request) {
    const cache = await caches.open(CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    // Check if we have a cached response and if it's still valid
    if (cachedResponse) {
        const cachedDate = cachedResponse.headers.get('sw-cached-date');
        if (cachedDate) {
            const cacheAge = Date.now() - parseInt(cachedDate);
            if (cacheAge < CACHE_DURATION) {
                console.log('Serving from service worker cache:', request.url);
                return cachedResponse;
            } else {
                console.log('Cached image expired, removing:', request.url);
                await cache.delete(request);
            }
        }
    }
    
    try {
        // Fetch from network
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Clone the response to cache it
            const responseToCache = networkResponse.clone();
            
            // Add cache timestamp header
            const headers = new Headers(responseToCache.headers);
            headers.set('sw-cached-date', Date.now().toString());
            
            const cachedResponse = new Response(responseToCache.body, {
                status: responseToCache.status,
                statusText: responseToCache.statusText,
                headers: headers
            });
            
            // Manage cache size before adding new item
            await manageCacheSize(cache);
            
            // Cache the response
            await cache.put(request, cachedResponse);
            console.log('Cached image:', request.url);
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Error fetching image:', error);
        
        // If network fails, try to return cached version even if expired
        if (cachedResponse) {
            console.log('Network failed, serving expired cache:', request.url);
            return cachedResponse;
        }
        
        // Return a placeholder image if all else fails
        return new Response(
            createPlaceholderSVG(),
            {
                headers: {
                    'Content-Type': 'image/svg+xml',
                    'Cache-Control': 'no-cache'
                }
            }
        );
    }
}

async function manageCacheSize(cache) {
    const keys = await cache.keys();
    
    if (keys.length >= MAX_CACHE_SIZE) {
        // Remove oldest entries (simple FIFO approach)
        const keysToDelete = keys.slice(0, keys.length - MAX_CACHE_SIZE + 1);
        
        await Promise.all(
            keysToDelete.map(key => {
                console.log('Removing old cached image:', key.url);
                return cache.delete(key);
            })
        );
    }
}

function createPlaceholderSVG() {
    return `
        <svg width="110" height="154" viewBox="0 0 110 154" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="a" x1="0" y1="0" x2="1" y2="0">
                    <stop stop-color="#34495e"/>
                    <stop offset="1" stop-color="#2c3e50"/>
                </linearGradient>
            </defs>
            <rect width="110" height="154" fill="url(#a)" rx="6"/>
            <text x="55" y="77" fill="#95a5a6" font-family="sans-serif" font-size="12" text-anchor="middle">Card</text>
        </svg>
    `;
}

// Handle messages from the main thread
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'CACHE_STATS') {
        getCacheStats().then(stats => {
            event.ports[0].postMessage(stats);
        });
    } else if (event.data && event.data.type === 'CLEAR_CACHE') {
        clearImageCache().then(() => {
            event.ports[0].postMessage({ success: true });
        });
    }
});

async function getCacheStats() {
    try {
        const cache = await caches.open(CACHE_NAME);
        const keys = await cache.keys();
        
        let totalSize = 0;
        const entries = [];
        
        for (const key of keys) {
            const response = await cache.match(key);
            if (response) {
                const cachedDate = response.headers.get('sw-cached-date');
                const size = response.headers.get('content-length') || 0;
                totalSize += parseInt(size);
                
                entries.push({
                    url: key.url,
                    cachedDate: cachedDate ? new Date(parseInt(cachedDate)) : null,
                    size: parseInt(size)
                });
            }
        }
        
        return {
            totalEntries: keys.length,
            totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
            maxCacheSize: MAX_CACHE_SIZE,
            cacheDurationHours: CACHE_DURATION / (60 * 60 * 1000),
            entries: entries
        };
    } catch (error) {
        console.error('Error getting cache stats:', error);
        return { error: error.message };
    }
}

async function clearImageCache() {
    try {
        const cache = await caches.open(CACHE_NAME);
        const keys = await cache.keys();
        
        await Promise.all(
            keys.map(key => cache.delete(key))
        );
        
        console.log('Image cache cleared');
        return { success: true };
    } catch (error) {
        console.error('Error clearing cache:', error);
        return { error: error.message };
    }
}