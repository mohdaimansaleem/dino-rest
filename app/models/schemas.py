"""
Unified Schemas for Dino Multi-Venue Platform
Consolidated and comprehensive data models with consistent terminology
"""
from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date, time
from enum import Enum
import re


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class UserRole(str, Enum):
    """User roles with hierarchy"""
    SUPERADMIN = "superadmin"  # Full workspace access, create venues, manage all
    ADMIN = "admin"           # Full venue access, manage operators
    OPERATOR = "operator"     # Limited access, view orders, update tables

class BusinessType(str, Enum):
    """Business types"""
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    BOTH = "both"

class SubscriptionPlan(str, Enum):
    """Subscription plans"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class VenueStatus(str, Enum):
    """Venue operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"

class WorkspaceStatus(str, Enum):
    """Workspace status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"

class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    DELIVERED = "delivered"
    OUT_FOR_DELIVERY = "out_for_delivery"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class PaymentMethod(str, Enum):
    """Payment methods"""
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"

class PaymentGateway(str, Enum):
    """Payment gateways"""
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    PAYTM = "paytm"
    CASH = "cash"

class OrderType(str, Enum):
    """Order types"""
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"

class OrderSource(str, Enum):
    """Order source types"""
    QR_SCAN = "qr_scan"
    WALK_IN = "walk_in"
    ONLINE = "online"
    PHONE = "phone"

class TableStatus(str, Enum):
    """Table status"""
    AVAILABLE = "available"
    BOOKED = "booked"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"

class NotificationType(str, Enum):
    """Notification types"""
    ORDER_PLACED = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_READY = "order_ready"
    ORDER_DELIVERED = "order_delivered"
    PAYMENT_RECEIVED = "payment_received"
    SYSTEM_ALERT = "system_alert"

class TransactionType(str, Enum):
    """Transaction types"""
    PAYMENT = "payment"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"

class FeedbackType(str, Enum):
    """Feedback types"""
    ORDER = "order"
    SERVICE = "service"
    FOOD = "food"
    AMBIANCE = "ambiance"
    OVERALL = "overall"

class PriceRange(str, Enum):
    """Price ranges"""
    BUDGET = "budget"
    MID_RANGE = "mid_range"
    PREMIUM = "premium"
    LUXURY = "luxury"

class SpiceLevel(str, Enum):
    """Spice levels"""
    MILD = "mild"
    MEDIUM = "medium"
    HOT = "hot"
    EXTRA_HOT = "extra_hot"

class Priority(str, Enum):
    """Priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class RecipientType(str, Enum):
    """Notification recipient types"""
    USER = "user"
    VENUE = "venue"
    WORKSPACE = "workspace"

class CustomerType(str, Enum):
    """Customer types"""
    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"

# =============================================================================
# BASE MODELS
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# =============================================================================
# LOCATION AND CONTACT SCHEMAS
# =============================================================================
class VenueLocation(BaseModel):
    """Venue location details"""
    address: str = Field(..., min_length=10, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    landmark: Optional[str] = Field(None, max_length=200)

class VenueOperatingHours(BaseModel):
    """Operating hours for a venue"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_open: bool = Field(default=True, description="Whether venue is open on this day")
    open_time: Optional[time] = Field(None, description="Opening time")
    close_time: Optional[time] = Field(None, description="Closing time")
    is_24_hours: bool = Field(default=False, description="Whether venue is open 24 hours")
    break_start: Optional[time] = Field(None, description="Break start time (optional)")
    break_end: Optional[time] = Field(None, description="Break end time (optional)")

# =============================================================================
# WORKSPACE SCHEMAS (Optimized)
# =============================================================================
class WorkspaceBase(BaseSchema):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class WorkspaceCreate(WorkspaceBase):
    """Schema for creating workspace"""
    pass

class WorkspaceUpdate(BaseSchema):
    """Schema for updating workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class Workspace(WorkspaceBase, TimestampMixin):
    """Complete workspace schema"""
    id: str
    venue_ids: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)

# =============================================================================
# USER SCHEMAS (Optimized)
# =============================================================================
class UserBase(BaseSchema):
    """Base user schema"""
    email: EmailStr
    mobile_number: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$", description="Unique mobile number")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

