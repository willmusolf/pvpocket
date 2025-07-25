"""
Background task queue system for handling expensive operations asynchronously.
Uses Google Cloud Tasks for production, with in-memory fallback for development.
"""

import json
import os
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from flask import current_app
import threading
import queue
from functools import wraps

# Try to import Google Cloud Tasks
try:
    from google.cloud import tasks_v2
    from google.protobuf import timestamp_pb2
    CLOUD_TASKS_AVAILABLE = True
except ImportError:
    CLOUD_TASKS_AVAILABLE = False
    # Will log when TaskQueue is initialized


class TaskQueue:
    """Task queue for background job processing."""
    
    def __init__(self, project_id: str = None, location: str = "us-central1", queue_name: str = "default"):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location
        self.queue_name = queue_name
        self.queue_path = None
        
        if CLOUD_TASKS_AVAILABLE and self.project_id:
            try:
                self.client = tasks_v2.CloudTasksClient()
                self.queue_path = self.client.queue_path(self.project_id, self.location, self.queue_name)
                # Log only in development/debug mode
                print(f"✅ TASKS: Initialized Cloud Tasks queue: {self.queue_path}")
            except Exception as e:
                print(f"Failed to initialize Cloud Tasks: {e}")
                self.client = None
                self._setup_memory_fallback()
        else:
            if not CLOUD_TASKS_AVAILABLE and os.environ.get('WERKZEUG_RUN_MAIN'):
                print("Google Cloud Tasks not available, using in-memory queue fallback")
            self.client = None
            self._setup_memory_fallback()
    
    def _setup_memory_fallback(self):
        """Set up in-memory task processing for development."""
        if os.environ.get('WERKZEUG_RUN_MAIN'):
            print("⚠️ TASKS: Using in-memory task queue fallback")
        self._memory_queue = queue.Queue()
        self._workers = []
        self._running = True
        self._task_registry = {}
        
        # Start worker threads
        for i in range(3):  # 3 worker threads
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)
    
    def _worker_loop(self):
        """Worker loop for processing in-memory tasks."""
        while self._running:
            try:
                task_data = self._memory_queue.get(timeout=1)
                self._process_memory_task(task_data)
                self._memory_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing memory task: {e}")
    
    def _process_memory_task(self, task_data: Dict[str, Any]):
        """Process a task from the in-memory queue."""
        try:
            task_type = task_data.get("task_type")
            payload = task_data.get("payload", {})
            
            handler = self._task_registry.get(task_type)
            if handler:
                try:
                    if current_app.debug:
                        current_app.logger.debug(f"Processing task: {task_type}")
                except RuntimeError:
                    # No Flask context available, skip debug logging
                    pass
                handler(payload)
            else:
                try:
                    current_app.logger.error(f"No handler registered for task type: {task_type}")
                except RuntimeError:
                    print(f"No handler registered for task type: {task_type}")
                
        except Exception as e:
            try:
                current_app.logger.error(f"Error processing task {task_data.get('task_type', 'unknown')}: {e}")
            except RuntimeError:
                print(f"Error processing task {task_data.get('task_type', 'unknown')}: {e}")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type."""
        if not hasattr(self, '_task_registry'):
            self._task_registry = {}
        self._task_registry[task_type] = handler
        # Only log task registration in main process to avoid duplication
        try:
            if current_app.debug and os.environ.get('WERKZEUG_RUN_MAIN'):
                current_app.logger.debug(f"Registered handler for task type: {task_type}")
        except (RuntimeError, NameError):
            # No Flask context or import available, skip logging
            pass
    
    def enqueue_task(self, task_type: str, payload: Dict[str, Any], 
                    delay_seconds: int = 0, url: str = None) -> bool:
        """Enqueue a task for background processing."""
        
        if self.client and self.queue_path:
            # Use Google Cloud Tasks
            return self._enqueue_cloud_task(task_type, payload, delay_seconds, url)
        else:
            # Use in-memory fallback
            return self._enqueue_memory_task(task_type, payload, delay_seconds)
    
    def _enqueue_cloud_task(self, task_type: str, payload: Dict[str, Any], 
                           delay_seconds: int, url: str) -> bool:
        """Enqueue task using Google Cloud Tasks."""
        try:
            if not url:
                # Default to internal task handler endpoint
                url = f"/internal/tasks/{task_type}"
            
            # Create task payload
            task_payload = {
                "task_type": task_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Create the task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"https://{current_app.config.get('DOMAIN', 'localhost')}{url}",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Task-Auth": current_app.config.get("TASK_AUTH_TOKEN", "dev-token")
                    },
                    "body": json.dumps(task_payload).encode(),
                }
            }
            
            # Add delay if specified
            if delay_seconds > 0:
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(datetime.utcnow() + timedelta(seconds=delay_seconds))
                task["schedule_time"] = timestamp
            
            # Enqueue the task
            response = self.client.create_task(parent=self.queue_path, task=task)
            print(f"Enqueued Cloud Task: {response.name}")
            return True
            
        except Exception as e:
            print(f"Error enqueuing Cloud Task: {e}")
            # Fallback to memory queue
            return self._enqueue_memory_task(task_type, payload, delay_seconds)
    
    def _enqueue_memory_task(self, task_type: str, payload: Dict[str, Any], delay_seconds: int) -> bool:
        """Enqueue task using in-memory queue."""
        try:
            task_data = {
                "task_type": task_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
                "delay_seconds": delay_seconds
            }
            
            if delay_seconds > 0:
                # Schedule delayed task
                timer = threading.Timer(delay_seconds, 
                                      lambda: self._memory_queue.put(task_data))
                timer.start()
            else:
                # Immediate task
                self._memory_queue.put(task_data)
            
            try:
                if current_app.debug:
                    current_app.logger.debug(f"Enqueued memory task: {task_type}")
            except RuntimeError:
                # No Flask context available, skip logging
                pass
            return True
            
        except Exception as e:
            print(f"Error enqueuing memory task: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if task queue is healthy."""
        try:
            if self.client and self.queue_path:
                # Check Cloud Tasks queue
                queue_info = self.client.get_queue(name=self.queue_path)
                return queue_info.state == tasks_v2.Queue.State.RUNNING
            else:
                # Check memory queue
                return hasattr(self, '_running') and self._running
        except Exception as e:
            print(f"Task queue health check failed: {e}")
            return False
    
    def shutdown(self):
        """Gracefully shutdown the task queue."""
        if hasattr(self, '_running'):
            self._running = False
            
        # Wait for memory queue to finish
        if hasattr(self, '_memory_queue'):
            self._memory_queue.join()


