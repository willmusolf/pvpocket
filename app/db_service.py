"""
Enhanced database service with connection pooling and retry logic.
Provides resilient Firestore operations with better error handling.
"""

import time
import random
from typing import Optional, List, Dict, Any, Callable
from functools import wraps
from flask import current_app
from google.cloud import firestore
from google.api_core.exceptions import (
    RetryError, 
    ServiceUnavailable, 
    DeadlineExceeded,
    InternalServerError,
    Cancelled,
    ResourceExhausted
)
import threading
import queue
import os


class FirestoreConnectionPool:
    """Connection pool for Firestore clients to improve performance."""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._logged_init = False
        # DB Pool initialized (logging will be done when first accessed)
        
    def get_client(self) -> firestore.Client:
        """Get a Firestore client from the pool or create a new one."""
        # Log initialization only once when first accessed
        if not self._logged_init:
            try:
                from flask import current_app
                if hasattr(current_app, 'debug') and current_app.debug:
                    current_app.logger.debug(f"✅ DB POOL: Initialized connection pool (max: {self.max_connections})")
                elif 'development' in str(current_app.config.get('FLASK_ENV', '')):
                    current_app.logger.debug(f"✅ DB POOL: Initialized connection pool (max: {self.max_connections})")
                self._logged_init = True
            except RuntimeError:
                # No Flask context available, skip logging
                self._logged_init = True
        
        try:
            # Try to get from pool (non-blocking)
            return self._pool.get_nowait()
        except queue.Empty:
            # Create new connection if under limit
            with self._lock:
                if self._created_connections < self.max_connections:
                    self._created_connections += 1
                    return firestore.Client()
                else:
                    # Wait for available connection
                    try:
                        return self._pool.get(timeout=5)
                    except queue.Empty:
                        # Database connection pool exhausted - critical error
                        if os.environ.get('FLASK_ENV') == 'production':
                            try:
                                from .alerts import alert_database_failure
                                alert_database_failure("Database connection pool exhausted - all connections in use")
                            except:
                                pass
                        raise Exception("Database connection pool exhausted")
    
    def return_client(self, client: firestore.Client) -> None:
        """Return a client to the pool."""
        try:
            self._pool.put_nowait(client)
        except queue.Full:
            # Pool is full, connection will be garbage collected
            pass
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                # Firestore clients don't have explicit close method
                del client
            except queue.Empty:
                break


# Global connection pool instance - reduced for cost optimization
_connection_pool = FirestoreConnectionPool(max_connections=10)