class UserCreate(UserBase):
    """Schema for creating users"""
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    role_id: Optional[str] = None

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseSchema):
    """User login schema"""
    email: EmailStr
    password: str
    remember_me: bool = Field(default=False)

class UserUpdate(BaseSchema):
    """Schema for updating users"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    mobile_number: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")
    is_active: Optional[bool] = None

class User(UserBase, TimestampMixin):
    """Complete user schema"""
    id: str
    role_id: Optional[str] = None
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    mobile_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None

# =============================================================================
# VENUE SCHEMAS (Unified from Cafe)
# =============================================================================
class VenueBase(BaseSchema):
    """Base venue schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    location: VenueLocation
    mobile_number: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: EmailStr
    website: Optional[HttpUrl] = None
    cuisine_types: List[str] = Field(default_factory=list)
    price_range: PriceRange
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE

class VenueCreate(VenueBase):
    """Schema for creating venues"""
    admin_id: Optional[str] = None  # Will be set automatically

class VenueUpdate(BaseSchema):
    """Schema for updating venues"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    mobile_number: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    logo_url: Optional[HttpUrl] = None
    cuisine_types: Optional[List[str]] = None
    price_range: Optional[PriceRange] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    subscription_status: Optional[SubscriptionStatus] = None
    status: Optional[VenueStatus] = None
    is_active: Optional[bool] = None

class Venue(VenueBase, TimestampMixin):
    """Complete venue schema"""
    id: str
    admin_id: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    status: VenueStatus = VenueStatus.ACTIVE
    is_active: bool = Field(default=True)
    rating: float = Field(default=0.0, ge=0, le=5)
    total_reviews: int = Field(default=0)

class VenuePublicInfo(BaseModel):
    """Public venue information for QR access"""
    id: str
    name: str
    description: Optional[str] = None
    cuisine_types: List[str] = Field(default_factory=list)
    location: VenueLocation
    mobile_number: str
    website: Optional[str] = None
    price_range: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    is_open: bool
    current_wait_time: Optional[int] = None
    rating: float = Field(default=0.0)
    total_reviews: int = Field(default=0)

# =============================================================================
# MENU SCHEMAS
# =============================================================================
class MenuCategoryBase(BaseSchema):
    """Base menu category schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)

class MenuCategoryCreate(MenuCategoryBase):
    """Schema for creating menu categories"""
    venue_id: str

class MenuCategoryUpdate(BaseSchema):
    """Schema for updating menu categories"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class MenuCategory(MenuCategoryBase, TimestampMixin):
    """Complete menu category schema"""
    id: str
    venue_id: str
    image_url: Optional[str] = None
    is_active: bool = Field(default=True)

class MenuItemBase(BaseSchema):
    """Base menu item schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    category_id: str
    is_vegetarian: bool = Field(default=True)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)

class MenuItemCreate(MenuItemBase):
    """Schema for creating menu items"""
    venue_id: str

class MenuItemUpdate(BaseSchema):
    """Schema for updating menu items"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    spice_level: Optional[SpiceLevel] = None
    preparation_time_minutes: Optional[int] = Field(None, ge=5, le=120)
    is_available: Optional[bool] = None

class MenuItem(MenuItemBase, TimestampMixin):
    """Complete menu item schema"""
    id: str
    venue_id: str
    image_urls: List[HttpUrl] = Field(default_factory=list)
    is_available: bool = Field(default=True)
    rating: float = Field(default=0.0, ge=0, le=5)

# =============================================================================
# TABLE SCHEMAS
# =============================================================================
class TableBase(BaseSchema):
    """Base table schema"""
    table_number: int = Field(..., ge=1)
    capacity: int = Field(..., ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)

class TableCreate(TableBase):
    """Schema for creating tables"""
    venue_id: str

class TableUpdate(BaseSchema):
    """Schema for updating tables"""
    capacity: Optional[int] = Field(None, ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    table_status: Optional[TableStatus] = None
    is_active: Optional[bool] = None

class Table(TableBase, TimestampMixin):
    """Complete table schema"""
    id: str
    venue_id: str
    table_status: TableStatus = TableStatus.AVAILABLE
    is_active: bool = Field(default=True)

# =============================================================================
# CUSTOMER SCHEMAS
# =============================================================================
class CustomerBase(BaseSchema):
    """Base customer schema"""
    name: str = Field(..., min_length=1, max_length=100)
    mobile_number: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$")

class CustomerCreate(CustomerBase):
    """Schema for creating customers"""
    pass

class CustomerUpdate(BaseSchema):
    """Schema for updating customers"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    mobile_number: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")

