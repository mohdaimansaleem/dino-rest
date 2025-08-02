"""
Permissions Management API Endpoints
Comprehensive permission management with role mapping
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.models.schemas import (
    ApiResponse, PaginatedResponse
)
from app.database.firestore import get_firestore_client
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# =============================================================================
# PYDANTIC SCHEMAS FOR PERMISSIONS
# =============================================================================

from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class PermissionBase(BaseModel):
    """Base permission schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Permission name")
    description: str = Field(..., max_length=500, description="Permission description")
    resource: str = Field(..., pattern="^(workspace|venue|menu|order|user|analytics|table)$", description="Resource type")
    action: str = Field(..., pattern="^(create|read|update|delete|manage)$", description="Action type")
    scope: str = Field(..., pattern="^(own|venue|workspace|all)$", description="Permission scope")

    @validator('name')
    def validate_name(cls, v):
        if not v:
            raise ValueError('Name is required')
        # Allow resource.action format
        import re
        if not re.match(r'^[a-z]+\.[a-z]+$', v):
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        return v

class PermissionCreate(PermissionBase):
    """Schema for creating permissions"""
    pass

class PermissionUpdate(BaseModel):
    """Schema for updating permissions"""
    description: Optional[str] = Field(None, max_length=500)

class PermissionResponse(PermissionBase):
    """Complete permission response schema"""
    id: str
    is_system_permission: bool = Field(default=True)
    roles_count: int = Field(default=0, description="Number of roles with this permission")
    created_at: datetime

class PermissionFilters(BaseModel):
    """Permission filtering options"""
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    scope: Optional[str] = None
    search: Optional[str] = None

class PermissionCategory(BaseModel):
    """Permission category schema"""
    name: str
    display_name: str
    description: str
    permissions: List[PermissionResponse] = Field(default_factory=list)

class PermissionMatrix(BaseModel):
    """Permission matrix schema"""
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    matrix: Dict[str, Dict[str, Optional[PermissionResponse]]] = Field(default_factory=dict)

class PermissionStatistics(BaseModel):
    """Permission statistics schema"""
    total_permissions: int = 0
    system_permissions: int = 0
    custom_permissions: int = 0
    permissions_by_resource: Dict[str, int] = Field(default_factory=dict)
    permissions_by_action: Dict[str, int] = Field(default_factory=dict)
    permissions_by_category: Dict[str, int] = Field(default_factory=dict)
    unused_permissions: int = 0

class BulkPermissionCreate(BaseModel):
    """Schema for bulk permission creation"""
    permissions: List[PermissionCreate] = Field(..., min_items=1, max_items=100)

class BulkPermissionResponse(BaseModel):
    """Response for bulk operations"""
    success: bool = True
    created: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    created_permissions: List[PermissionResponse] = Field(default_factory=list)

# =============================================================================
# PERMISSION REPOSITORY
# =============================================================================

