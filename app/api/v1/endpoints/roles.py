"""
Roles Management API Endpoints
Comprehensive role management with permissions mapping
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.models.schemas import (
    ApiResponse, PaginatedResponse, UserRole as UserRoleEnum
)
# Removed base endpoint dependency
from app.database.firestore import get_firestore_client
from app.services.role_permission_service import role_permission_service
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# =============================================================================
# PYDANTIC SCHEMAS FOR ROLES
# =============================================================================

from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class RoleBase(BaseModel):
    """Base role schema"""
    name: UserRoleEnum = Field(..., description="Role name from enum")
    description: str = Field(..., min_length=5, max_length=500, description="Role description")
    is_active: bool = Field(default=True, description="Whether role is active")

    @validator('name')
    def validate_name(cls, v):
        # Ensure it's a valid UserRole enum value
        if isinstance(v, str):
            try:
                return UserRoleEnum(v)
            except ValueError:
                raise ValueError(f'Invalid role name. Must be one of: {[role.value for role in UserRoleEnum]}')
        return v

class RoleCreate(RoleBase):
    """Schema for creating roles"""
    permission_ids: List[str] = Field(default_factory=list, description="List of permission IDs")

class RoleUpdate(BaseModel):
    """Schema for updating roles"""
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    is_active: Optional[bool] = None
    permission_ids: Optional[List[str]] = None

class RoleResponse(RoleBase):
    """Complete role response schema"""
    id: str
    permission_ids: List[str] = Field(default_factory=list)
    permissions: List[Dict[str, Any]] = Field(default_factory=list)
    user_count: int = Field(default=0, description="Number of users with this role")
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

class RoleFilters(BaseModel):
    """Role filtering options"""
    is_active: Optional[bool] = None
    search: Optional[str] = None

class RolePermissionMapping(BaseModel):
    """Role-permission mapping schema"""
    role_id: str
    permission_ids: List[str]

class RoleAssignment(BaseModel):
    """Role assignment to user schema"""
    user_id: str
    role_id: str
    workspace_id: Optional[str] = None
    venue_id: Optional[str] = None

class RoleStatistics(BaseModel):
    """Role statistics schema"""
    total_roles: int = 0
    active_roles: int = 0
    users_by_role: Dict[str, int] = Field(default_factory=dict)

# =============================================================================
# ROLE REPOSITORY
# =============================================================================

class RoleRepository:
    """Repository for role operations"""
    
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = "roles"
    
    async def create(self, role_data: Dict[str, Any]) -> str:
        """Create a new role"""
        role_data['created_at'] = datetime.utcnow()
        role_data['updated_at'] = datetime.utcnow()
        
        doc_ref = self.db.collection(self.collection).document()
        role_data['id'] = doc_ref.id
        
        doc_ref.set(role_data)
        logger.info(f"Role created: {role_data['name']} ({doc_ref.id})")
        return doc_ref.id
    
    async def get_by_id(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role by ID"""
        doc = self.db.collection(self.collection).document(role_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        query = self.db.collection(self.collection).where("name", "==", name)
        
        docs = list(query.limit(1).stream())
        if docs:
            return docs[0].to_dict()
        return None
    
    async def list_roles(self, 
                        filters: Optional[Dict[str, Any]] = None,
                        page: int = 1,
                        page_size: int = 10) -> tuple[List[Dict[str, Any]], int]:
        """List roles with pagination and filtering"""
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
        roles = [doc.to_dict() for doc in docs]
        
        # Apply search filter (client-side for Firestore)
        if filters and filters.get('search'):
            search_term = filters['search'].lower()
            roles = [
                role for role in roles
                if search_term in role.get('name', '').lower() or
                   search_term in role.get('description', '').lower()
            ]
        
        return roles, total
    
    async def update(self, role_id: str, update_data: Dict[str, Any]) -> bool:
        """Update role"""
        update_data['updated_at'] = datetime.utcnow()
        
        doc_ref = self.db.collection(self.collection).document(role_id)
        doc_ref.update(update_data)  # Remove await
        
        logger.info(f"Role updated: {role_id}")
        return True
    
    async def delete(self, role_id: str) -> bool:
        """Delete role (soft delete by deactivating)"""
        update_data = {"is_active": False, "deleted_at": datetime.utcnow()}
        update_data['updated_at'] = datetime.utcnow()
        doc_ref = self.db.collection(self.collection).document(role_id)
        doc_ref.update(update_data)
        logger.info(f"Role soft deleted: {role_id}")
        return True
    
    async def hard_delete(self, role_id: str) -> bool:
        """Hard delete role"""
        self.db.collection(self.collection).document(role_id).delete()  # Remove await
        logger.info(f"Role hard deleted: {role_id}")
        return True
    
    async def get_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """Get permissions for a role"""
        role = await self.get_by_id(role_id)
        if not role:
            return []
        
        permission_ids = role.get('permission_ids', [])
        if not permission_ids:
            return []
        
        # Get permissions from permissions collection
        permissions = []
        for perm_id in permission_ids:
            perm_doc = self.db.collection("permissions").document(perm_id).get()  # Remove await
            if perm_doc.exists:
                permissions.append(perm_doc.to_dict())
        
        return permissions
    
    async def assign_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Assign permissions to role"""
        return await self.update(role_id, {"permission_ids": permission_ids})
    
    async def add_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Add permissions to role"""
        role = await self.get_by_id(role_id)
        if not role:
            return False
        
        current_permissions = set(role.get('permission_ids', []))
        new_permissions = current_permissions.union(set(permission_ids))
        
        return await self.update(role_id, {"permission_ids": list(new_permissions)})
    
    async def remove_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Remove permissions from role"""
        role = await self.get_by_id(role_id)
        if not role:
            return False
        
        current_permissions = set(role.get('permission_ids', []))
        remaining_permissions = current_permissions - set(permission_ids)
        
        return await self.update(role_id, {"permission_ids": list(remaining_permissions)})
    
    async def get_users_with_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get users with specific role"""
        users_query = self.db.collection("users").where("role_id", "==", role_id)
        users_docs = list(users_query.stream())  # Use stream() instead of get()
        return [doc.to_dict() for doc in users_docs]
    
    async def get_role_statistics(self) -> Dict[str, Any]:
        """Get role statistics"""
        query = self.db.collection(self.collection)
        
        roles = list(query.stream())  # Use stream() instead of get()
        roles_data = [doc.to_dict() for doc in roles]
        
        stats = {
            "total_roles": len(roles_data),
            "active_roles": len([r for r in roles_data if r.get('is_active', True)]),
            "users_by_role": {}
        }
        
        # Count users by role
        for role in roles_data:
            users = await self.get_users_with_role(role['id'])
            stats["users_by_role"][role['name']] = len(users)
        
        return stats

# Initialize repository
role_repo = RoleRepository()

# =============================================================================
# ROLE ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get roles",
            description="Get paginated list of roles with filtering")