class Customer(CustomerBase, TimestampMixin):
    """Complete customer schema"""
    id: str
    customer_type: CustomerType = CustomerType.NEW
    total_orders: int = Field(default=0)
    total_spent: float = Field(default=0.0)
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    loyalty_points: int = Field(default=0)
    marketing_consent: bool = Field(default=False)

# =============================================================================
# ORDER SCHEMAS
# =============================================================================
class OrderItemBase(BaseSchema):
    """Base order item schema"""
    menu_item_id: str
    menu_item_name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)
    special_instructions: Optional[str] = Field(None, max_length=500)

class OrderItemCreate(BaseSchema):
    """Schema for creating order items"""
    menu_item_id: str
    quantity: int = Field(..., ge=1, le=50)
    customizations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    special_instructions: Optional[str] = Field(None, max_length=500)

class OrderBase(BaseSchema):
    """Base order schema"""
    venue_id: str
    customer_id: str
    order_type: OrderType
    table_id: Optional[str] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)

class OrderCreate(OrderBase):
    """Schema for creating orders"""
    items: List[OrderItemCreate] = Field(..., min_items=1)

class PublicOrderCreate(BaseModel):
    """Schema for creating orders from public interface (QR scan)"""
    venue_id: str = Field(..., description="Venue where order is placed")
    table_id: Optional[str] = Field(None, description="Table ID from QR scan")
    customer: CustomerCreate
    items: List[OrderItemCreate] = Field(..., min_items=1, max_items=50)
    order_type: OrderSource = OrderSource.QR_SCAN
    special_instructions: Optional[str] = Field(None, max_length=1000)

class OrderUpdate(BaseSchema):
    """Schema for updating orders"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    estimated_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)

class Order(OrderBase, TimestampMixin):
    """Complete order schema"""
    id: str
    order_number: str
    items: List[OrderItemBase]
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    total_amount: float = Field(..., gt=0)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    estimated_ready_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None

# =============================================================================
# TRANSACTION SCHEMAS
# =============================================================================
class TransactionBase(BaseSchema):
    """Base transaction schema"""
    venue_id: str
    order_id: str
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    payment_method: PaymentMethod
    payment_gateway: Optional[PaymentGateway] = None
    gateway_transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    status: PaymentStatus

class TransactionCreate(TransactionBase):
    """Schema for creating transactions"""
    pass

class Transaction(TransactionBase, TimestampMixin):
    """Complete transaction schema"""
    id: str
    processed_at: Optional[datetime] = None
    refunded_amount: float = Field(default=0.0, ge=0)

# =============================================================================
# NOTIFICATION SCHEMAS
# =============================================================================
class NotificationBase(BaseSchema):
    """Base notification schema"""
    recipient_id: str
    recipient_type: RecipientType
    notification_type: NotificationType
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    data: Optional[Dict[str, Any]] = None
    priority: Priority = Priority.NORMAL

class NotificationCreate(NotificationBase):
    """Schema for creating notifications"""
    pass

class Notification(NotificationBase, TimestampMixin):
    """Complete notification schema"""
    id: str
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None

# =============================================================================
# REVIEW SCHEMAS
# =============================================================================
class ReviewBase(BaseSchema):
    """Base review schema"""
    venue_id: str
    order_id: str
    customer_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    feedback_type: FeedbackType = FeedbackType.OVERALL

class ReviewCreate(ReviewBase):
    """Schema for creating reviews"""
    pass

class ReviewUpdate(BaseSchema):
    """Schema for updating reviews"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    is_verified: Optional[bool] = None

class Review(ReviewBase, TimestampMixin):
    """Complete review schema"""
    id: str
    is_verified: bool = Field(default=False)
    helpful_count: int = Field(default=0)

# =============================================================================
# ROLE AND PERMISSION SCHEMAS
# =============================================================================
class RoleBase(BaseSchema):
    """Base role schema"""
    name: UserRole
    description: str = Field(..., max_length=500)
    permission_ids: List[str] = Field(default_factory=list)

