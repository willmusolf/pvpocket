// Service Worker for persistent image caching
// This will cache images across browser sessions for faster loading

const CACHE_NAME = 'pokemon-tcg-images-v2';
const MAX_CACHE_SIZE = 200; // Increased maximum number of images to cache
const CACHE_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds (increased from 24 hours)
const HIGH_PRIORITY_CACHE_SIZE = 50; // Reserve space for high-priority images

// Install event - set up the cache
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache;
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
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
    
    // Cache CDN images and card images directly (now that CORS is configured)
    if (request.url.includes('cdn.pvpocket.xyz') || 
        request.url.includes('firebasestorage.googleapis.com') ||
        request.url.includes('/api/proxy-image')) { // Keep proxy support for legacy/fallback
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
                // Update access metadata for cache management
                await updateAccessMetadata(cache, request, cachedResponse);
                
                return cachedResponse;
            } else {
                // Cached image expired, removing
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
            
            // Add cache metadata headers
            const headers = new Headers(responseToCache.headers);
            const now = Date.now().toString();
            headers.set('sw-cached-date', now);
            headers.set('sw-last-accessed', now);
            headers.set('sw-access-count', '1');
            
            const cachedResponse = new Response(responseToCache.body, {
                status: responseToCache.status,
                statusText: responseToCache.statusText,
                headers: headers
            });
            
            // Manage cache size before adding new item
            await manageCacheSize(cache);
            
            // Cache the response
            await cache.put(request, cachedResponse);
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Error fetching image:', error);
        
        // If network fails, try to return cached version even if expired
        if (cachedResponse) {
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
        // Get metadata for all cached items
        const cacheEntries = await Promise.all(
            keys.map(async (key) => {
                const response = await cache.match(key);
                const cachedDate = response?.headers.get('sw-cached-date') || Date.now();
                const accessCount = parseInt(response?.headers.get('sw-access-count') || '1');
                const isHighRes = key.url.includes('high_res_cards');
                
                return {
                    key,
                    cachedDate: parseInt(cachedDate),
                    accessCount,
                    isHighRes,
                    lastAccessed: parseInt(response?.headers.get('sw-last-accessed') || cachedDate)
                };
            })
        );

        // Sort by priority score (lower = delete first)
        cacheEntries.sort((a, b) => {
            // High-res images get bonus points
            const scoreA = calculatePriorityScore(a);
            const scoreB = calculatePriorityScore(b);
            return scoreA - scoreB;
        });

        // Delete oldest/least used entries, but preserve high-priority items
        const entriesToDelete = cacheEntries.slice(0, Math.ceil(keys.length * 0.25));
        const keysToDelete = entriesToDelete
            .filter(entry => !shouldPreserve(entry, cacheEntries))
            .map(entry => entry.key);
        
        await Promise.all(
            keysToDelete.map(key => {
                return cache.delete(key);
            })
        );
    }
}

function calculatePriorityScore(entry) {
    const now = Date.now();
    const ageHours = (now - entry.cachedDate) / (1000 * 60 * 60);
    const timeSinceAccess = (now - entry.lastAccessed) / (1000 * 60 * 60);
    
    // Base score (higher = keep longer)
    let score = entry.accessCount * 10; // Access frequency
    
    // Bonus for high-res images
    if (entry.isHighRes) {
        score += 50;
    }
    
    // Penalty for old age
    score -= ageHours * 0.5;
    
    // Penalty for not being accessed recently
    score -= timeSinceAccess * 2;
    
    return score;
}

function shouldPreserve(entry, allEntries) {
    // Always preserve the most frequently accessed high-res images
    if (entry.isHighRes && entry.accessCount >= 3) {
        return true;
    }
    
    // Preserve recently accessed items (within 1 hour)
    const oneHourAgo = Date.now() - (60 * 60 * 1000);
    if (entry.lastAccessed > oneHourAgo) {
        return true;
    }
    
    return false;
}

async function updateAccessMetadata(cache, request, cachedResponse) {
    try {
        const accessCount = parseInt(cachedResponse.headers.get('sw-access-count') || '1');
        const cachedDate = cachedResponse.headers.get('sw-cached-date');
        
        // Create updated response with incremented access count
        const headers = new Headers(cachedResponse.headers);
        headers.set('sw-access-count', (accessCount + 1).toString());
        headers.set('sw-last-accessed', Date.now().toString());
        
        const updatedResponse = new Response(cachedResponse.body, {
            status: cachedResponse.status,
            statusText: cachedResponse.statusText,
            headers: headers
        });
        
        // Update the cache with new metadata
        await cache.put(request, updatedResponse.clone());
    } catch (error) {
        // Failed to update access metadata (silent)
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
                const lastAccessed = response.headers.get('sw-last-accessed');
                const accessCount = response.headers.get('sw-access-count');
                const size = response.headers.get('content-length') || 0;
                const isHighRes = key.url.includes('high_res_cards');
                
                totalSize += parseInt(size);
                
                entries.push({
                    url: key.url,
                    cachedDate: cachedDate ? new Date(parseInt(cachedDate)) : null,
                    lastAccessed: lastAccessed ? new Date(parseInt(lastAccessed)) : null,
                    accessCount: parseInt(accessCount || '1'),
                    size: parseInt(size),
                    isHighRes
                });
            }
        }
        
        const highResEntries = entries.filter(e => e.isHighRes).length;
        const totalAccesses = entries.reduce((sum, e) => sum + e.accessCount, 0);
        const avgAccessCount = entries.length > 0 ? (totalAccesses / entries.length).toFixed(1) : 0;

        return {
            totalEntries: keys.length,
            highResEntries,
            standardEntries: keys.length - highResEntries,
            totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
            totalAccesses,
            avgAccessCount,
            maxCacheSize: MAX_CACHE_SIZE,
            cacheDurationHours: CACHE_DURATION / (60 * 60 * 1000),
            entries: entries.sort((a, b) => b.accessCount - a.accessCount) // Sort by most accessed
        };
    } catch (error) {
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
        
        // Image cache cleared
        return { success: true };
    } catch (error) {
        return { error: error.message };
    }
}