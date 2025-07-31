"""
Enhanced Workspace Management API Endpoints
Refactored with standardized patterns, enhanced security, and comprehensive management
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.models.schemas import (
    Workspace, WorkspaceCreate, WorkspaceUpdate, ApiResponse, PaginatedResponse,
    User, Venue
)
from app.core.base_endpoint import BaseEndpoint
from app.database.firestore import get_workspace_repo, WorkspaceRepository
from app.core.security import get_current_user, get_current_admin_user, verify_workspace_access
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class WorkspacesEndpoint(BaseEndpoint[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    """Enhanced Workspaces endpoint with comprehensive management"""
    
    def __init__(self):
        super().__init__(
            model_class=Workspace,
            create_schema=WorkspaceCreate,
            update_schema=WorkspaceUpdate,
            collection_name="workspaces",
            require_auth=True,
            require_admin=True
        )
    
    def get_repository(self) -> WorkspaceRepository:
        return get_workspace_repo()
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare workspace data before creation"""
        if current_user:
            data['owner_id'] = current_user['id']
        
        # Generate unique workspace name from display name
        display_name = data['display_name']
        workspace_name = self._generate_workspace_name(display_name)
        data['name'] = workspace_name
        
        # Set default values
        data['venue_ids'] = []
        data['is_active'] = True
        
        return data
    
    def _generate_workspace_name(self, display_name: str) -> str:
        """Generate unique workspace name from display name"""
        import re
        import uuid
        
        # Convert to lowercase and replace spaces/special chars with underscores
        name = re.sub(r'[^a-zA-Z0-9\s]', '', display_name.lower())
        name = re.sub(r'\s+', '_', name.strip())
        
        # Add unique suffix
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{name}_{unique_suffix}"
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate workspace creation permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Only admins can create workspaces
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create workspaces"
            )
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate workspace access permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Admin users can access all workspaces
        if current_user.get('role') == 'admin':
            return
        
        # Users can only access their own workspace
        user_workspace_id = current_user.get('workspace_id')
        if user_workspace_id != item['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Not authorized for this workspace"
            )
    
    async def _filter_items_for_user(self, 
                                   items: List[Dict[str, Any]], 
                                   current_user: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter workspaces based on user permissions"""
        if not current_user:
            return []
        
        # Admin users see all workspaces
        if current_user.get('role') == 'admin':
            return items
        
        # Regular users only see their workspace
        user_workspace_id = current_user.get('workspace_id')
        if user_workspace_id:
            return [item for item in items if item['id'] == user_workspace_id]
        
        return []
    
    async def get_workspace_statistics(self, 
                                     workspace_id: str,
                                     current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive workspace statistics"""
        repo = self.get_repository()
        
        # Validate access
        workspace_data = await repo.get_by_id(workspace_id)
        if not workspace_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        await self._validate_access_permissions(workspace_data, current_user)
        
        # Get related data
        from app.database.firestore import (
            get_venue_repo, get_user_repo, get_order_repo, get_menu_item_repo
        )
        
        venue_repo = get_venue_repo()
        user_repo = get_user_repo()
        order_repo = get_order_repo()
        menu_repo = get_menu_item_repo()
        
        # Get workspace venues
        venues = await venue_repo.get_by_workspace(workspace_id)
        active_venues = [venue for venue in venues if venue.get('is_active', False)]
        
        # Get workspace users
        users = await user_repo.get_by_workspace(workspace_id)
        active_users = [user for user in users if user.get('is_active', False)]
        
        # Get total orders across all venues
        total_orders = 0
        total_menu_items = 0
        
        for venue in venues:
            venue_id = venue['id']
            venue_orders = await order_repo.get_by_venue(venue_id, limit=1000)
            total_orders += len(venue_orders)
            
            venue_menu_items = await menu_repo.get_by_venue(venue_id)
            total_menu_items += len(venue_menu_items)
        
        return {
            "workspace_id": workspace_id,
            "workspace_name": workspace_data.get('display_name'),
            "total_venues": len(venues),
            "active_venues": len(active_venues),
            "total_users": len(users),
            "active_users": len(active_users),
            "total_orders": total_orders,
            "total_menu_items": total_menu_items,
            "created_at": workspace_data.get('created_at'),
            "is_active": workspace_data.get('is_active', False)
        }
    
    async def transfer_ownership(self, 
                               workspace_id: str,
                               new_owner_id: str,
                               current_user: Dict[str, Any]) -> bool:
        """Transfer workspace ownership to another user"""
        repo = self.get_repository()
        
        # Validate current ownership
        workspace_data = await repo.get_by_id(workspace_id)
        if not workspace_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        if workspace_data.get('owner_id') != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owner can transfer ownership"
            )
        
        # Validate new owner exists and is in the workspace
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        new_owner = await user_repo.get_by_id(new_owner_id)
        if not new_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New owner not found"
            )
        
        if new_owner.get('workspace_id') != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New owner must be a member of the workspace"
            )
        
        # Transfer ownership
        await repo.update(workspace_id, {"owner_id": new_owner_id})
        
        logger.info(f"Workspace ownership transferred: {workspace_id} -> {new_owner_id}")
        return True


