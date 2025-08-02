"""
Workspace Onboarding Service
Handles complete workspace setup including venues, users, and initial configuration
"""
from typing import Dict, Any
from datetime import datetime
import uuid

from app.core.logging_config import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


class WorkspaceOnboardingService:
    """Service for handling workspace onboarding"""
    
    async def create_workspace_with_venue(self, workspace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a complete workspace with venue and admin user
        """
        try:
            from app.database.firestore import get_workspace_repo, get_venue_repo, get_user_repo
            from app.core.security import get_password_hash
            
            workspace_repo = get_workspace_repo()
            venue_repo = get_venue_repo()
            user_repo = get_user_repo()
            
            # Generate IDs
            workspace_id = str(uuid.uuid4())
            venue_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            
            current_time = datetime.utcnow()
            
            # Create workspace
            workspace = {
                "id": workspace_id,
                "name": workspace_data.get("workspace_name", "").lower().replace(" ", "_"),
                "display_name": workspace_data.get("workspace_name", ""),
                "description": workspace_data.get("description", ""),
                "business_type": workspace_data.get("business_type", "restaurant"),
                "venue_ids": [venue_id],
                "owner_id": user_id,
                "is_active": True,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # Create venue
            venue = {
                "id": venue_id,
                "name": workspace_data.get("venue_name", ""),
                "description": workspace_data.get("venue_description", ""),
                "workspace_id": workspace_id,
                "owner_id": user_id,
                "admin_id": user_id,
                "location": workspace_data.get("location", {}),
                "mobile_number": workspace_data.get("mobile_number", ""),
                "email": workspace_data.get("email", ""),
                "is_active": True,
                "rating": 0.0,
                "total_reviews": 0,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # Create admin user
            owner_data = workspace_data.get("owner_details", {})
            user = {
                "id": user_id,
                "email": owner_data.get("email", ""),
                "mobile_number": owner_data.get("mobile_number", ""),
                "first_name": owner_data.get("first_name", ""),
                "last_name": owner_data.get("last_name", ""),
                "hashed_password": get_password_hash(owner_data.get("password", "")),
                "role_id": "superadmin_role_id",  # This should be fetched from roles
                "workspace_id": workspace_id,
                "venue_id": venue_id,
                "is_active": True,
                "is_verified": False,
                "email_verified": False,
                "mobile_verified": False,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # Create all entities
            await workspace_repo.create(workspace)
            await venue_repo.create(venue)
            await user_repo.create(user)
            
            logger.info(f"Workspace onboarding completed: {workspace_id}")
            
            return {
                "workspace_id": workspace_id,
                "venue_id": venue_id,
                "user_id": user_id,
                "workspace": workspace,
                "venue": venue,
                "user": {k: v for k, v in user.items() if k != "hashed_password"}
            }
            
        except Exception as e:
            logger.error(f"Workspace onboarding failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workspace onboarding failed"
            )


# Global instance
workspace_onboarding_service = WorkspaceOnboardingService()


def get_workspace_onboarding_service() -> WorkspaceOnboardingService:
    """Get workspace onboarding service instance"""
    return workspace_onboarding_service