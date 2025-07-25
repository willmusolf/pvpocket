/**
 * Client-side caching using browser storage
 * Reduces server requests and improves performance
 */

class ClientCache {
    constructor() {
        this.storage = window.localStorage;
        this.sessionStorage = window.sessionStorage;
        this.cachePrefix = 'pkmn_';
        this.maxAge = 3600000; // 1 hour default
    }

    /**
     * Set item in cache with expiration
     */
    set(key, value, maxAgeMs = this.maxAge) {
        try {
            const item = {
                value: value,
                expires: Date.now() + maxAgeMs,
                cached: new Date().toISOString()
            };
            this.storage.setItem(this.cachePrefix + key, JSON.stringify(item));
            return true;
        } catch (e) {
            // Cache set error (silent in production)
            // Handle quota exceeded
            if (e.name === 'QuotaExceededError') {
                this.cleanup();
                try {
                    this.storage.setItem(this.cachePrefix + key, JSON.stringify(item));
                } catch (e2) {
                    return false;
                }
            }
            return false;
        }
    }

    /**
     * Get item from cache
     */
    get(key) {
        try {
            const item = this.storage.getItem(this.cachePrefix + key);
            if (!item) return null;

            const parsed = JSON.parse(item);
            
            // Check if expired
            if (parsed.expires && Date.now() > parsed.expires) {
                this.storage.removeItem(this.cachePrefix + key);
                return null;
            }

            return parsed.value;
        } catch (e) {
            // Cache get error (silent in production)
            return null;
        }
    }

    /**
     * Cache API response
     */
    async fetchWithCache(url, options = {}, maxAgeMs = this.maxAge) {
        const cacheKey = `api_${url}_${JSON.stringify(options)}`;
        
        // Try cache first
        const cached = this.get(cacheKey);
        if (cached) {
            return cached;
        }

        // Fetch from server
        try {
            const response = await fetch(url, options);
            const data = await response.json();
            
            // Cache successful responses
            if (response.ok) {
                this.set(cacheKey, data, maxAgeMs);
            }
            
            return data;
        } catch (error) {
            // Fetch error (silent in production)
            throw error;
        }
    }

    /**
     * Cache card collection data
     */
    cacheCards(cards) {
        // Store cards in chunks to avoid quota issues
        const chunkSize = 50;
        const chunks = [];
        
        for (let i = 0; i < cards.length; i += chunkSize) {
            chunks.push(cards.slice(i, i + chunkSize));
        }

        chunks.forEach((chunk, index) => {
            this.set(`cards_chunk_${index}`, chunk, 86400000); // 24 hours
        });
        
        this.set('cards_chunk_count', chunks.length, 86400000);
        // Cached cards successfully
    }

    /**
     * Get cached cards
     */
    getCachedCards() {
        const chunkCount = this.get('cards_chunk_count');
        if (!chunkCount) return null;

        const cards = [];
        for (let i = 0; i < chunkCount; i++) {
            const chunk = this.get(`cards_chunk_${i}`);
            if (!chunk) return null; // Missing chunk, invalidate all
            cards.push(...chunk);
        }

        // Retrieved cards from client cache
        return cards;
    }

    /**
     * Clean up expired items
     */
    cleanup() {
        const keys = Object.keys(this.storage);
        let removed = 0;

        keys.forEach(key => {
            if (key.startsWith(this.cachePrefix)) {
                try {
                    const item = JSON.parse(this.storage.getItem(key));
                    if (item.expires && Date.now() > item.expires) {
                        this.storage.removeItem(key);
                        removed++;
                    }
                } catch (e) {
                    // Invalid item, remove it
                    this.storage.removeItem(key);
                    removed++;
                }
            }
        });

        // Cleaned up expired cache items
    }

    /**
     * Clear all cache
     */
    clear() {
        const keys = Object.keys(this.storage);
        keys.forEach(key => {
            if (key.startsWith(this.cachePrefix)) {
                this.storage.removeItem(key);
            }
        });
        // Client cache cleared
    }

    /**
     * Get cache size
     */
    getSize() {
        let size = 0;
        const keys = Object.keys(this.storage);
        
        keys.forEach(key => {
            if (key.startsWith(this.cachePrefix)) {
                size += this.storage.getItem(key).length;
            }
        });

        return {
            bytes: size,
            mb: (size / 1024 / 1024).toFixed(2)
        };
    }
}

// Initialize global cache instance
window.clientCache = new ClientCache();

// Auto cleanup on load
window.clientCache.cleanup();

// Example usage in your pages:
/*
// Cache API responses
const decks = await clientCache.fetchWithCache('/api/decks', {}, 300000); // 5 min cache

// Cache card data
clientCache.cacheCards(allCards);

// Get cached cards
const cachedCards = clientCache.getCachedCards();
if (cachedCards) {
    renderCards(cachedCards);
} else {
    // Fetch from server
}
*/