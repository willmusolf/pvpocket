/**
 * Universal image URL utility for Firebase Storage URLs
 * Uses direct Firebase Storage with optimized caching headers
 */

// Image URL helper optimized for Firebase Storage
function getImageUrl(originalUrl) {
    if (!originalUrl) return '';

    // If already a Firebase Storage URL, return as-is
    if (originalUrl.includes('firebasestorage.googleapis.com')) {
        return originalUrl;
    }

    // Convert relative paths to Firebase Storage URLs
    if (originalUrl.startsWith('/') || !originalUrl.includes('://')) {
        const path = originalUrl.startsWith('/') ? originalUrl.substring(1) : originalUrl;
        const encodedPath = encodeURIComponent(path.replace(/\//g, '%2F'));
        return `https://firebasestorage.googleapis.com/v0/b/pvpocket-dd286.firebasestorage.app/o/${encodedPath}?alt=media`;
    }

    // For any other URLs, return as-is
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