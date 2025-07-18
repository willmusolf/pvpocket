from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    jsonify,
    Response,
) 
from flask_login import (
    current_user as flask_login_current_user,
)
import requests
import time
import hashlib
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import io
from PIL import Image

main_bp = Blueprint("main", __name__)

# Create a requests session with connection pooling and retry strategy
def create_requests_session():
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # Configure HTTP adapter with connection pooling
    adapter = HTTPAdapter(
        pool_connections=10,  # Number of connection pools
        pool_maxsize=20,      # Maximum number of connections in each pool
        max_retries=retry_strategy
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default timeout
    session.timeout = 10
    
    return session

# Global session instance for connection pooling
http_session = create_requests_session()

# Simple in-memory cache for proxy images
class ImageCache:
    def __init__(self, max_size=100, ttl=3600):  # 1 hour TTL, max 100 images
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = Lock()
    
    def _generate_key(self, url):
        """Generate a cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_expired(self, timestamp):
        """Check if cache entry is expired"""
        return time.time() - timestamp > self.ttl
    
    def _evict_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.access_times.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used entries to maintain max_size"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.access_times, key=self.access_times.get)
            self.cache.pop(oldest_key, None)
            self.access_times.pop(oldest_key, None)
    
    def get(self, url):
        """Get cached image data"""
        with self.lock:
            key = self._generate_key(url)
            if key in self.cache and not self._is_expired(self.access_times[key]):
                self.access_times[key] = time.time()  # Update access time
                return self.cache[key]
            return None
    
    def set(self, url, data, content_type):
        """Cache image data"""
        with self.lock:
            self._evict_expired()
            key = self._generate_key(url)
            
            # Evict LRU if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = {
                'data': data,
                'content_type': content_type,
                'size': len(data)
            }
            self.access_times[key] = time.time()
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            self._evict_expired()
            total_size = sum(entry['size'] for entry in self.cache.values())
            return {
                'entries': len(self.cache),
                'total_size_mb': total_size / (1024 * 1024),
                'max_size': self.max_size,
                'ttl': self.ttl
            }

# Global cache instance
image_cache = ImageCache(max_size=100, ttl=3600)  # 1 hour TTL, max 100 images

# Modern image format support
def detect_browser_support(request):
    """Detect if browser supports WebP/AVIF based on Accept header"""
    accept_header = request.headers.get('Accept', '')
    
    supports_avif = 'image/avif' in accept_header
    supports_webp = 'image/webp' in accept_header
    
    return {
        'avif': supports_avif,
        'webp': supports_webp
    }

def convert_image_format(image_data, target_format, quality=85):
    """Convert image to target format (webp or avif)"""
    try:
        # Open the image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            if target_format.lower() == 'webp':
                # WebP supports transparency
                pass
            else:
                # Convert to RGB for formats that don't support transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
        
        # Save to target format
        output = io.BytesIO()
        if target_format.lower() == 'webp':
            img.save(output, format='WEBP', quality=quality, optimize=True)
            return output.getvalue(), 'image/webp'
        elif target_format.lower() == 'avif':
            # Note: AVIF support requires pillow-avif-plugin
            # For now, fall back to WebP if AVIF is not available
            try:
                img.save(output, format='AVIF', quality=quality, optimize=True)
                return output.getvalue(), 'image/avif'
            except Exception:
                # Fall back to WebP
                img.save(output, format='WEBP', quality=quality, optimize=True)
                return output.getvalue(), 'image/webp'
        else:
            # Fall back to original format
            return image_data, 'image/png'
            
    except Exception as e:
        current_app.logger.error(f"Error converting image format: {e}")
        return image_data, 'image/png'

def get_optimal_format(browser_support, file_size):
    """Determine the best format based on browser support and file size"""
    # For small images, conversion overhead might not be worth it
    if file_size < 10 * 1024:  # 10KB
        return None
    
    # Prefer AVIF for better compression, fall back to WebP
    if browser_support['avif']:
        return 'avif'
    elif browser_support['webp']:
        return 'webp'
    else:
        return None


@main_bp.route("/")
def index():
    db = current_app.config.get("FIRESTORE_DB")  # Get Firestore client

    # Get card collection from app config (still from CardCollection loaded in memory)
    card_collection = current_app.config.get("card_collection", [])
    total_cards = len(card_collection)

    # --- Get Total Users from Firestore ---
    total_users = 0
    if db:
        try:
            # WARNING: Streaming all documents just to count can be inefficient for very large collections.
            # Consider a distributed counter for production if user numbers are huge.
            users_query = (
                db.collection("users").select([]).stream()
            )  # select([]) fetches only IDs, more efficient
            total_users = len(list(users_query))
        except Exception as e:
            current_app.logger.error(f"Error counting users from Firestore: {e}")
            # Fallback or set to a placeholder if count fails
            total_users = "N/A"
    else:
        total_users = "N/A"  # DB not available

    # --- Get Total Decks from Firestore ---
    total_decks = 0
    if db:
        try:
            # Same warning as for users regarding counting large collections.
            decks_query = db.collection("decks").select([]).stream()
            total_decks = len(list(decks_query))
        except Exception as e:
            current_app.logger.error(f"Error counting decks from Firestore: {e}")
            total_decks = "N/A"
    else:
        total_decks = "N/A"  # DB not available

    battle_history = current_app.config.get("battle_history", [])
    total_battles = len(battle_history)
    recent_battles = battle_history[-5:] if battle_history else []
    # TODO: Migrate battle_history to Firestore and update fetching here.

    meta_stats = current_app.config.get("meta_stats", {"decks": {}})
    top_decks_data = []
    if db:
        for deck_name, stats in meta_stats.get("decks", {}).items():
            if (
                stats.get("total_battles", 0) >= 5
            ):
                win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100

                deck_types_from_fs = []
                try:
                    deck_query_by_name = (
                        db.collection("decks")
                        .where("name", "==", deck_name)
                        .limit(1)
                        .stream()
                    )
                    for deck_doc_found in deck_query_by_name:
                        deck_data_fs = deck_doc_found.to_dict()
                        deck_types_from_fs = deck_data_fs.get("deck_types", [])
                        break
                except Exception as e_deck_type:
                    current_app.logger.error(
                        f"Error fetching types for deck '{deck_name}' from Firestore: {e_deck_type}"
                    )

                top_decks_data.append(
                    {
                        "name": deck_name,
                        "win_rate": round(win_rate, 1),
                        "types": deck_types_from_fs,
                    }
                )
    else:
        for deck_name, stats in meta_stats.get("decks", {}).items():
            if stats.get("total_battles", 0) >= 5:
                win_rate = (stats.get("wins", 0) / stats["total_battles"]) * 100
                top_decks_data.append(
                    {"name": deck_name, "win_rate": round(win_rate, 1), "types": []}
                )

    top_decks_data.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
    top_decks_data = top_decks_data[:5]

    return render_template(
        "main_index.html",
        total_cards=total_cards,
        total_users=total_users,
        total_decks=total_decks,
        total_battles=total_battles,
        recent_battles=recent_battles,
        top_decks=top_decks_data,
        user_logged_in=flask_login_current_user.is_authenticated,
        username=(
            flask_login_current_user.username
            if flask_login_current_user.is_authenticated
            else None
        ),
    )


@main_bp.route("/api/proxy-image")
def proxy_image():
    """Proxy route to handle CORS issues with Firebase Storage images with caching and format optimization"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({"error": "No URL provided"}), 400
        
        # Validate URL is from expected domains
        allowed_domains = [
            'storage.googleapis.com',
            'firebasestorage.googleapis.com'
        ]
        
        if not any(domain in image_url for domain in allowed_domains):
            return jsonify({"error": "Invalid domain"}), 400
        
        # Detect browser support for modern formats
        browser_support = detect_browser_support(request)
        
        # Create cache key that includes format preferences
        cache_key = f"{image_url}_{browser_support['avif']}_{browser_support['webp']}"
        
        # Check cache first
        cached_data = image_cache.get(cache_key)
        if cached_data:
            # Cache hit - return cached data
            return Response(
                cached_data['data'],
                mimetype=cached_data['content_type'],
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Cache-Control': 'public, max-age=3600',
                    'X-Cache': 'HIT',
                    'X-Image-Format': cached_data['content_type']
                }
            )
        
        # Cache miss - fetch from Firebase Storage using pooled session
        response = http_session.get(image_url)
        response.raise_for_status()
        
        # Get original content type and data
        original_content_type = response.headers.get('content-type', 'image/png')
        image_data = response.content
        
        # Skip format conversion for now - it's too slow
        content_type = original_content_type
        
        # Optional: Only convert if specifically requested via query param
        if request.args.get('convert') == 'true':
            optimal_format = get_optimal_format(browser_support, len(image_data))
            
            if optimal_format and original_content_type.startswith('image/'):
                try:
                    converted_data, converted_content_type = convert_image_format(
                        image_data, optimal_format, quality=85
                    )
                    
                    if len(converted_data) < len(image_data):
                        image_data = converted_data
                        content_type = converted_content_type
                except Exception as e:
                    current_app.logger.error(f"Error converting image format: {e}")
                    content_type = original_content_type
        
        # Cache the response data (with format-specific key)
        image_cache.set(cache_key, image_data, content_type)
        
        # Return the image with CORS headers
        return Response(
            image_data,
            mimetype=content_type,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Cache-Control': 'public, max-age=3600',
                'X-Cache': 'MISS',
                'X-Image-Format': content_type,
                'X-Original-Format': original_content_type
            }
        )
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching image: {e}")
        return jsonify({"error": "Failed to fetch image"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in proxy_image: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_bp.route("/api/proxy-image-stats")
def proxy_image_stats():
    """Get cache statistics for debugging"""
    try:
        stats = image_cache.get_stats()
        return jsonify({
            "cache_stats": stats,
            "status": "success"
        })
    except Exception as e:
        current_app.logger.error(f"Error in proxy_image_stats: {e}")
        return jsonify({"error": "Internal server error"}), 500