# Initialize endpoint
workspaces_endpoint = WorkspacesEndpoint()


# =============================================================================
# WORKSPACE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get workspaces",
            description="Get paginated list of workspaces")
async def get_workspaces(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get workspaces with pagination and filtering"""
    filters = {}
    if is_active is not None:
        filters['is_active'] = is_active
    
    return await workspaces_endpoint.get_items(
        page=page,
        page_size=page_size,
        search=search,
        filters=filters,
        current_user=current_user
    )


@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create workspace",
             description="Create a new workspace")
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new workspace"""
    return await workspaces_endpoint.create_item(workspace_data, current_user)


@router.get("/{workspace_id}", 
            response_model=Workspace,
            summary="Get workspace by ID",
            description="Get specific workspace by ID")
async def get_workspace(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get workspace by ID"""
    return await workspaces_endpoint.get_item(workspace_id, current_user)


@router.put("/{workspace_id}", 
            response_model=ApiResponse,
            summary="Update workspace",
            description="Update workspace information")
async def update_workspace(
    workspace_id: str,
    workspace_update: WorkspaceUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update workspace information"""
    return await workspaces_endpoint.update_item(workspace_id, workspace_update, current_user)


@router.delete("/{workspace_id}", 
               response_model=ApiResponse,
               summary="Delete workspace",
               description="Deactivate workspace (soft delete)")
async def delete_workspace(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete workspace (soft delete by deactivating)"""
    return await workspaces_endpoint.delete_item(workspace_id, current_user, soft_delete=True)


@router.post("/{workspace_id}/activate", 
             response_model=ApiResponse,
             summary="Activate workspace",
             description="Activate deactivated workspace")
async def activate_workspace(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Activate workspace"""
    try:
        repo = get_workspace_repo()
        
        # Check if workspace exists
        workspace = await repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Validate permissions
        await workspaces_endpoint._validate_access_permissions(workspace, current_user)
        
        # Activate workspace
        await repo.update(workspace_id, {"is_active": True})
        
        logger.info(f"Workspace activated: {workspace_id}")
        return ApiResponse(
            success=True,
            message="Workspace activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate workspace"
        )


# =============================================================================
# WORKSPACE CONTENT ENDPOINTS
# =============================================================================

@router.get("/{workspace_id}/venues", 
            response_model=List[Venue],
            summary="Get workspace venues",
            description="Get all venues in workspace")
async def get_workspace_venues(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get venues in workspace"""
    try:
        # Verify workspace access
        await verify_workspace_access(workspace_id, current_user)
        
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        venues_data = await venue_repo.get_by_workspace(workspace_id)
        
        venues = [Venue(**venue) for venue in venues_data]
        
        logger.info(f"Retrieved {len(venues)} venues for workspace: {workspace_id}")
        return venues
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace venues"
        )


@router.get("/{workspace_id}/users", 
            response_model=List[User],
            summary="Get workspace users",
            description="Get all users in workspace")
async def get_workspace_users(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get users in workspace"""
    try:
        # Verify workspace access
        await verify_workspace_access(workspace_id, current_user)
        
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        users_data = await user_repo.get_by_workspace(workspace_id)
        
        users = [User(**user) for user in users_data]
        
        logger.info(f"Retrieved {len(users)} users for workspace: {workspace_id}")
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace users"
        )


# =============================================================================
# WORKSPACE ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/{workspace_id}/statistics", 
            response_model=Dict[str, Any],
            summary="Get workspace statistics",
            description="Get comprehensive workspace statistics")
async def get_workspace_statistics(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get workspace statistics"""
    try:
        statistics = await workspaces_endpoint.get_workspace_statistics(workspace_id, current_user)
        
        logger.info(f"Statistics retrieved for workspace: {workspace_id}")
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace statistics"
        )


@router.get("/{workspace_id}/analytics/summary", 
            response_model=Dict[str, Any],
            summary="Get workspace analytics summary",
            description="Get workspace analytics summary")
async def get_workspace_analytics_summary(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get workspace analytics summary"""
    try:
        # Verify workspace access
        await verify_workspace_access(workspace_id, current_user)
        
        from app.database.firestore import get_venue_repo, get_order_repo
        venue_repo = get_venue_repo()
        order_repo = get_order_repo()
        
        # Get workspace venues
        venues = await venue_repo.get_by_workspace(workspace_id)
        
        # Calculate analytics
        total_revenue = 0.0
        total_orders = 0
        active_venues = 0
        
        for venue in venues:
            if venue.get('is_active', False):
                active_venues += 1
            
            venue_id = venue['id']
            orders = await order_repo.get_by_venue(venue_id, limit=1000)
            
            for order in orders:
                if order.get('payment_status') == 'paid':
                    total_revenue += order.get('total_amount', 0)
                total_orders += 1
        
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        analytics = {
            "workspace_id": workspace_id,
            "total_venues": len(venues),
            "active_venues": active_venues,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": average_order_value,
            "period": "all_time"
        }
        
        logger.info(f"Analytics summary retrieved for workspace: {workspace_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace analytics"
        )


# =============================================================================
# WORKSPACE MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/{workspace_id}/transfer-ownership", 
             response_model=ApiResponse,
             summary="Transfer workspace ownership",
             description="Transfer workspace ownership to another user")
async def transfer_workspace_ownership(
    workspace_id: str,
    new_owner_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Transfer workspace ownership"""
    try:
        success = await workspaces_endpoint.transfer_ownership(
            workspace_id, new_owner_id, current_user
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="Workspace ownership transferred successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to transfer ownership"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring workspace ownership: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transfer ownership"
        )


@router.post("/{workspace_id}/add-venue", 
             response_model=ApiResponse,
             summary="Add venue to workspace",
             description="Add existing venue to workspace")
async def add_venue_to_workspace(
    workspace_id: str,
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Add venue to workspace"""
    try:
        # Verify workspace access
        await verify_workspace_access(workspace_id, current_user)
        
        # Verify venue exists and user has access
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Update venue workspace
        await venue_repo.update(venue_id, {"workspace_id": workspace_id})
        
        # Update workspace venue list
        repo = get_workspace_repo()
        workspace = await repo.get_by_id(workspace_id)
        venue_ids = workspace.get('venue_ids', [])
        
        if venue_id not in venue_ids:
            venue_ids.append(venue_id)
            await repo.update(workspace_id, {"venue_ids": venue_ids})
        
        logger.info(f"Venue {venue_id} added to workspace {workspace_id}")
        return ApiResponse(
            success=True,
            message="Venue added to workspace successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding venue to workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add venue to workspace"
        )


@router.delete("/{workspace_id}/remove-venue/{venue_id}", 
               response_model=ApiResponse,
               summary="Remove venue from workspace",
               description="Remove venue from workspace")
async def remove_venue_from_workspace(
    workspace_id: str,
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Remove venue from workspace"""
    try:
        # Verify workspace access
        await verify_workspace_access(workspace_id, current_user)
        
        # Update workspace venue list
        repo = get_workspace_repo()
        workspace = await repo.get_by_id(workspace_id)
        venue_ids = workspace.get('venue_ids', [])
        
        if venue_id in venue_ids:
            venue_ids.remove(venue_id)
            await repo.update(workspace_id, {"venue_ids": venue_ids})
        
        # Optionally remove workspace from venue
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        await venue_repo.update(venue_id, {"workspace_id": None})
        
        logger.info(f"Venue {venue_id} removed from workspace {workspace_id}")
        return ApiResponse(
            success=True,
            message="Venue removed from workspace successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing venue from workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove venue from workspace"
        )


# =============================================================================
# WORKSPACE ONBOARDING ENDPOINTS (Consolidated from workspace_onboarding.py)
# =============================================================================

@router.post("/onboard", 
             response_model=Dict[str, Any],
             status_code=status.HTTP_201_CREATED,
             summary="Complete Workspace Onboarding",
             description="Create workspace with default venue and superadmin user")
async def create_workspace_with_venue(workspace_data: Dict[str, Any]):
    """
    Complete workspace onboarding process:
    - Creates workspace
    - Creates default venue with operating hours
    - Creates superadmin user
    - Generates initial tables with QR codes
    - Sets up default permissions
    """
    try:
        from app.services.workspace_onboarding_service import workspace_onboarding_service
        
        result = await workspace_onboarding_service.create_workspace_with_venue(workspace_data)
        
        logger.info(f"Workspace onboarding completed: {result.workspace_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace onboarding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workspace onboarding failed"
        )


@router.post("/validate-workspace-data",
             response_model=Dict[str, Any],
             summary="Validate Workspace Data",
             description="Validate workspace data before creation")
async def validate_workspace_data(workspace_data: Dict[str, Any]):
    """
    Validate workspace data without creating it
    """
    try:
        # This would call validation methods from the service
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check workspace name uniqueness
        workspace_repo = get_workspace_repo()
        
        existing_workspace = await workspace_repo.query([
            ('name', '==', workspace_data.get('workspace_name', '').lower().strip())
        ])
        
        if existing_workspace:
            validation_result["valid"] = False
            validation_result["errors"].append("Workspace name already exists")
        
        # Check email uniqueness
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        owner_email = workspace_data.get('owner_details', {}).get('email', '').lower()
        if owner_email:
            existing_user = await user_repo.query([
                ('email', '==', owner_email)
            ])
            
            if existing_user:
                validation_result["valid"] = False
                validation_result["errors"].append("Email address already registered")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Workspace validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.post("/{workspace_id}/create-user",
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create Venue User",
             description="Create Admin or Operator user for a venue")
async def create_venue_user(
    workspace_id: str,
    user_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new user (Admin/Operator) for a venue
    - SuperAdmin can create Admin users
    - Admin can create Operator users
    - One role per venue constraint enforced
    """
    try:
        from app.services.role_permission_service import role_permission_service
        
        user_id = await role_permission_service.create_venue_user(
            creator_id=current_user["id"],
            venue_id=user_data.get("venue_id"),
            user_data=user_data
        )
        
        logger.info(f"Venue user created: {user_id} with role {user_data.get('role')}")
        
        return ApiResponse(
            success=True,
            message=f"{user_data.get('role', 'User')} created successfully",
            data={"user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/{workspace_id}/info",
            response_model=Dict[str, Any],
            summary="Get Workspace Information",
            description="Get current workspace information and statistics")
async def get_workspace_info(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get workspace information for current user
    """
    try:
        workspace_repo = get_workspace_repo()
        
        workspace = await workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Validate access
        await workspaces_endpoint._validate_access_permissions(workspace, current_user)
        
        # Filter sensitive information based on user role
        user_role = current_user.get("role")
        
        workspace_info = {
            "id": workspace["id"],
            "name": workspace.get("display_name"),
            "business_type": workspace.get("business_type"),
            "status": workspace.get("status"),
            "total_venues": workspace.get("total_venues", 0),
            "total_users": workspace.get("total_users", 0),
            "created_at": workspace.get("created_at"),
            "features_enabled": workspace.get("features_enabled", [])
        }
        
        # Add additional info for SuperAdmin
        if user_role == "superadmin":
            workspace_info.update({
                "subscription_plan": workspace.get("subscription_plan"),
                "trial_ends_at": workspace.get("trial_ends_at"),
                "max_venues": workspace.get("max_venues"),
                "max_users": workspace.get("max_users"),
                "venue_ids": workspace.get("venue_ids", [])
            })
        
        return {
            "success": True,
            "data": workspace_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace info retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace information"
        )