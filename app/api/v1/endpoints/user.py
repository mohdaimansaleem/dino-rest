"""
User Management API Endpoints
Comprehensive user management with authentication, profiles, and administration
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.security import HTTPBearer

from app.models.schemas import (
    UserCreate, User, UserUpdate, UserLogin, AuthToken,
    ApiResponse, UserAddress, UserPreferences, ImageUploadResponse,
    PaginatedResponse
)
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.firestore import get_user_repo, UserRepository
from app.database.validated_repository import get_validated_user_repo, ValidatedUserRepository
from app.services.validation_service import get_validation_service
from app.services.auth_service import auth_service
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


class UserEndpoint(WorkspaceIsolatedEndpoint[User, UserCreate, UserUpdate]):
    """User endpoint with standardized CRUD operations"""
    
    def __init__(self):
        super().__init__(
            model_class=User,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            collection_name="users",
            require_auth=True,
            require_admin=False
        )
    
    def get_repository(self) -> ValidatedUserRepository:
        return get_validated_user_repo()
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare user data before creation"""
        # Remove confirm_password field
        data.pop('confirm_password', None)
        
        # Set default values
        data['is_active'] = True
        data['is_verified'] = False
        data['email_verified'] = False
        data['phone_verified'] = False
        
        # Set workspace from current user if not provided
        if not data.get('workspace_id') and current_user:
            data['workspace_id'] = current_user.get('workspace_id')
        
        return data
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate user creation permissions"""
        if not current_user:
            return  # Public registration allowed
        
        # Check if user can create users in the specified workspace
        target_workspace_id = data.get('workspace_id')
        user_workspace_id = current_user.get('workspace_id')
        
        if target_workspace_id and user_workspace_id != target_workspace_id:
            if current_user.get('role') != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create users in different workspace"
                )
    
    async def _validate_update_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate user update permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Users can update their own profile
        if item['id'] == current_user['id']:
            return
        
        # Admins can update users in their workspace
        if current_user.get('role') == 'admin':
            if item.get('workspace_id') == current_user.get('workspace_id'):
                return
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    async def _build_query_filters(self, 
                                  filters: Optional[Dict[str, Any]], 
                                  search: Optional[str],
                                  current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters for user search"""
        query_filters = []
        
        # Add workspace filter for non-admin users
        if current_user and current_user.get('role') != 'admin':
            workspace_id = current_user.get('workspace_id')
            if workspace_id:
                query_filters.append(('workspace_id', '==', workspace_id))
        
        # Add additional filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters
    
    async def search_users_by_text(self, 
                                  search_term: str,
                                  current_user: Dict[str, Any]) -> List[User]:
        """Search users by name, email, or phone"""
        repo = self.get_repository()
        
        # Build base filters
        base_filters = await self._build_query_filters(None, None, current_user)
        
        # Search in multiple fields
        search_fields = ['first_name', 'last_name', 'email', 'phone']
        matching_users = await repo.search_text(
            search_fields=search_fields,
            search_term=search_term,
            additional_filters=base_filters,
            limit=50
        )
        
        return [User(**user) for user in matching_users]


# Initialize endpoint
user_endpoint = UserEndpoint()


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/register", 
             response_model=AuthToken,
             status_code=status.HTTP_201_CREATED,
             summary="Register new user",
             description="Register a new user account. Public endpoint - no authentication required.")
async def register_user(user_data: UserCreate):
    """Register a new user with comprehensive validation"""
    try:
        # Get validation service
        validation_service = get_validation_service()
        
        # Convert Pydantic model to dict for validation
        user_dict = user_data.dict()
        
        # Validate user data (this will check uniqueness, format, etc.)
        validation_errors = await validation_service.validate_user_data(user_dict, is_update=False)
        if validation_errors:
            validation_service.raise_validation_exception(validation_errors)
        
        # Register user (auth_service will handle password hashing)
        user = await auth_service.register_user(user_data)
        
        # Login user immediately after registration
        login_data = UserLogin(email=user_data.email, password=user_data.password)
        token = await auth_service.login_user(login_data)
        
        logger.info(f"User registered successfully: {user_data.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", 
             response_model=AuthToken,
             summary="User login",
             description="Authenticate user and return JWT token")