class RoleCreate(RoleBase):
    """Schema for creating roles"""
    pass

class RoleUpdate(BaseSchema):
    """Schema for updating roles"""
    description: Optional[str] = Field(None, max_length=500)
    permission_ids: Optional[List[str]] = None

class Role(RoleBase, TimestampMixin):
    """Complete role schema"""
    id: str

class PermissionBase(BaseSchema):
    """Base permission schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    resource: str = Field(..., pattern="^(workspace|venue|menu|order|user|analytics|table|dashboard|cafe|orders|tables|users|settings|qr|reports|notifications|profile|password)$")
    action: str = Field(..., pattern="^(create|read|update|delete|manage|view|activate|deactivate|switch|generate|print)$")
    scope: str = Field(..., pattern="^(own|venue|workspace|all|system)$")
    
    @validator('name')
    def validate_name_format(cls, v):
        """Validate permission name format - allow both dot and colon separators"""
        if '.' in v or ':' in v:
            # Split by either . or :
            parts = v.replace(':', '.').split('.')
            if len(parts) >= 2:
                return v
        # If no separator, check if it follows resource.action format
        if '.' not in v and ':' not in v:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        return v

class PermissionCreate(PermissionBase):
    """Schema for creating permissions"""
    pass

class PermissionUpdate(BaseSchema):
    """Schema for updating permissions"""
    description: Optional[str] = Field(None, max_length=500)

class Permission(PermissionBase, TimestampMixin):
    """Complete permission schema"""
    id: str
    is_system_permission: bool = Field(default=True)

class PermissionCheck(BaseSchema):
    """Permission check result"""
    has_permission: bool
    reason: Optional[str] = None
    required_role: Optional[UserRole] = None
    user_role: Optional[UserRole] = None
    
# =============================================================================
# WORKSPACE ONBOARDING SCHEMAS
# =============================================================================

class UserDetails(BaseModel):
    """Owner/SuperAdmin details for workspace creation"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = Field(None, max_length=500)

class WorkspaceRegistration(BaseSchema):
    """Workspace registration schema"""
    # Workspace details
    workspace_name: str = Field(..., min_length=1, max_length=100, alias="workspaceName")
    workspace_description: Optional[str] = Field(None, max_length=500, alias="workspaceDescription")
    
    # Venue details
    venue_name: str = Field(..., min_length=1, max_length=100, alias="venueName")
    venue_description: Optional[str] = Field(None, max_length=1000, alias="venueDescription")
    venue_location: VenueLocation = Field(..., alias="venueLocation")
    venue_mobile: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="venueMobile")
    venue_email: Optional[EmailStr] = Field(None, alias="venueEmail")
    venue_website: Optional[HttpUrl] = Field(None, alias="venueWebsite")
    price_range: PriceRange = Field(..., alias="priceRange")
    
    # Owner details
    owner_email: EmailStr = Field(..., alias="ownerEmail")
    owner_mobile: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="ownerMobile")
    owner_phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="ownerPhone")
    venue_phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="venuePhone")
    owner_first_name: str = Field(..., min_length=1, max_length=50, alias="ownerFirstName")
    owner_last_name: str = Field(..., min_length=1, max_length=50, alias="ownerLastName")
    owner_password: str = Field(..., min_length=8, max_length=128, alias="ownerPassword")
    confirm_password: str = Field(..., min_length=8, max_length=128, alias="confirmPassword")
    
    class Config:
        populate_by_name = True
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'owner_password' in values and v != values['owner_password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('owner_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    def get_owner_mobile_number(self) -> Optional[str]:
        """Get owner mobile number from any available field"""
        return self.owner_mobile or self.owner_phone
    
    def get_venue_mobile_number(self) -> Optional[str]:
        """Get venue mobile number from any available field"""
        return self.venue_mobile or self.venue_phone or self.get_owner_mobile_number()


# =============================================================================
# QR CODE AND PUBLIC ACCESS SCHEMAS
# =============================================================================

class QRCodeData(BaseModel):
    """QR code data structure"""
    venue_id: str
    table_id: str
    table_number: int
    encrypted_token: str
    generated_at: datetime


class MenuPublicAccess(BaseModel):
    """Public menu access response"""
    venue: VenuePublicInfo
    table: Optional[Dict[str, Any]] = None
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    special_offers: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_preparation_times: Dict[str, int] = Field(default_factory=dict)


class VenueOperatingStatus(BaseModel):
    """Current venue operating status"""
    venue_id: str
    is_open: bool
    current_status: VenueStatus
    next_opening: Optional[datetime] = None
    next_closing: Optional[datetime] = None
    break_time: Optional[Dict[str, datetime]] = None
    message: str


class OrderValidationResponse(BaseModel):
    """Response for order validation"""
    is_valid: bool
    venue_open: bool
    items_available: List[str] = Field(default_factory=list)
    items_unavailable: List[str] = Field(default_factory=list)
    estimated_total: float = Field(default=0.0)
    estimated_preparation_time: Optional[int] = None
    message: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class SalesAnalytics(BaseSchema):
    """Consolidated sales analytics schema"""
    total_revenue: float
    total_orders: int
    average_order_value: float
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_by_day: List[Dict[str, Any]] = Field(default_factory=list)
    orders_by_status: List[Dict[str, Any]] = Field(default_factory=list)


class VenueAnalytics(BaseModel):
    """Venue analytics data"""
    venue_id: str
    venue_name: str
    period: str
    total_orders: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0
    total_customers: int = 0
    new_customers: int = 0
    returning_customers: int = 0
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    peak_hours: List[Dict[str, Any]] = Field(default_factory=list)
    table_utilization: float = 0.0
    customer_satisfaction: float = 0.0
    order_status_breakdown: Dict[str, int] = Field(default_factory=dict)


class DashboardStats(BaseSchema):
    """Dashboard statistics"""
    total_orders_today: int = Field(default=0)
    total_revenue_today: float = Field(default=0.0)
    pending_orders: int = Field(default=0)
    active_customers: int = Field(default=0)
    average_order_value: float = Field(default=0.0)
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardData(BaseModel):
    """Dashboard data based on user role"""
    user_role: UserRole
    workspace_id: str
    venue_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)
    analytics: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = Field(default_factory=list)


