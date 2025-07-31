"""
Authentication Service
Production-ready user authentication and management
"""
from typing import Optional, Dict, Any
from datetime import timedelta
from fastapi import HTTPException, status

from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.logging_config import LoggerMixin
from app.database.firestore import get_user_repo
from app.models.schemas import UserCreate, UserLogin, User, Token, AuthToken


class AuthService(LoggerMixin):
    """Authentication service for user management"""
    
    def _convert_date_to_datetime(self, date_obj):
        """Convert date object to datetime for Firestore compatibility"""
        if date_obj is None:
            return None
        
        from datetime import datetime, date
        if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
            # Convert date to datetime at midnight
            return datetime.combine(date_obj, datetime.min.time())
        elif isinstance(date_obj, datetime):
            return date_obj
        else:
            return date_obj
    
    def _convert_datetime_to_date(self, datetime_obj):
        """Convert datetime object back to date for schema compatibility"""
        if datetime_obj is None:
            return None
        
        from datetime import datetime, date
        if isinstance(datetime_obj, datetime):
            # Convert datetime to date
            return datetime_obj.date()
        elif isinstance(datetime_obj, date):
            return datetime_obj
        else:
            return datetime_obj
    
    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Register a new user"""
        user_repo = get_user_repo()
        
        try:
            # Check if user already exists
            existing_user = await user_repo.get_by_email(user_data.email)
            if existing_user:
                self.logger.warning("Registration attempt with existing email", extra={
                    "email": user_data.email
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Set default role_id if not provided
            role_id = user_data.role_id
            if not role_id:
                # Get or create default customer role
                from app.database.firestore import get_role_repo
                role_repo = get_role_repo()
                
                # Try to find existing customer role
                customer_role = await role_repo.get_by_name("customer")
                if customer_role:
                    role_id = customer_role["id"]
                else:
                    # Create default customer role if it doesn't exist
                    role_data = {
                        "name": "customer",
                        "description": "Default customer role",
                        "permission_ids": [],
                        "is_system_role": True
                    }
                    role_id = await role_repo.create(role_data)
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            
            # Create user data
            user_dict = {
                "email": user_data.email,
                "phone": user_data.phone,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "role_id": role_id,
                "workspace_id": user_data.workspace_id,
                "venue_id": user_data.venue_id,
                "date_of_birth": self._convert_date_to_datetime(user_data.date_of_birth),
                "gender": user_data.gender,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_verified": False,
                "email_verified": False,
                "phone_verified": False,
                "login_count": 0,
                "total_orders": 0,
                "total_spent": 0.0,
                "addresses": [],
                "preferences": {}
            }
            
            # Save to database
            user_id = await user_repo.create(user_dict)
            
            # Get created user (without password)
            user = await user_repo.get_by_id(user_id)
            if user:
                user.pop("hashed_password", None)
            
            self.log_operation("user_registration", user_id=user_id, email=user_data.email)
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "user_registration", email=user_data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user_repo = get_user_repo()
        
        try:
            user = await user_repo.get_by_email(email)
            if not user:
                self.logger.warning("Authentication attempt with non-existent email", extra={
                    "email": email
                })
                return None
            
            if not verify_password(password, user["hashed_password"]):
                self.logger.warning("Authentication attempt with invalid password", extra={
                    "email": email,
                    "user_id": user.get("id")
                })
                return None
            
            # Remove password from user data
            user.pop("hashed_password", None)
            
            self.log_operation("user_authentication", user_id=user.get("id"), email=email)
            return user
            
        except Exception as e:
            self.log_error(e, "user_authentication", email=email)
            return None
    
    async def login_user(self, login_data: UserLogin) -> AuthToken:
        """Login user and return JWT token"""
        try:
            user = await self.authenticate_user(login_data.email, login_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.get("is_active", True):
                self.logger.warning("Login attempt by inactive user", extra={
                    "user_id": user.get("id"),
                    "email": login_data.email
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
            
            # Create access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user["id"], "email": user["email"], "role_id": user["role_id"]},
                expires_delta=access_token_expires
            )
            
            # Update login count
            user_repo = get_user_repo()
            await user_repo.update(user["id"], {
                "login_count": user.get("login_count", 0) + 1,
                "last_login": user.get("updated_at")
            })
            
            self.log_operation("user_login", user_id=user["id"], email=login_data.email)
            
            # Ensure user data has all required fields for User schema
            user_for_token = {
                "id": user["id"],
                "email": user["email"],
                "phone": user["phone"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "workspace_id": user.get("workspace_id"),
                "venue_id": user.get("venue_id"),
                "role_id": user.get("role_id"),
                "date_of_birth": self._convert_datetime_to_date(user.get("date_of_birth")),
                "gender": user.get("gender"),
                "is_active": user.get("is_active", True),
                "is_verified": user.get("is_verified", False),
                "email_verified": user.get("email_verified", False),
                "phone_verified": user.get("phone_verified", False),
                "last_login": user.get("last_login"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at")
            }
            
            # Create refresh token
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = create_access_token(
                data={"sub": user["id"], "type": "refresh"},
                expires_delta=refresh_token_expires
            )
            
            return AuthToken(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=refresh_token,
                user=User(**user_for_token)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "user_login", email=login_data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user_repo = get_user_repo()
        
        try:
            user = await user_repo.get_by_id(user_id)
            if user:
                user.pop("hashed_password", None)
            
            self.log_operation("get_user_by_id", user_id=user_id, found=user is not None)
            return user
            
        except Exception as e:
            self.log_error(e, "get_user_by_id", user_id=user_id)
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        user_repo = get_user_repo()
        
        try:
            # Remove sensitive fields that shouldn't be updated directly
            update_data.pop("hashed_password", None)
            update_data.pop("id", None)
            update_data.pop("created_at", None)
            
            # Convert date fields to datetime for Firestore compatibility
            if "date_of_birth" in update_data:
                update_data["date_of_birth"] = self._convert_date_to_datetime(update_data["date_of_birth"])
            
            # Update user
            await user_repo.update(user_id, update_data)
            
            # Return updated user
            user = await user_repo.get_by_id(user_id)
            if user:
                user.pop("hashed_password", None)
            
            self.log_operation("update_user", user_id=user_id, fields=list(update_data.keys()))
            return user
            
        except Exception as e:
            self.log_error(e, "update_user", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update failed"
            )
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        user_repo = get_user_repo()
        
        try:
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not verify_password(current_password, user["hashed_password"]):
                self.logger.warning("Password change attempt with invalid current password", extra={
                    "user_id": user_id
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect current password"
                )
            
            # Hash new password
            new_hashed_password = get_password_hash(new_password)
            
            # Update password
            await user_repo.update(user_id, {"hashed_password": new_hashed_password})
            
            self.log_operation("change_password", user_id=user_id)
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "change_password", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        user_repo = get_user_repo()
        
        try:
            await user_repo.update(user_id, {"is_active": False})
            self.log_operation("deactivate_user", user_id=user_id)
            return True
            
        except Exception as e:
            self.log_error(e, "deactivate_user", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account deactivation failed"
            )
    
    async def refresh_token(self, refresh_token: str) -> AuthToken:
        """Refresh JWT token"""
        from app.core.security import verify_token, create_access_token
        
        try:
            # Verify refresh token
            payload = verify_token(refresh_token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id or token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Get user data
            user = await self.get_user_by_id(user_id)
            if not user or not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Create new access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user["id"], "email": user["email"], "role_id": user["role_id"]},
                expires_delta=access_token_expires
            )
            
            # Create new refresh token
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            new_refresh_token = create_access_token(
                data={"sub": user["id"], "type": "refresh"},
                expires_delta=refresh_token_expires
            )
            
            # Prepare user data for response
            user_for_token = {
                "id": user["id"],
                "email": user["email"],
                "phone": user["phone"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "workspace_id": user.get("workspace_id"),
                "venue_id": user.get("venue_id"),
                "role_id": user.get("role_id"),
                "date_of_birth": self._convert_datetime_to_date(user.get("date_of_birth")),
                "gender": user.get("gender"),
                "is_active": user.get("is_active", True),
                "is_verified": user.get("is_verified", False),
                "email_verified": user.get("email_verified", False),
                "phone_verified": user.get("phone_verified", False),
                "last_login": user.get("last_login"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at")
            }
            
            self.log_operation("token_refresh", user_id=user_id)
            
            return AuthToken(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=new_refresh_token,
                user=User(**user_for_token)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.log_error(e, "token_refresh")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )


# Service instance
auth_service = AuthService()