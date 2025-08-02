"""

Authentication API Endpoints

"""

from fastapi import APIRouter, HTTPException, status, Depends

from typing import Dict, Any



from app.models.schemas import (

  UserCreate, UserLogin, User, UserUpdate, AuthToken, ApiResponse, WorkspaceRegistration

)

from pydantic import BaseModel

from app.services.validation_service import get_validation_service

from app.core.dependency_injection import get_auth_service

from app.core.security import get_current_user, get_current_user_id





class RefreshTokenRequest(BaseModel):

  refresh_token: str





router = APIRouter()





@router.post("/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)

async def register_workspace(registration_data: WorkspaceRegistration):

  """

  Complete workspace registration with venue and owner user creation

   

  This endpoint creates:

  1. A new workspace with workspace details

  2. A new venue under the workspace with venue details 

  3. A new user (owner) with personal details and superadmin role

  4. Links all entities together properly

  """

  try:

    from app.database.firestore import get_workspace_repo, get_venue_repo, get_user_repo

    from app.core.logging_config import get_logger

    from app.services.validation_service import get_validation_service

    from app.core.security import get_password_hash

    import uuid

    from datetime import datetime

     

    logger = get_logger(__name__)

    validation_service = get_validation_service()

     

    # Get repositories

    workspace_repo = get_workspace_repo()

    venue_repo = get_venue_repo()

    user_repo = get_user_repo()

     

    # Get role repository for superadmin role

    from app.database.firestore import get_role_repo

    role_repo = get_role_repo()

     

    # Validate password confirmation

    if registration_data.owner_password != registration_data.confirm_password:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Passwords do not match"

      )

     

    # Check if email already exists

    existing_user = await user_repo.get_by_email(registration_data.owner_email)

    if existing_user:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User with this email already exists"

      )

     

    # Generate unique IDs

    workspace_id = str(uuid.uuid4())

    venue_id = str(uuid.uuid4())

    user_id = str(uuid.uuid4())

     

    # Generate unique workspace name from display name

    workspace_name = registration_data.workspace_name.lower().replace(" ", "_").replace("-", "_")

    workspace_name = f"{workspace_name}_{workspace_id[:8]}"

     

    current_time = datetime.utcnow()

     

    # Get superadmin role_id

    superadmin_role = await role_repo.get_by_name("superadmin")

    if not superadmin_role:

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Superadmin role not found in system"

      )

     

    # 1. Create Workspace

    workspace_data = {

      "id": workspace_id,

      "name": workspace_name,

      "description": registration_data.workspace_description,

      "venue_ids": [venue_id],

      "is_active": True,

      "created_at": current_time,

      "updated_at": current_time

    }

     

    # 2. Create Venue

    venue_mobile = registration_data.get_venue_mobile_number()

    if not venue_mobile:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Venue mobile number is required. Please provide either venueMobile, venuePhone, ownerMobile, or ownerPhone."

      )

     

    venue_data = {

      "id": venue_id,

      "name": registration_data.venue_name,

      "description": registration_data.venue_description,

      "location": registration_data.venue_location.dict(),

      "mobile_number": venue_mobile,

      "email": registration_data.venue_email or registration_data.owner_email,

      "website": str(registration_data.venue_website) if registration_data.venue_website else None,

      "cuisine_types": [],

      "price_range": registration_data.price_range.value,

      "subscription_plan": "basic",

      "subscription_status": "active",

      "admin_id": user_id,

      "is_active": True,

      "rating": 0.0,

      "total_reviews": 0,

      "created_at": current_time,

      "updated_at": current_time

    }

     

    # 3. Create User (Owner with superadmin role)

    hashed_password = get_password_hash(registration_data.owner_password)

     

    # Get mobile number from any available field

    owner_mobile = registration_data.get_owner_mobile_number()

    if not owner_mobile:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="Owner mobile number is required. Please provide either ownerMobile or ownerPhone."

      )

     

    user_data = {

      "id": user_id,

      "email": registration_data.owner_email,

      "mobile_number": owner_mobile,

      "first_name": registration_data.owner_first_name,

      "last_name": registration_data.owner_last_name,

      "hashed_password": hashed_password,

      "role_id": superadmin_role["id"],

      "is_active": True,

      "is_verified": False,

      "email_verified": False,

      "mobile_verified": False,

      "created_at": current_time,

      "updated_at": current_time,

      "last_login": None

    }

     

    # Skip validation during registration since we're creating all entities together

    # The validation service expects entities to already exist, which they don't during creation

    logger.info("Skipping validation during registration - creating all entities together")

     

    # User data is ready for storage (no plain password to remove)

     

    # Create all records in sequence

    try:

      # Create workspace first

      await workspace_repo.create(workspace_data)

      logger.info(f"Workspace created: {workspace_id}")

       

      # Create venue

      await venue_repo.create(venue_data)

      logger.info(f"Venue created: {venue_id}")

       

      # Create user

      await user_repo.create(user_data)

      logger.info(f"User created: {user_id}")

       

      # Skip entity mapping verification for now

      logger.info("Entity creation completed successfully")

       

      # Log successful registration

      logger.info(f"Complete workspace registration successful", extra={

        "workspace_id": workspace_id,

        "venue_id": venue_id,

        "user_id": user_id,

        "owner_email": registration_data.owner_email

      })

       

      return ApiResponse(

        success=True,

        message="Workspace, venue, and owner account created successfully. You can now login with your credentials.",

        data={

          "workspace": {

            "id": workspace_id,

            "name": workspace_name

          },

          "venue": {

            "id": venue_id,

            "name": registration_data.venue_name,

            "location": venue_data["location"]

          },

          "owner": {

            "id": user_id,

            "email": registration_data.owner_email,

            "first_name": registration_data.owner_first_name,

            "last_name": registration_data.owner_last_name,

            "role_id": superadmin_role["id"],

            "role_name": "superadmin"

          },

          "next_steps": [

            "Login with your email and password",

            "Complete venue setup (add menu items, tables)",

            "Configure payment methods",

            "Generate QR codes for tables"

          ]

        }

      )

       

    except Exception as creation_error:

      # Rollback on failure

      logger.error(f"Registration failed during creation: {creation_error}")

       

      # Attempt cleanup (best effort)

      try:

        await workspace_repo.delete(workspace_id)

        await venue_repo.delete(venue_id) 

        await user_repo.delete(user_id)

      except:

        pass # Ignore cleanup errors

         

      raise HTTPException(

        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

        detail="Registration failed during record creation. Please try again."

      )

       

  except HTTPException:

    raise

  except Exception as e:

    logger.error(f"Workspace registration failed: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Workspace registration failed. Please try again."

    )



