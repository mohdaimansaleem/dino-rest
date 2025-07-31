# Dino Multi-Venue Platform - API Documentation

## Overview

This is the comprehensive API documentation for the Dino Multi-Venue Platform backend. The API provides complete restaurant/venue management functionality with multi-tenant workspace isolation, role-based access control, and public ordering capabilities.

**Base URL:** `http://localhost:8000/api/v1`

**Authentication:** JWT Bearer Token (except for public endpoints)

## Table of Contents

1. [Authentication & Registration](#authentication--registration)
2. [Workspace Management](#workspace-management)
3. [Venue Management](#venue-management)
4. [Menu Management](#menu-management)
5. [Table Management](#table-management)
6. [Order Management](#order-management)
7. [User Management](#user-management)
8. [Dashboard & Analytics](#dashboard--analytics)
9. [Public Ordering (QR-based)](#public-ordering-qr-based)
10. [Validation Endpoints](#validation-endpoints)
11. [Common Response Formats](#common-response-formats)
12. [Error Handling](#error-handling)

---

## Authentication & Registration

### POST `/auth/register`
Register a new user in an existing workspace.

**Request Body:**
```json
{
  "email": "user@example.com",
  "phone": "+1234567890",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "role_id": "optional_role_id",
  "workspace_id": "workspace_id",
  "venue_id": "optional_venue_id",
  "date_of_birth": "1990-01-01",
  "gender": "male"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": "user_id",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "workspace_id": "workspace_id",
    "role": "operator",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### POST `/auth/login`
Login user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "remember_me": false
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "refresh_token": "refresh_token_here",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "admin",
    "workspace_id": "workspace_id",
    "venue_id": "venue_id"
  }
}
```

### POST `/auth/register-workspace`
Register a complete new workspace with venue and superadmin user.

**Request Body:**
```json
{
  "workspace_display_name": "My Restaurant Chain",
  "workspace_description": "A chain of fine dining restaurants",
  "business_type": "restaurant",
  "venue_name": "Main Branch",
  "venue_description": "Our flagship restaurant",
  "venue_location": {
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "postal_code": "10001",
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "venue_phone": "+1234567890",
  "venue_email": "venue@example.com",
  "venue_website": "https://example.com",
  "cuisine_types": ["italian", "american"],
  "price_range": "mid_range",
  "owner_email": "owner@example.com",
  "owner_phone": "+1234567890",
  "owner_first_name": "Jane",
  "owner_last_name": "Smith",
  "owner_password": "SecurePass123",
  "confirm_password": "SecurePass123"
}
```

### GET `/auth/me`
Get current user information.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "admin",
  "workspace_id": "workspace_id",
  "venue_id": "venue_id",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### PUT `/auth/me`
Update current user information.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "date_of_birth": "1990-01-01"
}
```

### POST `/auth/change-password`
Change user password.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "OldPass123",
  "new_password": "NewPass123"
}
```

### POST `/auth/refresh`
Refresh JWT token.

**Request Body:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

### POST `/auth/logout`
Logout user (client-side token removal).

**Headers:** `Authorization: Bearer <token>`

---

## Workspace Management

### GET `/workspaces/`
Get paginated list of workspaces (Admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 10, max: 100)
- `search` (string): Search by name or description
- `is_active` (boolean): Filter by active status

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "workspace_id",
      "name": "my_restaurant_chain_abc123",
      "display_name": "My Restaurant Chain",
      "description": "A chain of fine dining restaurants",
      "business_type": "restaurant",
      "owner_id": "user_id",
      "venue_ids": ["venue1", "venue2"],
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### POST `/workspaces/`
Create a new workspace (Admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "display_name": "New Workspace",
  "description": "Description of the workspace",
  "business_type": "restaurant"
}
```

### GET `/workspaces/{workspace_id}`
Get specific workspace by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/workspaces/{workspace_id}`
Update workspace information.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "display_name": "Updated Workspace Name",
  "description": "Updated description",
  "is_active": true
}
```

### GET `/workspaces/{workspace_id}/venues`
Get all venues in workspace.

**Headers:** `Authorization: Bearer <token>`

### GET `/workspaces/{workspace_id}/users`
Get all users in workspace.

**Headers:** `Authorization: Bearer <token>`

### GET `/workspaces/{workspace_id}/statistics`
Get comprehensive workspace statistics.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "workspace_id": "workspace_id",
  "workspace_name": "My Restaurant Chain",
  "total_venues": 3,
  "active_venues": 2,
  "total_users": 15,
  "active_users": 12,
  "total_orders": 1250,
  "total_menu_items": 85,
  "created_at": "2024-01-01T00:00:00Z",
  "is_active": true
}
```

---

## Venue Management

### GET `/venues/public`
Get public venues (no authentication required).

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page (max: 50)
- `search` (string): Search by name or cuisine
- `cuisine_type` (string): Filter by cuisine type
- `price_range` (string): Filter by price range

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "venue_id",
      "name": "Main Branch",
      "description": "Our flagship restaurant",
      "location": {
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "postal_code": "10001",
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "phone": "+1234567890",
      "email": "venue@example.com",
      "website": "https://example.com",
      "cuisine_types": ["italian", "american"],
      "price_range": "mid_range",
      "rating": 4.5,
      "total_reviews": 125,
      "is_active": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### GET `/venues/public/{venue_id}`
Get public venue details by ID.

### GET `/venues/`
Get venues (authenticated - filtered by user permissions).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size`, `search` (same as public)
- `subscription_status` (string): Filter by subscription status
- `is_active` (boolean): Filter by active status

### POST `/venues/`
Create a new venue.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "New Venue",
  "description": "A great restaurant",
  "location": {
    "address": "456 Oak St",
    "city": "Los Angeles",
    "state": "CA",
    "country": "USA",
    "postal_code": "90210"
  },
  "phone": "+1987654321",
  "email": "newvenue@example.com",
  "website": "https://newvenue.com",
  "cuisine_types": ["mexican", "fusion"],
  "price_range": "premium",
  "operating_hours": [
    {
      "day_of_week": 0,
      "is_open": true,
      "open_time": "09:00:00",
      "close_time": "22:00:00",
      "is_24_hours": false
    }
  ],
  "workspace_id": "workspace_id"
}
```

### GET `/venues/{venue_id}`
Get venue by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/venues/{venue_id}`
Update venue information.

**Headers:** `Authorization: Bearer <token>`

### DELETE `/venues/{venue_id}`
Deactivate venue (soft delete).

**Headers:** `Authorization: Bearer <token>`

### POST `/venues/{venue_id}/activate`
Activate deactivated venue.

**Headers:** `Authorization: Bearer <token>`

### GET `/venues/{venue_id}/analytics`
Get venue analytics.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "venue_id": "venue_id",
  "total_menu_items": 45,
  "total_tables": 20,
  "recent_orders": 15,
  "total_customers": 350,
  "rating": 4.5,
  "total_reviews": 125,
  "subscription_status": "active",
  "is_active": true
}
```

### PUT `/venues/{venue_id}/hours`
Update venue operating hours.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
[
  {
    "day_of_week": 0,
    "is_open": true,
    "open_time": "09:00:00",
    "close_time": "22:00:00",
    "is_24_hours": false,
    "break_start": "14:00:00",
    "break_end": "16:00:00"
  }
]
```

### GET `/venues/{venue_id}/hours`
Get venue operating hours.

**Headers:** `Authorization: Bearer <token>`

---

## Menu Management

### GET `/menu/categories`
Get menu categories with pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size` (pagination)
- `venue_id` (string): Filter by venue ID
- `is_active` (boolean): Filter by active status

### POST `/menu/categories`
Create a new menu category.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Appetizers",
  "description": "Start your meal with these delicious appetizers",
  "venue_id": "venue_id"
}
```

### GET `/menu/categories/{category_id}`
Get menu category by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/menu/categories/{category_id}`
Update menu category.

**Headers:** `Authorization: Bearer <token>`

### DELETE `/menu/categories/{category_id}`
Deactivate menu category.

**Headers:** `Authorization: Bearer <token>`

### GET `/menu/items`
Get menu items with pagination and filtering.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size` (pagination)
- `venue_id` (string): Filter by venue ID
- `category_id` (string): Filter by category ID
- `is_available` (boolean): Filter by availability
- `is_vegetarian` (boolean): Filter by vegetarian
- `spice_level` (string): Filter by spice level

### POST `/menu/items`
Create a new menu item.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Margherita Pizza",
  "description": "Classic pizza with tomato sauce, mozzarella, and basil",
  "base_price": 12.99,
  "category_id": "category_id",
  "venue_id": "venue_id",
  "is_vegetarian": true,
  "is_vegan": false,
  "is_gluten_free": false,
  "spice_level": "mild",
  "preparation_time_minutes": 15,
  "nutritional_info": {
    "calories": 280
  }
}
```

### GET `/menu/items/{item_id}`
Get menu item by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/menu/items/{item_id}`
Update menu item.

**Headers:** `Authorization: Bearer <token>`

### DELETE `/menu/items/{item_id}`
Mark menu item as unavailable.

**Headers:** `Authorization: Bearer <token>`

### GET `/menu/venues/{venue_id}/categories`
Get all categories for a specific venue.

**Headers:** `Authorization: Bearer <token>`

### GET `/menu/venues/{venue_id}/items`
Get all menu items for a specific venue.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `category_id` (string): Filter by category

### GET `/menu/venues/{venue_id}/search`
Search menu items within a venue.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `q` (string, required): Search query (min 2 characters)

---

## Table Management

### GET `/tables/`
Get tables with pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size` (pagination)
- `venue_id` (string): Filter by venue ID
- `table_status` (string): Filter by table status
- `is_active` (boolean): Filter by active status

### POST `/tables/`
Create a new table with QR code.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "table_number": 5,
  "capacity": 4,
  "location": "Window side",
  "venue_id": "venue_id"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Table created successfully",
  "data": {
    "id": "table_id",
    "table_number": 5,
    "capacity": 4,
    "location": "Window side",
    "venue_id": "venue_id",
    "qr_code": "encoded_qr_data.hash",
    "table_status": "available",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### GET `/tables/{table_id}`
Get table by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/tables/{table_id}`
Update table information.

**Headers:** `Authorization: Bearer <token>`

### DELETE `/tables/{table_id}`
Deactivate table.

**Headers:** `Authorization: Bearer <token>`

### PUT `/tables/{table_id}/status`
Update table status.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "new_status": "occupied"
}
```

**Available statuses:** `available`, `booked`, `occupied`, `maintenance`, `out_of_service`

### POST `/tables/{table_id}/occupy`
Mark table as occupied.

**Headers:** `Authorization: Bearer <token>`

### POST `/tables/{table_id}/free`
Mark table as available.

**Headers:** `Authorization: Bearer <token>`

### GET `/tables/{table_id}/qr-code`
Get table QR code data.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "table_id": "table_id",
  "qr_code": "encoded_qr_data.hash",
  "qr_code_url": "https://example.com/qr/table_id.png",
  "venue_id": "venue_id",
  "table_number": 5
}
```

### POST `/tables/{table_id}/regenerate-qr`
Regenerate QR code for table.

**Headers:** `Authorization: Bearer <token>`

### POST `/tables/verify-qr`
Verify and decode table QR code.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "qr_code": "encoded_qr_data.hash"
}
```

### GET `/tables/venues/{venue_id}/tables`
Get all tables for a venue.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (string): Filter by table status

### POST `/tables/bulk-create`
Create multiple tables at once.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `venue_id` (string, required): Venue ID
- `start_number` (int, required): Starting table number
- `count` (int, required): Number of tables to create (max: 50)
- `capacity` (int): Default capacity (default: 4)
- `location` (string): Default location

---

## Order Management

### GET `/orders/`
Get orders with pagination and filtering.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size` (pagination)
- `venue_id` (string): Filter by venue ID
- `status` (string): Filter by order status
- `payment_status` (string): Filter by payment status
- `order_type` (string): Filter by order type

### POST `/orders/`
Create a new order.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "venue_id": "venue_id",
  "customer_id": "customer_id",
  "order_type": "dine_in",
  "table_id": "table_id",
  "items": [
    {
      "menu_item_id": "item_id",
      "quantity": 2,
      "special_instructions": "No onions"
    }
  ],
  "special_instructions": "Please serve quickly"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order created successfully",
  "data": {
    "id": "order_id",
    "order_number": "ORD-202401011200-ABC123",
    "venue_id": "venue_id",
    "customer_id": "customer_id",
    "items": [
      {
        "menu_item_id": "item_id",
        "menu_item_name": "Margherita Pizza",
        "quantity": 2,
        "unit_price": 12.99,
        "total_price": 25.98
      }
    ],
    "subtotal": 25.98,
    "tax_amount": 4.68,
    "total_amount": 30.66,
    "status": "pending",
    "payment_status": "pending",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### GET `/orders/{order_id}`
Get order by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/orders/{order_id}`
Update order information.

**Headers:** `Authorization: Bearer <token>`

### PUT `/orders/{order_id}/status`
Update order status.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "new_status": "confirmed"
}
```

**Available statuses:** `pending`, `confirmed`, `preparing`, `ready`, `out_for_delivery`, `delivered`, `served`, `cancelled`

### POST `/orders/{order_id}/confirm`
Confirm pending order.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `estimated_minutes` (int): Estimated preparation time

### POST `/orders/{order_id}/cancel`
Cancel order.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `reason` (string): Cancellation reason

### GET `/orders/venues/{venue_id}/orders`
Get all orders for a venue.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (string): Filter by status
- `limit` (int): Maximum number of orders (default: 50, max: 200)

### GET `/orders/venues/{venue_id}/analytics`
Get order analytics for a venue.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (datetime): Start date for analytics
- `end_date` (datetime): End date for analytics

### GET `/orders/venues/{venue_id}/live`
Get real-time order status for venue dashboard.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "venue_id": "venue_id",
  "timestamp": "2024-01-01T12:00:00Z",
  "summary": {
    "total_active_orders": 8,
    "pending_orders": 2,
    "preparing_orders": 4,
    "ready_orders": 2
  },
  "orders_by_status": {
    "pending": [...],
    "confirmed": [...],
    "preparing": [...],
    "ready": [...]
  }
}
```

---

## User Management

### GET `/users/`
Get users with pagination (Admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page`, `page_size` (pagination)
- `workspace_id` (string): Filter by workspace
- `venue_id` (string): Filter by venue
- `role` (string): Filter by role
- `is_active` (boolean): Filter by active status

### POST `/users/`
Create a new user (Admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "phone": "+1234567890",
  "first_name": "New",
  "last_name": "User",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "role_id": "role_id",
  "workspace_id": "workspace_id",
  "venue_id": "venue_id"
}
```

### GET `/users/{user_id}`
Get user by ID.

**Headers:** `Authorization: Bearer <token>`

### PUT `/users/{user_id}`
Update user information.

**Headers:** `Authorization: Bearer <token>`

### DELETE `/users/{user_id}`
Deactivate user.

**Headers:** `Authorization: Bearer <token>`

### POST `/users/{user_id}/activate`
Activate deactivated user.

**Headers:** `Authorization: Bearer <token>`

---

## Dashboard & Analytics

### GET `/dashboard/`
Get role-based dashboard data.

**Headers:** `Authorization: Bearer <token>`

**Response varies by role:**

**SuperAdmin Response:**
```json
{
  "user_role": "superadmin",
  "workspace_id": "workspace_id",
  "summary": {
    "total_venues": 5,
    "active_venues": 4,
    "total_orders": 1250,
    "total_revenue": 45000.00
  },
  "all_venues": [...],
  "workspace_analytics": {...},
  "user_management": {...},
  "alerts": [...],
  "quick_actions": [...]
}
```

**Admin Response:**
```json
{
  "user_role": "admin",
  "workspace_id": "workspace_id",
  "venue_id": "venue_id",
  "summary": {
    "today_orders": 25,
    "today_revenue": 850.00,
    "active_tables": 20,
    "occupied_tables": 12
  },
  "venue_analytics": {...},
  "staff_performance": {...},
  "inventory_alerts": [...]
}
```

**Operator Response:**
```json
{
  "user_role": "operator",
  "workspace_id": "workspace_id",
  "venue_id": "venue_id",
  "summary": {
    "active_orders": 8,
    "pending_orders": 2,
    "ready_orders": 3,
    "occupied_tables": 12
  },
  "active_orders": [...],
  "table_status": [...],
  "today_summary": {...}
}
```

### GET `/dashboard/summary`
Get quick dashboard summary.

**Headers:** `Authorization: Bearer <token>`

### GET `/dashboard/analytics/venue/{venue_id}`
Get detailed venue analytics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (datetime): Start date for analytics
- `end_date` (datetime): End date for analytics

### GET `/dashboard/analytics/workspace`
Get workspace-wide analytics (SuperAdmin only).

**Headers:** `Authorization: Bearer <token>`

### GET `/dashboard/live/orders`
Get real-time order status.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `venue_id` (string): Venue ID (required for Admin/Operator)

### GET `/dashboard/live/tables`
Get real-time table status.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `venue_id` (string): Venue ID (required for Admin/Operator)

---

## Public Ordering (QR-based)

These endpoints don't require authentication and are used for customer ordering via QR code scanning.

### GET `/orders/public/qr/{qr_code}`
Access venue menu via QR code scan.

**Response:**
```json
{
  "venue": {
    "id": "venue_id",
    "name": "Main Branch",
    "description": "Our flagship restaurant",
    "cuisine_types": ["italian", "american"],
    "location": {...},
    "phone": "+1234567890",
    "is_open": true,
    "current_wait_time": 15,
    "rating": 4.5
  },
  "table": {
    "id": "table_id",
    "table_number": 5,
    "capacity": 4
  },
  "categories": [
    {
      "id": "category_id",
      "name": "Appetizers",
      "description": "Start your meal..."
    }
  ],
  "items": [
    {
      "id": "item_id",
      "name": "Margherita Pizza",
      "description": "Classic pizza...",
      "base_price": 12.99,
      "category_id": "category_id",
      "is_available": true,
      "preparation_time_minutes": 15,
      "image_urls": [...]
    }
  ]
}
```

### GET `/orders/public/venue/{venue_id}/status`
Check venue operating status.

**Response:**
```json
{
  "venue_id": "venue_id",
  "is_open": true,
  "current_status": "active",
  "next_opening": null,
  "next_closing": "2024-01-01T22:00:00Z",
  "break_time": {
    "start": "2024-01-01T14:00:00Z",
    "end": "2024-01-01T16:00:00Z"
  },
  "message": "We're open! Kitchen closes at 10 PM."
}
```

### POST `/orders/public/validate-order`
Validate order before creation.

**Request Body:**
```json
{
  "venue_id": "venue_id",
  "table_id": "table_id",
  "items": [
    {
      "menu_item_id": "item_id",
      "quantity": 2
    }
  ]
}
```

**Response:**
```json
{
  "is_valid": true,
  "venue_open": true,
  "items_available": ["item_id"],
  "items_unavailable": [],
  "estimated_total": 30.66,
  "estimated_preparation_time": 20,
  "message": "Order is valid and can be placed",
  "errors": []
}
```

### POST `/orders/public/create-order`
Create order from public interface.

**Request Body:**
```json
{
  "venue_id": "venue_id",
  "table_id": "table_id",
  "customer": {
    "name": "John Doe",
    "phone": "+1234567890",
    "email": "john@example.com"
  },
  "items": [
    {
      "menu_item_id": "item_id",
      "quantity": 2,
      "special_instructions": "No onions"
    }
  ],
  "order_type": "qr_scan",
  "special_instructions": "Table by the window",
  "estimated_guests": 2
}
```

**Response:**
```json
{
  "success": true,
  "order_id": "order_id",
  "order_number": "ORD-202401011200-ABC123",
  "estimated_preparation_time": 20,
  "total_amount": 30.66,
  "payment_required": true,
  "message": "Order placed successfully!",
  "customer_id": "customer_id"
}
```

### GET `/orders/public/{order_id}/status`
Track order status using order ID.

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "order_id",
    "order_number": "ORD-202401011200-ABC123",
    "status": "preparing",
    "estimated_ready_time": "2024-01-01T12:20:00Z",
    "total_amount": 30.66,
    "payment_status": "paid",
    "venue_name": "Main Branch",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### GET `/orders/public/{order_id}/receipt`
Get detailed order receipt.

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "order_id",
    "order_number": "ORD-202401011200-ABC123",
    "venue": {
      "name": "Main Branch",
      "address": "123 Main St, New York, NY",
      "phone": "+1234567890"
    },
    "items": [
      {
        "menu_item_name": "Margherita Pizza",
        "quantity": 2,
        "unit_price": 12.99,
        "total_price": 25.98
      }
    ],
    "subtotal": 25.98,
    "tax_amount": 4.68,
    "total_amount": 30.66,
    "payment_status": "paid",
    "order_date": "2024-01-01T12:00:00Z",
    "table_number": 5
  }
}
```

### POST `/orders/public/{order_id}/feedback`
Submit feedback for completed order.

**Query Parameters:**
- `rating` (int, required): Rating from 1 to 5
- `feedback` (string): Optional feedback text (max 1000 chars)

**Response:**
```json
{
  "success": true,
  "message": "Thank you for your feedback!"
}
```

---

## Validation Endpoints

### POST `/validation/workspace-data`
Validate workspace data before creation.

**Request Body:**
```json
{
  "workspace_name": "My Restaurant",
  "owner_email": "owner@example.com"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### POST `/validation/venue-data`
Validate venue data before creation.

### POST `/validation/user-data`
Validate user data before creation.

### POST `/validation/menu-item-data`
Validate menu item data before creation.

---

## Common Response Formats

### Standard API Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10,
  "has_next": true,
  "has_prev": false
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "email",
    "message": "Email already exists"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful GET, PUT requests
- **201 Created**: Successful POST requests
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource already exists
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server error

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `AUTHENTICATION_REQUIRED`: JWT token required
- `ACCESS_DENIED`: Insufficient permissions
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `DUPLICATE_RESOURCE`: Resource already exists
- `VENUE_CLOSED`: Venue is not open for orders
- `ITEM_UNAVAILABLE`: Menu item is not available
- `INVALID_QR_CODE`: QR code is invalid or expired

### Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Rate Limiting

- Public endpoints: 100 requests per minute per IP
- Authenticated endpoints: 1000 requests per minute per user
- Order creation: 10 requests per minute per user

### Pagination

Most list endpoints support pagination with these parameters:
- `page`: Page number (starts from 1)
- `page_size`: Items per page (default: 10, max varies by endpoint)

### Filtering and Search

Many endpoints support filtering and search:
- Use query parameters for filtering (e.g., `is_active=true`)
- Use `search` parameter for text search
- Multiple filters can be combined

### Date/Time Format

All dates and times are in ISO 8601 format (UTC):
```
2024-01-01T12:00:00Z
```

---

## Getting Started

1. **Register a workspace**: Use `POST /auth/register-workspace` to create a complete workspace with venue and superadmin user.

2. **Login**: Use `POST /auth/login` to get JWT token.

3. **Set up venue**: Add menu categories and items, create tables with QR codes.

4. **Start taking orders**: Use the public ordering endpoints for customer orders via QR codes, or authenticated endpoints for staff-created orders.

5. **Monitor operations**: Use dashboard endpoints to track orders, analytics, and venue performance.

For any questions or issues, please refer to the API health check endpoint at `GET /api/v1/health` for system status.