class SuperAdminDashboard(DashboardData):
    """SuperAdmin dashboard with workspace-wide data"""
    all_venues: List[Dict[str, Any]] = Field(default_factory=list)
    workspace_analytics: Dict[str, Any] = Field(default_factory=dict)
    user_management: Dict[str, Any] = Field(default_factory=dict)


class AdminDashboard(DashboardData):
    """Admin dashboard with venue-specific data"""
    venue_analytics: Optional[VenueAnalytics] = None
    staff_performance: Dict[str, Any] = Field(default_factory=dict)
    inventory_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class OperatorDashboard(DashboardData):
    """Operator dashboard with operational data"""
    active_orders: List[Dict[str, Any]] = Field(default_factory=list)
    table_status: List[Dict[str, Any]] = Field(default_factory=list)
    today_summary: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class AuthToken(BaseSchema):
    """Authentication token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: User


class Token(BaseSchema):
    """Simple token response"""
    access_token: str
    token_type: str = "bearer"
    user: User


class ApiResponse(BaseSchema):
    """Standard API response"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseSchema):
    """Paginated response"""
    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ErrorResponse(BaseSchema):
    """Error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceOnboardingResponse(BaseModel):
    """Response after successful workspace onboarding"""
    success: bool
    workspace_id: str
    default_venue_id: str
    superadmin_user_id: str
    access_token: str
    refresh_token: str
    message: str
    next_steps: List[str] = Field(default_factory=list)

class OrderCreationResponse(BaseModel):
    """Response after order creation"""
    success: bool
    order_id: str
    order_number: str
    estimated_preparation_time: Optional[int] = None
    total_amount: float
    payment_required: bool
    message: str
    customer_id: str
# =============================================================================
# FILE UPLOAD SCHEMAS
# =============================================================================
class ImageUploadResponse(BaseSchema):
    """Image upload response"""
    success: bool = True
    file_url: HttpUrl
    file_name: str
    file_size: int
    content_type: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)

class BulkImageUploadResponse(BaseSchema):
    """Bulk image upload response"""
    success: bool = True
    uploaded_files: List[ImageUploadResponse]
    failed_files: List[Dict[str, str]] = Field(default_factory=list)
    total_uploaded: int
    total_failed: int