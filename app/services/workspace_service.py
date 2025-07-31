"""
Workspace Service
Handles workspace registration and management
"""
import uuid
import random
import string
from typing import Dict, Any, Tuple
from fastapi import HTTPException, status

from app.core.logging_config import LoggerMixin
from app.core.security import get_password_hash
from app.database.firestore import (
    get_workspace_repo, get_venue_repo, get_user_repo, 
    get_role_repo, get_permission_repo
)
from app.models.schemas import WorkspaceRegistration, UserRole


class WorkspaceService(LoggerMixin):
    """Service for workspace management"""
    
    def _generate_workspace_name(self) -> str:
        """Generate unique workspace name"""
        # Generate a random 8-character string
        chars = string.ascii_lowercase + string.digits
        random_part = ''.join(random.choices(chars, k=8))
        return f"ws_{random_part}"
    
    async def _ensure_system_roles_exist(self):
        """Ensure system roles exist in database"""
        role_repo = get_role_repo()
        
        system_roles = [
            {
                "name": UserRole.SUPERADMIN,
                "description": "Super administrator with full workspace access",
                "permission_ids": [],  # Will be populated with all permissions
                "is_system_role": True
            },
            {
                "name": UserRole.ADMIN,
                "description": "Administrator with venue management access",
                "permission_ids": [],  # Will be populated with venue permissions
                "is_system_role": True
            },
            {
                "name": UserRole.OPERATOR,
                "description": "Operator with limited venue access",
                "permission_ids": [],  # Will be populated with basic permissions
                "is_system_role": True
            },
            {
                "name": UserRole.CUSTOMER,
                "description": "Customer with ordering access",
                "permission_ids": [],  # Will be populated with customer permissions
                "is_system_role": True
            }
        ]
        
        created_roles = {}
        
        for role_data in system_roles:
            existing_role = await role_repo.get_by_name(role_data["name"])
            if not existing_role:
                role_id = await role_repo.create(role_data)
                created_roles[role_data["name"]] = role_id
                self.logger.info(f"Created system role: {role_data['name']}")
            else:
                created_roles[role_data["name"]] = existing_role["id"]
        
        return created_roles
    
    async def _ensure_system_permissions_exist(self):
        """Ensure system permissions exist in database"""
        permission_repo = get_permission_repo()
        
        system_permissions = [
            # Workspace permissions
            {"name": "workspace.manage", "description": "Manage workspace settings", "resource": "workspace", "action": "manage", "scope": "workspace"},
            {"name": "workspace.read", "description": "View workspace information", "resource": "workspace", "action": "read", "scope": "workspace"},
            
            # Cafe permissions
            {"name": "venue.create", "description": "Create new venues", "resource": "venue", "action": "create", "scope": "workspace"},
            {"name": "venue.read", "description": "View venue information", "resource": "venue", "action": "read", "scope": "venue"},
            {"name": "venue.update", "description": "Update venue information", "resource": "venue", "action": "update", "scope": "venue"},
            {"name": "venue.delete", "description": "Delete venues", "resource": "venue", "action": "delete", "scope": "venue"},
            {"name": "venue.manage", "description": "Full venue management", "resource": "venue", "action": "manage", "scope": "venue"},
            
            # Menu permissions
            {"name": "menu.create", "description": "Create menu items", "resource": "menu", "action": "create", "scope": "venue"},
            {"name": "menu.read", "description": "View menu items", "resource": "menu", "action": "read", "scope": "venue"},
            {"name": "menu.update", "description": "Update menu items", "resource": "menu", "action": "update", "scope": "venue"},
            {"name": "menu.delete", "description": "Delete menu items", "resource": "menu", "action": "delete", "scope": "venue"},
            
            # Order permissions
            {"name": "order.create", "description": "Create orders", "resource": "order", "action": "create", "scope": "venue"},
            {"name": "order.read", "description": "View orders", "resource": "order", "action": "read", "scope": "venue"},
            {"name": "order.update", "description": "Update order status", "resource": "order", "action": "update", "scope": "venue"},
            {"name": "order.manage", "description": "Full order management", "resource": "order", "action": "manage", "scope": "venue"},
            
            # User permissions
            {"name": "user.create", "description": "Create users", "resource": "user", "action": "create", "scope": "workspace"},
            {"name": "user.read", "description": "View users", "resource": "user", "action": "read", "scope": "workspace"},
            {"name": "user.update", "description": "Update users", "resource": "user", "action": "update", "scope": "workspace"},
            {"name": "user.delete", "description": "Delete users", "resource": "user", "action": "delete", "scope": "workspace"},
            
            # Table permissions
            {"name": "table.create", "description": "Create tables", "resource": "table", "action": "create", "scope": "venue"},
            {"name": "table.read", "description": "View tables", "resource": "table", "action": "read", "scope": "venue"},
            {"name": "table.update", "description": "Update tables", "resource": "table", "action": "update", "scope": "venue"},
            {"name": "table.delete", "description": "Delete tables", "resource": "table", "action": "delete", "scope": "venue"},
            
            # Analytics permissions
            {"name": "analytics.read", "description": "View analytics", "resource": "analytics", "action": "read", "scope": "venue"},
        ]
        
        created_permissions = {}
        
        for perm_data in system_permissions:
            perm_data["is_system_permission"] = True
            existing_perm = await permission_repo.get_by_name(perm_data["name"])
            if not existing_perm:
                perm_id = await permission_repo.create(perm_data)
                created_permissions[perm_data["name"]] = perm_id
                self.logger.info(f"Created system permission: {perm_data['name']}")
            else:
                created_permissions[perm_data["name"]] = existing_perm["id"]
        
        return created_permissions
    
    async def register_workspace(self, registration_data: WorkspaceRegistration) -> Dict[str, Any]:
        """Register a new workspace with venue and superadmin user"""
        try:
            # Ensure system roles and permissions exist
            roles = await self._ensure_system_roles_exist()
            permissions = await self._ensure_system_permissions_exist()
            
            # Check if email already exists
            user_repo = get_user_repo()
            existing_user = await user_repo.get_by_email(registration_data.owner_email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Check if phone already exists
            existing_phone = await user_repo.get_by_phone(registration_data.owner_phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
            
            # Generate unique workspace name
            workspace_repo = get_workspace_repo()
            workspace_name = self._generate_workspace_name()
            
            # Ensure workspace name is unique
            while await workspace_repo.get_by_name(workspace_name):
                workspace_name = self._generate_workspace_name()
            
            # Create workspace
            workspace_data = {
                "name": workspace_name,
                "description": registration_data.workspace_description,
                "owner_id": "",  # Will be updated after user creation
                "venue_ids": [],
                "is_active": True
            }
            
            workspace_id = await workspace_repo.create(workspace_data)
            
            # Create superadmin user
            hashed_password = get_password_hash(registration_data.owner_password)
            
            user_data = {
                "workspace_id": workspace_id,
                "venue_id": None,  # Superadmin is not tied to specific venue
                "email": registration_data.owner_email,
                "phone": registration_data.owner_phone,
                "hashed_password": hashed_password,
                "first_name": registration_data.owner_first_name,
                "last_name": registration_data.owner_last_name,
                "role_id": roles[UserRole.SUPERADMIN],
                "is_active": True,
                "is_verified": False,
                "email_verified": False,
                "phone_verified": False
            }
            
            user_id = await user_repo.create(user_data)
            
            # Update workspace with owner_id
            await workspace_repo.update(workspace_id, {"owner_id": user_id})
            
            # Create venue
            venue_repo = get_venue_repo()
            venue_data = {
                "workspace_id": workspace_id,
                "admin_id": None,  # Will be set when admin is created
                "name": registration_data.venue_name,
                "description": registration_data.venue_description,
                "location": registration_data.venue_location.dict(),
                "phone": registration_data.venue_phone,
                "email": registration_data.venue_email,
                "website": str(registration_data.venue_website) if registration_data.venue_website else None,
                "cuisine_types": registration_data.cuisine_types,
                "price_range": registration_data.price_range.value,
                "operating_hours": [],
                "subscription_plan": "basic",
                "subscription_status": "active",
                "is_active": True,
                "is_verified": False,
                "rating": 0.0,
                "total_reviews": 0
            }
            
            venue_id = await venue_repo.create(venue_data)
            
            # Update workspace with venue_id
            await workspace_repo.update(workspace_id, {"venue_ids": [venue_id]})
            
            # Get created entities
            workspace = await workspace_repo.get_by_id(workspace_id)
            user = await user_repo.get_by_id(user_id)
            venue = await venue_repo.get_by_id(venue_id)
            
            # Remove password from user data
            user.pop("hashed_password", None)
            
            result = {
                "workspace": workspace,
                "user": user,
                "venue": venue,
                "message": "Workspace registered successfully"
            }
            
            self.log_operation("register_workspace", 
                             workspace_id=workspace_id,
                             user_id=user_id,
                             venue_id=venue_id,
                             workspace_name=workspace_name)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "register_workspace", 
                          email=registration_data.owner_email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workspace registration failed"
            )
    
    async def get_workspace_by_user(self, user_id: str) -> Dict[str, Any]:
        """Get workspace information for a user"""
        try:
            user_repo = get_user_repo()
            user_data = await user_repo.get_by_id(user_id)
            
            if not user_data or not user_data.get("workspace_id"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User workspace not found"
                )
            
            workspace_repo = get_workspace_repo()
            workspace = await workspace_repo.get_by_id(user_data["workspace_id"])
            
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
            
            return workspace
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "get_workspace_by_user", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get workspace information"
            )


# Service instance
workspace_service = WorkspaceService()