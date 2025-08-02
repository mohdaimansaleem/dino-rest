"""
Validated Repository Classes
Provides repository classes with built-in validation and business rule enforcement
"""
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from app.database.firestore import (
    UserRepository, VenueRepository, WorkspaceRepository,
    get_user_repo, get_venue_repo, get_workspace_repo
)
from app.services.validation_service import get_validation_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ValidatedRepository(ABC):
    """Base class for repositories with validation"""
    
    def __init__(self, base_repository):
        self.base_repo = base_repository
        self.validation_service = get_validation_service()
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create with validation"""
        # Validate before creation
        await self._validate_create(data)
        
        # Create using base repository
        return await self.base_repo.create(data)
    
    async def update(self, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update with validation"""
        # Validate before update
        await self._validate_update(item_id, data)
        
        # Update using base repository
        return await self.base_repo.update(item_id, data)
    
    @abstractmethod
    async def _validate_create(self, data: Dict[str, Any]):
        """Validate data before creation"""
        pass
    
    @abstractmethod
    async def _validate_update(self, item_id: str, data: Dict[str, Any]):
        """Validate data before update"""
        pass
    
    # Delegate all other methods to base repository
    def __getattr__(self, name):
        return getattr(self.base_repo, name)


class ValidatedUserRepository(ValidatedRepository):
    """User repository with validation"""
    
    def __init__(self):
        super().__init__(get_user_repo())
    
    async def _validate_create(self, data: Dict[str, Any]):
        """Validate user data before creation"""
        errors = await self.validation_service.validate_user_data(data, is_update=False)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "user_creation", data
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)
    
    async def _validate_update(self, item_id: str, data: Dict[str, Any]):
        """Validate user data before update"""
        errors = await self.validation_service.validate_user_data(data, is_update=True)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Check if user exists
        existing_user = await self.base_repo.get_by_id(item_id)
        if not existing_user:
            self.validation_service.raise_validation_exception(["User not found"])
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "user_update", data, {"existing_user": existing_user}
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)


class ValidatedVenueRepository(ValidatedRepository):
    """Venue repository with validation"""
    
    def __init__(self):
        super().__init__(get_venue_repo())
    
    async def _validate_create(self, data: Dict[str, Any]):
        """Validate venue data before creation"""
        errors = await self.validation_service.validate_venue_data(data, is_update=False)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "venue_creation", data
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)
    
    async def _validate_update(self, item_id: str, data: Dict[str, Any]):
        """Validate venue data before update"""
        errors = await self.validation_service.validate_venue_data(data, is_update=True)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Check if venue exists
        existing_venue = await self.base_repo.get_by_id(item_id)
        if not existing_venue:
            self.validation_service.raise_validation_exception(["Venue not found"])
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "venue_update", data, {"existing_venue": existing_venue}
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)


class ValidatedWorkspaceRepository(ValidatedRepository):
    """Workspace repository with validation"""
    
    def __init__(self):
        super().__init__(get_workspace_repo())
    
    async def _validate_create(self, data: Dict[str, Any]):
        """Validate workspace data before creation"""
        errors = await self.validation_service.validate_workspace_data(data, is_update=False)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "workspace_creation", data
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)
    
    async def _validate_update(self, item_id: str, data: Dict[str, Any]):
        """Validate workspace data before update"""
        errors = await self.validation_service.validate_workspace_data(data, is_update=True)
        if errors:
            self.validation_service.raise_validation_exception(errors)
        
        # Check if workspace exists
        existing_workspace = await self.base_repo.get_by_id(item_id)
        if not existing_workspace:
            self.validation_service.raise_validation_exception(["Workspace not found"])
        
        # Additional business rule validation
        business_errors = await self.validation_service.validate_business_rules(
            "workspace_update", data, {"existing_workspace": existing_workspace}
        )
        if business_errors:
            self.validation_service.raise_validation_exception(business_errors)


# Global instances
_validated_user_repo = None
_validated_venue_repo = None
_validated_workspace_repo = None


def get_validated_user_repo() -> ValidatedUserRepository:
    """Get validated user repository instance"""
    global _validated_user_repo
    if _validated_user_repo is None:
        _validated_user_repo = ValidatedUserRepository()
    return _validated_user_repo


def get_validated_venue_repo() -> ValidatedVenueRepository:
    """Get validated venue repository instance"""
    global _validated_venue_repo
    if _validated_venue_repo is None:
        _validated_venue_repo = ValidatedVenueRepository()
    return _validated_venue_repo


def get_validated_workspace_repo() -> ValidatedWorkspaceRepository:
    """Get validated workspace repository instance"""
    global _validated_workspace_repo
    if _validated_workspace_repo is None:
        _validated_workspace_repo = ValidatedWorkspaceRepository()
    return _validated_workspace_repo