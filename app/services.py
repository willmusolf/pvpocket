"""
Service layer for handling data access patterns.
Provides clean interfaces for accessing cached data without storing in app config.
"""

from typing import Optional, List, Dict, Any
import threading
from flask import current_app
from Card import CardCollection, Card
from .cache_manager import cache_manager
from .db_service import db_service


class CardService:
    """Service for handling card collection operations."""
    
    # Define priority sets for initial loading (most recent/popular sets)
    # NOTE: This should be updated when new sets are released
    PRIORITY_SETS = [
        "Eevee Grove",              # Most recent
        "Extradimensional Crisis",  # Second most recent
        "Celestial Guardians",      # Third most recent
        "Shining Revelry",          # Fourth most recent
        "Triumphant Light"          # Fifth most recent
    ]
    
    # Track background loading state
    _background_loading_lock = threading.Lock()
    _background_loading_active = False
    
    @staticmethod
    def get_dynamic_priority_sets() -> List[str]:
        """Get priority sets dynamically based on release order.
        This allows for automatic adaptation when new sets are released.
        """
        # In the future, this could query the database for the most recent sets
        # For now, return the hardcoded list but this makes it easier to update
        return CardService.PRIORITY_SETS
    
    @staticmethod
    def _is_background_loading_active() -> bool:
        """Check if background loading is currently active."""
        with CardService._background_loading_lock:
            return CardService._background_loading_active
    
    @staticmethod
    def _set_background_loading_active(active: bool):
        """Set background loading state."""
        with CardService._background_loading_lock:
            CardService._background_loading_active = active
    
    @staticmethod
    def get_card_collection() -> CardCollection:
        """Get card collection with graceful fallback for startup optimization."""
        # Always try full collection from cache first
        full_collection = cache_manager.get_card_collection(cache_key="global_cards")
        
        if full_collection and len(full_collection.cards) > 1000:  # Full collection threshold
            return full_collection
        
        # If no full collection, check if we have a priority collection cached
        priority_collection = cache_manager.get_card_collection(cache_key="global_cards_priority")
        
        # If we have priority collection but no background loading started, start it
        if priority_collection and len(priority_collection.cards) > 0:
            # Check if full collection loading is already in progress
            if not CardService._is_background_loading_active():
                CardService._background_load_remaining_sets()
            return priority_collection
        
        # No cached collections available - try loading priority collection first for better startup performance
        priority_collection = CardService._get_priority_card_collection()
        
        if priority_collection and len(priority_collection.cards) > 0:
            # Start background loading of remaining sets
            if not CardService._is_background_loading_active():
                CardService._background_load_remaining_sets()
            return priority_collection
        
        # Fallback to full collection if priority loading fails
        return CardService._load_full_collection()
    
    @staticmethod
    def _get_priority_card_collection() -> Optional[CardCollection]:
        """Get card collection with only priority sets loaded."""
        # Try priority collection from cache
        priority_collection = cache_manager.get_card_collection(cache_key="global_cards_priority")
        
        if priority_collection:
            return priority_collection
        
        # Load priority sets from Firestore
        db_client = current_app.config.get("FIRESTORE_DB")
        if not db_client:
            # Only log critical errors
            if current_app and current_app.debug:
                print("ERROR: Firestore client not available for priority card loading.")
            return None
        
        try:
            priority_sets = CardService.get_dynamic_priority_sets()
            collection = CardCollection()
            
            total_loaded = 0
            for set_name in priority_sets:
                loaded_count = CardService._load_cards_from_set(db_client, collection, set_name)
                total_loaded += loaded_count
            
            if total_loaded > 0:
                # Cache priority collection with shorter TTL
                cache_manager.set_card_collection(collection, cache_key="global_cards_priority", ttl_hours=12)
                return collection
            else:
                return None
                
        except Exception as e:
            # Only log critical errors in debug mode
            if current_app and current_app.debug:
                print(f"❌ Error loading priority card collection: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    @staticmethod
    def _load_cards_from_set(db_client, collection: CardCollection, set_name: str) -> int:
        """Load cards from a specific set into the collection."""
        try:
            sets_collection_ref = db_client.collection("cards")
            all_set_docs = list(sets_collection_ref.stream())
            
            loaded_count = 0
            set_found = False
            
            for set_doc in all_set_docs:
                # Load cards from this set's subcollection
                cards_subcollection_ref = set_doc.reference.collection("set_cards")
                card_docs = list(cards_subcollection_ref.stream())
                
                set_loaded_count = 0
                for card_doc in card_docs:
                    card_data = card_doc.to_dict()
                    if card_data is None:
                        continue
                    
                    # Check if this card belongs to our target set
                    card_set_name = card_data.get("set_name", "")
                    if card_set_name != set_name:
                        continue
                    
                    set_found = True
                    try:
                        card_pk_id = card_data.get("id")
                        if card_pk_id is None:
                            continue

                        card = Card(
                            id=int(card_pk_id),
                            name=card_data.get("name", ""),
                            energy_type=card_data.get("energy_type", ""),
                            set_name=card_data.get("set_name", ""),
                            set_code=card_data.get("set_code", ""),
                            card_number=card_data.get("card_number"),
                            card_number_str=card_data.get("card_number_str", ""),
                            card_type=card_data.get("card_type", ""),
                            hp=card_data.get("hp"),
                            attacks=card_data.get("attacks", []),
                            weakness=card_data.get("weakness"),
                            retreat_cost=card_data.get("retreat_cost"),
                            illustrator=card_data.get("illustrator"),
                            firebase_image_url=card_data.get("firebase_image_url"),
                            rarity=card_data.get("rarity", ""),
                            pack=card_data.get("pack", ""),
                            original_image_url=card_data.get("original_image_url"),
                            flavor_text=card_data.get("flavor_text"),
                            abilities=card_data.get("abilities", []),
                        )
                        collection.add_card(card)
                        set_loaded_count += 1
                        loaded_count += 1
                        
                    except Exception as e_card_init:
                        # Card initialization error (debug only)
                        if current_app and current_app.debug:
                            print(f"Error initializing Card from {set_doc.id}/{card_doc.id}: {e_card_init}")
                
                # Progress update for this set document
                if set_loaded_count > 0:
                    # Debug info for card loading
                    if current_app and current_app.debug:
                        print(f"Found {set_loaded_count} cards from set '{set_name}' in document {set_doc.id}")
            
            if not set_found:
                # Warning only in debug mode
                if current_app and current_app.debug:
                    print(f"WARNING: No cards found for set '{set_name}' - may need to update PRIORITY_SETS")
            else:
                # Success message only in debug mode
                if current_app and current_app.debug:
                    print(f"Successfully loaded {loaded_count} cards from set '{set_name}'")
            
            return loaded_count
            
        except Exception as e:
            # Error logging only in debug mode
            if current_app and current_app.debug:
                print(f"Error loading cards from set '{set_name}': {e}")
            return 0
    
    @staticmethod
    def _background_load_remaining_sets():
        """Trigger background loading of remaining card sets (non-priority)."""
        # This would typically be handled by a background task queue
        # For now, we'll use a simple approach that doesn't block the main request
        from threading import Thread
        
        def load_remaining():
            try:
                CardService._set_background_loading_active(True)
                # Background loading status only in debug
                if current_app and current_app.debug:
                    current_app.logger.debug("Starting background load of remaining card sets...")
                
                with current_app.app_context():
                    CardService._load_full_collection(cache_as_full=True)
                    # Completion status only in debug
                    if current_app and current_app.debug:
                        current_app.logger.debug("Background loading of remaining sets completed.")
            except Exception as e:
                # Background loading errors only in debug
                if current_app and current_app.debug:
                    current_app.logger.error(f"Error in background loading: {e}")
                import traceback
                traceback.print_exc()
            finally:
                CardService._set_background_loading_active(False)
        
        # Start background thread (non-blocking)
        thread = Thread(target=load_remaining, daemon=True)
        thread.start()
    
    @staticmethod
    def _load_full_collection(cache_as_full: bool = True) -> CardCollection:
        """Load the complete card collection from Firestore."""
        db_client = current_app.config.get("FIRESTORE_DB")
        if not db_client:
            # Critical error logging
            if current_app and current_app.debug:
                print("ERROR: Firestore client not available for card loading.")
            return CardCollection()
        
        try:
            # Loading status only in debug
            if current_app and current_app.debug:
                current_app.logger.debug("Loading complete card collection from Firestore...")
            collection = CardCollection()
            collection.load_from_firestore(db_client)
            
            if cache_as_full:
                # Cache as full collection
                cache_manager.set_card_collection(collection, ttl_hours=24)
                # Success message only in debug
                if current_app and current_app.debug:
                    current_app.logger.debug(f"Loaded and cached {len(collection)} cards (full collection).")
            
            return collection
        except Exception as e:
            # Error logging only in debug
            if current_app and current_app.debug:
                print(f"Error loading full card collection: {e}")
            return CardCollection()
    
    @staticmethod
    def get_card_by_id(card_id: int) -> Optional[Card]:
        """Get a specific card by ID."""
        collection = CardService.get_card_collection()
        card = collection.get_card_by_id(card_id)
        
        # If card not found in current collection and we're using priority loading,
        # try loading full collection immediately
        if not card and len(collection.cards) < 1000:
            # Debug info for collection fallback
            if current_app and current_app.debug:
                print(f"Card {card_id} not found in priority collection. Loading full collection...")
            full_collection = CardService._load_full_collection(cache_as_full=True)
            card = full_collection.get_card_by_id(card_id)
        
        return card
    
    @staticmethod
    def get_cards_by_name(name: str) -> List[Card]:
        """Get cards by name."""
        collection = CardService.get_card_collection()
        return collection.get_cards_by_name(name)
    
    @staticmethod
    def filter_cards(**kwargs) -> List[Card]:
        """Filter cards by various criteria."""
        collection = CardService.get_card_collection()
        return collection.filter(**kwargs)
    
    @staticmethod
    def get_full_card_collection() -> CardCollection:
        """Get the full card collection, loading it immediately if needed.
        This is used by API endpoints that need access to all cards.
        """
        # Try full collection from cache first
        full_collection = cache_manager.get_card_collection(cache_key="global_cards")
        
        if full_collection and len(full_collection.cards) > 1000:
            return full_collection
        
        # Load full collection immediately
        # API loading message only in debug
        if current_app and current_app.debug:
            print("🔄 API request requires full collection. Loading immediately...")
        full_collection = CardService._load_full_collection(cache_as_full=True)
        return full_collection
    
    @staticmethod
    def refresh_card_collection() -> bool:
        """Force refresh of card collection from Firestore."""
        try:
            # Invalidate both full and priority caches
            cache_manager.invalidate_card_cache()
            cache_manager.invalidate_card_cache(cache_key="global_cards_priority")
            
            # Load fresh priority data first
            db_client = current_app.config.get("FIRESTORE_DB")
            if not db_client:
                return False
            
            # Load priority collection
            priority_collection = CardCollection()
            priority_sets = CardService.get_dynamic_priority_sets()
            for set_name in priority_sets:
                CardService._load_cards_from_set(db_client, priority_collection, set_name)
            
            # Cache priority collection
            cache_manager.set_card_collection(priority_collection, cache_key="global_cards_priority", ttl_hours=12)
            
            # Load and cache full collection
            full_collection = CardCollection()
            full_collection.load_from_firestore(db_client)
            cache_manager.set_card_collection(full_collection, ttl_hours=24)
            
            return True
        except Exception as e:
            # Error logging only in debug
            if current_app and current_app.debug:
                print(f"Error refreshing card collection: {e}")
            return False


class UserService:
    """Service for handling user data operations."""
    
    @staticmethod
    def get_user_collection(user_id: str) -> Optional[Dict]:
        """Get user's personal card collection with enhanced database service."""
        # Try cache first
        cached_collection = cache_manager.get_user_collection(user_id)
        if cached_collection:
            return cached_collection
        
        # Load from Firestore using enhanced service
        try:
            user_data = db_service.get_document("users", user_id)
            if user_data:
                collection_data = user_data.get("collection", {})
                
                # Cache for 6 hours
                cache_manager.set_user_collection(user_id, collection_data, ttl_hours=6)
                return collection_data
            
        except Exception as e:
            # Error logging only in debug
            if current_app and current_app.debug:
                print(f"Error loading user collection for {user_id}: {e}")
        
        return None
    
    @staticmethod
    def get_user_decks(user_id: str) -> List[Dict]:
        """Get user's decks with enhanced database service and caching."""
        # Try cache first
        cached_decks = cache_manager.get_user_decks(user_id)
        if cached_decks:
            return cached_decks
        
        # Load from Firestore using enhanced service
        try:
            filters = [("user_id", "==", user_id)]
            decks_data = db_service.query_collection("decks", filters=filters)
            
            # Cache for 2 hours
            cache_manager.set_user_decks(user_id, decks_data, ttl_hours=2)
            return decks_data
            
        except Exception as e:
            # Error logging only in debug
            if current_app and current_app.debug:
                print(f"Error loading user decks for {user_id}: {e}")
            return []
    
    @staticmethod
    def invalidate_user_cache(user_id: str) -> None:
        """Invalidate all cached data for a user."""
        cache_manager.invalidate_user_cache(user_id)


class DatabaseService:
    """Service for handling database connections and operations."""
    
    @staticmethod
    def get_db():
        """Helper to get Firestore DB client from app config."""
        db = current_app.config.get("FIRESTORE_DB")
        if not db:
            current_app.logger.critical(
                "Firestore client (FIRESTORE_DB) not available in app config."
            )
            raise Exception("Firestore client not available. Check app initialization.")
        return db



class UrlService:
    """Service for handling URL transformations and processing."""
    
    @staticmethod
    def process_firebase_to_cdn_url(image_path: str) -> str:
        """
        Convert Firebase storage URLs to CDN URLs.
        Always converts to CDN regardless of environment.
        
        Args:
            image_path: The original image path (URL or relative path)
            
        Returns:
            CDN URL ready for use
        """
        if not image_path:
            return image_path
            
        # If already a CDN URL, return as-is
        if image_path.startswith('https://cdn.pvpocket.xyz'):
            return image_path
            
        # Define the mappings
        OLD_STORAGE_BASE_URL = 'https://storage.googleapis.com/pvpocket-dd286.firebasestorage.app'
        CDN_BASE_URL = 'https://cdn.pvpocket.xyz'
        
        # Simple direct replacement
        if image_path.startswith(OLD_STORAGE_BASE_URL):
            return image_path.replace(OLD_STORAGE_BASE_URL, CDN_BASE_URL)
            
        # Handle other Firebase URLs
        if 'firebasestorage.googleapis.com' in image_path:
            # Extract path after /o/
            if '/o/' in image_path:
                path_part = image_path.split('/o/', 1)[1].split('?')[0]
                from urllib.parse import unquote
                relative_path = unquote(path_part)
                return f"{CDN_BASE_URL}/{relative_path}"
                
        # For relative paths
        if not image_path.startswith('http'):
            clean_path = image_path.lstrip('/')
            return f"{CDN_BASE_URL}/{clean_path}"
            
        # Fallback - return original
        return image_path


class MetricsService:
    """Service for tracking application metrics."""
    
    @staticmethod
    def track_cache_hit(cache_type: str) -> None:
        """Track cache hits for monitoring."""
        # This could be expanded to send metrics to monitoring systems
        # Cache metrics only in debug
        if current_app and current_app.debug:
            print(f"Cache hit: {cache_type}")
    
    @staticmethod
    def track_cache_miss(cache_type: str) -> None:
        """Track cache misses for monitoring."""
        # Cache metrics only in debug
        if current_app and current_app.debug:
            print(f"Cache miss: {cache_type}")
    
    @staticmethod
    def track_db_query(query_type: str, duration_ms: int) -> None:
        """Track database query performance."""
        # DB performance metrics only in debug
        if current_app and current_app.debug:
            print(f"DB query {query_type}: {duration_ms}ms")


# Convenience instances
card_service = CardService()
user_service = UserService()
database_service = DatabaseService()
url_service = UrlService()
metrics_service = MetricsService()