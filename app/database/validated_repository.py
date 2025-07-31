"""
Validated Repository Classes
Enhanced repositories with automatic validation
"""
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.database.firestore import FirestoreRepository
from app.services.validation_service import get_validation_service
from app.core.logging_config import LoggerMixin


class ValidatedFirestoreRepository(FirestoreRepository):
    """Enhanced Firestore repository with automatic validation"""
    
    def __init__(self, collection_name: str, enable_validation: bool = True):
        super().__init__(collection_name)
        self.enable_validation = enable_validation
        self.validation_service = get_validation_service()
    
    async def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Create a new document with validation"""
        if self.enable_validation:
            # Validate data before creation
            errors = await self.validation_service.validate_collection_data(
                self.collection_name, data, is_update=False
            )
            
            if errors:
                self.validation_service.raise_validation_exception(errors)
        
        # Call parent create method
        return await super().create(data, doc_id)
    
    async def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update document by ID with validation"""
        if self.enable_validation:
            # Validate data before update
            errors = await self.validation_service.validate_collection_data(
                self.collection_name, data, is_update=True, item_id=doc_id
            )
            
            if errors:
                self.validation_service.raise_validation_exception(errors)
        
        # Call parent update method
        return await super().update(doc_id, data)
    
    async def create_or_update(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Create or update document with validation"""
        if doc_id:
            # Check if document exists
            existing = await self.get_by_id(doc_id)
            if existing:
                await self.update(doc_id, data)
                return doc_id
        
        return await self.create(data, doc_id)
    
    async def validate_data(self, data: Dict[str, Any], is_update: bool = False, 
                          item_id: str = None) -> Dict[str, Any]:
        """Validate data without saving"""
        errors = await self.validation_service.validate_collection_data(
            self.collection_name, data, is_update=is_update, item_id=item_id
        )
        
        return self.validation_service.format_validation_errors(errors)


class ValidatedUserRepository(ValidatedFirestoreRepository):
    """Validated user repository"""
    
    def __init__(self):
        super().__init__("users", enable_validation=True)
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        results = await self.query([("email", "==", email)])
        return results[0] if results else None
    
    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        results = await self.query([("phone", "==", phone)])
        return results[0] if results else None
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get users by workspace ID"""
        return await self.query([("workspace_id", "==", workspace_id)])
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get users by venue ID"""
        return await self.query([("venue_id", "==", venue_id)])
    
    async def get_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get users by role ID"""
        return await self.query([("role_id", "==", role_id)])
    
    async def create_user_with_role_validation(self, data: Dict[str, Any], 
                                             doc_id: Optional[str] = None) -> str:
        """Create user with additional role validation"""
        # Additional business logic validation
        if 'role_id' in data and data['role_id']:
            # Check if role exists and is appropriate for the workspace/venue
            role_repo = ValidatedRoleRepository()
            role = await role_repo.get_by_id(data['role_id'])
            
            if not role:
                from app.services.validation_service import ValidationError
                error = ValidationError("role_id", data['role_id'], "existing role", 
                                      f"Role with ID {data['role_id']} does not exist")
                self.validation_service.raise_validation_exception([error])
        
        return await self.create(data, doc_id)


class ValidatedWorkspaceRepository(ValidatedFirestoreRepository):
    """Validated workspace repository"""
    
    def __init__(self):
        super().__init__("workspaces", enable_validation=True)
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workspace by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_by_owner(self, owner_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by owner ID"""
        results = await self.query([("owner_id", "==", owner_id)])
        return results[0] if results else None
    
    async def create_workspace_with_validation(self, data: Dict[str, Any], 
                                             doc_id: Optional[str] = None) -> str:
        """Create workspace with additional validation"""
        # Generate unique workspace name if not provided
        if 'name' not in data and 'display_name' in data:
            import re
            import uuid
            display_name = data['display_name']
            name = re.sub(r'[^a-zA-Z0-9\s]', '', display_name.lower())
            name = re.sub(r'\s+', '_', name.strip())
            unique_suffix = str(uuid.uuid4())[:8]
            data['name'] = f"{name}_{unique_suffix}"
        
        return await self.create(data, doc_id)


class ValidatedVenueRepository(ValidatedFirestoreRepository):
    """Validated venue repository"""
    
    def __init__(self):
        super().__init__("venues", enable_validation=True)
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get venues by workspace ID"""
        return await self.query([("workspace_id", "==", workspace_id)])
    
    async def get_by_admin(self, admin_id: str) -> List[Dict[str, Any]]:
        """Get venues by admin ID"""
        return await self.query([("admin_id", "==", admin_id)])
    
    async def get_active_venues(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all active venues"""
        return await self.query([("is_active", "==", True)], limit=limit)


class ValidatedRoleRepository(ValidatedFirestoreRepository):
    """Validated role repository"""
    
    def __init__(self):
        super().__init__("roles", enable_validation=True)
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_system_roles(self) -> List[Dict[str, Any]]:
        """Get all system roles"""
        return await self.query([("is_system_role", "==", True)])


class ValidatedPermissionRepository(ValidatedFirestoreRepository):
    """Validated permission repository"""
    
    def __init__(self):
        super().__init__("permissions", enable_validation=True)
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        results = await self.query([("name", "==", name)])
        return results[0] if results else None
    
    async def get_system_permissions(self) -> List[Dict[str, Any]]:
        """Get all system permissions"""
        return await self.query([("is_system_permission", "==", True)])


class ValidatedMenuItemRepository(ValidatedFirestoreRepository):
    """Validated menu item repository"""
    
    def __init__(self):
        super().__init__("menu_items", enable_validation=True)
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get menu items by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at")
    
    async def get_by_category(self, venue_id: str, category_id: str) -> List[Dict[str, Any]]:
        """Get menu items by venue and category"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("category_id", "==", category_id)
        ], order_by="created_at")


class ValidatedMenuCategoryRepository(ValidatedFirestoreRepository):
    """Validated menu category repository"""
    
    def __init__(self):
        super().__init__("menu_categories", enable_validation=True)
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get menu categories by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at")


class ValidatedTableRepository(ValidatedFirestoreRepository):
    """Validated table repository"""
    
    def __init__(self):
        super().__init__("tables", enable_validation=True)
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get tables by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="table_number")
    
    async def get_by_table_number(self, venue_id: str, table_number: int) -> Optional[Dict[str, Any]]:
        """Get table by venue and table number"""
        results = await self.query([
            ("venue_id", "==", venue_id),
            ("table_number", "==", table_number)
        ])
        return results[0] if results else None
    
    async def get_by_qr_code(self, qr_code: str) -> Optional[Dict[str, Any]]:
        """Get table by QR code"""
        results = await self.query([("qr_code", "==", qr_code)])
        return results[0] if results else None