class PermissionRepository:
    """Repository for permission operations"""
    
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = "permissions"
    
    async def create(self, permission_data: Dict[str, Any]) -> str:
        """Create a new permission"""
        permission_data['created_at'] = datetime.utcnow()
        
        doc_ref = self.db.collection(self.collection).document()
        permission_data['id'] = doc_ref.id
        
        doc_ref.set(permission_data)  # Remove await - Firestore is synchronous
        logger.info(f"Permission created: {permission_data['action']} ({doc_ref.id})")
        return doc_ref.id
    
    async def get_by_id(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """Get permission by ID"""
        doc = self.db.collection(self.collection).document(permission_id).get()  # Remove await
        if doc.exists:
            return doc.to_dict()
        return None
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        query = self.db.collection(self.collection).where("name", "==", name)
        
        docs = list(query.limit(1).stream())  # Use stream() instead of get()
        if docs:
            return docs[0].to_dict()
        return None
    
    async def get_by_resource_and_action(self, resource: str, action: str) -> Optional[Dict[str, Any]]:
        """Get permission by resource and action combination"""
        name = f"{resource}.{action}"
        return await self.get_by_name(name)
    
    async def list_permissions(self, 
                              filters: Optional[Dict[str, Any]] = None,
                              page: int = 1,
                              page_size: int = 10) -> tuple[List[Dict[str, Any]], int]:
        """List permissions with pagination and filtering"""
        query = self.db.collection(self.collection)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if value is not None and field != 'search':
                    query = query.where(field, "==", value)
        
        # Get total count
        total_docs = list(query.stream())  # Use stream() instead of get()
        total = len(total_docs)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        docs = list(query.stream())  # Use stream() instead of get()
        permissions = [doc.to_dict() for doc in docs]
        
        # Apply search filter (client-side for Firestore)
        if filters and filters.get('search'):
            search_term = filters['search'].lower()
            permissions = [
                perm for perm in permissions
                if search_term in perm.get('name', '').lower() or
                   search_term in perm.get('description', '').lower() or
                   search_term in perm.get('resource', '').lower() or
                   search_term in perm.get('action', '').lower()
            ]
        
        return permissions, total
    
    async def update(self, permission_id: str, update_data: Dict[str, Any]) -> bool:
        """Update permission"""
        update_data['updated_at'] = datetime.utcnow()
        
        doc_ref = self.db.collection(self.collection).document(permission_id)
        doc_ref.update(update_data)  # Remove await
        
        logger.info(f"Permission updated: {permission_id}")
        return True
    
    async def delete(self, permission_id: str) -> bool:
        """Delete permission (hard delete)"""
        self.db.collection(self.collection).document(permission_id).delete()  # Remove await
        logger.info(f"Permission deleted: {permission_id}")
        return True
    
    async def get_roles_with_permission(self, permission_id: str) -> List[Dict[str, Any]]:
        """Get roles that have this permission"""
        roles_query = self.db.collection("roles").where("permission_ids", "array_contains", permission_id)
        roles_docs = list(roles_query.stream())  # Use stream() instead of get()
        return [doc.to_dict() for doc in roles_docs]
    
    async def get_permissions_by_category(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get permissions grouped by category"""
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
        permissions = [doc.to_dict() for doc in docs]
        
        # Group by resource
        categories = {}
        for perm in permissions:
            resource = perm.get('resource', 'uncategorized')
            if resource not in categories:
                categories[resource] = {
                    'name': resource,
                    'display_name': resource.replace('_', ' ').title(),
                    'description': f'Permissions related to {resource}',
                    'permissions': []
                }
            categories[resource]['permissions'].append(perm)
        
        return list(categories.values())
    
    async def get_permission_matrix(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get permission matrix (resources vs actions)"""
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
        permissions = [doc.to_dict() for doc in docs]
        
        resources = set()
        actions = set()
        matrix = {}
        
        for perm in permissions:
            resource = perm.get('resource')
            action = perm.get('action')
            
            if resource and action:
                resources.add(resource)
                actions.add(action)
                
                if resource not in matrix:
                    matrix[resource] = {}
                matrix[resource][action] = perm
        
        return {
            'resources': sorted(list(resources)),
            'actions': sorted(list(actions)),
            'matrix': matrix
        }
    
    async def get_resources(self) -> List[str]:
        """Get all unique resources"""
        docs = list(self.db.collection(self.collection).stream())
        resources = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('resource'):
                resources.add(data['resource'])
        return sorted(list(resources))
    
    async def get_actions(self) -> List[str]:
        """Get all unique actions"""
        docs = list(self.db.collection(self.collection).stream())
        actions = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('action'):
                actions.add(data['action'])
        return sorted(list(actions))
    
    async def get_permission_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get permission statistics"""
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
        permissions = [doc.to_dict() for doc in docs]
        
        stats = {
            "total_permissions": len(permissions),
            "system_permissions": len([p for p in permissions if p.get('is_system_permission', False)]),
            "custom_permissions": len([p for p in permissions if not p.get('is_system_permission', False)]),
            "permissions_by_resource": {},
            "permissions_by_action": {},
            "permissions_by_category": {},
            "unused_permissions": 0
        }
        
        # Count by resource, action, and scope
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            action = perm.get('action', 'unknown')
            scope = perm.get('scope', 'unknown')
            
            stats["permissions_by_resource"][resource] = stats["permissions_by_resource"].get(resource, 0) + 1
            stats["permissions_by_action"][action] = stats["permissions_by_action"].get(action, 0) + 1
            stats["permissions_by_category"][scope] = stats["permissions_by_category"].get(scope, 0) + 1
        
        # Count unused permissions
        for perm in permissions:
            roles = await self.get_roles_with_permission(perm['id'])
            if not roles:
                stats["unused_permissions"] += 1
        
        return stats
    
    async def bulk_create(self, permissions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create permissions"""
        created = 0
        skipped = 0
        errors = []
        created_permissions = []
        
        for perm_data in permissions_data:
            try:
                # Check if permission with same name already exists
                existing = await self.get_by_name(perm_data['name'])
                if existing:
                    skipped += 1
                    errors.append(f"Permission '{perm_data['name']}' already exists")
                    continue
                
                # Create permission
                perm_id = await self.create(perm_data)
                created_perm = await self.get_by_id(perm_id)
                created_permissions.append(created_perm)
                created += 1
                
            except Exception as e:
                skipped += 1
                errors.append(f"Failed to create permission '{perm_data.get('name', 'unknown')}': {str(e)}")
        
        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "created_permissions": created_permissions
        }

# Initialize repository
perm_repo = PermissionRepository()

# =============================================================================
# PERMISSION ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get permissions",
            description="Get paginated list of permissions with filtering")