async def login_user(login_data: UserLogin):
    """Login user"""
    try:
        token = await auth_service.login_user(login_data)
        
        # Update last login
        user_repo = get_user_repo()
        await user_repo.update(token.user.id, {"last_login": token.user.created_at})
        
        logger.info(f"User logged in successfully: {login_data.email}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# =============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/profile", 
            response_model=User,
            summary="Get user profile",
            description="Get current user's profile information")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return User(**current_user)


@router.put("/profile", 
            response_model=ApiResponse,
            summary="Update user profile",
            description="Update current user's profile information")
async def update_user_profile(
    update_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    try:
        user_repo = get_user_repo()
        
        # Check if email is being updated and is unique
        if hasattr(update_data, 'email') and update_data.email and update_data.email != current_user.get("email"):
            existing_user = await user_repo.get_by_email(update_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        # Check if phone is being updated and is unique
        if hasattr(update_data, 'phone') and update_data.phone and update_data.phone != current_user.get("phone"):
            existing_phone = await user_repo.get_by_phone(update_data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already in use"
                )
        
        # Update user
        updated_user = await auth_service.update_user(current_user['id'], update_data.dict(exclude_unset=True))
        
        logger.info(f"User profile updated: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Profile updated successfully",
            data=User(**updated_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/profile/image", 
             response_model=ImageUploadResponse,
             summary="Upload profile image",
             description="Upload user profile image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload user profile image"""
    try:
        # TODO: Implement storage service
        # storage_service = get_storage_service()
        # image_url = await storage_service.upload_image(...)
        
        # Mock implementation for now
        mock_image_url = f"https://example.com/profiles/{current_user['id']}/profile.jpg"
        
        # Update user profile with image URL
        user_repo = get_user_repo()
        await user_repo.update(current_user['id'], {
            "profile_image_url": mock_image_url
        })
        
        logger.info(f"Profile image uploaded for user: {current_user['id']}")
        return ImageUploadResponse(
            success=True,
            file_url=mock_image_url,
            file_name=file.filename,
            file_size=0,
            content_type=file.content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image upload failed"
        )


# =============================================================================
# USER MANAGEMENT ENDPOINTS (Admin)
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get users",
            description="Get paginated list of users (admin only)")
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    role_id: Optional[str] = Query(None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get users with pagination and filtering"""
    filters = {}
    if role_id:
        filters['role_id'] = role_id
    if is_active is not None:
        filters['is_active'] = is_active
    
    return await user_endpoint.get_items(
        page=page,
        page_size=page_size,
        search=search,
        filters=filters,
        current_user=current_user
    )


@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create user",
             description="Create a new user (admin only)")
async def create_user(
    user_data: UserCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new user"""
    return await user_endpoint.create_item(user_data, current_user)


@router.get("/{user_id}", 
            response_model=User,
            summary="Get user by ID",
            description="Get specific user by ID")
async def get_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user by ID"""
    return await user_endpoint.get_item(user_id, current_user)


@router.put("/{user_id}", 
            response_model=ApiResponse,
            summary="Update user",
            description="Update user by ID")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user by ID"""
    return await user_endpoint.update_item(user_id, update_data, current_user)


@router.delete("/{user_id}", 
               response_model=ApiResponse,
               summary="Delete user",
               description="Deactivate user by ID (soft delete)")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete user (soft delete by deactivating)"""
    return await user_endpoint.delete_item(user_id, current_user, soft_delete=True)


@router.post("/{user_id}/activate", 
             response_model=ApiResponse,
             summary="Activate user",
             description="Activate deactivated user")
async def activate_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Activate user"""
    try:
        user_repo = get_user_repo()
        
        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions
        await user_endpoint._validate_update_permissions(user, current_user)
        
        # Activate user
        await user_repo.update(user_id, {"is_active": True})
        
        logger.info(f"User activated: {user_id}")
        return ApiResponse(
            success=True,
            message="User activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user"
        )


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.get("/search/text", 
            response_model=List[User],
            summary="Search users",
            description="Search users by name, email, or phone")
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search users by text"""
    try:
        # Check permissions
        if current_user.get("role") not in ["admin", "operator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to search users"
            )
        
        users = await user_endpoint.search_users_by_text(q, current_user)
        
        logger.info(f"User search performed: '{q}' - {len(users)} results")
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


# =============================================================================
# ADDRESS MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/addresses", 
             response_model=ApiResponse,
             summary="Add user address",
             description="Add a new address for the current user")
async def add_user_address(
    address: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add a new address for the user"""
    try:
        user_repo = get_user_repo()
        
        # Get current user data
        user_data = await user_repo.get_by_id(current_user['id'])
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Add address to user's addresses
        addresses = user_data.get('addresses', [])
        address_dict = address.dict()
        address_dict['id'] = f"addr_{len(addresses) + 1}"
        addresses.append(address_dict)
        
        # Update user
        await user_repo.update(current_user['id'], {"addresses": addresses})
        
        logger.info(f"Address added for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address added successfully",
            data=address_dict
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add address"
        )


@router.get("/addresses", 
            response_model=List[UserAddress],
            summary="Get user addresses",
            description="Get all addresses for the current user")
async def get_user_addresses(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get all addresses for the user"""
    try:
        user_repo = get_user_repo()
        user_data = await user_repo.get_by_id(current_user['id'])
        
        if user_data and "addresses" in user_data:
            return [UserAddress(**addr) for addr in user_data["addresses"]]
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting addresses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get addresses"
        )


@router.put("/addresses/{address_id}", 
            response_model=ApiResponse,
            summary="Update user address",
            description="Update a specific address")
async def update_user_address(
    address_id: str,
    address_data: UserAddress,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a specific address"""
    try:
        user_repo = get_user_repo()
        
        # Get current user data
        user_data = await user_repo.get_by_id(current_user['id'])
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Find and update address
        addresses = user_data.get('addresses', [])
        address_found = False
        
        for i, addr in enumerate(addresses):
            if addr.get('id') == address_id:
                addresses[i] = address_data.dict()
                addresses[i]['id'] = address_id
                address_found = True
                break
        
        if not address_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        
        # Update user
        await user_repo.update(current_user['id'], {"addresses": addresses})
        
        logger.info(f"Address updated for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address"
        )


@router.delete("/addresses/{address_id}", 
               response_model=ApiResponse,
               summary="Delete user address",
               description="Delete a specific address")
async def delete_user_address(
    address_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a specific address"""
    try:
        user_repo = get_user_repo()
        
        # Get current user data
        user_data = await user_repo.get_by_id(current_user['id'])
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove address
        addresses = user_data.get('addresses', [])
        addresses = [addr for addr in addresses if addr.get('id') != address_id]
        
        # Update user
        await user_repo.update(current_user['id'], {"addresses": addresses})
        
        logger.info(f"Address deleted for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Address deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address"
        )


# =============================================================================
# PREFERENCES MANAGEMENT ENDPOINTS
# =============================================================================

@router.put("/preferences", 
            response_model=ApiResponse,
            summary="Update user preferences",
            description="Update user preferences and settings")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        user_repo = get_user_repo()
        
        # Update user preferences
        await user_repo.update(current_user['id'], {
            "preferences": preferences.dict()
        })
        
        logger.info(f"Preferences updated for user: {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Preferences updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/preferences", 
            response_model=UserPreferences,
            summary="Get user preferences",
            description="Get current user preferences")
async def get_user_preferences(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user preferences"""
    try:
        user_repo = get_user_repo()
        user_data = await user_repo.get_by_id(current_user['id'])
        
        if user_data and "preferences" in user_data:
            return UserPreferences(**user_data["preferences"])
        
        return UserPreferences()
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences"
        )


# =============================================================================
# SECURITY ENDPOINTS
# =============================================================================

@router.post("/change-password", 
             response_model=ApiResponse,
             summary="Change password",
             description="Change user password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change user password"""
    try:
        success = await auth_service.change_password(
            current_user['id'], 
            current_password, 
            new_password
        )
        
        if success:
            logger.info(f"Password changed for user: {current_user['id']}")
            return ApiResponse(
                success=True,
                message="Password changed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/deactivate", 
             response_model=ApiResponse,
             summary="Deactivate account",
             description="Deactivate current user account")
async def deactivate_account(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deactivate user account"""
    try:
        success = await auth_service.deactivate_user(current_user['id'])
        
        if success:
            logger.info(f"Account deactivated for user: {current_user['id']}")
            return ApiResponse(
                success=True,
                message="Account deactivated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate account"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account"
        )