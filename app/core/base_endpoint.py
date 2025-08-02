"""
Base Endpoint Classes for Standardized CRUD Operations
Provides common patterns for API endpoints with authentication, validation, and workspace isolation
"""
from typing import TypeVar, Generic, List, Dict, Any, Optional, Type
from fastapi import HTTPException, status
from pydantic import BaseModel
from abc import ABC, abstractmethod

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Type variables for generic classes
ModelType = TypeVar('ModelType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class BaseEndpoint(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base endpoint class providing standardized CRUD operations
    """
    
    def __init__(self, 
                 model_class: Type[ModelType],
                 create_schema: Type[CreateSchemaType],
                 update_schema: Type[UpdateSchemaType],
                 collection_name: str,
                 require_auth: bool = True,
                 require_admin: bool = False):
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
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data before creation - override in subclasses"""
        return data
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate creation permissions - override in subclasses"""
        if self.require_auth and not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate access permissions - override in subclasses"""
        if self.require_auth and not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    async def _validate_update_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate update permissions - override in subclasses"""
        await self._validate_access_permissions(item, current_user)
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items based on user permissions - override in subclasses"""
        return items
    
    async def _build_query_filters(self, 
                                 filters: Optional[Dict[str, Any]], 
                                 search: Optional[str],
                                 current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters - override in subclasses"""
        query_filters = []
        
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters
    
    async def create_item(self, 
                         item_data: CreateSchemaType, 
                         current_user: Optional[Dict[str, Any]]):
        """Create a new item"""
        try:
            # Convert to dict
            data = item_data.dict() if hasattr(item_data, 'dict') else dict(item_data)
            
            # Validate permissions
            await self._validate_create_permissions(data, current_user)
            
            # Prepare data
            prepared_data = await self._prepare_create_data(data, current_user)
            
            # Create item
            repo = self.get_repository()
            created_item = await repo.create(prepared_data)
            
            logger.info(f"{self.collection_name.title()} created: {created_item.get('id')}")
            
            from app.models.schemas import ApiResponse
            return ApiResponse(
                success=True,
                message=f"{self.collection_name.title()} created successfully",
                data=self.model_class(**created_item)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating {self.collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.collection_name}"
            )
    
    async def get_item(self, 
                      item_id: str, 
                      current_user: Optional[Dict[str, Any]]):
        """Get item by ID"""
        try:
            repo = self.get_repository()
            item = await repo.get_by_id(item_id)
            
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate access
            await self._validate_access_permissions(item, current_user)
            
            return self.model_class(**item)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting {self.collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get {self.collection_name}"
            )
    
    async def update_item(self, 
                         item_id: str, 
                         update_data: UpdateSchemaType, 
                         current_user: Optional[Dict[str, Any]]):
        """Update item by ID"""
        try:
            repo = self.get_repository()
            
            # Check if item exists
            item = await repo.get_by_id(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate permissions
            await self._validate_update_permissions(item, current_user)
            
            # Convert to dict and exclude unset values
            update_dict = update_data.dict(exclude_unset=True) if hasattr(update_data, 'dict') else dict(update_data)
            
            # Update item
            updated_item = await repo.update(item_id, update_dict)
            
            logger.info(f"{self.collection_name.title()} updated: {item_id}")
            
            from app.models.schemas import ApiResponse
            return ApiResponse(
                success=True,
                message=f"{self.collection_name.title()} updated successfully",
                data=self.model_class(**updated_item)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating {self.collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.collection_name}"
            )
    
    async def delete_item(self, 
                         item_id: str, 
                         current_user: Optional[Dict[str, Any]], 
                         soft_delete: bool = True):
        """Delete item by ID"""
        try:
            repo = self.get_repository()
            
            # Check if item exists
            item = await repo.get_by_id(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.collection_name.title()} not found"
                )
            
            # Validate permissions
            await self._validate_update_permissions(item, current_user)
            
            if soft_delete:
                # Soft delete by setting is_active to False
                await repo.update(item_id, {"is_active": False})
                message = f"{self.collection_name.title()} deactivated successfully"
            else:
                # Hard delete
                await repo.delete(item_id)
                message = f"{self.collection_name.title()} deleted successfully"
            
            logger.info(f"{self.collection_name.title()} {'deactivated' if soft_delete else 'deleted'}: {item_id}")
            
            from app.models.schemas import ApiResponse
            return ApiResponse(
                success=True,
                message=message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting {self.collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.collection_name}"
            )
    
    async def get_items(self, 
                       page: int = 1, 
                       page_size: int = 10,
                       search: Optional[str] = None,
                       filters: Optional[Dict[str, Any]] = None,
                       current_user: Optional[Dict[str, Any]] = None):
        """Get paginated list of items"""
        try:
            repo = self.get_repository()
            
            # Build query filters
            query_filters = await self._build_query_filters(filters, search, current_user)
            
            # Get all items matching filters
            all_items = await repo.query(query_filters) if query_filters else await repo.get_all()
            
            # Apply text search if provided
            if search:
                search_lower = search.lower()
                # Basic text search - override in subclasses for more sophisticated search
                all_items = [
                    item for item in all_items
                    if any(search_lower in str(value).lower() for value in item.values() if isinstance(value, str))
                ]
            
            # Filter items based on user permissions
            filtered_items = await self._filter_items_for_user(all_items, current_user)
            
            # Calculate pagination
            total = len(filtered_items)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items_page = filtered_items[start_idx:end_idx]
            
            # Convert to model objects
            items = [self.model_class(**item) for item in items_page]
            
            # Calculate pagination metadata
            total_pages = (total + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            from app.models.schemas import PaginatedResponse
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
            logger.error(f"Error getting {self.collection_name} list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get {self.collection_name} list"
            )


class WorkspaceIsolatedEndpoint(BaseEndpoint[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Endpoint class with workspace isolation
    Ensures users can only access items within their workspace
    """
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate workspace access permissions"""
        # Call parent validation first
        await super()._validate_access_permissions(item, current_user)
        
        if not current_user:
            return
        
        # Get user role from role_id
        from app.core.security import _get_user_role
        try:
            user_role = await _get_user_role(current_user)
        except:
            user_role = current_user.get('role', 'operator')
        
        # Admin users can access all items
        if user_role in ['admin', 'superadmin']:
            return
        
        # Check workspace isolation
        item_workspace_id = item.get('workspace_id')
        user_workspace_id = current_user.get('workspace_id')
        
        if item_workspace_id and user_workspace_id != item_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Item not in your workspace"
            )
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items based on workspace isolation"""
        if not current_user:
            return []
        
        # Get user role from role_id
        from app.core.security import _get_user_role
        try:
            user_role = await _get_user_role(current_user)
        except:
            user_role = current_user.get('role', 'operator')
        
        # Admin users see all items
        if user_role in ['admin', 'superadmin']:
            return items
        
        # Filter by workspace
        user_workspace_id = current_user.get('workspace_id')
        if user_workspace_id:
            return [item for item in items if item.get('workspace_id') == user_workspace_id]
        
        return []
    
    async def _build_query_filters(self, 
                                 filters: Optional[Dict[str, Any]], 
                                 search: Optional[str],
                                 current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters with workspace isolation"""
        query_filters = []
        
        # Add workspace filter for non-admin users
        if current_user:
            # Get user role from role_id
            from app.core.security import _get_user_role
            try:
                user_role = await _get_user_role(current_user)
            except:
                user_role = current_user.get('role', 'operator')
            
            if user_role not in ['admin', 'superadmin']:
                workspace_id = current_user.get('workspace_id')
                if workspace_id:
                    query_filters.append(('workspace_id', '==', workspace_id))
        
        # Add additional filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters