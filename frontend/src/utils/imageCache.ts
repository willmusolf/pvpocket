/**
 * Simple image cache utility for better performance in battle simulator
 */

interface CacheEntry {
  loaded: boolean;
  failed: boolean;
  timestamp: number;
}

class ImageCache {
  private cache = new Map<string, CacheEntry>();
  private readonly CACHE_DURATION = 10 * 60 * 1000; // 10 minutes

  /**
   * Check if image is in cache and still valid
   */
  isLoaded(url: string): boolean {
    const entry = this.cache.get(url);
    if (!entry) return false;
    
    // Check if cache entry is still valid
    const now = Date.now();
    if (now - entry.timestamp > this.CACHE_DURATION) {
      this.cache.delete(url);
      return false;
    }
    
    return entry.loaded;
  }

  /**
   * Check if image loading previously failed
   */
  hasFailed(url: string): boolean {
    const entry = this.cache.get(url);
    if (!entry) return false;
    
    // Check if cache entry is still valid
    const now = Date.now();
    if (now - entry.timestamp > this.CACHE_DURATION) {
      this.cache.delete(url);
      return false;
    }
    
    return entry.failed;
  }

  /**
   * Mark image as loaded
   */
  markLoaded(url: string): void {
    this.cache.set(url, {
      loaded: true,
      failed: false,
      timestamp: Date.now()
    });
  }

  /**
   * Mark image as failed
   */
  markFailed(url: string): void {
    this.cache.set(url, {
      loaded: false,
      failed: true,
      timestamp: Date.now()
    });
  }

  /**
   * Preload an image
   */
  preload(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isLoaded(url)) {
        resolve();
        return;
      }

      if (this.hasFailed(url)) {
        reject(new Error('Image previously failed to load'));
        return;
      }

      const img = new Image();
      img.onload = () => {
        this.markLoaded(url);
        resolve();
      };
      img.onerror = () => {
        this.markFailed(url);
        reject(new Error('Failed to preload image'));
      };
      img.src = url;
    });
  }

  /**
   * Clear old cache entries
   */
  cleanup(): void {
    const now = Date.now();
    for (const [url, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.CACHE_DURATION) {
        this.cache.delete(url);
      }
    }
  }

  /**
   * Get cache stats for debugging
   */
  getStats() {
    const now = Date.now();
    let loadedCount = 0;
    let failedCount = 0;
    let expiredCount = 0;

    for (const entry of this.cache.values()) {
      if (now - entry.timestamp > this.CACHE_DURATION) {
        expiredCount++;
      } else if (entry.loaded) {
        loadedCount++;
      } else if (entry.failed) {
        failedCount++;
      }
    }

    return {
      total: this.cache.size,
      loaded: loadedCount,
      failed: failedCount,
      expired: expiredCount
    };
  }
}

// Export singleton instance
export const imageCache = new ImageCache();

// Cleanup cache every 5 minutes
setInterval(() => {
  imageCache.cleanup();
}, 5 * 60 * 1000);