@router.get("", 
            response_model=PaginatedResponse,
            summary="Get permissions",
            description="Get paginated list of permissions with filtering")
async def get_permissions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    name: Optional[str] = Query(None, description="Filter by name"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    action: Optional[str] = Query(None, description="Filter by action"),
    scope: Optional[str] = Query(None, description="Filter by scope"),
    search: Optional[str] = Query(None, description="Search by name, description, resource, or action")
):
    """Get permissions with pagination and filtering"""
    try:
        # Build filters
        filters = {}
        if name:
            filters['name'] = name
        if resource:
            filters['resource'] = resource
        if action:
            filters['action'] = action
        if scope:
            filters['scope'] = scope
        if search:
            filters['search'] = search
        
        permissions, total = await perm_repo.list_permissions(filters, page, page_size)
        
        # Enrich permissions with roles count
        enriched_permissions = []
        for perm in permissions:
            roles = await perm_repo.get_roles_with_permission(perm['id'])
            
            perm_response = PermissionResponse(
                **perm,
                roles_count=len(roles)
            )
            enriched_permissions.append(perm_response.dict())
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            data=enriched_permissions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )

@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create permission",
             description="Create a new permission (NO AUTH - TESTING ONLY)")
@router.post("", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create permission",
             description="Create a new permission (NO AUTH - TESTING ONLY)")
async def create_permission(
    permission_data: PermissionCreate
    # current_user: Dict[str, Any] = Depends(get_current_admin_user)  # REMOVED FOR TESTING
):
    """Create a new permission"""
    try:
        # Check if permission with same name already exists
        existing_permission = await perm_repo.get_by_name(permission_data.name)
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission with name '{permission_data.name}' already exists"
            )
        
        # Prepare permission data
        perm_dict = permission_data.dict()
        
        # Create permission
        perm_id = await perm_repo.create(perm_dict)
        
        # Get created permission
        created_permission = await perm_repo.get_by_id(perm_id)
        
        perm_response = PermissionResponse(
            **created_permission,
            roles_count=0
        )
        
        logger.info(f"Permission created: {permission_data.name} by system_test")
        return ApiResponse(
            success=True,
            message="Permission created successfully",
            data=perm_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create permission"
        )

@router.get("/{permission_id}", 
            response_model=PermissionResponse,
            summary="Get permission by ID",
            description="Get specific permission by ID")
