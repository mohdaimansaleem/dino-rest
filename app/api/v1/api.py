"""
Dino Multi-Venue Platform - Main API Router
Consolidated router with all platform endpoints and features
"""
from fastapi import APIRouter

# Import consolidated endpoints
from app.api.v1.endpoints import (
    # Core management endpoints
    user,
    venue, 
    workspace,
    menu,
    table,
    order,
    
    # Multi-venue platform endpoints
    dashboard,
    
    # Essential endpoints
    auth,
    
    # Validation endpoints
    validation
)

# Import API documentation
from app.core.api_docs import setup_api_documentation

api_router = APIRouter()

# =============================================================================
# CORE MANAGEMENT ENDPOINTS (Enhanced)
# =============================================================================

# User Management (Enhanced)
api_router.include_router(
    user.router, 
    prefix="/users", 
    tags=["users"],
    responses={
        404: {"description": "User not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# Venue Management (Enhanced)
api_router.include_router(
    venue.router, 
    prefix="/venues", 
    tags=["venues"],
    responses={
        404: {"description": "Venue not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# Workspace Management (Enhanced)
api_router.include_router(
    workspace.router, 
    prefix="/workspaces", 
    tags=["workspaces"],
    responses={
        404: {"description": "Workspace not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# Menu Management (Enhanced)
api_router.include_router(
    menu.router, 
    prefix="/menu", 
    tags=["menu"],
    responses={
        404: {"description": "Menu item/category not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# Table Management (Enhanced)
api_router.include_router(
    table.router, 
    prefix="/tables", 
    tags=["tables"],
    responses={
        404: {"description": "Table not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# Order Management (Enhanced)
api_router.include_router(
    order.router, 
    prefix="/orders", 
    tags=["orders"],
    responses={
        404: {"description": "Order not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# =============================================================================
# MULTI-VENUE PLATFORM ENDPOINTS
# =============================================================================

# Note: Workspace onboarding and public ordering are now consolidated 
# into workspace.py and order.py respectively

# Dashboard Analytics
api_router.include_router(
    dashboard.router, 
    prefix="/dashboard", 
    tags=["dashboard"],
    responses={
        404: {"description": "Dashboard data not found"},
        403: {"description": "Access denied"},
        401: {"description": "Authentication required"}
    }
)

# =============================================================================
# ESSENTIAL ENDPOINTS
# =============================================================================

# Authentication & Registration (Consolidated)
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["authentication"],
    responses={
        401: {"description": "Authentication failed"},
        400: {"description": "Invalid credentials"},
        409: {"description": "User already exists"}
    }
)

# Validation Endpoints
api_router.include_router(
    validation.router, 
    prefix="/validation", 
    tags=["validation"],
    responses={
        422: {"description": "Validation failed"},
        401: {"description": "Authentication required"},
        400: {"description": "Invalid request"}
    }
)

# =============================================================================
# API HEALTH CHECK
# =============================================================================

@api_router.get(
    "/health",
    summary="API Health Check",
    description="Check if the API is healthy and responsive",
    tags=["health"]
)
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy", 
        "service": "dino-multi-venue-platform",
        "version": "2.0.0",
        "platform_features": {
            "workspace_onboarding": "Complete workspace creation with venue setup",
            "role_hierarchy": "SuperAdmin → Admin → Operator with proper isolation",
            "public_ordering": "QR-based ordering with customer management",
            "venue_validation": "Operating hours and availability checking",
            "dashboard_analytics": "Role-specific dashboards and insights"
        },
        "endpoints": {
            "core_management": [
                "users", "venues", "workspaces", 
                "menu", "tables", "orders"
            ],
            "platform_features": [
                "dashboard", "workspace-onboarding", "public-ordering"
            ],
            "essential": [
                "auth"
            ]
        },
        "architecture": {
            "multi_tenancy": "Workspace-based isolation",
            "role_based_access": "Three-tier hierarchy with permissions",
            "public_api": "QR-based ordering without authentication",
            "real_time": "Live order and table status tracking"
        }
    }


# =============================================================================
# API STATISTICS ENDPOINT
# =============================================================================

@api_router.get(
    "/stats",
    summary="API Statistics",
    description="Get API usage statistics and endpoint information",
    tags=["statistics"]
)
async def get_api_statistics():
    """Get API statistics"""
    return {
        "total_endpoints": len([
            route for route in api_router.routes 
            if hasattr(route, 'methods')
        ]),
        "endpoint_groups": {
            "core_management": 6,
            "platform_features": 1,
            "essential": 1,
            "utility": 2
        },
        "features": {
            "authentication": "JWT-based with role hierarchy",
            "authorization": "Role-based access control (SuperAdmin/Admin/Operator)",
            "multi_tenancy": "Workspace-based isolation",
            "public_ordering": "QR-based ordering without authentication",
            "real_time": "Live order and table status tracking",
            "analytics": "Role-specific dashboard analytics",
            "venue_management": "Operating hours validation and management"
        },
        "data_models": {
            "workspaces": "Multi-tenant isolation with subscription management",
            "users": "Role-based permissions with venue access control",
            "venues": "Business management with operating hours",
            "menu": "Categories and items with availability tracking",
            "tables": "QR code integration with status management",
            "orders": "Complete lifecycle management with customer tracking",
            "customers": "Phone-based identification with order history",
            "analytics": "Role-specific business insights"
        }
    }


def setup_enhanced_api_router(app):
    """Setup enhanced API router with documentation"""
    # Setup API documentation
    doc_generator = setup_api_documentation(app)
    
    # Add the enhanced router to the app
    app.include_router(api_router, prefix="/api/v1")
    
    return doc_generator