class ValidatedOrderRepository(ValidatedFirestoreRepository):
    """Validated order repository"""
    
    def __init__(self):
        super().__init__("orders", enable_validation=True)
    
    async def get_by_venue(self, venue_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get orders by venue ID"""
        return await self.query([("venue_id", "==", venue_id)], order_by="created_at", limit=limit)
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get orders by venue and status"""
        return await self.query([
            ("venue_id", "==", venue_id),
            ("status", "==", status)
        ], order_by="created_at")
    
    async def get_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get orders by customer ID"""
        return await self.query([("customer_id", "==", customer_id)], order_by="created_at")


class ValidatedCustomerRepository(ValidatedFirestoreRepository):
    """Validated customer repository"""
    
    def __init__(self):
        super().__init__("customers", enable_validation=True)
    
    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get customer by phone"""
        results = await self.query([("phone", "==", phone)])
        return results[0] if results else None
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get customer by email"""
        results = await self.query([("email", "==", email)])
        return results[0] if results else None


# Repository instances with validation
validated_user_repo = ValidatedUserRepository()
validated_workspace_repo = ValidatedWorkspaceRepository()
validated_venue_repo = ValidatedVenueRepository()
validated_role_repo = ValidatedRoleRepository()
validated_permission_repo = ValidatedPermissionRepository()
validated_menu_item_repo = ValidatedMenuItemRepository()
validated_menu_category_repo = ValidatedMenuCategoryRepository()
validated_table_repo = ValidatedTableRepository()
validated_order_repo = ValidatedOrderRepository()
validated_customer_repo = ValidatedCustomerRepository()


# Getter functions
def get_validated_user_repo() -> ValidatedUserRepository:
    """Get validated user repository instance"""
    return validated_user_repo


def get_validated_workspace_repo() -> ValidatedWorkspaceRepository:
    """Get validated workspace repository instance"""
    return validated_workspace_repo


def get_validated_venue_repo() -> ValidatedVenueRepository:
    """Get validated venue repository instance"""
    return validated_venue_repo


def get_validated_role_repo() -> ValidatedRoleRepository:
    """Get validated role repository instance"""
    return validated_role_repo


def get_validated_permission_repo() -> ValidatedPermissionRepository:
    """Get validated permission repository instance"""
    return validated_permission_repo


def get_validated_menu_item_repo() -> ValidatedMenuItemRepository:
    """Get validated menu item repository instance"""
    return validated_menu_item_repo


def get_validated_menu_category_repo() -> ValidatedMenuCategoryRepository:
    """Get validated menu category repository instance"""
    return validated_menu_category_repo


def get_validated_table_repo() -> ValidatedTableRepository:
    """Get validated table repository instance"""
    return validated_table_repo


def get_validated_order_repo() -> ValidatedOrderRepository:
    """Get validated order repository instance"""
    return validated_order_repo


def get_validated_customer_repo() -> ValidatedCustomerRepository:
    """Get validated customer repository instance"""
    return validated_customer_repo