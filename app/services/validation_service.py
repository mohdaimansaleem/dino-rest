"""
Validation Service
Provides comprehensive validation for user data, business rules, and data integrity
"""
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status
import re
from datetime import datetime

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ValidationService:
    """Service for validating user data and business rules"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.mobile_pattern = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format
        self.password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    
    async def validate_user_data(self, user_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate user data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Email validation
        email = user_data.get('email', '').strip().lower()
        if not is_update or email:  # Required for creation, optional for update
            if not email:
                errors.append("Email is required")
            elif not self.email_pattern.match(email):
                errors.append("Invalid email format")
            else:
                # Check email uniqueness
                if not is_update:
                    existing_user = await self._check_email_exists(email)
                    if existing_user:
                        errors.append("Email already exists")
        
        # Mobile number validation
        mobile = user_data.get('mobile_number', '').strip()
        if mobile:
            if not self.mobile_pattern.match(mobile):
                errors.append("Invalid mobile number format")
            else:
                # Check mobile uniqueness
                if not is_update:
                    existing_mobile = await self._check_mobile_exists(mobile)
                    if existing_mobile:
                        errors.append("Mobile number already exists")
        
        # Password validation (only for creation or when password is being updated)
        password = user_data.get('password')
        if password:
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long")
            elif not self.password_pattern.match(password):
                errors.append("Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character")
        elif not is_update:
            errors.append("Password is required")
        
        # Confirm password validation
        confirm_password = user_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match")
        
        # Name validation
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        
        if not is_update or first_name is not None:
            if not first_name:
                errors.append("First name is required")
            elif len(first_name) < 2:
                errors.append("First name must be at least 2 characters long")
        
        if not is_update or last_name is not None:
            if not last_name:
                errors.append("Last name is required")
            elif len(last_name) < 2:
                errors.append("Last name must be at least 2 characters long")
        
        return errors
    
    async def validate_venue_data(self, venue_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate venue data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Name validation
        name = venue_data.get('name', '').strip()
        if not is_update or name is not None:
            if not name:
                errors.append("Venue name is required")
            elif len(name) < 2:
                errors.append("Venue name must be at least 2 characters long")
        
        # Email validation (if provided)
        email = venue_data.get('email', '').strip().lower()
        if email and not self.email_pattern.match(email):
            errors.append("Invalid venue email format")
        
        # Mobile validation (if provided)
        mobile = venue_data.get('mobile_number', '').strip()
        if mobile and not self.mobile_pattern.match(mobile):
            errors.append("Invalid venue mobile number format")
        
        # Location validation
        location = venue_data.get('location', {})
        if not is_update or location:
            if not isinstance(location, dict):
                errors.append("Location must be an object")
            else:
                address = location.get('address', '').strip()
                if not address:
                    errors.append("Venue address is required")
        
        return errors
    
    async def validate_workspace_data(self, workspace_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate workspace data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Display name validation
        display_name = workspace_data.get('display_name', '').strip()
        if not is_update or display_name is not None:
            if not display_name:
                errors.append("Workspace display name is required")
            elif len(display_name) < 2:
                errors.append("Workspace display name must be at least 2 characters long")
        
        # Description validation
        description = workspace_data.get('description', '').strip()
        if description and len(description) > 500:
            errors.append("Workspace description must be less than 500 characters")
        
        return errors
    
    async def validate_menu_item_data(self, menu_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate menu item data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Name validation
        name = menu_data.get('name', '').strip()
        if not is_update or name is not None:
            if not name:
                errors.append("Menu item name is required")
            elif len(name) < 2:
                errors.append("Menu item name must be at least 2 characters long")
        
        # Price validation
        price = menu_data.get('price')
        if not is_update or price is not None:
            if price is None:
                errors.append("Price is required")
            elif not isinstance(price, (int, float)) or price < 0:
                errors.append("Price must be a positive number")
        
        # Category validation
        category_id = menu_data.get('category_id', '').strip()
        if not is_update or category_id is not None:
            if not category_id:
                errors.append("Category is required")
        
        return errors
    
    async def validate_order_data(self, order_data: Dict[str, Any], is_update: bool = False) -> List[str]:
        """
        Validate order data for creation or update
        Returns list of validation errors
        """
        errors = []
        
        # Items validation
        items = order_data.get('items', [])
        if not is_update or items is not None:
            if not items:
                errors.append("Order must contain at least one item")
            elif not isinstance(items, list):
                errors.append("Order items must be a list")
            else:
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append(f"Order item {i+1} must be an object")
                        continue
                    
                    if not item.get('menu_item_id'):
                        errors.append(f"Order item {i+1} must have a menu_item_id")
                    
                    quantity = item.get('quantity')
                    if not isinstance(quantity, int) or quantity <= 0:
                        errors.append(f"Order item {i+1} quantity must be a positive integer")
        
        # Table validation
        table_id = order_data.get('table_id', '').strip()
        if not is_update or table_id is not None:
            if not table_id:
                errors.append("Table ID is required")
        
        return errors
    
    async def _check_email_exists(self, email: str) -> bool:
        """Check if email already exists in the system"""
        try:
            from app.database.firestore import get_user_repo
            user_repo = get_user_repo()
            existing_user = await user_repo.get_by_email(email)
            return existing_user is not None
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
    
    async def _check_mobile_exists(self, mobile: str) -> bool:
        """Check if mobile number already exists in the system"""
        try:
            from app.database.firestore import get_user_repo
            user_repo = get_user_repo()
            existing_user = await user_repo.get_by_mobile(mobile)
            return existing_user is not None
        except Exception as e:
            logger.error(f"Error checking mobile existence: {e}")
            return False
    
    def raise_validation_exception(self, errors: List[str]):
        """Raise HTTPException with validation errors"""
        if errors:
            error_message = "; ".join(errors)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation failed: {error_message}"
            )
    
    def validate_email_format(self, email: str) -> bool:
        """Validate email format"""
        return bool(self.email_pattern.match(email.strip().lower()))
    
    def validate_mobile_format(self, mobile: str) -> bool:
        """Validate mobile number format"""
        return bool(self.mobile_pattern.match(mobile.strip()))
    
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength"""
        return bool(self.password_pattern.match(password))
    
    async def validate_business_rules(self, entity_type: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> List[str]:
        """
        Validate business rules for different entity types
        """
        errors = []
        context = context or {}
        
        if entity_type == "user_role_assignment":
            # Validate role assignment rules
            role_name = data.get('role_name', '').lower()
            venue_id = data.get('venue_id')
            
            if role_name in ['admin', 'operator'] and not venue_id:
                errors.append("Admin and Operator roles require a venue assignment")
            
            # Check if user already has a role in this venue
            user_id = data.get('user_id')
            if user_id and venue_id:
                existing_role = await self._check_user_venue_role(user_id, venue_id)
                if existing_role:
                    errors.append(f"User already has role '{existing_role}' in this venue")
        
        elif entity_type == "venue_capacity":
            # Validate venue capacity rules
            max_tables = data.get('max_tables', 0)
            current_tables = context.get('current_tables', 0)
            
            if max_tables < current_tables:
                errors.append(f"Cannot reduce max tables below current table count ({current_tables})")
        
        elif entity_type == "order_timing":
            # Validate order timing rules
            venue_id = data.get('venue_id')
            if venue_id:
                is_open = await self._check_venue_operating_hours(venue_id)
                if not is_open:
                    errors.append("Venue is currently closed for orders")
        
        return errors
    
    async def _check_user_venue_role(self, user_id: str, venue_id: str) -> Optional[str]:
        """Check if user already has a role in the venue"""
        try:
            from app.database.firestore import get_user_repo
            user_repo = get_user_repo()
            user = await user_repo.get_by_id(user_id)
            
            if user and user.get('venue_id') == venue_id:
                # Get role name from role_id
                role_id = user.get('role_id')
                if role_id:
                    from app.database.firestore import get_role_repo
                    role_repo = get_role_repo()
                    role = await role_repo.get_by_id(role_id)
                    return role.get('name') if role else None
            
            return None
        except Exception as e:
            logger.error(f"Error checking user venue role: {e}")
            return None
    
    async def _check_venue_operating_hours(self, venue_id: str) -> bool:
        """Check if venue is currently open"""
        try:
            from app.database.firestore import get_venue_repo
            venue_repo = get_venue_repo()
            venue = await venue_repo.get_by_id(venue_id)
            
            if not venue or not venue.get('is_active'):
                return False
            
            # Simple check - in a real implementation, you'd check operating hours
            # against current time and day of week
            operating_hours = venue.get('operating_hours', [])
            if not operating_hours:
                return True  # Assume open if no hours specified
            
            # For now, just return True - implement proper time checking as needed
            return True
            
        except Exception as e:
            logger.error(f"Error checking venue operating hours: {e}")
            return False


# Global instance
_validation_service = None


def get_validation_service() -> ValidationService:
    """Get validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service