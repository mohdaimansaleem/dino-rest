"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id: str = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Get current user from database"""
    from app.database.firestore import get_user_repo
    
    user_repo = get_user_repo()
    user_data = await user_repo.get_by_id(user_id)
    
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data


async def get_current_admin_user(current_user = Depends(get_current_user)):
    """Get current admin user (role-based access control)"""
    # Get user role from role_id
    user_role = await _get_user_role(current_user)
    
    if user_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user


async def _get_user_role(user_data: Dict[str, Any]) -> str:
    """Get user role from role_id"""
    role_id = user_data.get("role_id")
    if not role_id:
        return "operator"  # Default role
    
    try:
        from app.database.firestore import get_role_repo
        role_repo = get_role_repo()
        role = await role_repo.get_by_id(role_id)
        
        if role:
            return role.get("name", "operator")
    except Exception as e:
        # Log error but don't fail - return default role
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get user role: {e}")
    
    return "operator"


def verify_cafe_ownership(cafe_owner_id: str, current_user_id: str) -> bool:
    """Verify if current user owns the cafe"""
    return cafe_owner_id == current_user_id


async def verify_venue_access(venue_id: str, current_user: Dict[str, Any]) -> bool:
    """Verify if current user has access to venue"""
    from app.database.firestore import get_venue_repo
    
    venue_repo = get_venue_repo()
    venue = await venue_repo.get_by_id(venue_id)
    
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
    
    # Get user role
    user_role = await _get_user_role(current_user)
    
    # SuperAdmin and Admin can access all venues
    if user_role in ["superadmin", "admin"]:
        return True
    
    # Venue owner can only access their own venues
    if not verify_cafe_ownership(venue.get("admin_id", ""), current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this venue"
        )
    
    return True


async def verify_workspace_access(workspace_id: str, current_user: Dict[str, Any]) -> bool:
    """Verify if current user has access to workspace"""
    from app.database.firestore import get_workspace_repo
    
    workspace_repo = get_workspace_repo()
    workspace = await workspace_repo.get_by_id(workspace_id)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Get user role
    user_role = await _get_user_role(current_user)
    
    # SuperAdmin can access all workspaces
    if user_role == "superadmin":
        return True
    
    # Admin and operator roles can access workspaces
    # TODO: Implement proper workspace-user relationship logic
    if user_role in ["admin", "operator"]:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions to access this workspace"
    )
    
    return True