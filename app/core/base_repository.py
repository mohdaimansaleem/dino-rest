"""
Enhanced Base Repository Class
Provides advanced query capabilities, caching, and optimized database operations
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio
from functools import wraps

from app.database.firestore import FirestoreRepository
from app.core.logging_config import LoggerMixin


def cache_result(ttl_seconds: int = 300):
    """
    Decorator for caching repository results
    
    Args:
        ttl_seconds: Time to live for cached results in seconds
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if datetime.utcnow() - timestamp < timedelta(seconds=ttl_seconds):
                    self.log_operation("cache_hit", method=func.__name__, cache_key=cache_key)
                    return result
            
            # Execute function and cache result
            result = await func(self, *args, **kwargs)
            cache[cache_key] = (result, datetime.utcnow())
            
            # Clean old cache entries
            current_time = datetime.utcnow()
            cache_keys_to_remove = [
                key for key, (_, timestamp) in cache.items()
                if current_time - timestamp >= timedelta(seconds=ttl_seconds)
            ]
            for key in cache_keys_to_remove:
                del cache[key]
            
            self.log_operation("cache_miss", method=func.__name__, cache_key=cache_key)
            return result
        
        return wrapper
    return decorator


class EnhancedRepository(FirestoreRepository):
    """
    Enhanced repository with advanced querying, caching, and batch operations
    """
    
    def __init__(self, collection_name: str):
        super().__init__(collection_name)
        self._cache_enabled = True
        self._batch_size = 500
    
    async def create_batch(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple items in batch
        
        Args:
            items: List of item data dictionaries
            
        Returns:
            List of created item IDs
        """
        try:
            self._ensure_collection()
            
            created_ids = []
            current_time = datetime.utcnow()
            
            # Process in batches to avoid Firestore limits
            for i in range(0, len(items), self._batch_size):
                batch_items = items[i:i + self._batch_size]
                batch = self.db.batch()
                batch_ids = []
                
                for item_data in batch_items:
                    # Add timestamps
                    item_data['created_at'] = current_time
                    item_data['updated_at'] = current_time
                    
                    # Create document reference
                    doc_ref = self.collection.document()
                    batch.set(doc_ref, item_data)
                    batch_ids.append(doc_ref.id)
                
                # Commit batch
                batch.commit()
                created_ids.extend(batch_ids)
            
            self.log_operation(
                "create_batch",
                collection=self.collection_name,
                count=len(items),
                batches=len(range(0, len(items), self._batch_size))
            )
            
            return created_ids
            
        except Exception as e:
            self.log_error(e, "create_batch", collection=self.collection_name, count=len(items))
            raise
    
    async def update_batch(self, updates: List[tuple]) -> bool:
        """
        Update multiple items in batch
        
        Args:
            updates: List of (item_id, update_data) tuples
            
        Returns:
            Success status
        """
        try:
            self._ensure_collection()
            
            current_time = datetime.utcnow()
            
            # Process in batches
            for i in range(0, len(updates), self._batch_size):
                batch_updates = updates[i:i + self._batch_size]
                batch = self.db.batch()
                
                for item_id, update_data in batch_updates:
                    # Add update timestamp
                    update_data['updated_at'] = current_time
                    
                    # Add to batch
                    doc_ref = self.collection.document(item_id)
                    batch.update(doc_ref, update_data)
                
                # Commit batch
                batch.commit()
            
            self.log_operation(
                "update_batch",
                collection=self.collection_name,
                count=len(updates),
                batches=len(range(0, len(updates), self._batch_size))
            )
            
            return True
            
        except Exception as e:
            self.log_error(e, "update_batch", collection=self.collection_name, count=len(updates))
            raise
    
    async def delete_batch(self, item_ids: List[str], soft_delete: bool = True) -> bool:
        """
        Delete multiple items in batch
        
        Args:
            item_ids: List of item IDs to delete
            soft_delete: Whether to perform soft delete (deactivate)
            
        Returns:
            Success status
        """
        try:
            self._ensure_collection()
            
            if soft_delete:
                # Soft delete by updating is_active field
                updates = [(item_id, {"is_active": False}) for item_id in item_ids]
                return await self.update_batch(updates)
            else:
                # Hard delete
                for i in range(0, len(item_ids), self._batch_size):
                    batch_ids = item_ids[i:i + self._batch_size]
                    batch = self.db.batch()
                    
                    for item_id in batch_ids:
                        doc_ref = self.collection.document(item_id)
                        batch.delete(doc_ref)
                    
                    # Commit batch
                    batch.commit()
            
            self.log_operation(
                "delete_batch",
                collection=self.collection_name,
                count=len(item_ids),
                soft_delete=soft_delete,
                batches=len(range(0, len(item_ids), self._batch_size))
            )
            
            return True
            
        except Exception as e:
            self.log_error(e, "delete_batch", collection=self.collection_name, count=len(item_ids))
            raise
    
    @cache_result(ttl_seconds=300)
    async def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        Get single item by field value (cached)
        
        Args:
            field: Field name to search
            value: Field value to match
            
        Returns:
            Item data or None
        """
        results = await self.query([(field, "==", value)], limit=1)
        return results[0] if results else None
    
    @cache_result(ttl_seconds=180)
    async def get_by_fields(self, field_values: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get items by multiple field values (cached)
        
        Args:
            field_values: Dictionary of field names and values
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        filters = [(field, "==", value) for field, value in field_values.items()]
        return await self.query(filters, limit=limit)
    
    async def search_text(self, 
                         search_fields: List[str], 
                         search_term: str, 
                         additional_filters: Optional[List[tuple]] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search items by text in multiple fields
        
        Args:
            search_fields: List of field names to search in
            search_term: Text to search for
            additional_filters: Additional query filters
            limit: Maximum number of results
            
        Returns:
            List of matching items
        """
        try:
            # Get all items (Firestore doesn't support full-text search natively)
            filters = additional_filters or []
            all_items = await self.query(filters)
            
            # Filter by search term
            search_term_lower = search_term.lower()
            matching_items = []
            
            for item in all_items:
                for field in search_fields:
                    field_value = item.get(field, "")
                    if isinstance(field_value, str) and search_term_lower in field_value.lower():
                        matching_items.append(item)
                        break
            
            # Apply limit
            if limit:
                matching_items = matching_items[:limit]
            
            self.log_operation(
                "search_text",
                collection=self.collection_name,
                search_term=search_term,
                search_fields=search_fields,
                results=len(matching_items)
            )
            
            return matching_items
            
        except Exception as e:
            self.log_error(e, "search_text", collection=self.collection_name, search_term=search_term)
            raise
    
    async def get_paginated(self, 
                           page: int = 1, 
                           page_size: int = 10,
                           filters: Optional[List[tuple]] = None,
                           order_by: Optional[str] = None,
                           order_desc: bool = False) -> Dict[str, Any]:
        """
        Get paginated results with metadata
        
        Args:
            page: Page number (starts from 1)
            page_size: Number of items per page
            filters: Query filters
            order_by: Field to order by
            order_desc: Whether to order in descending order
            
        Returns:
            Dictionary with items and pagination metadata
        """
        try:
            # Get all matching items
            if filters:
                all_items = await self.query(filters, order_by=order_by)
            else:
                all_items = await self.get_all()
            
            # Apply ordering if specified and not already applied
            if order_by and not filters:
                reverse = order_desc
                all_items.sort(key=lambda x: x.get(order_by, ""), reverse=reverse)
            
            # Calculate pagination
            total = len(all_items)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items_page = all_items[start_idx:end_idx]
            
            # Calculate metadata
            total_pages = (total + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            self.log_operation(
                "get_paginated",
                collection=self.collection_name,
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages
            )
            
            return {
                "items": items_page,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
            
        except Exception as e:
            self.log_error(e, "get_paginated", collection=self.collection_name)
            raise
    
    async def count_by_filters(self, filters: List[tuple]) -> int:
        """
        Count items matching filters
        
        Args:
            filters: Query filters
            
        Returns:
            Count of matching items
        """
        try:
            items = await self.query(filters)
            count = len(items)
            
            self.log_operation(
                "count_by_filters",
                collection=self.collection_name,
                filters=len(filters),
                count=count
            )
            
            return count
            
        except Exception as e:
            self.log_error(e, "count_by_filters", collection=self.collection_name)
            raise
    
    async def get_distinct_values(self, field: str, filters: Optional[List[tuple]] = None) -> List[Any]:
        """
        Get distinct values for a field
        
        Args:
            field: Field name to get distinct values for
            filters: Optional filters to apply
            
        Returns:
            List of distinct values
        """
        try:
            if filters:
                items = await self.query(filters)
            else:
                items = await self.get_all()
            
            # Extract distinct values
            values = set()
            for item in items:
                value = item.get(field)
                if value is not None:
                    values.add(value)
            
            distinct_values = list(values)
            
            self.log_operation(
                "get_distinct_values",
                collection=self.collection_name,
                field=field,
                distinct_count=len(distinct_values)
            )
            
            return distinct_values
            
        except Exception as e:
            self.log_error(e, "get_distinct_values", collection=self.collection_name, field=field)
            raise
    
    async def aggregate_by_field(self, 
                                group_by_field: str, 
                                aggregate_field: str,
                                operation: str = "sum",
                                filters: Optional[List[tuple]] = None) -> Dict[str, float]:
        """
        Aggregate values by grouping field
        
        Args:
            group_by_field: Field to group by
            aggregate_field: Field to aggregate
            operation: Aggregation operation (sum, avg, count, min, max)
            filters: Optional filters to apply
            
        Returns:
            Dictionary mapping group values to aggregated results
        """
        try:
            if filters:
                items = await self.query(filters)
            else:
                items = await self.get_all()
            
            # Group items
            groups = {}
            for item in items:
                group_value = item.get(group_by_field)
                if group_value is not None:
                    if group_value not in groups:
                        groups[group_value] = []
                    groups[group_value].append(item)
            
            # Aggregate
            results = {}
            for group_value, group_items in groups.items():
                if operation == "count":
                    results[group_value] = len(group_items)
                else:
                    values = [item.get(aggregate_field, 0) for item in group_items if item.get(aggregate_field) is not None]
                    if values:
                        if operation == "sum":
                            results[group_value] = sum(values)
                        elif operation == "avg":
                            results[group_value] = sum(values) / len(values)
                        elif operation == "min":
                            results[group_value] = min(values)
                        elif operation == "max":
                            results[group_value] = max(values)
                        else:
                            results[group_value] = 0
                    else:
                        results[group_value] = 0
            
            self.log_operation(
                "aggregate_by_field",
                collection=self.collection_name,
                group_by_field=group_by_field,
                aggregate_field=aggregate_field,
                operation=operation,
                groups=len(results)
            )
            
            return results
            
        except Exception as e:
            self.log_error(e, "aggregate_by_field", collection=self.collection_name)
            raise
    
    async def bulk_upsert(self, items: List[Dict[str, Any]], id_field: str = "id") -> Dict[str, List[str]]:
        """
        Bulk upsert (insert or update) items
        
        Args:
            items: List of item data
            id_field: Field name containing the ID
            
        Returns:
            Dictionary with lists of created and updated IDs
        """
        try:
            self._ensure_collection()
            
            created_ids = []
            updated_ids = []
            current_time = datetime.utcnow()
            
            # Process in batches
            for i in range(0, len(items), self._batch_size):
                batch_items = items[i:i + self._batch_size]
                batch = self.db.batch()
                
                for item_data in batch_items:
                    item_id = item_data.get(id_field)
                    
                    if item_id:
                        # Check if exists
                        existing = await self.exists(item_id)
                        if existing:
                            # Update
                            item_data['updated_at'] = current_time
                            doc_ref = self.collection.document(item_id)
                            batch.update(doc_ref, item_data)
                            updated_ids.append(item_id)
                        else:
                            # Create with specified ID
                            item_data['created_at'] = current_time
                            item_data['updated_at'] = current_time
                            doc_ref = self.collection.document(item_id)
                            batch.set(doc_ref, item_data)
                            created_ids.append(item_id)
                    else:
                        # Create with auto-generated ID
                        item_data['created_at'] = current_time
                        item_data['updated_at'] = current_time
                        doc_ref = self.collection.document()
                        batch.set(doc_ref, item_data)
                        created_ids.append(doc_ref.id)
                
                # Commit batch
                batch.commit()
            
            self.log_operation(
                "bulk_upsert",
                collection=self.collection_name,
                total_items=len(items),
                created=len(created_ids),
                updated=len(updated_ids)
            )
            
            return {
                "created": created_ids,
                "updated": updated_ids
            }
            
        except Exception as e:
            self.log_error(e, "bulk_upsert", collection=self.collection_name, count=len(items))
            raise
    
    def clear_cache(self):
        """Clear all cached results"""
        # This would clear method-level caches if implemented
        self.log_operation("clear_cache", collection=self.collection_name)
    
    def enable_cache(self, enabled: bool = True):
        """Enable or disable caching"""
        self._cache_enabled = enabled
        self.log_operation("cache_toggle", collection=self.collection_name, enabled=enabled)
    
    def set_batch_size(self, batch_size: int):
        """Set batch size for bulk operations"""
        self._batch_size = max(1, min(batch_size, 500))  # Firestore limit is 500
        self.log_operation("set_batch_size", collection=self.collection_name, batch_size=self._batch_size)