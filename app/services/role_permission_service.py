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
                    user_role=UserRole.OPERATOR,
                    venue_access=False,
                    workspace_access=False,
                    denied_reason="User not found"
                )
            
            if not user.get('is_active', False):
                return PermissionCheck(
                    has_permission=False,
                    user_role=UserRole(user.get('role', 'operator')),
                    venue_access=False,
                    workspace_access=False,
                    denied_reason="User account is inactive"
                )
            
            user_role = UserRole(user.get('role', 'operator'))
            user_permissions = set(user.get('permissions', []))
            user_workspace_id = user.get('workspace_id')
            user_venue_access = user.get('venue_access', [])
            
            # Check workspace access
            workspace_access = True
            if workspace_id and user_workspace_id != workspace_id:
                if user_role != UserRole.SUPERADMIN:
                    workspace_access = False
            
            # Check venue access
            venue_access = True
            if venue_id:
                if user_role == UserRole.SUPERADMIN:
                    # SuperAdmin can access any venue in their workspace
                    venue = await self.venue_repo.get_by_id(venue_id)
                    if venue and venue.get('workspace_id') != user_workspace_id:
                        venue_access = False
                elif user_role == UserRole.ADMIN:
                    # Admin can access venues they're assigned to
                    if venue_id not in user_venue_access:
                        venue_access = False
                elif user_role == UserRole.OPERATOR:
                    # Operator can only access their assigned venue
                    if user.get('venue_id') != venue_id:
                        venue_access = False
            
            # Check specific permissions
            required_perms_set = set(required_permissions)
            has_all_permissions = required_perms_set.issubset(user_permissions)
            
            # Role-based permission override
            if not has_all_permissions:
                has_all_permissions = self._check_role_based_permissions(
                    user_role, required_permissions
                )
            
            overall_permission = (
                has_all_permissions and 
                workspace_access and 
                venue_access
            )
            
            denied_reason = None
            if not overall_permission:
                if not workspace_access:
                    denied_reason = "Access denied: Different workspace"
                elif not venue_access:
                    denied_reason = "Access denied: No venue access"
                elif not has_all_permissions:
                    denied_reason = f"Missing permissions: {', '.join(required_perms_set - user_permissions)}"
            
            return PermissionCheck(
                has_permission=overall_permission,
                user_role=user_role,
                venue_access=venue_access,
                workspace_access=workspace_access,
                specific_permissions=list(user_permissions),
                denied_reason=denied_reason
            )
            
        except Exception as e:
            logger.error(f"Permission validation error: {e}")
            return PermissionCheck(
                has_permission=False,
                user_role=UserRole.OPERATOR,
                venue_access=False,
                workspace_access=False,
                denied_reason=f"Permission check failed: {str(e)}"
            )
    
    def _check_role_based_permissions(self, role: UserRole, required_permissions: List[str]) -> bool:
        """Check if role inherently has the required permissions"""
        
        # SuperAdmin has all permissions
        if role == UserRole.SUPERADMIN:
            return True
        
        # Admin has most permissions except workspace-level ones
        if role == UserRole.ADMIN:
            admin_denied_permissions = [
                "workspace:delete", "workspace:settings",
                "user:create", "user:delete", "role:manage",
                "venue:create", "venue:delete"
            ]
            return not any(perm in admin_denied_permissions for perm in required_permissions)
        
        # Operator has very limited permissions
        if role == UserRole.OPERATOR:
            operator_allowed_permissions = [
                "venue:read", "order:read", "order:update_status",
                "table:read", "table:update_status", "customer:read"
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
        
        # Same workspace check
        if manager.get('workspace_id') != target.get('workspace_id'):
            return False
        
        # Role hierarchy check
        manager_level = self.role_hierarchy.get(manager_role, 0)
        target_level = self.role_hierarchy.get(target_role, 0)
        
        # Can only manage users with lower or equal hierarchy level
        if manager_level <= target_level:
            return False
        
        # Additional rules
        if manager_role == UserRole.ADMIN:
            # Admin can only manage operators in their venue
            if target_role == UserRole.OPERATOR:
                return target.get('venue_id') in manager.get('venue_access', [])
            else:
                return False
        
        return True
    
    async def get_user_accessible_venues(self, user_id: str) -> List[str]:
        """Get list of venue IDs user can access"""
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return []
        
        user_role = UserRole(user.get('role', 'operator'))
        workspace_id = user.get('workspace_id')
        
        if user_role == UserRole.SUPERADMIN:
            # SuperAdmin can access all venues in workspace
            workspace = await self.workspace_repo.get_by_id(workspace_id)
            return workspace.get('venue_ids', []) if workspace else []
        
        elif user_role == UserRole.ADMIN:
            # Admin can access assigned venues
            return user.get('venue_access', [])
        
        elif user_role == UserRole.OPERATOR:
            # Operator can only access their assigned venue
            venue_id = user.get('venue_id')
            return [venue_id] if venue_id else []
        
        return []
    
    async def validate_venue_role_constraint(self, venue_id: str, role: UserRole) -> bool:
        """
        Validate that venue doesn't already have a user with this role
        (One role per venue constraint)
        """
        
        if role == UserRole.SUPERADMIN:
            # SuperAdmin is workspace-level, not venue-specific
            return True
        
        # Check if venue already has a user with this role
        existing_users = await self.user_repo.query([
            ('venue_id', '==', venue_id),
            ('role', '==', role.value),
            ('is_active', '==', True)
        ])
        
        return len(existing_users) == 0
    
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
            ["user:create", "user:create_operator"],
            venue_id=venue_id
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=permission_check.denied_reason
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
            "workspace_id": creator.get('workspace_id'),
            "venue_id": venue_id,
            "email": user_data['email'].lower(),
            "phone": user_data.get('phone'),
            "full_name": user_data['full_name'],
            "role": target_role.value,
            "hashed_password": get_password_hash(user_data['password']),
            "is_active": True,
            "is_verified": False,
            "is_owner": False,
            "permissions": self._get_role_permissions(target_role),
            "venue_access": [venue_id] if target_role == UserRole.ADMIN else [],
            "created_by": creator_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.user_repo.create(new_user)
        
        # Update workspace user count
        workspace_id = creator.get('workspace_id')
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if workspace:
            await self.workspace_repo.update(workspace_id, {
                "total_users": workspace.get('total_users', 0) + 1
            })
        
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
        
        # Validate venue belongs to user's workspace
        venue = await self.venue_repo.get_by_id(target_venue_id)
        if not venue or venue.get('workspace_id') != user.get('workspace_id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found in your workspace"
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
                "workspace:read", "workspace:update", "workspace:analytics",
                "venue:create", "venue:read", "venue:update", "venue:delete",
                "venue:switch", "venue:analytics", "venue:settings",
                "user:create", "user:read", "user:update", "user:delete",
                "user:change_password", "role:manage",
                "menu:create", "menu:read", "menu:update", "menu:delete",
                "order:read", "order:update", "order:analytics",
                "table:create", "table:read", "table:update", "table:delete",
                "customer:read", "customer:analytics"
            ]
        
        elif role == UserRole.ADMIN:
            return [
                "venue:read", "venue:update", "venue:analytics", "venue:settings",
                "user:create_operator", "user:read", "user:update_operator",
                "user:change_operator_password",
                "menu:create", "menu:read", "menu:update", "menu:delete",
                "order:read", "order:update", "order:analytics",
                "table:create", "table:read", "table:update", "table:delete",
                "customer:read", "customer:analytics"
            ]
        
        elif role == UserRole.OPERATOR:
            return [
                "venue:read",
                "order:read", "order:update_status",
                "table:read", "table:update_status",
                "customer:read"
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