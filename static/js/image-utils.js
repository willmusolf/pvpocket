/**
 * Universal image URL utility for converting Firebase Storage URLs to CDN URLs
 * This ensures all images load from the CDN for better performance and CORS compliance
 */

// Image URL helper with fallback strategy for CDN optimization
function getImageUrl(originalUrl) {
    if (!originalUrl) return '';

    // If the URL already includes the CDN domain, return as-is
    if (originalUrl.startsWith('https://cdn.pvpocket.xyz')) {
        return originalUrl;
    }

    // Priority 1: Try CDN first for Firebase Storage URLs
    if (originalUrl.includes('firebasestorage.googleapis.com') || originalUrl.includes('storage.googleapis.com')) {
        // Extract the path from Firebase Storage URLs
        // Examples:
        // https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/energy_icons%2Fwater.png?alt=media
        // https://storage.googleapis.com/pvpocket-dd286.firebasestorage.app/cards/genetic-apex/267
        
        let path = '';
        
        if (originalUrl.includes('firebasestorage.googleapis.com')) {
            // Handle Firebase Storage URLs with encoded paths
            const pathMatch = originalUrl.match(/\/o\/([^?]+)/);
            if (pathMatch) {
                path = '/' + decodeURIComponent(pathMatch[1]);
            }
        } else if (originalUrl.includes('storage.googleapis.com')) {
            // Handle Google Cloud Storage URLs  
            const pathMatch = originalUrl.match(/pvpocket-dd286\.firebasestorage\.app\/(.+)$/);
            if (pathMatch) {
                path = '/' + pathMatch[1];
            }
        }
        
        if (path) {
            return 'https://cdn.pvpocket.xyz' + path;
        }
    }
    
    // If it's a relative path, prepend the CDN base URL
    if (originalUrl.startsWith('/') || !originalUrl.includes('://')) {
        return 'https://cdn.pvpocket.xyz' + (originalUrl.startsWith('/') ? originalUrl : '/' + originalUrl);
    }
    
    // For any other URLs, return as-is (fallback)
    return originalUrl;
}

// Helper function to update an image element's src with CDN URL
function setCdnImageSrc(imgElement, originalUrl) {
    if (imgElement && originalUrl) {
        imgElement.src = getImageUrl(originalUrl);
    }
}

// Helper function to update all images on page with CDN URLs
function convertAllImagesToCdn() {
    const images = document.querySelectorAll('img[src]');
    images.forEach(img => {
        const originalSrc = img.getAttribute('src');
        if (originalSrc && (originalSrc.includes('firebasestorage.googleapis.com') || originalSrc.includes('storage.googleapis.com'))) {
            img.src = getImageUrl(originalSrc);
        }
    });
}

// Enhanced image loading with fallback strategy for cost optimization
function loadImageWithFallback(imgElement, originalUrl) {
    if (!imgElement || !originalUrl) return;

    // Try CDN first (fastest, cheapest)
    const cdnUrl = getImageUrl(originalUrl);

    const tryImage = (url, fallbackUrl = null) => {
        imgElement.onerror = null; // Reset error handler
        imgElement.src = url;

        if (fallbackUrl) {
            imgElement.onerror = () => {
                console.warn(`Image failed to load from ${url}, trying fallback: ${fallbackUrl}`);
                tryImage(fallbackUrl);
            };
        } else {
            imgElement.onerror = () => {
                console.error(`All image sources failed for: ${originalUrl}`);
                // Set a placeholder or hide the image
                imgElement.style.display = 'none';
            };
        }
    };

    // Try CDN first, then fallback to original Firebase Storage URL
    if (cdnUrl !== originalUrl) {
        tryImage(cdnUrl, originalUrl);
    } else {
        tryImage(originalUrl);
    }
}

// Enhanced helper to update all images with fallback strategy
function convertAllImagesToCdnWithFallback() {
    const images = document.querySelectorAll('img[src]');
    images.forEach(img => {
        const originalSrc = img.getAttribute('src');
        if (originalSrc && (originalSrc.includes('firebasestorage.googleapis.com') || originalSrc.includes('storage.googleapis.com'))) {
            loadImageWithFallback(img, originalSrc);
        }
    });
}

// Auto-convert images when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', convertAllImagesToCdnWithFallback);
} else {
    convertAllImagesToCdnWithFallback();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getImageUrl, setCdnImageSrc, loadImageWithFallback };
}