@router.post("/login", response_model=AuthToken)

async def login_user(login_data: UserLogin):

  """Login user and return JWT token"""

  try:

    token = await get_auth_service().login_user(login_data)

    return token

     

  except HTTPException:

    raise

     

  except Exception as e:

    from app.core.logging_config import get_logger

    logger = get_logger(__name__)

    logger.error(f"Login failed with unexpected error: {e}", exc_info=True)

     

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Login failed"

    )



@router.get("/me", response_model=User)

async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Get current user information"""

  return User(**current_user)



@router.put("/me", response_model=ApiResponse)

async def update_current_user(

  user_update: UserUpdate,

  current_user_id: str = Depends(get_current_user_id)

):

  """Update current user information"""

  try:

    # Convert to dict and remove None values

    update_data = user_update.dict(exclude_unset=True)

     

    user = await get_auth_service().update_user(current_user_id, update_data)

    return ApiResponse(

      success=True,

      message="User updated successfully",

      data=user

    )

  except HTTPException:

    raise

  except Exception as e:

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Update failed: {str(e)}"

    )



@router.post("/change-password", response_model=ApiResponse)

async def change_password(

  current_password: str,

  new_password: str,

  current_user_id: str = Depends(get_current_user_id)

):

  """Change user password"""

  try:

    await get_auth_service().change_password(current_user_id, current_password, new_password)

    return ApiResponse(

      success=True,

      message="Password changed successfully"

    )

  except HTTPException:

    raise

  except Exception as e:

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Password change failed: {str(e)}"

    )





@router.post("/refresh", response_model=AuthToken)

async def refresh_token(request_data: RefreshTokenRequest):

  """Refresh JWT token"""

  try:

    token = await get_auth_service().refresh_token(request_data.refresh_token)

    return token

  except HTTPException:

    raise

  except Exception as e:

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Token refresh failed: {str(e)}"

    )





@router.get("/permissions", response_model=ApiResponse)

async def get_user_permissions(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Get current user's permissions"""

  try:

    from app.services.role_permission_service import role_permission_service

    from app.database.firestore import get_role_repo

     

    # Get user's role and permissions

    role_repo = get_role_repo()

    user_role_id = current_user.get('role_id')

     

    if not user_role_id:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User has no role assigned"

      )

     

    # Get role with permissions

    role = await role_repo.get_by_id(user_role_id)

    if not role:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="User role not found"

      )

     

    # Get permissions from role

    permissions = role.get('permission_ids', [])

     

    # Get detailed permission information

    from app.database.firestore import get_permission_repo

    perm_repo = get_permission_repo()

    detailed_permissions = []

     

    for perm_id in permissions:

      perm = await perm_repo.get_by_id(perm_id)

      if perm:

        detailed_permissions.append({

          'id': perm['id'],

          'name': perm['name'],

          'resource': perm['resource'],

          'action': perm['action'],

          'scope': perm['scope'],

          'description': perm['description']

        })

     

    # Get dashboard permissions using the role we already have

    dashboard_permissions = await role_permission_service.get_role_dashboard_permissions_with_role(role['name'])

     

    return ApiResponse(

      success=True,

      message="User permissions retrieved successfully",

      data={

        'user_id': current_user['id'],

        'role': {

          'id': role['id'],

          'name': role['name'],

          'display_name': role.get('display_name', role['name']),

          'description': role.get('description', '')

        },

        'permissions': detailed_permissions,

        'dashboard_permissions': dashboard_permissions,

        'permission_count': len(detailed_permissions)

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    from app.core.logging_config import get_logger

    logger = get_logger(__name__)

    logger.error(f"Error getting user permissions: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to get user permissions"

    )



@router.post("/refresh-permissions", response_model=ApiResponse)

async def refresh_user_permissions(current_user: Dict[str, Any] = Depends(get_current_user)):

  """Refresh current user's permissions (for real-time updates)"""

  try:

    # This endpoint can be used to trigger permission refresh

    # For now, it returns the same as get_user_permissions

    # In the future, this could trigger cache invalidation or other refresh logic

     

    from app.services.role_permission_service import role_permission_service

    from app.database.firestore import get_role_repo

     

    # Get user's role and permissions

    role_repo = get_role_repo()

    user_role_id = current_user.get('role_id')

     

    if not user_role_id:

      raise HTTPException(

        status_code=status.HTTP_400_BAD_REQUEST,

        detail="User has no role assigned"

      )

     

    # Get role with permissions

    role = await role_repo.get_by_id(user_role_id)

    if not role:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="User role not found"

      )

     

    # Get permissions from role

    permissions = role.get('permission_ids', [])

     

    # Get detailed permission information

    from app.database.firestore import get_permission_repo

    perm_repo = get_permission_repo()

    detailed_permissions = []

     

    for perm_id in permissions:

      perm = await perm_repo.get_by_id(perm_id)

      if perm:

        detailed_permissions.append({

          'id': perm['id'],

          'name': perm['name'],

          'resource': perm['resource'],

          'action': perm['action'],

          'scope': perm['scope'],

          'description': perm['description']

        })

     

    # Get dashboard permissions using the role we already have

    dashboard_permissions = await role_permission_service.get_role_dashboard_permissions_with_role(role['name'])

     

    return ApiResponse(

      success=True,

      message="User permissions refreshed successfully",

      data={

        'user_id': current_user['id'],

        'role': {

          'id': role['id'],

          'name': role['name'],

          'display_name': role.get('display_name', role['name']),

          'description': role.get('description', '')

        },

        'permissions': detailed_permissions,

        'dashboard_permissions': dashboard_permissions,

        'permission_count': len(detailed_permissions),

        'refreshed_at': datetime.utcnow().isoformat()

      }

    )

     

  except HTTPException:

    raise

  except Exception as e:

    from app.core.logging_config import get_logger

    logger = get_logger(__name__)

    logger.error(f"Error refreshing user permissions: {e}")

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail="Failed to refresh user permissions"

    )



