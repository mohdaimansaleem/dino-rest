"""
Firestore Database Connection and Repository Classes
Production-ready implementation for Google Cloud Run
"""
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.core.config import get_firestore_client
from app.core.logging_config import EnhancedLoggerMixin, log_function_call
from app.core.logging_middleware import db_logger
import time

logger = logging.getLogger(__name__)


class FirestoreRepository(EnhancedLoggerMixin):
    """Base repository class for Firestore operations"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.db = None
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize collection reference"""
        try:
            self.db = get_firestore_client()
            self.collection = self.db.collection(self.collection_name)
            self.logger.info(f"Initialized Firestore collection: {self.collection_name}")
        except Exception as e:
            self.log_error(e, "initialize_collection", collection=self.collection_name)
            raise
    
    def _ensure_collection(self):
        """Ensure collection is available"""
        if not self.collection:
            self._initialize_collection()
        
        if not self.collection:
            raise RuntimeError(f"Firestore collection '{self.collection_name}' not available")
    
    def _doc_to_dict(self, doc) -> Dict[str, Any]:
        """Convert Firestore document to dictionary"""
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    
    def _prepare_data_for_firestore(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Firestore by converting incompatible types"""
        from datetime import date, datetime
        
        prepared_data = {}
        for key, value in data.items():
            if isinstance(value, date) and not isinstance(value, datetime):
                # Convert date to datetime at midnight
                prepared_data[key] = datetime.combine(value, datetime.min.time())
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                prepared_data[key] = self._prepare_data_for_firestore(value)
            elif isinstance(value, list):
                # Handle lists that might contain date objects
                prepared_data[key] = [
                    datetime.combine(item, datetime.min.time()) if isinstance(item, date) and not isinstance(item, datetime)
                    else self._prepare_data_for_firestore(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                prepared_data[key] = value
        
        return prepared_data
    
    @log_function_call(include_args=False, include_result=False)
    async def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document"""
        start_time = time.time()
        self._ensure_collection()
        
        try:
            self.log_debug(f"Creating document in {self.collection_name}", 
                          doc_id=doc_id, 
                          data_keys=list(data.keys()) if data else None)
            
            # Convert date objects to datetime for Firestore compatibility
            data = self._prepare_data_for_firestore(data)
            
            # Add timestamps
            data['created_at'] = datetime.utcnow()
            data['updated_at'] = datetime.utcnow()
            
            if doc_id:
                doc_ref = self.collection.document(doc_id)
                doc_ref.set(data)
                created_id = doc_id
            else:
                doc_ref = self.collection.add(data)[1]
                created_id = doc_ref.id
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log to database logger (conditional)
            try:
                from app.core.feature_manager import get_feature_manager
                feature_manager = get_feature_manager()
                if feature_manager and feature_manager.is_database_logging_enabled():
                    db_logger.log_query(
                        operation="create",
                        collection=self.collection_name,
                        duration_ms=duration_ms,
                        result_count=1,
                        doc_id=created_id
                    )
            except Exception:
                pass  # Skip logging if feature manager not available
            
            self.log_operation("create_document", 
                             collection=self.collection_name, 
                             doc_id=created_id,
                             duration_ms=duration_ms)
            
            # Return the created document with ID
            data['id'] = created_id
            return data
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log to database logger
            db_logger.log_error(
                operation="create",
                collection=self.collection_name,
                error=e,
                doc_id=doc_id,
                duration_ms=duration_ms
            )
            
            self.log_error(e, "create_document", 
                          collection=self.collection_name, 
                          doc_id=doc_id,
                          duration_ms=duration_ms)
            raise
    
    @log_function_call(include_args=False, include_result=False)
    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        start_time = time.time()
        self._ensure_collection()
        
        try:
            self.log_debug(f"Getting document by ID from {self.collection_name}", doc_id=doc_id)
            
            # Add timeout protection for Firestore operations
            import asyncio
            try:
                doc = await asyncio.wait_for(
                    asyncio.to_thread(self.collection.document(doc_id).get),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.log_error("Firestore timeout during get_by_id", collection=self.collection_name, doc_id=doc_id)
                raise Exception(f"Database timeout for {self.collection_name}.get_by_id({doc_id})")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Log to database logger (conditional)
                try:
                    from app.core.feature_manager import get_feature_manager
                    feature_manager = get_feature_manager()
                    if feature_manager and feature_manager.is_database_logging_enabled():
                        db_logger.log_query(
                            operation="get_by_id",
                            collection=self.collection_name,
                            duration_ms=duration_ms,
                            result_count=1,
                            doc_id=doc_id
                        )
                except Exception:
                    pass  # Skip logging if feature manager not available
                
                self.log_operation("get_document", 
                                 collection=self.collection_name, 
                                 doc_id=doc_id, 
                                 found=True,
                                 duration_ms=duration_ms)
                return data
            
            # Log to database logger
            db_logger.log_query(
                operation="get_by_id",
                collection=self.collection_name,
                duration_ms=duration_ms,
                result_count=0,
                doc_id=doc_id
            )
            
            self.log_operation("get_document", 
                             collection=self.collection_name, 
                             doc_id=doc_id, 
                             found=False,
                             duration_ms=duration_ms)
            return None
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log to database logger
            db_logger.log_error(
                operation="get_by_id",
                collection=self.collection_name,
                error=e,
                doc_id=doc_id,
                duration_ms=duration_ms
            )
            
            self.log_error(e, "get_document", 
                          collection=self.collection_name, 
                          doc_id=doc_id,
                          duration_ms=duration_ms)
            raise
    
    async def update(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document by ID"""
        self._ensure_collection()
        
        try:
            # Convert date objects to datetime for Firestore compatibility
            data = self._prepare_data_for_firestore(data)
            
            # Add update timestamp
            data['updated_at'] = datetime.utcnow()
            
            doc_ref = self.collection.document(doc_id)
            doc_ref.update(data)
            self.log_operation("update_document", 
                             collection=self.collection_name, 
                             doc_id=doc_id)
            
            # Get and return the updated document
            updated_doc = await self.get_by_id(doc_id)
            return updated_doc
        except Exception as e:
            self.log_error(e, "update_document", 
                          collection=self.collection_name, 
                          doc_id=doc_id)
            raise
    
    async def delete(self, doc_id: str) -> bool:
        """Delete document by ID"""
        self._ensure_collection()
        
        try:
            self.collection.document(doc_id).delete()
            self.log_operation("delete_document", 
                             collection=self.collection_name, 
                             doc_id=doc_id)
            return True
        except Exception as e:
            self.log_error(e, "delete_document", 
                          collection=self.collection_name, 
                          doc_id=doc_id)
            raise
    
    async def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all documents in collection"""
        self._ensure_collection()
        
        try:
            query = self.collection
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            self.log_operation("get_all_documents", 
                             collection=self.collection_name, 
                             count=len(results), 
                             limit=limit)
            return results
        except Exception as e:
            self.log_error(e, "get_all_documents", 
                          collection=self.collection_name, 
                          limit=limit)
            raise
    
    async def query(self, filters: List[tuple], order_by: Optional[str] = None, 
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query documents with filters"""
        self._ensure_collection()
        
        try:
            query = self.collection
            
            # Apply filters
            for field, operator, value in filters:
                query = query.where(filter=FieldFilter(field, operator, value))
            
            # Apply ordering
            if order_by:
                query = query.order_by(order_by)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Add timeout protection for query operations
            import asyncio
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(lambda: list(query.stream())),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                self.log_error("Firestore timeout during query", collection=self.collection_name, filters=filters)
                raise Exception(f"Database timeout for {self.collection_name}.query({filters})")
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            self.log_operation("query_documents", 
                             collection=self.collection_name, 
                             filters=len(filters), 
                             count=len(results), 
                             order_by=order_by, 
                             limit=limit)
            return results
        except Exception as e:
            self.log_error(e, "query_documents", 
                          collection=self.collection_name, 
                          filters=filters, 
                          order_by=order_by, 
                          limit=limit)
            raise
    
    async def exists(self, doc_id: str) -> bool:
        """Check if document exists"""
        self._ensure_collection()
        
        try:
            doc = self.collection.document(doc_id).get()
            exists = doc.exists
            self.log_operation("check_document_exists", 
                             collection=self.collection_name, 
                             doc_id=doc_id, 
                             exists=exists)
            return exists
        except Exception as e:
            self.log_error(e, "check_document_exists", 
                          collection=self.collection_name, 
                          doc_id=doc_id)
            raise
    
    async def update_batch(self, updates: List[tuple]) -> bool:
        """Batch update multiple documents"""
        self._ensure_collection()
        
        try:
            # Firestore batch operations
            batch = self.db.batch()
            
            for doc_id, update_data in updates:
                # Prepare data for Firestore
                update_data = self._prepare_data_for_firestore(update_data)
                update_data['updated_at'] = datetime.utcnow()
                
                doc_ref = self.collection.document(doc_id)
                batch.update(doc_ref, update_data)
            
            # Commit batch
            batch.commit()
            
            self.log_operation("batch_update", 
                             collection=self.collection_name, 
                             count=len(updates))
            return True
            
        except Exception as e:
            self.log_error(e, "batch_update", 
                          collection=self.collection_name, 
                          count=len(updates))
            raise
    
    async def create_batch(self, items_data: List[Dict[str, Any]]) -> List[str]:
        """Batch create multiple documents"""
        self._ensure_collection()
        
        try:
            # Firestore batch operations
            batch = self.db.batch()
            created_ids = []
            
            for data in items_data:
                # Prepare data for Firestore
                data = self._prepare_data_for_firestore(data)
                data['created_at'] = datetime.utcnow()
                data['updated_at'] = datetime.utcnow()
                
                doc_ref = self.collection.document()
                data['id'] = doc_ref.id
                batch.set(doc_ref, data)
                created_ids.append(doc_ref.id)
            
            # Commit batch
            batch.commit()
            
            self.log_operation("batch_create", 
                             collection=self.collection_name, 
                             count=len(created_ids))
            return created_ids
            
        except Exception as e:
            self.log_error(e, "batch_create", 
                          collection=self.collection_name, 
                          count=len(items_data))
            raise
    
    async def search_text(self, 
                         search_fields: List[str],
                         search_term: str,
                         additional_filters: Optional[List[tuple]] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for documents containing the search term in specified fields
        Note: This is a basic implementation. For production, consider using 
        Firestore's full-text search or Algolia integration.
        """
        self._ensure_collection()
        
        try:
            # Get all documents (or apply additional filters first)
            if additional_filters:
                all_docs = await self.query(additional_filters, limit=limit)
            else:
                all_docs = await self.get_all(limit=limit)
            
            # Filter documents that contain the search term in any of the specified fields
            search_term_lower = search_term.lower()
            matching_docs = []
            
            for doc in all_docs:
                for field in search_fields:
                    field_value = doc.get(field, '')
                    
                    # Handle different field types
                    if isinstance(field_value, str):
                        if search_term_lower in field_value.lower():
                            matching_docs.append(doc)
                            break
                    elif isinstance(field_value, list):
                        # Search in array fields (like cuisine_types)
                        for item in field_value:
                            if isinstance(item, str) and search_term_lower in item.lower():
                                matching_docs.append(doc)
                                break
                        if doc in matching_docs:
                            break
            
            self.log_operation("search_text", 
                             collection=self.collection_name, 
                             search_fields=search_fields,
                             search_term=search_term,
                             results_count=len(matching_docs))
            
            return matching_docs
            
        except Exception as e:
            self.log_error(e, "search_text", 
                          collection=self.collection_name, 
                          search_fields=search_fields,
                          search_term=search_term)
            raise


# Repository classes for each collection
class WorkspaceRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("workspaces")
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workspace by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_by_owner(self, owner_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by owner ID"""
        results = await self.query([("owner_id", "==", owner_id)])
        return results[0] if results else None


class RoleRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("roles")
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_system_roles(self) -> List[Dict[str, Any]]:
        """Get all system roles - Note: is_system_role field removed from schema"""
        # This method is kept for backward compatibility but will return all roles
        # since is_system_role field has been removed from roles collection
        return await self.get_all()


class PermissionRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("permissions")
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_system_permissions(self) -> List[Dict[str, Any]]:
        """Get all system permissions"""
        return await self.query([("is_system_permission", "==", True)])


class UserRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("users")
    
    async def get_by_venue_id(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get all users by venue ID"""
        try:
            query = self.collection.where('venue_id', '==', venue_id)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by venue_id {venue_id}: {e}")
            return []
    
    async def get_by_workspace_id(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all users by workspace ID"""
        try:
            query = self.collection.where('workspace_id', '==', workspace_id)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by workspace_id {workspace_id}: {e}")
            return []
    
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent users"""
        try:
            query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting recent users: {e}")
            return []

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        results = await self.query([("email", "==", email)])
        return results[0] if results else None
    
    async def get_by_mobile(self, mobile_number: str) -> Optional[Dict[str, Any]]:
        """Get user by mobile number"""
        results = await self.query([("mobile_number", "==", mobile_number)])
        return results[0] if results else None
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get users by workspace ID"""
        return await self.query([("workspace_id", "==", workspace_id)])
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get users by venue ID"""
        return await self.query([("venue_id", "==", venue_id)])
    
    async def get_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get users by role ID"""
        return await self.query([("role_id", "==", role_id)])


class VenueRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("venues")
    
    async def get_by_workspace_id(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all venues by workspace ID"""
        return await self.query([("workspace_id", "==", workspace_id)])
    
    async def get_by_venue_id(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get venue by venue ID (returns list for consistency)"""
        venue = await self.get_by_id(venue_id)
        return [venue] if venue else []
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get venues by workspace ID"""
        return await self.query([("workspace_id", "==", workspace_id)])
    
    async def get_by_admin(self, admin_id: str) -> List[Dict[str, Any]]:
        """Get cafes by admin ID"""
        return await self.query([("admin_id", "==", admin_id)])
    
    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get cafes by owner ID"""
        return await self.query([("owner_id", "==", owner_id)])
    
    async def get_active_venues(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all active venues"""
        return await self.query([("is_active", "==", True)], limit=limit)
    
    async def get_by_subscription_status(self, status: str) -> List[Dict[str, Any]]:
        """Get venues by subscription status"""
        return await self.query([("subscription_status", "==", status)])


class MenuItemRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("menu_items")
    
    async def get_by_venue_id(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get menu items by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get menu items by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="order")
    
    async def get_by_category(self, venue_id: str, category: str) -> List[Dict[str, Any]]:
        """Get menu items by cafe and category"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("category", "==", category)
        ], order_by="order")


class MenuCategoryRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("menu_categories")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get menu categories by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="order")


class TableRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("tables")
    
    async def get_by_venue_id(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get tables by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="table_number")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get tables by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="table_number")
    
    async def get_by_table_number(self, venue_id: str, table_number: int) -> Optional[Dict[str, Any]]:
        """Get table by cafe and table number"""
        results = await self.query([
            ("venue_id", "==", venue_id),
            ("table_number", "==", table_number)
        ])
        return results[0] if results else None
    
    async def get_by_qr_code(self, qr_code: str) -> Optional[Dict[str, Any]]:
        """Get table by QR code"""
        results = await self.query([("qr_code", "==", qr_code)])
        return results[0] if results else None
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get tables by status"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("table_status", "==", status)
        ])


class OrderRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("orders")
    
    async def get_by_venue_id(self, venue_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get orders by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at", limit=limit)
    
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent orders"""
        return await self.query([], order_by="created_at", limit=limit)
    
    async def get_by_cafe(self, venue_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get orders by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at", limit=limit)
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get orders by cafe and status"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("status", "==", status)
        ], order_by="created_at")


class AnalyticsRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("analytics")
    
    async def get_by_cafe_and_date_range(self, venue_id: str, start_date: datetime, 
                                       end_date: datetime) -> List[Dict[str, Any]]:
        """Get analytics by cafe and date range"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("date", ">=", start_date),
            ("date", "<=", end_date)
        ], order_by="date")


class CustomerRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("customers")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get customers by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)])
    
    async def get_by_mobile(self, mobile_number: str) -> Optional[Dict[str, Any]]:
        """Get customer by mobile number"""
        results = await self.query([("mobile_number", "==", mobile_number)])
        return results[0] if results else None
    
    async def get_by_venue_id(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get all users by venue ID"""
        try:
            query = self.collection.where('venue_id', '==', venue_id)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by venue_id {venue_id}: {e}")
            return []
    
    async def get_by_workspace_id(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all users by workspace ID"""
        try:
            query = self.collection.where('workspace_id', '==', workspace_id)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by workspace_id {workspace_id}: {e}")
            return []
    
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent users"""
        try:
            query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting recent users: {e}")
            return []

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get customer by email"""
        results = await self.query([("email", "==", email)])
        return results[0] if results else None


class ReviewRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("reviews")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get reviews by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at")
    
    async def get_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get reviews by customer ID"""
        return await self.query([("customer_id", "==", customer_id)])
    
    async def get_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get review by order ID"""
        results = await self.query([("order_id", "==", order_id)])
        return results[0] if results else None


class NotificationRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("notifications")
    
    async def get_by_recipient(self, recipient_id: str) -> List[Dict[str, Any]]:
        """Get notifications by recipient ID"""
        return await self.query([("recipient_id", "==", recipient_id)], order_by="created_at")
    
    async def get_unread(self, recipient_id: str) -> List[Dict[str, Any]]:
        """Get unread notifications"""
        return await self.query([
            ("recipient_id", "==", recipient_id),
            ("is_read", "==", False)
        ])


class TransactionRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("transactions")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get transactions by cafe ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at")
    
    async def get_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        """Get transactions by order ID"""
        return await self.query([("order_id", "==", order_id)])
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get transactions by status"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("status", "==", status)
        ])


# Repository instances
workspace_repo = WorkspaceRepository()
role_repo = RoleRepository()
permission_repo = PermissionRepository()
user_repo = UserRepository()
venue_repo = VenueRepository()
menu_item_repo = MenuItemRepository()
menu_category_repo = MenuCategoryRepository()
table_repo = TableRepository()
order_repo = OrderRepository()
customer_repo = CustomerRepository()
review_repo = ReviewRepository()
notification_repo = NotificationRepository()
transaction_repo = TransactionRepository()
analytics_repo = AnalyticsRepository()


def get_workspace_repo() -> WorkspaceRepository:
    """Get workspace repository instance"""
    return workspace_repo


def get_role_repo() -> RoleRepository:
    """Get role repository instance"""
    return role_repo


def get_permission_repo() -> PermissionRepository:
    """Get permission repository instance"""
    return permission_repo


def get_user_repo() -> UserRepository:
    """Get user repository instance"""
    return user_repo


def get_venue_repo() -> VenueRepository:
    """Get venue repository instance"""
    return venue_repo


def get_menu_item_repo() -> MenuItemRepository:
    """Get menu item repository instance"""
    return menu_item_repo


def get_menu_category_repo() -> MenuCategoryRepository:
    """Get menu category repository instance"""
    return menu_category_repo


def get_table_repo() -> TableRepository:
    """Get table repository instance"""
    return table_repo


def get_order_repo() -> OrderRepository:
    """Get order repository instance"""
    return order_repo


def get_customer_repo() -> CustomerRepository:
    """Get customer repository instance"""
    return customer_repo


def get_review_repo() -> ReviewRepository:
    """Get review repository instance"""
    return review_repo


def get_notification_repo() -> NotificationRepository:
    """Get notification repository instance"""
    return notification_repo


def get_transaction_repo() -> TransactionRepository:
    """Get transaction repository instance"""
    return transaction_repo


def get_analytics_repo() -> AnalyticsRepository:
    """Get analytics repository instance"""
    return analytics_repo