@router.get("", 
            response_model=PaginatedResponse,
            summary="Get roles",
            description="Get paginated list of roles with filtering")
async def get_roles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or description")
):
    """Get roles with pagination and filtering"""
    try:
        # Build filters
        filters = {}
        if is_active is not None:
            filters['is_active'] = is_active
        if search:
            filters['search'] = search
        
        # Workspace filtering removed for open API
        
        roles, total = await role_repo.list_roles(filters, page, page_size)
        
        # Enrich roles with permissions and user count
        enriched_roles = []
        for role in roles:
            permissions = await role_repo.get_role_permissions(role['id'])
            users = await role_repo.get_users_with_role(role['id'])
            
            role_response = RoleResponse(
                **role,
                permissions=permissions,
                user_count=len(users)
            )
            enriched_roles.append(role_response.dict())
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            data=enriched_roles,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error getting roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get roles"
        )

@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create role",
             description="Create a new role with permissions (NO AUTH - TESTING ONLY)")
@router.post("", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create role",
             description="Create a new role with permissions (NO AUTH - TESTING ONLY)")
async def create_role(
    role_data: RoleCreate
    # current_user: Dict[str, Any] = Depends(get_current_admin_user)  # REMOVED FOR TESTING
):
    """Create a new role"""
    try:
        # Check if role name already exists
        existing_role = await role_repo.get_by_name(role_data.name.value)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with name '{role_data.name.value}' already exists"
            )
        
        # Validate permissions exist (skip validation for testing)
        # if role_data.permission_ids:
        #     perm_repo = get_permission_repo()
        #     for perm_id in role_data.permission_ids:
        #         perm = await perm_repo.get_by_id(perm_id)
        #         if not perm:
        #             raise HTTPException(
        #                 status_code=status.HTTP_400_BAD_REQUEST,
        #                 detail=f"Permission with ID '{perm_id}' not found"
        #             )
        
        # Prepare role data
        role_dict = role_data.dict()
        role_dict['name'] = role_data.name.value  # Convert enum to string
        role_dict['created_by'] = "system_test"  # Hardcoded for testing
        
        # Create role
        role_id = await role_repo.create(role_dict)
        
        # Get created role with permissions
        created_role = await role_repo.get_by_id(role_id)
        permissions = await role_repo.get_role_permissions(role_id)
        
        role_response = RoleResponse(
            **created_role,
            permissions=permissions,
            user_count=0
        )
        
        logger.info(f"Role created: {role_data.name.value} by system_test")
        return ApiResponse(
            success=True,
            message="Role created successfully",
            data=role_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role"
        )