def retry_on_error(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for retrying Firestore operations with exponential backoff."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ServiceUnavailable, DeadlineExceeded, InternalServerError, 
                       Cancelled, ResourceExhausted) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Log retry exhaustion only in debug mode
                        if hasattr(current_app, 'debug') and current_app.debug:
                            print(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        # Alert on critical database failures after all retries exhausted
                        if os.environ.get('FLASK_ENV') == 'production':
                            try:
                                from .alerts import alert_database_failure
                                alert_database_failure(f"Database operation failed after {max_retries} retries: {func.__name__} - {type(e).__name__}: {str(e)}")
                            except:
                                pass
                        raise e
                    
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter
                    
                    # Log retry attempts only in debug mode
                    if hasattr(current_app, 'debug') and current_app.debug:
                        print(f"Retry {attempt + 1}/{max_retries} for {func.__name__} in {total_delay:.2f}s")
                    time.sleep(total_delay)
                    
                except Exception as e:
                    # Don't retry on non-retryable errors
                    # Log non-retryable errors only in debug mode
                    if hasattr(current_app, 'debug') and current_app.debug:
                        print(f"Non-retryable error in {func.__name__}: {e}")
                    raise e
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class DatabaseService:
    """Enhanced database service with connection pooling and retry logic."""
    
    @staticmethod
    def get_client() -> firestore.Client:
        """Get a Firestore client with connection pooling."""
        # Try pool first, fallback to app config
        try:
            return _connection_pool.get_client()
        except Exception as e:
            # Log connection pool errors only in debug mode
            if hasattr(current_app, 'debug') and current_app.debug:
                print(f"Error getting pooled client, falling back to app config: {e}")
            client = current_app.config.get("FIRESTORE_DB")
            if not client:
                raise Exception("No Firestore client available")
            return client
    
    @staticmethod
    def return_client(client: firestore.Client) -> None:
        """Return client to pool."""
        _connection_pool.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def get_document(collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a single document with retry logic."""
        client = DatabaseService.get_client()
        try:
            doc_ref = client.collection(collection).document(document_id)
            doc = doc_ref.get()
            
            # Track Firestore read operation
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_firestore_read(collection, 1)
            except:
                pass
            
            if doc.exists:
                return doc.to_dict()
            return None
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def get_documents_batch(collection: str, document_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple documents in a batch with retry logic."""
        if not document_ids:
            return []
            
        client = DatabaseService.get_client()
        try:
            # Firestore batch get (up to 500 documents)
            doc_refs = [client.collection(collection).document(doc_id) for doc_id in document_ids]
            
            results = []
            # Process in smaller chunks to optimize costs
            chunk_size = 100
            for i in range(0, len(doc_refs), chunk_size):
                chunk = doc_refs[i:i + chunk_size]
                docs = client.get_all(chunk)
                
                for doc in docs:
                    if doc.exists:
                        doc_data = doc.to_dict()
                        doc_data['id'] = doc.id
                        results.append(doc_data)
                
                # Track Firestore batch read operations
                try:
                    from .monitoring import performance_monitor
                    performance_monitor.metrics.record_firestore_batch_read(collection, len(chunk))
                except:
                    pass
            
            return results
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def query_collection(collection: str, filters: List[tuple] = None, 
                         order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query a collection with filters, ordering, and limits."""
        client = DatabaseService.get_client()
        try:
            query = client.collection(collection)
            
            # Apply filters
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Apply ordering
            if order_by:
                query = query.order_by(order_by)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            results = []
            docs_read = 0
            for doc in query.stream():
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                results.append(doc_data)
                docs_read += 1
            
            # Track Firestore read operations
            if docs_read > 0:
                try:
                    from .monitoring import performance_monitor
                    performance_monitor.metrics.record_firestore_read(collection, docs_read)
                except:
                    pass
            
            return results
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def create_document(collection: str, document_data: Dict[str, Any], 
                       document_id: str = None) -> str:
        """Create a new document with retry logic."""
        client = DatabaseService.get_client()
        try:
            collection_ref = client.collection(collection)
            
            if document_id:
                doc_ref = collection_ref.document(document_id)
                doc_ref.set(document_data)
                result_id = document_id
            else:
                doc_ref = collection_ref.add(document_data)
                result_id = doc_ref[1].id
            
            # Track Firestore write operation
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_firestore_write(collection, 1)
            except:
                pass
            
            return result_id
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def update_document(collection: str, document_id: str, 
                       updates: Dict[str, Any], merge: bool = True) -> bool:
        """Update a document with retry logic."""
        client = DatabaseService.get_client()
        try:
            doc_ref = client.collection(collection).document(document_id)
            doc_ref.set(updates, merge=merge)
            return True
        except Exception as e:
            # Log update errors only in debug mode
            if hasattr(current_app, 'debug') and current_app.debug:
                print(f"Error updating document {collection}/{document_id}: {e}")
            return False
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=3)
    def delete_document(collection: str, document_id: str) -> bool:
        """Delete a document with retry logic."""
        client = DatabaseService.get_client()
        try:
            doc_ref = client.collection(collection).document(document_id)
            doc_ref.delete()
            
            # Track Firestore delete operation
            try:
                from .monitoring import performance_monitor
                performance_monitor.metrics.record_firestore_delete(collection, 1)
            except:
                pass
            
            return True
        except Exception as e:
            # Log delete errors only in debug mode
            if hasattr(current_app, 'debug') and current_app.debug:
                print(f"Error deleting document {collection}/{document_id}: {e}")
            return False
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    @retry_on_error(max_retries=2)
    def execute_transaction(transaction_func: Callable, *args, **kwargs) -> Any:
        """Execute a Firestore transaction with retry logic."""
        client = DatabaseService.get_client()
        try:
            transaction = client.transaction()
            return transaction_func(transaction, *args, **kwargs)
        finally:
            DatabaseService.return_client(client)
    
    @staticmethod
    def health_check() -> bool:
        """Check if Firestore connection is healthy."""
        try:
            from flask import current_app
            
            # Get Firestore client from app config as fallback
            db_client = current_app.config.get("FIRESTORE_DB")
            if not db_client:
                # Log health check failures only in debug mode
                if hasattr(current_app, 'debug') and current_app.debug:
                    print("Database health check failed: No Firestore client available")
                return False
            
            # Try a simple operation - just test the connection
            users_collection = db_client.collection('users')
            list(users_collection.limit(1).stream())
            return True
        except Exception as e:
            # Log health check errors only in debug mode
            if hasattr(current_app, 'debug') and current_app.debug:
                print(f"Database health check failed: {e}")
            return False


# Global database service instance
db_service = DatabaseService()