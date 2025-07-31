"""
User Management Service
Handles user creation and management by SuperAdmin
"""
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from app.core.logging_config import LoggerMixin
from app.core.security import get_password_hash
from app.database.firestore import (
    get_user_repo, get_workspace_repo, get_cafe_repo, get_role_repo
)
from app.models.schemas import UserCreate, UserRole


class UserManagementService(LoggerMixin):
    """Service for user management operations"""
    
    async def create_user_by_superadmin(self, user_data: UserCreate, creator_id: str) -> Dict[str, Any]:
        """Create a new user by SuperAdmin"""
        try:
            user_repo = get_user_repo()
            workspace_repo = get_workspace_repo()
            cafe_repo = get_cafe_repo()
            role_repo = get_role_repo()
            
            # Verify creator is SuperAdmin
            creator = await user_repo.get_by_id(creator_id)
            if not creator:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Creator not found"
                )
            
            # Get creator's role
            creator_role = await role_repo.get_by_id(creator["role_id"])
            if not creator_role or creator_role["name"] != UserRole.SUPERADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only SuperAdmin can create users"
                )
            
            # Get creator's workspace
            workspace = await workspace_repo.get_by_id(creator["workspace_id"])
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
            
            # Check if email already exists
            existing_user = await user_repo.get_by_email(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Check if phone already exists
            existing_phone = await user_repo.get_by_phone(user_data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
            
            # Validate role
            target_role = await role_repo.get_by_id(user_data.role_id)
            if not target_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
            
            # SuperAdmin cannot create another SuperAdmin
            if target_role["name"] == UserRole.SUPERADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create another SuperAdmin"
                )
            
            # Validate cafe assignment for Admin/Operator roles
            if target_role["name"] in [UserRole.ADMIN, UserRole.OPERATOR]:
                if not user_data.cafe_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{target_role['name']} must be assigned to a cafe"
                    )
                
                # Verify cafe belongs to workspace
                cafe = await cafe_repo.get_by_id(user_data.cafe_id)
                if not cafe or cafe["workspace_id"] != workspace["id"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cafe does not belong to your workspace"
                    )
                
                # Check if cafe already has an admin (for Admin role)
                if target_role["name"] == UserRole.ADMIN:
                    if cafe.get("admin_id"):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cafe already has an admin"
                        )
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            
            # Create user data
            new_user_data = {
                "workspace_id": workspace["id"],
                "cafe_id": user_data.cafe_id if target_role["name"] in [UserRole.ADMIN, UserRole.OPERATOR] else None,
                "email": user_data.email,
                "phone": user_data.phone,
                "hashed_password": hashed_password,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "role_id": user_data.role_id,
                "date_of_birth": user_data.date_of_birth,
                "gender": user_data.gender.value if user_data.gender else None,
                "is_active": True,
                "is_verified": False,
                "email_verified": False,
                "phone_verified": False
            }
            
            # Create user
            user_id = await user_repo.create(new_user_data)
            
            # If creating an Admin, update cafe's admin_id
            if target_role["name"] == UserRole.ADMIN and user_data.cafe_id:
                await cafe_repo.update(user_data.cafe_id, {"admin_id": user_id})
            
            # Get created user (without password)
            user = await user_repo.get_by_id(user_id)
            user.pop("hashed_password", None)
            
            self.log_operation("create_user_by_superadmin", 
                             user_id=user_id,
                             creator_id=creator_id,
                             role=target_role["name"],
                             workspace_id=workspace["id"])
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "create_user_by_superadmin", 
                          email=user_data.email,
                          creator_id=creator_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
    
    async def get_workspace_users(self, workspace_id: str, requester_id: str) -> List[Dict[str, Any]]:
        """Get all users in a workspace"""
        try:
            user_repo = get_user_repo()
            role_repo = get_role_repo()
            
            # Verify requester has access to workspace
            requester = await user_repo.get_by_id(requester_id)
            if not requester or requester["workspace_id"] != workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to workspace users"
                )
            
            # Get all users in workspace
            users = await user_repo.get_by_workspace(workspace_id)
            
            # Remove passwords and add role names
            for user in users:
                user.pop("hashed_password", None)
                
                # Get role name
                if user.get("role_id"):
                    role = await role_repo.get_by_id(user["role_id"])
                    user["role_name"] = role["name"] if role else "unknown"
            
            self.log_operation("get_workspace_users", 
                             workspace_id=workspace_id,
                             requester_id=requester_id,
                             user_count=len(users))
            
            return users
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "get_workspace_users", 
                          workspace_id=workspace_id,
                          requester_id=requester_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get workspace users"
            )
    
    async def get_cafe_users(self, cafe_id: str, requester_id: str) -> List[Dict[str, Any]]:
        """Get all users assigned to a cafe"""
        try:
            user_repo = get_user_repo()
            cafe_repo = get_cafe_repo()
            role_repo = get_role_repo()
            
            # Verify cafe exists and requester has access
            cafe = await cafe_repo.get_by_id(cafe_id)
            if not cafe:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cafe not found"
                )
            
            requester = await user_repo.get_by_id(requester_id)
            if not requester:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requester not found"
                )
            
            # Check access: SuperAdmin can access any cafe in workspace, Admin/Operator only their cafe
            requester_role = await role_repo.get_by_id(requester["role_id"])
            if requester_role["name"] == UserRole.SUPERADMIN:
                if requester["workspace_id"] != cafe["workspace_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to cafe users"
                    )
            elif requester_role["name"] in [UserRole.ADMIN, UserRole.OPERATOR]:
                if requester["cafe_id"] != cafe_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to cafe users"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            # Get cafe users
            users = await user_repo.get_by_cafe(cafe_id)
            
            # Remove passwords and add role names
            for user in users:
                user.pop("hashed_password", None)
                
                # Get role name
                if user.get("role_id"):
                    role = await role_repo.get_by_id(user["role_id"])
                    user["role_name"] = role["name"] if role else "unknown"
            
            self.log_operation("get_cafe_users", 
                             cafe_id=cafe_id,
                             requester_id=requester_id,
                             user_count=len(users))
            
            return users
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "get_cafe_users", 
                          cafe_id=cafe_id,
                          requester_id=requester_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get cafe users"
            )
    
    async def deactivate_user(self, user_id: str, requester_id: str) -> bool:
        """Deactivate a user (SuperAdmin only)"""
        try:
            user_repo = get_user_repo()
            role_repo = get_role_repo()
            
            # Verify requester is SuperAdmin
            requester = await user_repo.get_by_id(requester_id)
            if not requester:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requester not found"
                )
            
            requester_role = await role_repo.get_by_id(requester["role_id"])
            if not requester_role or requester_role["name"] != UserRole.SUPERADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only SuperAdmin can deactivate users"
                )
            
            # Get target user
            target_user = await user_repo.get_by_id(user_id)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Cannot deactivate self
            if user_id == requester_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate yourself"
                )
            
            # Verify user belongs to same workspace
            if target_user["workspace_id"] != requester["workspace_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot deactivate user from different workspace"
                )
            
            # Deactivate user
            await user_repo.update(user_id, {"is_active": False})
            
            self.log_operation("deactivate_user", 
                             user_id=user_id,
                             requester_id=requester_id)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "deactivate_user", 
                          user_id=user_id,
                          requester_id=requester_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )


# Service instance
user_management_service = UserManagementService()