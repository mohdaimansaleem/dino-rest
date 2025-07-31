"""
Enhanced Base Endpoint Class
Provides standardized CRUD patterns, error handling, and documentation for all API endpoints
"""
from typing import List, Dict, Any, Optional, Type, TypeVar, Generic
from fastapi import HTTPException, status, Query, Depends
from pydantic import BaseModel
from abc import ABC, abstractmethod

from app.models.schemas import ApiResponse, PaginatedResponse, ErrorResponse
from app.core.logging_config import LoggerMixin
from app.core.security import get_current_user, get_current_admin_user

T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)


class BaseEndpoint(LoggerMixin, Generic[T, CreateT, UpdateT], ABC):
    """
    Base endpoint class providing standardized CRUD operations
    
    Features:
    - Standardized response patterns
    - Automatic error handling and logging
    - Role-based access control
    - Pagination support
    - Query filtering
    - OpenAPI documentation
    """
    
    def __init__(self, 
                 model_class: Type[T],
                 create_schema: Type[CreateT],
                 update_schema: Type[UpdateT],
                 collection_name: str,
                 require_auth: bool = True,
                 require_admin: bool = False):
        super().__init__()
        self.model_class = model_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.collection_name = collection_name
        self.require_auth = require_auth
        self.require_admin = require_admin
    
    @abstractmethod
    def get_repository(self):
        """Get the repository instance for this endpoint"""
        pass
    
    def get_auth_dependency(self):
        """Get the appropriate authentication dependency"""
        if not self.require_auth:
            return lambda: None
        elif self.require_admin:
            return get_current_admin_user
        else:
            return get_current_user
    
    async def create_item(self, 
                         item_data: CreateT, 
                         current_user: Optional[Dict[str, Any]] = None) -> ApiResponse:
        """
        Create a new item
        
        Args:
            item_data: Data for creating the item
            current_user: Current authenticated user
            
        Returns:
            ApiResponse with created item data
        """
        try:
            repo = self.get_repository()
            
            # Convert to dict and add metadata
            item_dict = item_data.dict()
            item_dict = await self._prepare_create_data(item_dict, current_user)
            
            # Validate creation permissions
            await self._validate_create_permissions(item_dict, current_user)
            
            # Create item
            item_id = await repo.create(item_dict)
            
            # Get created item
            created_item = await repo.get_by_id(item_id)
            
            self.log_operation(
                "create_item",
                collection=self.collection_name,
                item_id=item_id,
                user_id=current_user.get("id") if current_user else None
            )
            
            return ApiResponse(
                success=True,
                message=f"{self.collection_name.title()} created successfully",
                data=self.model_class(**created_item)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "create_item", collection=self.collection_name)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.collection_name}"
            )
    
    async def get_items(self,
                       page: int = Query(1, ge=1, description="Page number"),
                       page_size: int = Query(10, ge=1, le=100, description="Items per page"),
                       search: Optional[str] = Query(None, description="Search query"),
                       filters: Optional[Dict[str, Any]] = None,
                       current_user: Optional[Dict[str, Any]] = None) -> PaginatedResponse:
        """
        Get items with pagination and filtering
        
        Args:
            page: Page number (starts from 1)
            page_size: Number of items per page
            search: Search query
            filters: Additional filters
            current_user: Current authenticated user
            
        Returns:
            PaginatedResponse with items
        """
        try:
            repo = self.get_repository()
            
            # Build query filters
            query_filters = await self._build_query_filters(filters, search, current_user)
            
            # Get filtered items
            if query_filters:
                all_items = await repo.query(query_filters)
            else:
                all_items = await repo.get_all()
            
            # Apply user-specific filtering
            all_items = await self._filter_items_for_user(all_items, current_user)
            
            # Calculate pagination
            total = len(all_items)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items_page = all_items[start_idx:end_idx]
            
            # Convert to model objects
            items = [self.model_class(**item) for item in items_page]
            
            # Calculate pagination metadata
            total_pages = (total + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            self.log_operation(
                "get_items",
                collection=self.collection_name,
                page=page,
                page_size=page_size,
                total=total,
                user_id=current_user.get("id") if current_user else None
            )
            
            return PaginatedResponse(
                success=True,
                data=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "get_items", collection=self.collection_name)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {self.collection_name}"
            )
    
    async def get_item(self, 
                      item_id: str, 
                      current_user: Optional[Dict[str, Any]] = None) -> T:
        """
        Get item by ID
        
        Args:
            item_id: ID of the item to retrieve
            current_user: Current authenticated user
            
        Returns:
            Item model instance
        """
        try:
            repo = self.get_repository()
            
            item_data = await repo.get_by_id(item_id)
            if not item_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate access permissions
            await self._validate_access_permissions(item_data, current_user)
            
            self.log_operation(
                "get_item",
                collection=self.collection_name,
                item_id=item_id,
                user_id=current_user.get("id") if current_user else None
            )
            
            return self.model_class(**item_data)
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "get_item", collection=self.collection_name, item_id=item_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {self.collection_name}"
            )
    
    async def update_item(self, 
                         item_id: str, 
                         update_data: UpdateT, 
                         current_user: Optional[Dict[str, Any]] = None) -> ApiResponse:
        """
        Update item by ID
        
        Args:
            item_id: ID of the item to update
            update_data: Data for updating the item
            current_user: Current authenticated user
            
        Returns:
            ApiResponse with updated item data
        """
        try:
            repo = self.get_repository()
            
            # Check if item exists
            existing_item = await repo.get_by_id(item_id)
            if not existing_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate update permissions
            await self._validate_update_permissions(existing_item, current_user)
            
            # Prepare update data
            update_dict = update_data.dict(exclude_unset=True)
            update_dict = await self._prepare_update_data(update_dict, existing_item, current_user)
            
            # Update item
            await repo.update(item_id, update_dict)
            
            # Get updated item
            updated_item = await repo.get_by_id(item_id)
            
            self.log_operation(
                "update_item",
                collection=self.collection_name,
                item_id=item_id,
                updated_fields=list(update_dict.keys()),
                user_id=current_user.get("id") if current_user else None
            )
            
            return ApiResponse(
                success=True,
                message=f"{self.collection_name.title()} updated successfully",
                data=self.model_class(**updated_item)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "update_item", collection=self.collection_name, item_id=item_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.collection_name}"
            )
    
    async def delete_item(self, 
                         item_id: str, 
                         current_user: Optional[Dict[str, Any]] = None,
                         soft_delete: bool = True) -> ApiResponse:
        """
        Delete item by ID
        
        Args:
            item_id: ID of the item to delete
            current_user: Current authenticated user
            soft_delete: Whether to perform soft delete (deactivate) or hard delete
            
        Returns:
            ApiResponse confirming deletion
        """
        try:
            repo = self.get_repository()
            
            # Check if item exists
            existing_item = await repo.get_by_id(item_id)
            if not existing_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate delete permissions
            await self._validate_delete_permissions(existing_item, current_user)
            
            # Check for dependencies
            await self._check_delete_dependencies(item_id, existing_item)
            
            if soft_delete:
                # Soft delete by deactivating
                await repo.update(item_id, {"is_active": False})
                message = f"{self.collection_name.title()} deactivated successfully"
            else:
                # Hard delete
                await repo.delete(item_id)
                message = f"{self.collection_name.title()} deleted successfully"
            
            self.log_operation(
                "delete_item",
                collection=self.collection_name,
                item_id=item_id,
                soft_delete=soft_delete,
                user_id=current_user.get("id") if current_user else None
            )
            
            return ApiResponse(
                success=True,
                message=message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "delete_item", collection=self.collection_name, item_id=item_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.collection_name}"
            )
    
    # Hook methods for customization
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data before creation (override in subclasses)"""
        return data
    
    async def _prepare_update_data(self, 
                                  data: Dict[str, Any], 
                                  existing_item: Dict[str, Any],
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data before update (override in subclasses)"""
        return data
    
    async def _build_query_filters(self, 
                                  filters: Optional[Dict[str, Any]], 
                                  search: Optional[str],
                                  current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters (override in subclasses)"""
        query_filters = []
        
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, "==", value))
        
        return query_filters
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items based on user permissions (override in subclasses)"""
        return items
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate create permissions (override in subclasses)"""
        pass
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate access permissions (override in subclasses)"""
        pass
    
    async def _validate_update_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate update permissions (override in subclasses)"""
        pass
    
    async def _validate_delete_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate delete permissions (override in subclasses)"""
        pass
    
    async def _check_delete_dependencies(self, 
                                       item_id: str, 
                                       item: Dict[str, Any]):
        """Check for dependencies before deletion (override in subclasses)"""
        pass


class WorkspaceIsolatedEndpoint(BaseEndpoint[T, CreateT, UpdateT]):
    """
    Base endpoint for workspace-isolated resources
    Automatically filters resources by workspace
    """
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items by workspace"""
        if not current_user or not current_user.get("workspace_id"):
            return items
        
        # Filter by workspace
        workspace_id = current_user["workspace_id"]
        return [item for item in items if item.get("workspace_id") == workspace_id]
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate workspace access"""
        if not current_user:
            return
        
        user_workspace_id = current_user.get("workspace_id")
        item_workspace_id = item.get("workspace_id")
        
        if user_workspace_id and item_workspace_id and user_workspace_id != item_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Item belongs to different workspace"
            )


class VenueIsolatedEndpoint(BaseEndpoint[T, CreateT, UpdateT]):
    """
    Base endpoint for venue-isolated resources
    Automatically filters resources by venue access
    """
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items by venue access"""
        if not current_user:
            return items
        
        # Admin users see all items
        if current_user.get("role") == "admin":
            return items
        
        # Filter by user's venue access
        user_venue_id = current_user.get("venue_id")
        if user_venue_id:
            return [item for item in items if item.get("venue_id") == user_venue_id]
        
        return items
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate venue access"""
        if not current_user:
            return
        
        # Admin users have access to all items
        if current_user.get("role") == "admin":
            return
        
        user_venue_id = current_user.get("venue_id")
        item_venue_id = item.get("venue_id")
        
        if user_venue_id and item_venue_id and user_venue_id != item_venue_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Item belongs to different venue"
            )