@router.get("/{role_id}", 
            response_model=RoleResponse,
            summary="Get role by ID",
            description="Get specific role by ID with permissions")
async def get_role(
    role_id: str
):
    """Get role by ID"""
    try:
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Access permissions removed for open API
        
        # Get permissions and user count
        permissions = await role_repo.get_role_permissions(role_id)
        users = await role_repo.get_users_with_role(role_id)
        
        role_response = RoleResponse(
            **role,
            permissions=permissions,
            user_count=len(users)
        )
        
        return role_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role"
        )

@router.put("/{role_id}", 
            response_model=ApiResponse,
            summary="Update role",
            description="Update role information and permissions")
async def update_role(
    role_id: str,
    update_data: RoleUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update role"""
    try:
        # Check if role exists
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Access permissions simplified for new schema
        if current_user.get('role') != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can update roles"
            )
        
        # System roles are now managed by enum, no separate flag needed
        
        # Validate permissions if provided
        if update_data.permission_ids is not None:
            perm_repo = get_permission_repo()
            for perm_id in update_data.permission_ids:
                perm = await perm_repo.get_by_id(perm_id)
                if not perm:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Permission with ID '{perm_id}' not found"
                    )
        
        # Update role
        update_dict = update_data.dict(exclude_unset=True)
        update_dict['updated_by'] = current_user['id']
        
        await role_repo.update(role_id, update_dict)
        
        # Get updated role
        updated_role = await role_repo.get_by_id(role_id)
        permissions = await role_repo.get_role_permissions(role_id)
        users = await role_repo.get_users_with_role(role_id)
        
        role_response = RoleResponse(
            **updated_role,
            permissions=permissions,
            user_count=len(users)
        )
        
        logger.info(f"Role updated: {role_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Role updated successfully",
            data=role_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role"
        )

@router.delete("/{role_id}", 
               response_model=ApiResponse,
               summary="Delete role",
               description="Delete role (soft delete)")
async def delete_role(
    role_id: str,
    hard_delete: bool = Query(False, description="Perform hard delete"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete role"""
    try:
        # Check if role exists
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Access permissions simplified for new schema
        if current_user.get('role') != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can delete roles"
            )
        
        # Prevent deleting core system roles
        core_roles = ['superadmin', 'admin', 'operator']
        if role.get('name') in core_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete core system roles"
            )
        
        # Check if role is assigned to users
        users = await role_repo.get_users_with_role(role_id)
        if users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete role. It is assigned to {len(users)} users"
            )
        
        # Delete role
        if hard_delete and current_user.get('role') == 'superadmin':
            await role_repo.hard_delete(role_id)
            message = "Role permanently deleted"
        else:
            await role_repo.delete(role_id)
            message = "Role deactivated successfully"
        
        logger.info(f"Role deleted: {role_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role"
        )

# =============================================================================
# ROLE PERMISSIONS ENDPOINTS
# =============================================================================

@router.get("/{role_id}/permissions", 
            response_model=List[Dict[str, Any]],
            summary="Get role permissions",
            description="Get all permissions assigned to a role")
async def get_role_permissions(
    role_id: str
):
    """Get permissions for a role"""
    try:
        # Check if role exists and user has access
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Access permissions removed for open API
        
        permissions = await role_repo.get_role_permissions(role_id)
        return permissions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role permissions"
        )

@router.post("/{role_id}/permissions", 
             response_model=ApiResponse,
             summary="Assign permissions to role",
             description="Assign permissions to a role (replaces existing) - NO AUTH")
async def assign_permissions_to_role(
    role_id: str,
    permission_mapping: RolePermissionMapping
):
    """Assign permissions to role"""
    try:
        # Validate role exists and user has access
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Access permissions removed for open API
        
        # Validate permissions exist
        perm_repo = get_permission_repo()
        for perm_id in permission_mapping.permission_ids:
            perm = await perm_repo.get_by_id(perm_id)
            if not perm:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission with ID '{perm_id}' not found"
                )
        
        # Assign permissions
        await role_repo.assign_permissions(role_id, permission_mapping.permission_ids)
        
        logger.info(f"Permissions assigned to role {role_id} by system")
        return ApiResponse(
            success=True,
            message="Permissions assigned successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning permissions to role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permissions"
        )

@router.patch("/{role_id}/permissions/add", 
              response_model=ApiResponse,
              summary="Add permissions to role",
              description="Add permissions to a role (keeps existing)")
