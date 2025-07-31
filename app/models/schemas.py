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
    CUSTOMER = "customer"     # Customer role for orders


class BusinessType(str, Enum):
    """Business types"""
    VENUE = "venue"
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
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    SERVED = "served"
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
    DELIVERY = "delivery"


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


class Gender(str, Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


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
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
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
# WORKSPACE SCHEMAS
# =============================================================================

class WorkspaceBase(BaseSchema):
    """Base workspace schema"""
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    business_type: BusinessType


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating workspace"""
    pass


class WorkspaceUpdate(BaseSchema):
    """Schema for updating workspace"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    business_type: Optional[BusinessType] = None
    is_active: Optional[bool] = None


class Workspace(WorkspaceBase, TimestampMixin):
    """Complete workspace schema"""
    id: str
    name: str  # Auto-generated unique name
    owner_id: str
    venue_ids: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserAddress(BaseSchema):
    """User address schema"""
    id: Optional[str] = None
    label: str = Field(..., min_length=1, max_length=50)
    address_line_1: str = Field(..., min_length=5, max_length=200)
    address_line_2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=5, max_length=10)
    country: str = Field(default="India", max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_default: bool = Field(default=False)


class UserPreferences(BaseSchema):
    """User preferences schema"""
    dietary_restrictions: List[str] = Field(default_factory=list)
    favorite_cuisines: List[str] = Field(default_factory=list)
    spice_level: Optional[str] = Field(None, pattern="^(mild|medium|hot|extra_hot)$")
    notifications_enabled: bool = Field(default=True)
    email_notifications: bool = Field(default=True)
    sms_notifications: bool = Field(default=False)


class UserBase(BaseSchema):
    """Base user schema"""
    email: EmailStr
    phone: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)


class UserCreate(UserBase):
    """Schema for creating users"""
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    role_id: Optional[str] = None  # Role ID for database reference
    workspace_id: Optional[str] = None
    venue_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None

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
    phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    is_active: Optional[bool] = None


class User(UserBase, TimestampMixin):
    """Complete user schema"""
    id: str
    workspace_id: Optional[str] = None
    venue_id: Optional[str] = None
    role_id: Optional[str] = None  # Role ID for database reference
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None


# =============================================================================
# VENUE SCHEMAS (Unified from Cafe)
# =============================================================================

class VenueBase(BaseSchema):
    """Base venue schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    location: VenueLocation
    phone: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: EmailStr
    website: Optional[HttpUrl] = None
    cuisine_types: List[str] = Field(default_factory=list)
    price_range: PriceRange
    operating_hours: List[VenueOperatingHours] = Field(default_factory=list)
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE


class VenueCreate(VenueBase):
    """Schema for creating venues"""
    workspace_id: str
    admin_id: Optional[str] = None  # Will be set automatically


class VenueUpdate(BaseSchema):
    """Schema for updating venues"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    logo_url: Optional[HttpUrl] = None
    cuisine_types: Optional[List[str]] = None
    price_range: Optional[PriceRange] = None
    operating_hours: Optional[List[VenueOperatingHours]] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    subscription_status: Optional[SubscriptionStatus] = None
    status: Optional[VenueStatus] = None
    is_active: Optional[bool] = None


class Venue(VenueBase, TimestampMixin):
    """Complete venue schema"""
    id: str
    workspace_id: str
    admin_id: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    status: VenueStatus = VenueStatus.ACTIVE
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    rating: float = Field(default=0.0, ge=0, le=5)
    total_reviews: int = Field(default=0)


class VenuePublicInfo(BaseModel):
    """Public venue information for QR access"""
    id: str
    name: str
    description: Optional[str] = None
    cuisine_types: List[str] = Field(default_factory=list)
    location: VenueLocation
    phone: str
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


class NutritionalInfo(BaseSchema):
    """Nutritional information schema"""
    calories: Optional[int] = Field(None, ge=0)


class MenuItemBase(BaseSchema):
    """Base menu item schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    category_id: str
    is_vegetarian: bool = Field(default=True)
    is_vegan: bool = Field(default=False)
    is_gluten_free: bool = Field(default=False)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)
    nutritional_info: Optional[NutritionalInfo] = None


class MenuItemCreate(MenuItemBase):
    """Schema for creating menu items"""
    venue_id: str


class MenuItemUpdate(BaseSchema):
    """Schema for updating menu items"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    spice_level: Optional[SpiceLevel] = None
    preparation_time_minutes: Optional[int] = Field(None, ge=5, le=120)
    nutritional_info: Optional[NutritionalInfo] = None
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
    qr_code: str  # Encrypted venue_id + table_number
    qr_code_url: Optional[str] = None
    table_status: TableStatus = TableStatus.AVAILABLE
    is_active: bool = Field(default=True)


# =============================================================================
# CUSTOMER SCHEMAS
# =============================================================================