async def get_permission(
    permission_id: str
):
    """Get permission by ID"""
    try:
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Access permissions removed for open API
        
        # Get roles count
        roles = await perm_repo.get_roles_with_permission(permission_id)
        
        perm_response = PermissionResponse(
            **permission,
            roles_count=len(roles)
        )
        
        return perm_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission"
        )

@router.put("/{permission_id}", 
            response_model=ApiResponse,
            summary="Update permission",
            description="Update permission information")
async def update_permission(
    permission_id: str,
    update_data: PermissionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update permission"""
    try:
        # Check if permission exists
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Check access permissions
        if (current_user.get('role') != 'superadmin' and 
            permission.get('workspace_id') != current_user.get('workspace_id')):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to update this permission"
            )
        
        # Prevent updating system permissions
        if permission.get('is_system_permission', False) and current_user.get('role') != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update system permissions"
            )
        
        # Update permission
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_by'] = current_user['id']
        
        await perm_repo.update(permission_id, update_dict)
        
        # Get updated permission
        updated_permission = await perm_repo.get_by_id(permission_id)
        roles = await perm_repo.get_roles_with_permission(permission_id)
        
        perm_response = PermissionResponse(
            **updated_permission,
            roles_count=len(roles)
        )
        
        logger.info(f"Permission updated: {permission_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permission updated successfully",
            data=perm_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permission"
        )

@router.delete("/{permission_id}", 
               response_model=ApiResponse,
               summary="Delete permission",
               description="Delete permission (only if not assigned to any role)")
async def delete_permission(
    permission_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete permission"""
    try:
        # Check if permission exists
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Check access permissions
        if (current_user.get('role') != 'superadmin' and 
            permission.get('workspace_id') != current_user.get('workspace_id')):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to delete this permission"
            )
        
        # Prevent deleting system permissions
        if permission.get('is_system_permission', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system permissions"
            )
        
        # Check if permission is assigned to any roles
        roles = await perm_repo.get_roles_with_permission(permission_id)
        if roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete permission. It is assigned to {len(roles)} roles"
            )
        
        # Delete permission
        await perm_repo.delete(permission_id)
        
        logger.info(f"Permission deleted: {permission_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permission deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete permission"
        )

# =============================================================================
# PERMISSION ORGANIZATION ENDPOINTS
# =============================================================================

@router.get("/by-category", 
            response_model=List[PermissionCategory],
            summary="Get permissions by category",
            description="Get permissions grouped by category")
async def get_permissions_by_category(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permissions grouped by category"""
    try:
        # Workspace filtering removed for open API
        
        categories = await perm_repo.get_permissions_by_category(workspace_id)
        
        # Convert to response format
        category_responses = []
        for cat in categories:
            permissions = [
                PermissionResponse(**perm, roles_count=0) 
                for perm in cat['permissions']
            ]
            category_responses.append(
                PermissionCategory(
                    name=cat['name'],
                    display_name=cat['display_name'],
                    description=cat['description'],
                    permissions=permissions
                )
            )
        
        return category_responses
        
    except Exception as e:
        logger.error(f"Error getting permissions by category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions by category"
        )

@router.get("/matrix", 
            response_model=PermissionMatrix,
            summary="Get permission matrix",
            description="Get permission matrix (resources vs actions)")
async def get_permission_matrix(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permission matrix"""
    try:
        # Workspace filtering removed for open API
        
        matrix_data = await perm_repo.get_permission_matrix(workspace_id)
        
        # Convert permissions to response format
        matrix = {}
        for resource, actions in matrix_data['matrix'].items():
            matrix[resource] = {}
            for action, perm in actions.items():
                if perm:
                    matrix[resource][action] = PermissionResponse(**perm, roles_count=0)
                else:
                    matrix[resource][action] = None
        
        return PermissionMatrix(
            resources=matrix_data['resources'],
            actions=matrix_data['actions'],
            matrix=matrix
        )
        
    except Exception as e:
        logger.error(f"Error getting permission matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission matrix"
        )

@router.get("/resources", 
            response_model=List[str],
            summary="Get available resources",
            description="Get all available resource names")
async def get_resources():
    """Get all available resources"""
    try:
        resources = await perm_repo.get_resources()
        return resources
        
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resources"
        )

