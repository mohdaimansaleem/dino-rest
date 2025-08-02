"""
Optimized Authentication Service
Consolidated authentication, user management, and workspace operations
"""
from typing import Optional, Dict, Any, List
from datetime import timedelta, datetime
from fastapi import HTTPException, status
from functools import lru_cache

from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.logging_config import get_logger
from app.database.firestore import get_user_repo, get_role_repo
from app.models.schemas import UserCreate, UserLogin, User, AuthToken, UserRole

logger = get_logger(__name__)


class AuthService:
    """Optimized authentication service with consolidated functionality"""
    
    def __init__(self):
        self._role_cache = {}
        self._permission_cache = {}
    
    @lru_cache(maxsize=100)
    def _get_basic_role_permissions(self, role_name: str) -> List[Dict[str, Any]]:
        """Cached basic permissions for roles"""
        permissions_map = {
            'superadmin': [
                {'name': 'workspace:manage', 'resource': 'workspace', 'action': 'manage'},
                {'name': 'venue:manage', 'resource': 'venue', 'action': 'manage'},
                {'name': 'user:manage', 'resource': 'user', 'action': 'manage'},
                {'name': 'order:manage', 'resource': 'order', 'action': 'manage'},
                {'name': 'analytics:read', 'resource': 'analytics', 'action': 'read'}
            ],
            'admin': [
                {'name': 'venue:manage', 'resource': 'venue', 'action': 'manage'},
                {'name': 'order:manage', 'resource': 'order', 'action': 'manage'},
                {'name': 'menu:manage', 'resource': 'menu', 'action': 'manage'},
                {'name': 'analytics:read', 'resource': 'analytics', 'action': 'read'}
            ],
            'operator': [
                {'name': 'order:read', 'resource': 'order', 'action': 'read'},
                {'name': 'order:update', 'resource': 'order', 'action': 'update'},
                {'name': 'table:read', 'resource': 'table', 'action': 'read'},
                {'name': 'table:update', 'resource': 'table', 'action': 'update'}
            ]
        }
        return permissions_map.get(role_name, permissions_map['operator'])
    
    @lru_cache(maxsize=50)
    def _get_dashboard_permissions(self, role_name: str) -> Dict[str, Any]:
        """Cached dashboard permissions"""
        base_permissions = {
            'superadmin': {
                "components": {
                    "dashboard": True, "orders": True, "tables": True, "menu": True,
                    "customers": True, "analytics": True, "settings": True,
                    "user_management": True, "venue_management": True, "workspace_settings": True
                },
                "actions": {
                    "create_venue": True, "switch_venue": True, "create_users": True,
                    "change_passwords": True, "manage_menu": True, "view_analytics": True,
                    "update_order_status": True, "update_table_status": True
                }
            },
            'admin': {
                "components": {
                    "dashboard": True, "orders": True, "tables": True, "menu": True,
                    "customers": True, "analytics": True, "settings": True,
                    "user_management": False, "venue_management": False, "workspace_settings": False
                },
                "actions": {
                    "create_venue": False, "switch_venue": False, "create_users": True,
                    "change_passwords": True, "manage_menu": True, "view_analytics": True,
                    "update_order_status": True, "update_table_status": True
                }
            },
            'operator': {
                "components": {
                    "dashboard": True, "orders": True, "tables": True, "menu": False,
                    "customers": False, "analytics": False, "settings": False,
                    "user_management": False, "venue_management": False, "workspace_settings": False
                },
                "actions": {
                    "create_venue": False, "switch_venue": False, "create_users": False,
                    "change_passwords": False, "manage_menu": False, "view_analytics": False,
                    "update_order_status": True, "update_table_status": True
                }
            }
        }
        
        permissions = base_permissions.get(role_name, base_permissions['operator'])
        permissions["role"] = role_name
        return permissions
    
    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Register a new user with optimized validation"""
        user_repo = get_user_repo()
        
        try:
            # Check if user already exists (single query)
            existing_user = await user_repo.get_by_email(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Get or create default operator role
            role_id = await self._ensure_default_role()
            
            # Create user data
            user_dict = {
                "email": user_data.email,
                "mobile_number": user_data.mobile_number,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "role_id": role_id,
                "hashed_password": get_password_hash(user_data.password),
                "is_active": True,
                "is_verified": False,
                "email_verified": False,
                "mobile_verified": False
            }
            
            # Save to database
            created_user = await user_repo.create(user_dict)
            
            # Remove password from response
            created_user.pop("hashed_password", None)
            
            logger.info(f"User registered successfully: {user_data.email}")
            return created_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Optimized user authentication"""
        user_repo = get_user_repo()
        
        try:
            user = await user_repo.get_by_email(email)
            
            if not user or not user.get("is_active", True):
                return None
            
            if not verify_password(password, user["hashed_password"]):
                return None
            
            # Remove password from user data
            user.pop("hashed_password", None)
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def login_user(self, login_data: UserLogin) -> AuthToken:
        """Optimized login with cached permissions"""
        try:
            user = await self.authenticate_user(login_data.email, login_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            # Get user role and permissions
            role_name = await self._get_user_role_name(user.get("role_id"))
            permissions = self._get_basic_role_permissions(role_name)
            
            # Create tokens
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={
                    "sub": user["id"], 
                    "email": user["email"], 
                    "role": role_name,
                    "permissions": [p["name"] for p in permissions]
                },
                expires_delta=access_token_expires
            )
            
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = create_access_token(
                data={"sub": user["id"], "type": "refresh"},
                expires_delta=refresh_token_expires
            )
            
            # Update login count (async, don't wait)
            try:
                user_repo = get_user_repo()
                await user_repo.update(user["id"], {
                    "last_login": datetime.utcnow()
                })
            except Exception:
                pass  # Don't fail login for this
            
            # Prepare user data for response
            user_response = User(
                id=user["id"],
                email=user["email"],
                mobile_number=user["mobile_number"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                role_id=user.get("role_id"),
                is_active=user.get("is_active", True),
                is_verified=user.get("is_verified", False),
                email_verified=user.get("email_verified", False),
                mobile_verified=user.get("mobile_verified", False),
                last_login=user.get("last_login"),
                created_at=user.get("created_at"),
                updated_at=user.get("updated_at")
            )
            
            return AuthToken(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=refresh_token,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID without password"""
        try:
            user_repo = get_user_repo()
            user = await user_repo.get_by_id(user_id)
            if user:
                user.pop("hashed_password", None)
            return user
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        try:
            user_repo = get_user_repo()
            
            # Remove sensitive fields
            update_data.pop("hashed_password", None)
            update_data.pop("id", None)
            update_data.pop("created_at", None)
            
            # Update user
            updated_user = await user_repo.update(user_id, update_data)
            updated_user.pop("hashed_password", None)
            
            return updated_user
            
        except Exception as e:
            logger.error(f"Update user error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update failed"
            )
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            user_repo = get_user_repo()
            user = await user_repo.get_by_id(user_id)
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if not verify_password(current_password, user["hashed_password"]):
                raise HTTPException(status_code=400, detail="Incorrect current password")
            
            # Update password
            new_hashed_password = get_password_hash(new_password)
            await user_repo.update(user_id, {"hashed_password": new_hashed_password})
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password change error: {e}")
            raise HTTPException(status_code=500, detail="Password change failed")
    
    async def refresh_token(self, refresh_token: str) -> AuthToken:
        """Refresh JWT token"""
        from app.core.security import verify_token
        
        try:
            payload = verify_token(refresh_token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id or token_type != "refresh":
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            
            user = await self.get_user_by_id(user_id)
            if not user or not user.get("is_active", True):
                raise HTTPException(status_code=401, detail="User not found or inactive")
            
            # Get role and create new tokens
            role_name = await self._get_user_role_name(user.get("role_id"))
            permissions = self._get_basic_role_permissions(role_name)
            
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={
                    "sub": user["id"], 
                    "email": user["email"], 
                    "role": role_name,
                    "permissions": [p["name"] for p in permissions]
                },
                expires_delta=access_token_expires
            )
            
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            new_refresh_token = create_access_token(
                data={"sub": user["id"], "type": "refresh"},
                expires_delta=refresh_token_expires
            )
            
            user_response = User(
                id=user["id"],
                email=user["email"],
                mobile_number=user["mobile_number"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                role_id=user.get("role_id"),
                is_active=user.get("is_active", True),
                is_verified=user.get("is_verified", False),
                email_verified=user.get("email_verified", False),
                mobile_verified=user.get("mobile_verified", False),
                last_login=user.get("last_login"),
                created_at=user.get("created_at"),
                updated_at=user.get("updated_at")
            )
            
            return AuthToken(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=new_refresh_token,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(status_code=500, detail="Token refresh failed")
    
    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get user permissions and role information"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            role_name = await self._get_user_role_name(user.get("role_id"))
            permissions = self._get_basic_role_permissions(role_name)
            dashboard_permissions = self._get_dashboard_permissions(role_name)
            
            return {
                'user_id': user_id,
                'role': {'name': role_name, 'display_name': role_name.title()},
                'permissions': permissions,
                'dashboard_permissions': dashboard_permissions,
                'permission_count': len(permissions)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get permissions error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get permissions")
    
    async def _get_user_role_name(self, role_id: Optional[str]) -> str:
        """Get role name from role_id with caching"""
        if not role_id:
            return "operator"
        
        if role_id in self._role_cache:
            return self._role_cache[role_id]
        
        try:
            role_repo = get_role_repo()
            role = await role_repo.get_by_id(role_id)
            role_name = role.get("name", "operator") if role else "operator"
            
            # Cache the result
            self._role_cache[role_id] = role_name
            return role_name
            
        except Exception:
            return "operator"
    
    async def _ensure_default_role(self) -> str:
        """Ensure default operator role exists"""
        try:
            role_repo = get_role_repo()
            operator_role = await role_repo.get_by_name("operator")
            
            if operator_role:
                return operator_role["id"]
            
            # Create default operator role
            role_data = {
                "name": "operator",
                "description": "Default operator role",
                "permission_ids": []
            }
            return await role_repo.create(role_data)
            
        except Exception as e:
            logger.error(f"Error ensuring default role: {e}")
            raise HTTPException(status_code=500, detail="Role setup failed")


# Singleton instance
auth_service = AuthService()