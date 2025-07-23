#!/usr/bin/env python3
"""
Firestore backup script for Pokemon TCG Pocket application.
Creates exports of Firestore collections and stores them in Cloud Storage.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from google.cloud import firestore_admin_v1
from google.cloud import storage
from google.cloud import firestore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirestoreBackupManager:
    def __init__(self, project_id: str, backup_bucket: str):
        self.project_id = project_id
        self.backup_bucket = backup_bucket
        self.firestore_admin = firestore_admin_v1.FirestoreAdminClient()
        self.storage_client = storage.Client(project=project_id)
        self.firestore_client = firestore.Client(project=project_id)
        
    def create_firestore_export(self, collection_ids: List[str] = None) -> str:
        """Create a Firestore export to Cloud Storage."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        # Default to all collections if none specified
        if not collection_ids:
            collection_ids = ['users', 'decks', 'cards', 'internal_config']
            
        output_uri = f"gs://{self.backup_bucket}/firestore_exports/{timestamp}"
        
        database_path = self.firestore_admin.database_path(
            self.project_id, "(default)"
        )
        
        logger.info(f"Starting Firestore export to {output_uri}")
        logger.info(f"Collections: {collection_ids}")
        
        operation = self.firestore_admin.export_documents(
            request={
                "name": database_path,
                "output_uri_prefix": output_uri,
                "collection_ids": collection_ids
            }
        )
        
        logger.info("Export operation started, waiting for completion...")
        response = operation.result(timeout=1800)  # 30 minutes timeout
        
        logger.info(f"Export completed: {response.output_uri_prefix}")
        return response.output_uri_prefix
        
    def create_json_backup(self, collection_ids: List[str] = None) -> str:
        """Create a JSON backup of specific collections for easy inspection."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        if not collection_ids:
            collection_ids = ['users', 'decks', 'cards', 'internal_config']
            
        backup_data = {}
        
        for collection_id in collection_ids:
            logger.info(f"Backing up collection: {collection_id}")
            collection_ref = self.firestore_client.collection(collection_id)
            
            documents = []
            for doc in collection_ref.stream():
                doc_data = doc.to_dict()
                # Convert non-serializable types
                doc_data['_document_id'] = doc.id
                doc_data['_created_time'] = doc.create_time.isoformat() if doc.create_time else None
                doc_data['_updated_time'] = doc.update_time.isoformat() if doc.update_time else None
                documents.append(doc_data)
                
            backup_data[collection_id] = {
                'document_count': len(documents),
                'documents': documents
            }
            logger.info(f"Backed up {len(documents)} documents from {collection_id}")
            
        # Upload JSON backup to Cloud Storage
        backup_filename = f"json_backups/firestore_backup_{timestamp}.json"
        bucket = self.storage_client.bucket(self.backup_bucket)
        blob = bucket.blob(backup_filename)
        
        blob.upload_from_string(
            json.dumps(backup_data, indent=2, default=str),
            content_type='application/json'
        )
        
        logger.info(f"JSON backup uploaded to gs://{self.backup_bucket}/{backup_filename}")
        return f"gs://{self.backup_bucket}/{backup_filename}"
        
    def list_backups(self, backup_type: str = "all") -> List[Dict[str, Any]]:
        """List available backups."""
        bucket = self.storage_client.bucket(self.backup_bucket)
        backups = []
        
        prefixes = []
        if backup_type in ["all", "export"]:
            prefixes.append("firestore_exports/")
        if backup_type in ["all", "json"]:
            prefixes.append("json_backups/")
            
        for prefix in prefixes:
            for blob in bucket.list_blobs(prefix=prefix):
                backups.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created': blob.time_created.isoformat(),
                    'type': 'export' if 'exports' in blob.name else 'json'
                })
                
        return sorted(backups, key=lambda x: x['created'], reverse=True)
        
    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention_days."""
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        bucket = self.storage_client.bucket(self.backup_bucket)
        
        deleted_count = 0
        for prefix in ["firestore_exports/", "json_backups/"]:
            for blob in bucket.list_blobs(prefix=prefix):
                if blob.time_created < cutoff_date:
                    logger.info(f"Deleting old backup: {blob.name}")
                    blob.delete()
                    deleted_count += 1
                    
        logger.info(f"Cleaned up {deleted_count} old backups")
        
    def restore_from_export(self, export_uri: str, collection_ids: List[str] = None):
        """Restore from a Firestore export (WARNING: This overwrites existing data)."""
        logger.warning("RESTORE OPERATION - This will overwrite existing data!")
        
        database_path = self.firestore_admin.database_path(
            self.project_id, "(default)"
        )
        
        request = {
            "name": database_path,
            "input_uri_prefix": export_uri
        }
        
        if collection_ids:
            request["collection_ids"] = collection_ids
            
        operation = self.firestore_admin.import_documents(request=request)
        logger.info("Restore operation started, waiting for completion...")
        
        response = operation.result(timeout=1800)  # 30 minutes timeout
        logger.info("Restore completed successfully")
        return response


def main():
    project_id = os.environ.get('GCP_PROJECT_ID', 'pvpocket-dd286')
    backup_bucket = f"{project_id}-backups"
    
    if len(sys.argv) < 2:
        print("Usage: python firestore_backup.py <command> [options]")
        print("Commands:")
        print("  export [collection_ids...] - Create Firestore export")
        print("  json [collection_ids...] - Create JSON backup")
        print("  list [export|json|all] - List available backups")
        print("  cleanup [retention_days] - Clean up old backups")
        print("  restore <export_uri> [collection_ids...] - Restore from export")
        sys.exit(1)
        
    command = sys.argv[1]
    backup_manager = FirestoreBackupManager(project_id, backup_bucket)
    
    try:
        if command == "export":
            collection_ids = sys.argv[2:] if len(sys.argv) > 2 else None
            export_uri = backup_manager.create_firestore_export(collection_ids)
            print(f"Export completed: {export_uri}")
            
        elif command == "json":
            collection_ids = sys.argv[2:] if len(sys.argv) > 2 else None
            backup_uri = backup_manager.create_json_backup(collection_ids)
            print(f"JSON backup completed: {backup_uri}")
            
        elif command == "list":
            backup_type = sys.argv[2] if len(sys.argv) > 2 else "all"
            backups = backup_manager.list_backups(backup_type)
            
            print(f"Available backups ({backup_type}):")
            for backup in backups:
                print(f"  {backup['name']} ({backup['type']}) - {backup['created']} - {backup['size']} bytes")
                
        elif command == "cleanup":
            retention_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            backup_manager.cleanup_old_backups(retention_days)
            print(f"Cleanup completed (retention: {retention_days} days)")
            
        elif command == "restore":
            if len(sys.argv) < 3:
                print("Error: restore command requires export_uri")
                sys.exit(1)
                
            export_uri = sys.argv[2]
            collection_ids = sys.argv[3:] if len(sys.argv) > 3 else None
            
            response = input(f"WARNING: This will overwrite existing data. Continue? (yes/no): ")
            if response.lower() == 'yes':
                backup_manager.restore_from_export(export_uri, collection_ids)
                print("Restore completed")
            else:
                print("Restore cancelled")
                
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()