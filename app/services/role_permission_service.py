"""
Role and Permission Management Service
Handles role hierarchy, permission validation, and access control
"""
from typing import Dict, Any, List, Optional, Set
from fastapi import HTTPException, status
from datetime import datetime

from app.models.schemas import UserRole, PermissionCheck
from app.database.firestore import get_user_repo, get_workspace_repo, get_venue_repo
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RolePermissionService:
    """Service for managing roles, permissions, and access control"""
    
    def __init__(self):
        self.user_repo = get_user_repo()
        self.workspace_repo = get_workspace_repo()
        self.venue_repo = get_venue_repo()
        
        # Role hierarchy (higher number = more permissions)
        self.role_hierarchy = {
            UserRole.OPERATOR: 1,
            UserRole.ADMIN: 2,
            UserRole.SUPERADMIN: 3
        }
    
    async def validate_user_permissions(
        self, 
        user_id: str, 
        required_permissions: List[str],
        venue_id: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> PermissionCheck:
        """
        Validate if user has required permissions for the action
        """
        try:
            # Get user data
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return PermissionCheck(
                    has_permission=False,
                    reason="User not found",
                    required_role=None,
                    user_role=UserRole.OPERATOR
                )
            
            if not user.get('is_active', False):
                return PermissionCheck(
                    has_permission=False,
                    reason="User account is inactive",
                    required_role=None,
                    user_role=UserRole(user.get('role', 'operator'))
                )
            
            user_role = UserRole(user.get('role', 'operator'))
            user_permissions = set(user.get('permissions', []))
            
            # Check specific permissions
            required_perms_set = set(required_permissions)
            has_all_permissions = required_perms_set.issubset(user_permissions)
            
            # Role-based permission override
            if not has_all_permissions:
                has_all_permissions = self._check_role_based_permissions(
                    user_role, required_permissions
                )
            
            denied_reason = None
            if not has_all_permissions:
                missing_perms = required_perms_set - user_permissions
                denied_reason = f"Missing permissions: {', '.join(missing_perms)}"
            
            return PermissionCheck(
                has_permission=has_all_permissions,
                reason=denied_reason,
                required_role=None,
                user_role=user_role
            )
            
        except Exception as e:
            logger.error(f"Permission validation error: {e}")
            return PermissionCheck(
                has_permission=False,
                reason=f"Permission check failed: {str(e)}",
                required_role=None,
                user_role=UserRole.OPERATOR
            )
    
    def _check_role_based_permissions(self, role: UserRole, required_permissions: List[str]) -> bool:
        """Check if role inherently has the required permissions"""
        
        # SuperAdmin has all permissions
        if role == UserRole.SUPERADMIN:
            return True
        
        # Admin has most permissions except workspace-level ones
        if role == UserRole.ADMIN:
            admin_denied_permissions = [
                "workspace.delete", "workspace.manage", "workspace:delete", "workspace:settings",
                "user.create", "user.delete", "user:create", "user:delete", "role:manage",
                "venue.create", "venue.delete", "venue:create", "venue:delete"
            ]
            return not any(perm in admin_denied_permissions for perm in required_permissions)
        
        # Operator has very limited permissions
        if role == UserRole.OPERATOR:
            operator_allowed_permissions = [
                "venue.read", "venue:read", 
                "order.read", "order.update", "order:read", "order:update_status",
                "table.read", "table.update", "table:read", "table:update_status", 
                "customer:read", "analytics.read"
            ]
            return all(perm in operator_allowed_permissions for perm in required_permissions)
        
        return False
    
    async def can_user_manage_user(self, manager_id: str, target_user_id: str) -> bool:
        """Check if manager can manage target user based on role hierarchy"""
        
        manager = await self.user_repo.get_by_id(manager_id)
        target = await self.user_repo.get_by_id(target_user_id)
        
        if not manager or not target:
            return False
        
        manager_role = UserRole(manager.get('role', 'operator'))
        target_role = UserRole(target.get('role', 'operator'))
        
        # Role hierarchy check
        manager_level = self.role_hierarchy.get(manager_role, 0)
        target_level = self.role_hierarchy.get(target_role, 0)
        
        # Can only manage users with lower hierarchy level
        if manager_level <= target_level:
            return False
        
        # Additional rules
        if manager_role == UserRole.ADMIN:
            # Admin can only manage operators
            return target_role == UserRole.OPERATOR
        
        return True
    
    async def get_user_accessible_venues(self, user_id: str) -> List[str]:
        """Get list of venue IDs user can access"""
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return []
        
        user_role = UserRole(user.get('role', 'operator'))
        
        # Since workspace_id and venue_id fields removed from users schema,
        # venue access needs to be managed differently
        # For now, return all venues based on role
        if user_role == UserRole.SUPERADMIN:
            # SuperAdmin can access all venues
            all_venues = await self.venue_repo.get_all()
            return [venue['id'] for venue in all_venues]
        
        elif user_role == UserRole.ADMIN:
            # Admin can access venues they manage
            admin_venues = await self.venue_repo.get_by_admin(user_id)
            return [venue['id'] for venue in admin_venues]
        
        elif user_role == UserRole.OPERATOR:
            # Operator access would need to be managed through a separate mapping
            return []
        
        return []
    
    async def validate_venue_role_constraint(self, venue_id: str, role: UserRole) -> bool:
        """
        Validate that venue doesn't already have a user with this role
        (One role per venue constraint)
        """
        
        if role == UserRole.SUPERADMIN:
            # SuperAdmin is workspace-level, not venue-specific
            return True
        
        # Since venue_id field removed from users schema,
        # this constraint check would need alternative logic
        # For now, allow multiple users per venue
        return True
    
    async def create_venue_user(
        self, 
        creator_id: str,
        venue_id: str,
        user_data: Dict[str, Any]
    ) -> str:
        """
        Create a new user for a venue with role validation
        """
        
        # Validate creator permissions
        permission_check = await self.validate_user_permissions(
            creator_id, 
            ["user.create", "user:create", "user:create_operator"],
            venue_id=venue_id
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=permission_check.reason
            )
        
        # Get creator info
        creator = await self.user_repo.get_by_id(creator_id)
        creator_role = UserRole(creator.get('role', 'operator'))
        target_role = UserRole(user_data.get('role', 'operator'))
        
        # Validate role creation permissions
        if creator_role == UserRole.ADMIN and target_role != UserRole.OPERATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin can only create Operator users"
            )
        
        # Validate venue role constraint
        if not await self.validate_venue_role_constraint(venue_id, target_role):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Venue already has a {target_role.value} user"
            )
        
        # Create user
        from app.core.security import get_password_hash
        import uuid
        
        user_id = str(uuid.uuid4())
        
        new_user = {
            "id": user_id,
            "email": user_data['email'].lower(),
            "mobile_number": user_data.get('mobile_number'),
            "first_name": user_data.get('first_name', ''),
            "last_name": user_data.get('last_name', ''),
            "role_id": None,  # Will be set after role creation
            "hashed_password": get_password_hash(user_data['password']),
            "is_active": True,
            "is_verified": False,
            "email_verified": False,
            "mobile_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.user_repo.create(new_user)
        
        logger.info(f"User created: {user_id} with role {target_role.value} for venue {venue_id}")
        
        return user_id
    
    async def change_user_password(
        self, 
        changer_id: str, 
        target_user_id: str, 
        new_password: str
    ) -> bool:
        """
        Change password for a user (with proper authorization)
        """
        
        # Check if changer can manage target user
        can_manage = await self.can_user_manage_user(changer_id, target_user_id)
        if not can_manage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change this user's password"
            )
        
        # Hash new password
        from app.core.security import get_password_hash
        hashed_password = get_password_hash(new_password)
        
        # Update password
        await self.user_repo.update(target_user_id, {
            "hashed_password": hashed_password,
            "password_changed_at": datetime.utcnow(),
            "password_changed_by": changer_id
        })
        
        logger.info(f"Password changed for user {target_user_id} by {changer_id}")
        
        return True
    
    async def switch_venue_context(self, user_id: str, target_venue_id: str) -> bool:
        """
        Switch user's current venue context (for SuperAdmin)
        """
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_role = UserRole(user.get('role', 'operator'))
        
        if user_role != UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SuperAdmin can switch venue context"
            )
        
        # Validate venue exists
        venue = await self.venue_repo.get_by_id(target_venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Update user's current venue context
        await self.user_repo.update(user_id, {
            "current_venue_id": target_venue_id,
            "last_venue_switch": datetime.utcnow()
        })
        
        logger.info(f"User {user_id} switched to venue {target_venue_id}")
        
        return True
    
    def _get_role_permissions(self, role: UserRole) -> List[str]:
        """Get default permissions for a role"""
        
        if role == UserRole.SUPERADMIN:
            return [
                # Workspace permissions
                "workspace.read", "workspace.update", "workspace.manage",
                "workspace:read", "workspace:update", "workspace:analytics",
                
                # Venue permissions
                "venue.create", "venue.read", "venue.update", "venue.delete", "venue.manage",
                "venue:create", "venue:read", "venue:update", "venue:delete",
                "venue:switch", "venue:analytics", "venue:settings",
                
                # User permissions
                "user.create", "user.read", "user.update", "user.delete",
                "user:create", "user:read", "user:update", "user:delete",
                "user:change_password", "role:manage",
                
                # Menu permissions
                "menu.create", "menu.read", "menu.update", "menu.delete",
                "menu:create", "menu:read", "menu:update", "menu:delete",
                
                # Order permissions
                "order.create", "order.read", "order.update", "order.manage",
                "order:read", "order:update", "order:analytics",
                
                # Table permissions
                "table.create", "table.read", "table.update", "table.delete",
                "table:create", "table:read", "table:update", "table:delete",
                
                # Analytics permissions
                "analytics.read", "customer:read", "customer:analytics"
            ]
        
        elif role == UserRole.ADMIN:
            return [
                # Workspace permissions (limited)
                "workspace.read", "workspace:read",
                
                # Venue permissions
                "venue.read", "venue.update", "venue.manage",
                "venue:read", "venue:update", "venue:analytics", "venue:settings",
                
                # User permissions (limited)
                "user.read", "user.update", "user:read", "user:update_operator",
                "user:create_operator", "user:change_operator_password",
                
                # Menu permissions
                "menu.create", "menu.read", "menu.update", "menu.delete",
                "menu:create", "menu:read", "menu:update", "menu:delete",
                
                # Order permissions
                "order.create", "order.read", "order.update", "order.manage",
                "order:read", "order:update", "order:analytics",
                
                # Table permissions
                "table.create", "table.read", "table.update", "table.delete",
                "table:create", "table:read", "table:update", "table:delete",
                
                # Analytics permissions
                "analytics.read", "customer:read", "customer:analytics"
            ]
        
        elif role == UserRole.OPERATOR:
            return [
                # Venue permissions (read only)
                "venue.read", "venue:read",
                
                # Order permissions (operational)
                "order.read", "order.update", "order:read", "order:update_status",
                
                # Table permissions (operational)
                "table.read", "table.update", "table:read", "table:update_status",
                
                # Menu permissions (read only)
                "menu.read", "menu:read",
                
                # Analytics permissions (limited)
                "analytics.read", "customer:read"
            ]
        
        return []
    
    async def get_role_dashboard_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard permissions and accessible components for user"""
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        user_role = UserRole(user.get('role', 'operator'))
        
        dashboard_permissions = {
            "role": user_role.value,
            "components": {
                "dashboard": True,
                "orders": True,
                "tables": True,
                "menu": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "customers": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "analytics": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "settings": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "user_management": user_role == UserRole.SUPERADMIN,
                "venue_management": user_role == UserRole.SUPERADMIN,
                "workspace_settings": user_role == UserRole.SUPERADMIN
            },
            "actions": {
                "create_venue": user_role == UserRole.SUPERADMIN,
                "switch_venue": user_role == UserRole.SUPERADMIN,
                "create_users": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "change_passwords": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "manage_menu": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "view_analytics": user_role in [UserRole.SUPERADMIN, UserRole.ADMIN],
                "update_order_status": True,
                "update_table_status": True
            }
        }
        
        return dashboard_permissions


# Service instance
role_permission_service = RolePermissionService()