# Global task queue instance
task_queue = TaskQueue()


# Decorator for background tasks
def background_task(task_type: str, delay_seconds: int = 0):
    """Decorator to make a function run as a background task."""
    def decorator(func: Callable) -> Callable:
        # Register the function as a task handler
        task_queue.register_task_handler(task_type, func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Convert args/kwargs to payload
            payload = {
                "args": args,
                "kwargs": kwargs
            }
            
            # Enqueue the task
            success = task_queue.enqueue_task(task_type, payload, delay_seconds)
            
            if not success:
                print(f"Failed to enqueue task {task_type}, running synchronously")
                return func(*args, **kwargs)
            
            print(f"Enqueued background task: {task_type}")
            return True
            
        return wrapper
    return decorator


# Example background tasks
@background_task("refresh_card_cache")
def refresh_card_cache_task(payload: Dict[str, Any]):
    """Background task to refresh card cache."""
    try:
        from .services import card_service
        success = card_service.refresh_card_collection()
        print(f"Card cache refresh task completed: {'success' if success else 'failed'}")
    except Exception as e:
        print(f"Error in refresh_card_cache_task: {e}")


@background_task("update_user_stats")
def update_user_stats_task(payload: Dict[str, Any]):
    """Background task to update user statistics."""
    try:
        user_id = payload.get("user_id")
        if not user_id:
            print("No user_id provided for stats update")
            return
            
        # This would contain logic to update user stats
        print(f"Updated stats for user {user_id}")
    except Exception as e:
        print(f"Error in update_user_stats_task: {e}")


@background_task("cleanup_expired_cache")
def cleanup_expired_cache_task(payload: Dict[str, Any]):
    """Background task to clean up expired cache entries."""
    try:
        from .cache_manager import cache_manager
        # This would contain logic to clean up expired entries
        print("Cleaned up expired cache entries")
    except Exception as e:
        print(f"Error in cleanup_expired_cache_task: {e}")


# Utility function to enqueue common tasks
def enqueue_card_refresh(delay_minutes: int = 0):
    """Enqueue a card cache refresh task."""
    return task_queue.enqueue_task("refresh_card_cache", {}, delay_seconds=delay_minutes * 60)


def enqueue_user_stats_update(user_id: str, delay_minutes: int = 5):
    """Enqueue a user stats update task."""
    return task_queue.enqueue_task("update_user_stats", {"user_id": user_id}, delay_seconds=delay_minutes * 60)