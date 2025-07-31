"""
Comprehensive Validation Service
Ensures data consistency and integrity across all collections
"""
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, date
from fastapi import HTTPException, status
import re
from enum import Enum

from app.models.schemas import (
    UserRole, BusinessType, SubscriptionPlan, SubscriptionStatus, VenueStatus,
    WorkspaceStatus, OrderStatus, PaymentStatus, PaymentMethod, PaymentGateway,
    OrderType, OrderSource, TableStatus, NotificationType, TransactionType,
    FeedbackType, PriceRange, SpiceLevel, Gender, Priority, RecipientType,
    CustomerType
)
from app.database.firestore import (
    get_user_repo, get_workspace_repo, get_venue_repo, get_role_repo,
    get_permission_repo, get_menu_category_repo, get_menu_item_repo,
    get_table_repo, get_customer_repo, get_order_repo
)
from app.core.logging_config import LoggerMixin


class ValidationError(Exception):
    """Custom validation error with detailed information"""
    def __init__(self, field: str, value: Any, expected: str, message: str = None):
        self.field = field
        self.value = value
        self.expected = expected
        self.message = message or f"Invalid value for {field}: {value}. Expected: {expected}"
        super().__init__(self.message)


class ValidationService(LoggerMixin):
    """Comprehensive validation service for all collections"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = get_user_repo()
        self.workspace_repo = get_workspace_repo()
        self.venue_repo = get_venue_repo()
        self.role_repo = get_role_repo()
        self.permission_repo = get_permission_repo()
        self.menu_category_repo = get_menu_category_repo()
        self.menu_item_repo = get_menu_item_repo()
        self.table_repo = get_table_repo()
        self.customer_repo = get_customer_repo()
        self.order_repo = get_order_repo()
    
    # =============================================================================
    # CORE VALIDATION METHODS
    # =============================================================================
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> List[ValidationError]:
        """Validate that all required fields are present and not None/empty"""
        errors = []
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError(field, None, "required field", f"Missing required field: {field}"))
            elif data[field] is None:
                errors.append(ValidationError(field, None, "non-null value", f"Field {field} cannot be null"))
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(ValidationError(field, data[field], "non-empty string", f"Field {field} cannot be empty"))
        return errors
    
    def validate_string_field(self, field_name: str, value: Any, min_length: int = None, 
                            max_length: int = None, pattern: str = None) -> List[ValidationError]:
        """Validate string field with length and pattern constraints"""
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(field_name, value, "string", f"Field {field_name} must be a string"))
            return errors
        
        if min_length is not None and len(value) < min_length:
            errors.append(ValidationError(field_name, value, f"minimum {min_length} characters", 
                                        f"Field {field_name} must be at least {min_length} characters long"))
        
        if max_length is not None and len(value) > max_length:
            errors.append(ValidationError(field_name, value, f"maximum {max_length} characters", 
                                        f"Field {field_name} must be at most {max_length} characters long"))
        
        if pattern and not re.match(pattern, value):
            errors.append(ValidationError(field_name, value, f"pattern {pattern}", 
                                        f"Field {field_name} does not match required pattern"))
        
        return errors
    
    def validate_email(self, field_name: str, value: Any) -> List[ValidationError]:
        """Validate email format"""
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(field_name, value, "string", f"Field {field_name} must be a string"))
            return errors
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            errors.append(ValidationError(field_name, value, "valid email format", 
                                        f"Field {field_name} must be a valid email address"))
        
        return errors
    
    def validate_phone(self, field_name: str, value: Any) -> List[ValidationError]:
        """Validate phone number format"""
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(field_name, value, "string", f"Field {field_name} must be a string"))
            return errors
        
        phone_pattern = r'^[+]?[1-9]?[0-9]{7,15}$'
        if not re.match(phone_pattern, value):
            errors.append(ValidationError(field_name, value, "valid phone format", 
                                        f"Field {field_name} must be a valid phone number (7-15 digits, optional + prefix)"))
        
        return errors
    
    def validate_enum_field(self, field_name: str, value: Any, enum_class: Enum) -> List[ValidationError]:
        """Validate enum field"""
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(field_name, value, "string", f"Field {field_name} must be a string"))
            return errors
        
        valid_values = [item.value for item in enum_class]
        if value not in valid_values:
            errors.append(ValidationError(field_name, value, f"one of {valid_values}", 
                                        f"Field {field_name} must be one of: {', '.join(valid_values)}"))
        
        return errors
    
    def validate_numeric_field(self, field_name: str, value: Any, min_value: float = None, 
                             max_value: float = None, field_type: str = "number") -> List[ValidationError]:
        """Validate numeric field with range constraints"""
        errors = []
        
        if field_type == "integer":
            if not isinstance(value, int):
                errors.append(ValidationError(field_name, value, "integer", f"Field {field_name} must be an integer"))
                return errors
        else:
            if not isinstance(value, (int, float)):
                errors.append(ValidationError(field_name, value, "number", f"Field {field_name} must be a number"))
                return errors
        
        if min_value is not None and value < min_value:
            errors.append(ValidationError(field_name, value, f"minimum {min_value}", 
                                        f"Field {field_name} must be at least {min_value}"))
        
        if max_value is not None and value > max_value:
            errors.append(ValidationError(field_name, value, f"maximum {max_value}", 
                                        f"Field {field_name} must be at most {max_value}"))
        
        return errors
    
    def validate_boolean_field(self, field_name: str, value: Any) -> List[ValidationError]:
        """Validate boolean field"""
        errors = []
        
        if not isinstance(value, bool):
            errors.append(ValidationError(field_name, value, "boolean", f"Field {field_name} must be a boolean"))
        
        return errors
    
    def validate_datetime_field(self, field_name: str, value: Any) -> List[ValidationError]:
        """Validate datetime field"""
        errors = []
        
        if not isinstance(value, (datetime, date)):
            errors.append(ValidationError(field_name, value, "datetime", f"Field {field_name} must be a datetime"))
        
        return errors
    
    def validate_list_field(self, field_name: str, value: Any, min_items: int = None, 
                          max_items: int = None, item_type: type = None) -> List[ValidationError]:
        """Validate list field with constraints"""
        errors = []
        
        if not isinstance(value, list):
            errors.append(ValidationError(field_name, value, "list", f"Field {field_name} must be a list"))
            return errors
        
        if min_items is not None and len(value) < min_items:
            errors.append(ValidationError(field_name, value, f"minimum {min_items} items", 
                                        f"Field {field_name} must have at least {min_items} items"))
        
        if max_items is not None and len(value) > max_items:
            errors.append(ValidationError(field_name, value, f"maximum {max_items} items", 
                                        f"Field {field_name} must have at most {max_items} items"))
        
        if item_type:
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    errors.append(ValidationError(f"{field_name}[{i}]", item, item_type.__name__, 
                                                f"Item {i} in {field_name} must be of type {item_type.__name__}"))
        
        return errors
    
    # =============================================================================
    # REFERENCE VALIDATION METHODS
    # =============================================================================
    
    async def validate_workspace_reference(self, workspace_id: str) -> List[ValidationError]:
        """Validate that workspace exists and is active"""
        errors = []
        
        if not workspace_id:
            errors.append(ValidationError("workspace_id", workspace_id, "non-empty string", 
                                        "workspace_id is required"))
            return errors
        
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            errors.append(ValidationError("workspace_id", workspace_id, "existing workspace", 
                                        f"Workspace with ID {workspace_id} does not exist"))
        elif not workspace.get('is_active', False):
            errors.append(ValidationError("workspace_id", workspace_id, "active workspace", 
                                        f"Workspace {workspace_id} is not active"))
        
        return errors
    
    async def validate_venue_reference(self, venue_id: str) -> List[ValidationError]:
        """Validate that venue exists and is active"""
        errors = []
        
        if not venue_id:
            errors.append(ValidationError("venue_id", venue_id, "non-empty string", 
                                        "venue_id is required"))
            return errors
        
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            errors.append(ValidationError("venue_id", venue_id, "existing venue", 
                                        f"Venue with ID {venue_id} does not exist"))
        elif not venue.get('is_active', False):
            errors.append(ValidationError("venue_id", venue_id, "active venue", 
                                        f"Venue {venue_id} is not active"))
        
        return errors
    
    async def validate_role_reference(self, role_id: str) -> List[ValidationError]:
        """Validate that role exists"""
        errors = []
        
        if not role_id:
            errors.append(ValidationError("role_id", role_id, "non-empty string", 
                                        "role_id is required"))
            return errors
        
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            errors.append(ValidationError("role_id", role_id, "existing role", 
                                        f"Role with ID {role_id} does not exist"))
        
        return errors
    
    async def validate_user_reference(self, user_id: str) -> List[ValidationError]:
        """Validate that user exists and is active"""
        errors = []
        
        if not user_id:
            errors.append(ValidationError("user_id", user_id, "non-empty string", 
                                        "user_id is required"))
            return errors
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            errors.append(ValidationError("user_id", user_id, "existing user", 
                                        f"User with ID {user_id} does not exist"))
        elif not user.get('is_active', False):
            errors.append(ValidationError("user_id", user_id, "active user", 
                                        f"User {user_id} is not active"))
        
        return errors
    
    async def validate_menu_category_reference(self, category_id: str, venue_id: str = None) -> List[ValidationError]:
        """Validate that menu category exists"""
        errors = []
        
        if not category_id:
            errors.append(ValidationError("category_id", category_id, "non-empty string", 
                                        "category_id is required"))
            return errors
        
        category = await self.menu_category_repo.get_by_id(category_id)
        if not category:
            errors.append(ValidationError("category_id", category_id, "existing category", 
                                        f"Menu category with ID {category_id} does not exist"))
        elif venue_id and category.get('venue_id') != venue_id:
            errors.append(ValidationError("category_id", category_id, f"category in venue {venue_id}", 
                                        f"Menu category {category_id} does not belong to venue {venue_id}"))
        
        return errors
    
    async def validate_table_reference(self, table_id: str, venue_id: str = None) -> List[ValidationError]:
        """Validate that table exists"""
        errors = []
        
        if not table_id:
            errors.append(ValidationError("table_id", table_id, "non-empty string", 
                                        "table_id is required"))
            return errors
        
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            errors.append(ValidationError("table_id", table_id, "existing table", 
                                        f"Table with ID {table_id} does not exist"))
        elif venue_id and table.get('venue_id') != venue_id:
            errors.append(ValidationError("table_id", table_id, f"table in venue {venue_id}", 
                                        f"Table {table_id} does not belong to venue {venue_id}"))
        
        return errors
    
    # =============================================================================
    # UNIQUENESS VALIDATION METHODS
    # =============================================================================
    
    async def validate_email_uniqueness(self, email: str, exclude_user_id: str = None) -> List[ValidationError]:
        """Validate that email is unique"""
        errors = []
        
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user and existing_user.get('id') != exclude_user_id:
            errors.append(ValidationError("email", email, "unique email", 
                                        f"Email {email} is already registered"))
        
        return errors
    
    async def validate_phone_uniqueness(self, phone: str, exclude_user_id: str = None) -> List[ValidationError]:
        """Validate that phone number is unique"""
        errors = []
        
        existing_user = await self.user_repo.get_by_phone(phone)
        if existing_user and existing_user.get('id') != exclude_user_id:
            errors.append(ValidationError("phone", phone, "unique phone", 
                                        f"Phone number {phone} is already registered"))
        
        return errors
    
    async def validate_workspace_name_uniqueness(self, name: str, exclude_workspace_id: str = None) -> List[ValidationError]:
        """Validate that workspace name is unique"""
        errors = []
        
        existing_workspace = await self.workspace_repo.get_by_name(name)
        if existing_workspace and existing_workspace.get('id') != exclude_workspace_id:
            errors.append(ValidationError("name", name, "unique workspace name", 
                                        f"Workspace name {name} is already taken"))
        
        return errors
    
    # =============================================================================
    # COLLECTION-SPECIFIC VALIDATION METHODS
    # =============================================================================
    
    async def validate_user_data(self, data: Dict[str, Any], is_update: bool = False, 
                               user_id: str = None) -> List[ValidationError]:
        """Comprehensive user data validation"""
        errors = []
        
        # Required fields for creation
        if not is_update:
            required_fields = ['email', 'phone', 'first_name', 'last_name', 'password']
            errors.extend(self.validate_required_fields(data, required_fields))
        
        # Email validation
        if 'email' in data:
            errors.extend(self.validate_email('email', data['email']))
            errors.extend(await self.validate_email_uniqueness(data['email'], user_id))
        
        # Phone validation
        if 'phone' in data:
            errors.extend(self.validate_phone('phone', data['phone']))
            errors.extend(await self.validate_phone_uniqueness(data['phone'], user_id))
        
        # Name validation
        if 'first_name' in data:
            errors.extend(self.validate_string_field('first_name', data['first_name'], 1, 50))
        
        if 'last_name' in data:
            errors.extend(self.validate_string_field('last_name', data['last_name'], 1, 50))
        
        # Password validation
        if 'password' in data:
            errors.extend(self.validate_password_strength('password', data['password']))
        
        # Role validation
        if 'role_id' in data and data['role_id']:
            errors.extend(await self.validate_role_reference(data['role_id']))
        
        # Workspace validation
        if 'workspace_id' in data and data['workspace_id']:
            errors.extend(await self.validate_workspace_reference(data['workspace_id']))
        
        # Venue validation
        if 'venue_id' in data and data['venue_id']:
            errors.extend(await self.validate_venue_reference(data['venue_id']))
        
        # Gender validation
        if 'gender' in data and data['gender']:
            errors.extend(self.validate_enum_field('gender', data['gender'], Gender))
        
        # Boolean fields
        for field in ['is_active', 'is_verified', 'email_verified', 'phone_verified']:
            if field in data:
                errors.extend(self.validate_boolean_field(field, data[field]))
        
        # Date validation
        if 'date_of_birth' in data and data['date_of_birth']:
            errors.extend(self.validate_datetime_field('date_of_birth', data['date_of_birth']))
        
        return errors
    
    async def validate_workspace_data(self, data: Dict[str, Any], is_update: bool = False, 
                                    workspace_id: str = None) -> List[ValidationError]:
        """Comprehensive workspace data validation"""
        errors = []
        
        # Required fields for creation
        if not is_update:
            required_fields = ['display_name', 'business_type']
            errors.extend(self.validate_required_fields(data, required_fields))
            
        # Display name validation
        if 'display_name' in data:
            errors.extend(self.validate_string_field('display_name', data['display_name'], 1, 100))
        
        # Description validation
        if 'description' in data and data['description']:
            errors.extend(self.validate_string_field('description', data['description'], max_length=500))
        
        # Business type validation
        if 'business_type' in data:
            errors.extend(self.validate_enum_field('business_type', data['business_type'], BusinessType))
        
        # Owner validation
        if 'owner_id' in data and data['owner_id']:
            errors.extend(await self.validate_user_reference(data['owner_id']))
        
        # Venue IDs validation
        if 'venue_ids' in data:
            errors.extend(self.validate_list_field('venue_ids', data['venue_ids'], item_type=str))
            for venue_id in data['venue_ids']:
                errors.extend(await self.validate_venue_reference(venue_id))
        
        # Boolean fields
        if 'is_active' in data:
            errors.extend(self.validate_boolean_field('is_active', data['is_active']))
        
        return errors
    
    async def validate_venue_data(self, data: Dict[str, Any], is_update: bool = False, 
                                venue_id: str = None) -> List[ValidationError]:
        """Comprehensive venue data validation"""
        errors = []
        
        # Required fields for creation
        if not is_update:
            required_fields = ['name', 'description', 'location', 'phone', 'email', 'price_range', 'workspace_id']
            errors.extend(self.validate_required_fields(data, required_fields))
        
        # Name validation
        if 'name' in data:
            errors.extend(self.validate_string_field('name', data['name'], 1, 100))
        
        # Description validation
        if 'description' in data:
            errors.extend(self.validate_string_field('description', data['description'], max_length=1000))
        
        # Phone validation
        if 'phone' in data:
            errors.extend(self.validate_phone('phone', data['phone']))
        
        # Email validation
        if 'email' in data:
            errors.extend(self.validate_email('email', data['email']))
        
        # Price range validation
        if 'price_range' in data:
            errors.extend(self.validate_enum_field('price_range', data['price_range'], PriceRange))
        
        # Workspace validation
        if 'workspace_id' in data:
            errors.extend(await self.validate_workspace_reference(data['workspace_id']))
        
        # Admin validation
        if 'admin_id' in data and data['admin_id']:
            errors.extend(await self.validate_user_reference(data['admin_id']))
        
        # Status validation
        if 'status' in data:
            errors.extend(self.validate_enum_field('status', data['status'], VenueStatus))
        
        # Subscription validation
        if 'subscription_plan' in data:
            errors.extend(self.validate_enum_field('subscription_plan', data['subscription_plan'], SubscriptionPlan))
        
        if 'subscription_status' in data:
            errors.extend(self.validate_enum_field('subscription_status', data['subscription_status'], SubscriptionStatus))
        
        # Location validation
        if 'location' in data:
            errors.extend(self.validate_location_data(data['location']))
        
        # Cuisine types validation
        if 'cuisine_types' in data:
            errors.extend(self.validate_list_field('cuisine_types', data['cuisine_types'], item_type=str))
        
        # Operating hours validation
        if 'operating_hours' in data:
            errors.extend(self.validate_operating_hours(data['operating_hours']))
        
        # Boolean fields
        for field in ['is_active', 'is_verified']:
            if field in data:
                errors.extend(self.validate_boolean_field(field, data[field]))
        
        # Numeric fields
        if 'rating' in data:
            errors.extend(self.validate_numeric_field('rating', data['rating'], 0, 5))
        
        if 'total_reviews' in data:
            errors.extend(self.validate_numeric_field('total_reviews', data['total_reviews'], 0, field_type="integer"))
        
        return errors
    
    async def validate_order_data(self, data: Dict[str, Any], is_update: bool = False) -> List[ValidationError]:
        """Comprehensive order data validation"""
        errors = []
        
        # Required fields for creation
        if not is_update:
            required_fields = ['venue_id', 'customer_id', 'order_type', 'items']
            errors.extend(self.validate_required_fields(data, required_fields))
        
        # Venue validation
        if 'venue_id' in data:
            errors.extend(await self.validate_venue_reference(data['venue_id']))
        
        # Customer validation
        if 'customer_id' in data:
            customer = await self.customer_repo.get_by_id(data['customer_id'])
            if not customer:
                errors.append(ValidationError("customer_id", data['customer_id'], "existing customer", 
                                            f"Customer with ID {data['customer_id']} does not exist"))
        
        # Order type validation
        if 'order_type' in data:
            errors.extend(self.validate_enum_field('order_type', data['order_type'], OrderType))
        
        # Table validation (if provided)
        if 'table_id' in data and data['table_id']:
            errors.extend(await self.validate_table_reference(data['table_id'], data.get('venue_id')))
        
        # Items validation
        if 'items' in data:
            errors.extend(self.validate_list_field('items', data['items'], min_items=1, max_items=50))
            for i, item in enumerate(data['items']):
                errors.extend(self.validate_order_item_data(item, f"items[{i}]"))
        
        # Status validation
        if 'status' in data:
            errors.extend(self.validate_enum_field('status', data['status'], OrderStatus))
        
        if 'payment_status' in data:
            errors.extend(self.validate_enum_field('payment_status', data['payment_status'], PaymentStatus))
        
        if 'payment_method' in data and data['payment_method']:
            errors.extend(self.validate_enum_field('payment_method', data['payment_method'], PaymentMethod))
        
        # Numeric fields
        for field in ['subtotal', 'total_amount']:
            if field in data:
                errors.extend(self.validate_numeric_field(field, data[field], 0))
        
        for field in ['tax_amount', 'discount_amount']:
            if field in data:
                errors.extend(self.validate_numeric_field(field, data[field], 0))
        
        # Special instructions validation
        if 'special_instructions' in data and data['special_instructions']:
            errors.extend(self.validate_string_field('special_instructions', data['special_instructions'], max_length=1000))
        
        return errors
    
    def validate_password_strength(self, field_name: str, password: str) -> List[ValidationError]:
        """Validate password strength"""
        errors = []
        
        if not isinstance(password, str):
            errors.append(ValidationError(field_name, password, "string", f"Field {field_name} must be a string"))
            return errors
        
        if len(password) < 8:
            errors.append(ValidationError(field_name, password, "minimum 8 characters", 
                                        "Password must be at least 8 characters long"))
        
        if len(password) > 128:
            errors.append(ValidationError(field_name, password, "maximum 128 characters", 
                                        "Password must be at most 128 characters long"))
        
        if not re.search(r"[A-Z]", password):
            errors.append(ValidationError(field_name, password, "uppercase letter", 
                                        "Password must contain at least one uppercase letter"))
        
        if not re.search(r"[a-z]", password):
            errors.append(ValidationError(field_name, password, "lowercase letter", 
                                        "Password must contain at least one lowercase letter"))
        
        if not re.search(r"\d", password):
            errors.append(ValidationError(field_name, password, "digit", 
                                        "Password must contain at least one digit"))
        
        return errors
    
    def validate_location_data(self, location: Dict[str, Any]) -> List[ValidationError]:
        """Validate location data"""
        errors = []
        
        if not isinstance(location, dict):
            errors.append(ValidationError("location", location, "object", "Location must be an object"))
            return errors
        
        required_fields = ['address', 'city', 'state', 'country', 'postal_code']
        errors.extend(self.validate_required_fields(location, required_fields))
        
        # Address validation
        if 'address' in location:
            errors.extend(self.validate_string_field('location.address', location['address'], 10, 500))
        
        # City, state, country validation
        for field in ['city', 'state', 'country']:
            if field in location:
                errors.extend(self.validate_string_field(f'location.{field}', location[field], 2, 100))
        
        # Postal code validation
        if 'postal_code' in location:
            errors.extend(self.validate_string_field('location.postal_code', location['postal_code'], 3, 20))
        
        # Coordinates validation
        if 'latitude' in location and location['latitude'] is not None:
            errors.extend(self.validate_numeric_field('location.latitude', location['latitude'], -90, 90))
        
        if 'longitude' in location and location['longitude'] is not None:
            errors.extend(self.validate_numeric_field('location.longitude', location['longitude'], -180, 180))
        
        return errors
    
    def validate_operating_hours(self, operating_hours: List[Dict[str, Any]]) -> List[ValidationError]:
        """Validate operating hours data"""
        errors = []
        
        if not isinstance(operating_hours, list):
            errors.append(ValidationError("operating_hours", operating_hours, "list", "Operating hours must be a list"))
            return errors
        
        for i, hours in enumerate(operating_hours):
            if not isinstance(hours, dict):
                errors.append(ValidationError(f"operating_hours[{i}]", hours, "object", 
                                            f"Operating hours item {i} must be an object"))
                continue
            
            # Day of week validation
            if 'day_of_week' in hours:
                errors.extend(self.validate_numeric_field(f'operating_hours[{i}].day_of_week', 
                                                        hours['day_of_week'], 0, 6, "integer"))
            
            # Boolean fields
            for field in ['is_open', 'is_24_hours']:
                if field in hours:
                    errors.extend(self.validate_boolean_field(f'operating_hours[{i}].{field}', hours[field]))
        
        return errors
    
    def validate_order_item_data(self, item: Dict[str, Any], field_prefix: str) -> List[ValidationError]:
        """Validate order item data"""
        errors = []
        
        if not isinstance(item, dict):
            errors.append(ValidationError(field_prefix, item, "object", f"{field_prefix} must be an object"))
            return errors
        
        required_fields = ['menu_item_id', 'quantity']
        for field in required_fields:
            if field not in item:
                errors.append(ValidationError(f"{field_prefix}.{field}", None, "required field", 
                                            f"Missing required field: {field_prefix}.{field}"))
        
        # Quantity validation
        if 'quantity' in item:
            errors.extend(self.validate_numeric_field(f'{field_prefix}.quantity', item['quantity'], 1, 50, "integer"))
        
        # Special instructions validation
        if 'special_instructions' in item and item['special_instructions']:
            errors.extend(self.validate_string_field(f'{field_prefix}.special_instructions', 
                                                   item['special_instructions'], max_length=500))
        
        return errors
    
    # =============================================================================
    # MAIN VALIDATION METHODS
    # =============================================================================
    
    async def validate_collection_data(self, collection_name: str, data: Dict[str, Any], 
                                     is_update: bool = False, item_id: str = None) -> List[ValidationError]:
        """Main validation method for any collection"""
        errors = []
        
        try:
            if collection_name == "users":
                errors = await self.validate_user_data(data, is_update, item_id)
            elif collection_name == "workspaces":
                errors = await self.validate_workspace_data(data, is_update, item_id)
            elif collection_name == "venues":
                errors = await self.validate_venue_data(data, is_update, item_id)
            elif collection_name == "orders":
                errors = await self.validate_order_data(data, is_update)
            else:
                self.logger.warning(f"No specific validation implemented for collection: {collection_name}")
            
            self.log_operation("validate_collection_data", 
                             collection=collection_name, 
                             is_update=is_update, 
                             error_count=len(errors))
            
            return errors
            
        except Exception as e:
            self.log_error(e, "validate_collection_data", 
                          collection=collection_name, 
                          is_update=is_update)
            raise
    
    def format_validation_errors(self, errors: List[ValidationError]) -> Dict[str, Any]:
        """Format validation errors for API response"""
        if not errors:
            return {"valid": True, "errors": []}
        
        formatted_errors = []
        for error in errors:
            formatted_errors.append({
                "field": error.field,
                "value": str(error.value) if error.value is not None else None,
                "expected": error.expected,
                "message": error.message
            })
        
        return {
            "valid": False,
            "errors": formatted_errors,
            "error_count": len(errors)
        }
    
    def raise_validation_exception(self, errors: List[ValidationError]):
        """Raise HTTPException with formatted validation errors"""
        if errors:
            formatted = self.format_validation_errors(errors)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Validation failed",
                    "validation_errors": formatted["errors"],
                    "error_count": formatted["error_count"]
                }
            )


# Global validation service instance
validation_service = ValidationService()


def get_validation_service() -> ValidationService:
    """Get validation service instance"""
    return validation_service