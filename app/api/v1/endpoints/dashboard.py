"""
Dashboard API Endpoints
Role-based dashboard data for SuperAdmin, Admin, and Operator users
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime, timedelta

from app.models.schemas import DashboardData, VenueAnalytics, UserRole
from app.services.dashboard_analytics_service import dashboard_analytics_service
from app.services.role_permission_service import role_permission_service
from app.core.security import get_current_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# MAIN DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/",
            response_model=DashboardData,
            summary="Get Dashboard Data",
            description="Get role-based dashboard data for current user")
async def get_dashboard_data(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get dashboard data based on user role:
    - SuperAdmin: Workspace-wide analytics and venue management
    - Admin: Venue-specific analytics and staff management
    - Operator: Operational data (orders, tables)
    """
    try:
        dashboard_data = await dashboard_analytics_service.get_dashboard_data(current_user["id"])
        
        logger.info(f"Dashboard data retrieved for user {current_user['id']} - role: {dashboard_data.user_role}")
        return dashboard_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


@router.get("/summary",
            response_model=Dict[str, Any],
            summary="Get Dashboard Summary",
            description="Get quick summary metrics for dashboard")
async def get_dashboard_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get quick dashboard summary based on user role
    """
    try:
        user_role = UserRole(current_user.get("role", "operator"))
        workspace_id = current_user.get("workspace_id")
        venue_id = current_user.get("venue_id")
        
        if user_role == UserRole.SUPERADMIN:
            summary = await _get_superadmin_summary(workspace_id)
        elif user_role == UserRole.ADMIN:
            summary = await _get_admin_summary(venue_id)
        else:  # OPERATOR
            summary = await _get_operator_summary(venue_id)
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard summary"
        )


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/venue/{venue_id}",
            response_model=VenueAnalytics,
            summary="Get Venue Analytics",
            description="Get detailed analytics for a specific venue")
async def get_venue_analytics(
    venue_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed venue analytics
    - SuperAdmin: Can access any venue in workspace
    - Admin: Can access their assigned venues
    - Operator: Cannot access analytics
    """
    try:
        # Check permissions
        permission_check = await role_permission_service.validate_user_permissions(
            current_user["id"],
            ["venue:analytics"],
            venue_id=venue_id
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=permission_check.denied_reason
            )
        
        # Generate analytics
        analytics = await dashboard_analytics_service._generate_venue_analytics(venue_id)
        
        logger.info(f"Venue analytics retrieved: {venue_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Venue analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue analytics"
        )


@router.get("/analytics/workspace",
            response_model=Dict[str, Any],
            summary="Get Workspace Analytics",
            description="Get workspace-wide analytics (SuperAdmin only)")