class CustomerBase(BaseSchema):
    """Base customer schema"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: Optional[EmailStr] = None


class CustomerCreate(CustomerBase):
    """Schema for creating customers"""
    date_of_birth: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    dietary_restrictions: Optional[List[str]] = Field(default_factory=list)
    marketing_consent: bool = Field(default=False)


class CustomerUpdate(BaseSchema):
    """Schema for updating customers"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$")
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class Customer(CustomerBase, TimestampMixin):
    """Complete customer schema"""
    id: str
    customer_type: CustomerType = CustomerType.NEW
    total_orders: int = Field(default=0)
    total_spent: float = Field(default=0.0)
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    dietary_restrictions: List[str] = Field(default_factory=list)
    loyalty_points: int = Field(default=0)
    marketing_consent: bool = Field(default=False)
    is_active: bool = Field(default=True)


# =============================================================================
# ORDER SCHEMAS
# =============================================================================

class OrderItemBase(BaseSchema):
    """Base order item schema"""
    menu_item_id: str
    menu_item_name: str
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)
    special_instructions: Optional[str] = Field(None, max_length=500)


class OrderItemCreate(BaseSchema):
    """Schema for creating order items"""
    menu_item_id: str
    variant_id: Optional[str] = None
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
    estimated_guests: Optional[int] = Field(None, ge=1, le=20)


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
    is_system_role: bool = Field(default=True)


class PermissionBase(BaseSchema):
    """Base permission schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    resource: str = Field(..., pattern="^(workspace|venue|menu|order|user|analytics|table)$")
    action: str = Field(..., pattern="^(create|read|update|delete|manage)$")
    scope: str = Field(..., pattern="^(own|venue|workspace|all)$")


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

class OwnerDetails(BaseModel):
    """Owner/SuperAdmin details for workspace creation"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    id_proof_type: Optional[str] = Field(None, max_length=50)
    id_proof_number: Optional[str] = Field(None, max_length=50)


class WorkspaceOnboardingCreate(BaseModel):
    """Complete workspace onboarding schema"""
    workspace_name: str = Field(..., min_length=2, max_length=100)
    business_type: str = Field(..., min_length=2, max_length=50)
    business_registration_number: Optional[str] = Field(None, max_length=50)
    tax_id: Optional[str] = Field(None, max_length=50)
    default_venue: VenueCreate
    owner_details: OwnerDetails
    subscription_plan: str = Field(default="trial")
    billing_address: Optional[VenueLocation] = None
    terms_accepted: bool = Field(..., description="Must accept terms and conditions")
    marketing_consent: bool = Field(default=False)


class WorkspaceRegistration(BaseSchema):
    """Workspace registration schema"""
    # Workspace details
    workspace_name: str = Field(..., min_length=1, max_length=100, alias="workspaceName")
    workspace_description: Optional[str] = Field(None, max_length=500, alias="workspaceDescription")
    
    # Venue details
    venue_name: str = Field(..., min_length=1, max_length=100, alias="venueName")
    venue_description: Optional[str] = Field(None, max_length=1000, alias="venueDescription")
    venue_location: VenueLocation = Field(..., alias="venueLocation")
    venue_phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="venuePhone")
    venue_email: Optional[EmailStr] = Field(None, alias="venueEmail")
    venue_website: Optional[HttpUrl] = Field(None, alias="venueWebsite")
    price_range: PriceRange = Field(..., alias="priceRange")
    venu_type: BusinessType = Field(..., alias="venuType")
    
    # Owner details
    owner_email: EmailStr = Field(..., alias="ownerEmail")
    owner_phone: Optional[str] = Field(None, pattern="^[+]?[1-9]?[0-9]{7,15}$", alias="ownerPhone")
    owner_first_name: str = Field(..., min_length=1, max_length=50, alias="ownerFirstName")
    owner_last_name: str = Field(..., min_length=1, max_length=50, alias="ownerLastName")
    owner_password: str = Field(..., min_length=8, max_length=128, alias="ownerPassword")
    confirm_password: str = Field(..., min_length=8, max_length=128, alias="confirmPassword")
    
    class Config:
        allow_population_by_field_name = True
    
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

class PopularItem(BaseSchema):
    """Popular item analytics"""
    menu_item_id: str
    menu_item_name: str
    order_count: int
    revenue: float


class RevenueData(BaseSchema):
    """Revenue data analytics"""
    date: str
    revenue: float
    orders: int


class StatusData(BaseSchema):
    """Status data analytics"""
    status: OrderStatus
    count: int


class SalesAnalytics(BaseSchema):
    """Sales analytics schema"""
    total_revenue: float
    total_orders: int
    average_order_value: float
    popular_items: List[PopularItem]
    revenue_by_day: List[RevenueData]
    orders_by_status: List[StatusData]


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


class VenueCreationResponse(BaseModel):
    """Response after venue creation"""
    success: bool
    venue_id: str
    qr_codes_generated: int
    tables_created: int
    message: str


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


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def migrate_legacy_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate legacy field names to current naming convention"""
    # Map old field names to new ones
    field_mappings = {
        'cafe_id': 'venue_id',
        'cafe_name': 'venue_name',
        'cafe_description': 'venue_description',
        'cafe_address': 'venue_address',
        'cafe_phone': 'venue_phone',
        'cafe_email': 'venue_email',
        'cafe_website': 'venue_website'
    }
    
    for old_field, new_field in field_mappings.items():
        if old_field in data:
            data[new_field] = data.pop(old_field)
    
    return data