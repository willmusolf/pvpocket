/**
 * Universal image URL utility for converting Firebase Storage URLs to CDN URLs
 * This ensures all images load from the CDN for better performance and CORS compliance
 */

// Image URL helper - convert Firebase Storage URLs to CDN URLs
function getImageUrl(originalUrl) {
    if (!originalUrl) return '';
    
    // If the URL already includes the CDN domain, return as-is
    if (originalUrl.startsWith('https://cdn.pvpocket.xyz')) {
        return originalUrl;
    }
    
    // Convert Firebase Storage URLs to CDN URLs
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

// Auto-convert images when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', convertAllImagesToCdn);
} else {
    convertAllImagesToCdn();
}