@router.get("/actions", 
            response_model=List[str],
            summary="Get available actions",
            description="Get all available action names")
async def get_actions():
    """Get all available actions"""
    try:
        actions = await perm_repo.get_actions()
        return actions
        
    except Exception as e:
        logger.error(f"Error getting actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get actions"
        )

# =============================================================================
# BULK OPERATIONS
# =============================================================================

@router.post("/bulk-create", 
             response_model=BulkPermissionResponse,
             summary="Bulk create permissions",
             description="Create multiple permissions at once")
async def bulk_create_permissions(
    bulk_data: BulkPermissionCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Bulk create permissions"""
    try:
        # Prepare permissions data
        permissions_data = []
        for perm in bulk_data.permissions:
            perm_dict = perm.dict()
            perm_dict['workspace_id'] = perm.workspace_id or current_user.get('workspace_id')
            perm_dict['created_by'] = current_user['id']
            permissions_data.append(perm_dict)
        
        # Bulk create
        result = await perm_repo.bulk_create(permissions_data)
        
        # Convert created permissions to response format
        created_permissions = [
            PermissionResponse(**perm, roles_count=0)
            for perm in result['created_permissions']
        ]
        
        logger.info(f"Bulk permission creation: {result['created']} created, {result['skipped']} skipped by {current_user['id']}")
        
        return BulkPermissionResponse(
            success=True,
            created=result['created'],
            skipped=result['skipped'],
            errors=result['errors'],
            created_permissions=created_permissions
        )
        
    except Exception as e:
        logger.error(f"Error bulk creating permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create permissions"
        )

# =============================================================================
# PERMISSION STATISTICS AND UTILITIES
# =============================================================================

@router.get("/statistics", 
            response_model=PermissionStatistics,
            summary="Get permission statistics",
            description="Get comprehensive permission statistics")
async def get_permission_statistics(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permission statistics"""
    try:
        # Workspace filtering removed for open API
        
        stats = await perm_repo.get_permission_statistics(workspace_id)
        return PermissionStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Error getting permission statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission statistics"
        )

@router.get("/check-name", 
            response_model=Dict[str, bool],
            summary="Check permission name availability",
            description="Check if permission name is available")
async def check_permission_name_availability(
    name: str = Query(..., description="Permission name to check"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    exclude_id: Optional[str] = Query(None, description="Permission ID to exclude from check")
):
    """Check if permission name is available"""
    try:
        # Workspace filtering removed for open API
        
        existing_permission = await perm_repo.get_by_name(name)
        
        # If excluding a specific permission ID, check if it's the same permission
        if existing_permission and exclude_id and existing_permission.get('id') == exclude_id:
            return {"available": True}
        
        return {"available": existing_permission is None}
        
    except Exception as e:
        logger.error(f"Error checking permission name availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permission name availability"
        )

@router.get("/unused", 
            response_model=List[PermissionResponse],
            summary="Get unused permissions",
            description="Get permissions not assigned to any role")
async def get_unused_permissions(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get unused permissions"""
    try:
        # Workspace filtering removed for open API
        
        # Get all permissions
        filters = {}
        if workspace_id:
            filters['workspace_id'] = workspace_id
        
        permissions, _ = await perm_repo.list_permissions(filters, 1, 1000)
        
        # Filter unused permissions
        unused_permissions = []
        for perm in permissions:
            roles = await perm_repo.get_roles_with_permission(perm['id'])
            if not roles:
                unused_permissions.append(
                    PermissionResponse(**perm, roles_count=0)
                )
        
        return unused_permissions
        
    except Exception as e:
        logger.error(f"Error getting unused permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unused permissions"
        )