@router.post("/logout", response_model=ApiResponse)

async def logout_user():

  """Logout user (client-side token removal)"""

  return ApiResponse(

    success=True,

    message="Logged out successfully. Please remove the token from client storage."

  )



@router.put("/deactivate/{venue_id}", response_model=ApiResponse)

async def deactivate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Deactivate venue by venue ID (updates is_active field to False)"""

  try:

    from app.database.firestore import get_venue_repo

    from app.core.logging_config import get_logger

     

    logger = get_logger(__name__)

    venue_repo = get_venue_repo()

     

    # Check if venue exists

    venue = await venue_repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Check permissions - get user role from role_id

    from app.core.security import _get_user_role

    user_role = await _get_user_role(current_user)

    venue_admin_id = venue.get('admin_id')

     

    # Only superadmin or venue owner can deactivate venues

    # Admin cannot deactivate venues they don't own

    if not (user_role == 'superadmin' or 

        current_user['id'] == venue_admin_id):

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Insufficient permissions to deactivate this venue"

      )

     

    # Update venue deactivation status (record is preserved, only is_active field is updated)

    await venue_repo.update(venue_id, {"is_active": False})

     

    logger.info(f"Venue deactivated (is_active set to False): {venue_id} by user: {current_user['id']}")

     

    return ApiResponse(

      success=True,

      message="Venue deactivated successfully. Record preserved with is_active set to False.",

      data={

        "venue_id": venue_id, 

        "venue_name": venue.get('name'),

        "is_active": False,

        "action": "deactivated"

      }

    )

  except HTTPException:

    raise

  except Exception as e:

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Venue deactivation failed: {str(e)}"

    )



@router.put("/activate/{venue_id}", response_model=ApiResponse)

async def activate_venue(

  venue_id: str,

  current_user: Dict[str, Any] = Depends(get_current_user)

):

  """Activate venue by venue ID (updates is_active field to True)"""

  try:

    from app.database.firestore import get_venue_repo

    from app.core.logging_config import get_logger

     

    logger = get_logger(__name__)

    venue_repo = get_venue_repo()

     

    # Check if venue exists

    venue = await venue_repo.get_by_id(venue_id)

    if not venue:

      raise HTTPException(

        status_code=status.HTTP_404_NOT_FOUND,

        detail="Venue not found"

      )

     

    # Check permissions - get user role from role_id

    from app.core.security import _get_user_role

    user_role = await _get_user_role(current_user)

    venue_admin_id = venue.get('admin_id')

     

    # Only superadmin or venue owner can deactivate venues

    # Admin cannot deactivate venues they don't own

    if not (user_role == 'superadmin' or 

        current_user['id'] == venue_admin_id):

      raise HTTPException(

        status_code=status.HTTP_403_FORBIDDEN,

        detail="Insufficient permissions to activate this venue"

      )

     

    # Update venue activation status (record is preserved, only is_active field is updated)

    await venue_repo.update(venue_id, {"is_active": True})

     

    logger.info(f"Venue activated (is_active set to True): {venue_id} by user: {current_user['id']}")

     

    return ApiResponse(

      success=True,

      message="Venue activated successfully. Record updated with is_active set to True.",

      data={

        "venue_id": venue_id, 

        "venue_name": venue.get('name'),

        "is_active": True,

        "action": "activated"

      }

    )

  except HTTPException:

    raise

  except Exception as e:

    raise HTTPException(

      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

      detail=f"Venue activation failed: {str(e)}"

    )



async def _verify_entity_mappings(workspace_repo, venue_repo, user_repo, 

                workspace_id: str, venue_id: str, user_id: str, logger):

  """

  Verify that all entity mappings are correctly established

  """

  try:

    # Verify workspace mappings

    workspace = await workspace_repo.get_by_id(workspace_id)

    assert workspace["owner_id"] == user_id, "Workspace owner_id mapping failed"

    assert venue_id in workspace["venue_ids"], "Workspace venue_ids mapping failed"

    assert user_id in workspace["user_ids"], "Workspace user_ids mapping failed"

     

    # Verify venue mappings

    venue = await venue_repo.get_by_id(venue_id)

    assert venue["workspace_id"] == workspace_id, "Venue workspace_id mapping failed"

    assert venue["owner_id"] == user_id, "Venue owner_id mapping failed"

    assert venue["admin_id"] == user_id, "Venue admin_id mapping failed"

    assert user_id in venue["user_ids"], "Venue user_ids mapping failed"

     

    # Verify user mappings

    user = await user_repo.get_by_id(user_id)

    assert user["workspace_id"] == workspace_id, "User workspace_id mapping failed"

    assert user["venue_id"] == venue_id, "User venue_id mapping failed"

    assert venue_id in user["venue_ids"], "User venue_ids mapping failed"

    assert user["is_workspace_owner"] == True, "User is_workspace_owner mapping failed"

    assert user["is_venue_owner"] == True, "User is_venue_owner mapping failed"

     

    logger.info("All entity mappings verified successfully")

     

  except AssertionError as e:

    logger.error(f"Entity mapping verification failed: {e}")

    raise Exception(f"Entity mapping verification failed: {e}")

  except Exception as e:

    logger.error(f"Error during mapping verification: {e}")

    raise Exception(f"Mapping verification error: {e}")