async def add_permissions_to_role(
    role_id: str,
    permission_mapping: RolePermissionMapping,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Add permissions to role"""
    try:
        # Validate and add permissions
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        await role_repo.add_permissions(role_id, permission_mapping.permission_ids)
        
        logger.info(f"Permissions added to role {role_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permissions added successfully"
        )
        
    except Exception as e:
        logger.error(f"Error adding permissions to role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add permissions"
        )

@router.patch("/{role_id}/permissions/remove", 
              response_model=ApiResponse,
              summary="Remove permissions from role",
              description="Remove specific permissions from a role")
async def remove_permissions_from_role(
    role_id: str,
    permission_mapping: RolePermissionMapping,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Remove permissions from role"""
    try:
        # Validate and remove permissions
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        await role_repo.remove_permissions(role_id, permission_mapping.permission_ids)
        
        logger.info(f"Permissions removed from role {role_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permissions removed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error removing permissions from role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove permissions"
        )

# =============================================================================
# ROLE ASSIGNMENT ENDPOINTS
# =============================================================================

@router.get("/{role_id}/users", 
            response_model=List[Dict[str, Any]],
            summary="Get users with role",
            description="Get all users assigned to a specific role")
async def get_users_with_role(
    role_id: str
):
    """Get users with specific role"""
    try:
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        users = await role_repo.get_users_with_role(role_id)
        
        # Filter sensitive information
        filtered_users = []
        for user in users:
            filtered_user = {
                'id': user.get('id'),
                'email': user.get('email'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'is_active': user.get('is_active'),
                'created_at': user.get('created_at')
            }
            filtered_users.append(filtered_user)
        
        return filtered_users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users with role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users with role"
        )

# =============================================================================
# ROLE STATISTICS AND UTILITIES
# =============================================================================

@router.get("/statistics/overview", 
            response_model=RoleStatistics,
            summary="Get role statistics",
            description="Get comprehensive role statistics")
async def get_role_statistics(

):
    """Get role statistics"""
    try:
        stats = await role_repo.get_role_statistics()
        return RoleStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Error getting role statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role statistics"
        )

@router.get("/check-name", 
            response_model=Dict[str, bool],
            summary="Check role name availability",
            description="Check if role name is available")
async def check_role_name_availability(
    name: str = Query(..., description="Role name to check"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    exclude_id: Optional[str] = Query(None, description="Role ID to exclude from check")
):
    """Check if role name is available"""
    try:
        existing_role = await role_repo.get_by_name(name)
        
        # If excluding a specific role ID, check if it's the same role
        if existing_role and exclude_id and existing_role.get('id') == exclude_id:
            return {"available": True}
        
        return {"available": existing_role is None}
        
    except Exception as e:
        logger.error(f"Error checking role name availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check role name availability"
        )

def get_permission_repo():
    """Get permission repository instance"""
    from app.api.v1.endpoints.permissions import PermissionRepository
    return PermissionRepository()

# =============================================================================
# SIMPLIFIED ROLE-PERMISSION ASSIGNMENT (NO AUTH)
# =============================================================================

@router.post("/{role_id}/assign-permission", 
             response_model=ApiResponse,
             summary="Assign single permission to role",
             description="Assign a single permission to a role (NO AUTH - for seeding)")
async def assign_single_permission_to_role(
    role_id: str,
    permission_id: str = Query(..., description="Permission ID to assign")
):
    """Assign a single permission to role (simplified for seeding)"""
    try:
        # Validate role exists
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Validate permission exists
        perm_repo = get_permission_repo()
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Add permission to role
        await role_repo.add_permissions(role_id, [permission_id])
        
        logger.info(f"Permission {permission_id} assigned to role {role_id}")
        return ApiResponse(
            success=True,
            message="Permission assigned successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning permission to role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permission"
        )

class BulkPermissionAssignment(BaseModel):
    """Schema for bulk permission assignment"""
    permission_ids: List[str] = Field(..., description="List of permission IDs to assign")

@router.post("/{role_id}/assign-permissions-bulk", 
             response_model=ApiResponse,
             summary="Assign multiple permissions to role",
             description="Assign multiple permissions to a role (NO AUTH - for seeding)")
async def assign_bulk_permissions_to_role(
    role_id: str,
    assignment_data: BulkPermissionAssignment
):
    """Assign multiple permissions to role (simplified for seeding)"""
    try:
        # Validate role exists
        role = await role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Validate permissions exist
        perm_repo = get_permission_repo()
        valid_permissions = []
        for perm_id in assignment_data.permission_ids:
            permission = await perm_repo.get_by_id(perm_id)
            if permission:
                valid_permissions.append(perm_id)
            else:
                logger.warning(f"Permission {perm_id} not found, skipping")
        
        if not valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid permissions found"
            )
        
        # Add permissions to role
        await role_repo.add_permissions(role_id, valid_permissions)
        
        logger.info(f"{len(valid_permissions)} permissions assigned to role {role_id}")
        return ApiResponse(
            success=True,
            message=f"{len(valid_permissions)} permissions assigned successfully",
            data={"assigned_count": len(valid_permissions), "skipped_count": len(assignment_data.permission_ids) - len(valid_permissions)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk assigning permissions to role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permissions"
        )