async def get_workspace_analytics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get workspace-wide analytics (SuperAdmin only)
    """
    try:
        # Check if user is SuperAdmin
        if current_user.get("role") != UserRole.SUPERADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SuperAdmin can access workspace analytics"
            )
        
        workspace_id = current_user.get("workspace_id")
        
        # Get workspace analytics
        from app.database.firestore import get_workspace_repo, get_venue_repo, get_order_repo
        workspace_repo = get_workspace_repo()
        venue_repo = get_venue_repo()
        order_repo = get_order_repo()
        
        workspace = await workspace_repo.get_by_id(workspace_id)
        venues = await venue_repo.get_by_workspace(workspace_id)
        
        # Calculate workspace metrics
        total_orders = 0
        total_revenue = 0.0
        
        for venue in venues:
            venue_orders = await order_repo.get_by_venue(venue['id'], limit=1000)
            total_orders += len(venue_orders)
            total_revenue += sum(
                order.get('total_amount', 0) for order in venue_orders
                if order.get('payment_status') == 'paid'
            )
        
        analytics = {
            "workspace_id": workspace_id,
            "workspace_name": workspace.get('display_name'),
            "total_venues": len(venues),
            "active_venues": len([v for v in venues if v.get('is_active', False)]),
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_revenue_per_venue": total_revenue / len(venues) if venues else 0,
            "subscription_plan": workspace.get('subscription_plan'),
            "created_at": workspace.get('created_at')
        }
        
        return {
            "success": True,
            "data": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace analytics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace analytics"
        )


# =============================================================================
# REAL-TIME DATA ENDPOINTS
# =============================================================================

@router.get("/live/orders",
            response_model=Dict[str, Any],
            summary="Get Live Orders",
            description="Get real-time order status for venue")
async def get_live_orders(
    venue_id: Optional[str] = Query(None, description="Venue ID (required for Admin/Operator)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get live order status
    """
    try:
        user_role = UserRole(current_user.get("role", "operator"))
        
        # Determine venue ID based on role
        if user_role == UserRole.SUPERADMIN:
            if not venue_id:
                # Get default venue or first venue
                accessible_venues = await role_permission_service.get_user_accessible_venues(current_user["id"])
                venue_id = accessible_venues[0] if accessible_venues else None
        elif user_role in [UserRole.ADMIN, UserRole.OPERATOR]:
            if not venue_id:
                venue_id = current_user.get("venue_id")
        
        if not venue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue ID is required"
            )
        
        # Check permissions
        permission_check = await role_permission_service.validate_user_permissions(
            current_user["id"],
            ["order:read"],
            venue_id=venue_id
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=permission_check.denied_reason
            )
        
        # Get live orders
        active_orders = await dashboard_analytics_service._get_active_orders(venue_id)
        
        # Group by status
        orders_by_status = {
            "pending": [o for o in active_orders if o.get('status') == 'pending'],
            "confirmed": [o for o in active_orders if o.get('status') == 'confirmed'],
            "preparing": [o for o in active_orders if o.get('status') == 'preparing'],
            "ready": [o for o in active_orders if o.get('status') == 'ready']
        }
        
        return {
            "success": True,
            "data": {
                "venue_id": venue_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_active": len(active_orders),
                "orders_by_status": orders_by_status,
                "summary": {
                    "pending": len(orders_by_status["pending"]),
                    "confirmed": len(orders_by_status["confirmed"]),
                    "preparing": len(orders_by_status["preparing"]),
                    "ready": len(orders_by_status["ready"])
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live orders error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get live orders"
        )


@router.get("/live/tables",
            response_model=Dict[str, Any],
            summary="Get Live Table Status",
            description="Get real-time table status for venue")
async def get_live_table_status(
    venue_id: Optional[str] = Query(None, description="Venue ID (required for Admin/Operator)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get live table status
    """
    try:
        user_role = UserRole(current_user.get("role", "operator"))
        
        # Determine venue ID based on role
        if user_role == UserRole.SUPERADMIN:
            if not venue_id:
                accessible_venues = await role_permission_service.get_user_accessible_venues(current_user["id"])
                venue_id = accessible_venues[0] if accessible_venues else None
        elif user_role in [UserRole.ADMIN, UserRole.OPERATOR]:
            if not venue_id:
                venue_id = current_user.get("venue_id")
        
        if not venue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue ID is required"
            )
        
        # Check permissions
        permission_check = await role_permission_service.validate_user_permissions(
            current_user["id"],
            ["table:read"],
            venue_id=venue_id
        )
        
        if not permission_check.has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=permission_check.denied_reason
            )
        
        # Get table status
        table_status = await dashboard_analytics_service._get_table_status(venue_id)
        
        # Group by status
        tables_by_status = {
            "available": [t for t in table_status if t.get('status') == 'available'],
            "occupied": [t for t in table_status if t.get('status') == 'occupied'],
            "reserved": [t for t in table_status if t.get('status') == 'reserved'],
            "cleaning": [t for t in table_status if t.get('status') == 'cleaning']
        }
        
        return {
            "success": True,
            "data": {
                "venue_id": venue_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_tables": len(table_status),
                "tables_by_status": tables_by_status,
                "summary": {
                    "available": len(tables_by_status["available"]),
                    "occupied": len(tables_by_status["occupied"]),
                    "reserved": len(tables_by_status["reserved"]),
                    "cleaning": len(tables_by_status["cleaning"])
                },
                "utilization_rate": (len(tables_by_status["occupied"]) / len(table_status) * 100) if table_status else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live table status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get table status"
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_superadmin_summary(workspace_id: str) -> Dict[str, Any]:
    """Get SuperAdmin dashboard summary"""
    from app.database.firestore import get_workspace_repo, get_venue_repo, get_order_repo
    
    workspace_repo = get_workspace_repo()
    venue_repo = get_venue_repo()
    order_repo = get_order_repo()
    
    workspace = await workspace_repo.get_by_id(workspace_id)
    venues = await venue_repo.get_by_workspace(workspace_id)
    
    today = datetime.utcnow().date()
    today_orders = 0
    today_revenue = 0.0
    
    for venue in venues:
        venue_orders = await order_repo.get_by_venue(venue['id'], limit=100)
        venue_today_orders = [
            o for o in venue_orders
            if o.get('created_at') and o['created_at'].date() == today
        ]
        today_orders += len(venue_today_orders)
        today_revenue += sum(
            o.get('total_amount', 0) for o in venue_today_orders
            if o.get('payment_status') == 'paid'
        )
    
    return {
        "total_venues": len(venues),
        "active_venues": len([v for v in venues if v.get('is_active', False)]),
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "subscription_plan": workspace.get('subscription_plan') if workspace else None
    }


async def _get_admin_summary(venue_id: str) -> Dict[str, Any]:
    """Get Admin dashboard summary"""
    from app.database.firestore import get_order_repo, get_table_repo
    
    order_repo = get_order_repo()
    table_repo = get_table_repo()
    
    today = datetime.utcnow().date()
    orders = await order_repo.get_by_venue(venue_id, limit=100)
    today_orders = [
        o for o in orders
        if o.get('created_at') and o['created_at'].date() == today
    ]
    
    tables = await table_repo.get_by_venue(venue_id)
    occupied_tables = [t for t in tables if t.get('table_status') == 'occupied']
    
    return {
        "today_orders": len(today_orders),
        "today_revenue": sum(
            o.get('total_amount', 0) for o in today_orders
            if o.get('payment_status') == 'paid'
        ),
        "active_tables": len([t for t in tables if t.get('is_active', False)]),
        "occupied_tables": len(occupied_tables)
    }


async def _get_operator_summary(venue_id: str) -> Dict[str, Any]:
    """Get Operator dashboard summary"""
    from app.database.firestore import get_order_repo, get_table_repo
    
    order_repo = get_order_repo()
    table_repo = get_table_repo()
    
    orders = await order_repo.get_by_venue(venue_id, limit=50)
    active_orders = [
        o for o in orders
        if o.get('status') in ['pending', 'confirmed', 'preparing', 'ready']
    ]
    
    tables = await table_repo.get_by_venue(venue_id)
    occupied_tables = [t for t in tables if t.get('table_status') == 'occupied']
    
    return {
        "active_orders": len(active_orders),
        "pending_orders": len([o for o in active_orders if o.get('status') == 'pending']),
        "ready_orders": len([o for o in active_orders if o.get('status') == 'ready']),
        "occupied_tables": len(occupied_tables)
    }