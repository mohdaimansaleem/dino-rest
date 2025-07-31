"""
Dashboard Analytics Service
Role-based dashboard data and analytics for different user types
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.schemas import (
    UserRole, DashboardData, SuperAdminDashboard, AdminDashboard, OperatorDashboard,
    VenueAnalytics
)
from app.database.firestore import (
    get_workspace_repo, get_venue_repo, get_user_repo, get_order_repo,
    get_table_repo, get_customer_repo, get_menu_item_repo
)
from app.services.role_permission_service import role_permission_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DashboardAnalyticsService:
    """Service for generating role-based dashboard analytics"""
    
    def __init__(self):
        self.workspace_repo = get_workspace_repo()
        self.venue_repo = get_venue_repo()
        self.user_repo = get_user_repo()
        self.order_repo = get_order_repo()
        self.table_repo = get_table_repo()
        self.customer_repo = get_customer_repo()
        self.menu_repo = get_menu_item_repo()
    
    async def get_dashboard_data(self, user_id: str) -> DashboardData:
        """
        Get dashboard data based on user role
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user_role = UserRole(user.get('role', 'operator'))
            workspace_id = user.get('workspace_id')
            venue_id = user.get('venue_id')
            
            # Generate role-specific dashboard
            if user_role == UserRole.SUPERADMIN:
                return await self._get_superadmin_dashboard(user_id, workspace_id)
            elif user_role == UserRole.ADMIN:
                return await self._get_admin_dashboard(user_id, workspace_id, venue_id)
            elif user_role == UserRole.OPERATOR:
                return await self._get_operator_dashboard(user_id, workspace_id, venue_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user role"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Dashboard data generation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate dashboard data"
            )
    
    async def _get_superadmin_dashboard(self, user_id: str, workspace_id: str) -> SuperAdminDashboard:
        """Generate SuperAdmin dashboard with workspace-wide analytics"""
        
        # Get workspace information
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Get all venues in workspace
        venues = await self.venue_repo.get_by_workspace(workspace_id)
        active_venues = [v for v in venues if v.get('is_active', False)]
        
        # Get workspace users
        users = await self.user_repo.get_by_workspace(workspace_id)
        active_users = [u for u in users if u.get('is_active', False)]
        
        # Calculate workspace-wide metrics
        total_orders_today = 0
        total_revenue_today = 0.0
        total_customers = 0
        
        today = datetime.utcnow().date()
        
        for venue in venues:
            venue_id = venue['id']
            
            # Get today's orders for this venue
            venue_orders = await self.order_repo.get_by_venue(venue_id, limit=1000)
            today_orders = [
                order for order in venue_orders
                if order.get('created_at') and order['created_at'].date() == today
            ]
            
            total_orders_today += len(today_orders)
            total_revenue_today += sum(
                order.get('total_amount', 0) for order in today_orders
                if order.get('payment_status') == 'paid'
            )
            
            # Get venue customers
            venue_customers = await self.customer_repo.get_by_venue(venue_id)
            total_customers += len(venue_customers)
        
        # Get recent orders across all venues
        recent_orders = []
        for venue in venues[:3]:  # Top 3 venues
            venue_orders = await self.order_repo.get_by_venue(venue['id'], limit=5)
            for order in venue_orders:
                recent_orders.append({
                    "order_id": order['id'],
                    "order_number": order.get('order_number'),
                    "venue_name": venue['name'],
                    "total_amount": order.get('total_amount', 0),
                    "status": order.get('status'),
                    "created_at": order.get('created_at')
                })
        
        # Sort by creation time and limit
        recent_orders.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        recent_orders = recent_orders[:10]
        
        # Generate alerts
        alerts = await self._generate_superadmin_alerts(workspace_id, venues)
        
        # Quick actions for SuperAdmin
        quick_actions = [
            {"action": "create_venue", "label": "Create New Venue", "icon": "plus"},
            {"action": "manage_users", "label": "Manage Users", "icon": "users"},
            {"action": "view_analytics", "label": "View Analytics", "icon": "chart"},
            {"action": "workspace_settings", "label": "Workspace Settings", "icon": "settings"}
        ]
        
        # Venue summaries
        venue_summaries = []
        for venue in active_venues:
            venue_orders = await self.order_repo.get_by_venue(venue['id'], limit=100)
            today_venue_orders = [
                order for order in venue_orders
                if order.get('created_at') and order['created_at'].date() == today
            ]
            
            venue_summaries.append({
                "id": venue['id'],
                "name": venue['name'],
                "status": venue.get('status', 'active'),
                "today_orders": len(today_venue_orders),
                "today_revenue": sum(
                    order.get('total_amount', 0) for order in today_venue_orders
                    if order.get('payment_status') == 'paid'
                ),
                "rating": venue.get('rating', 0.0),
                "is_open": True  # TODO: Check actual operating status
            })
        
        return SuperAdminDashboard(
            user_role=UserRole.SUPERADMIN,
            workspace_id=workspace_id,
            summary={
                "total_venues": len(venues),
                "active_venues": len(active_venues),
                "total_users": len(users),
                "active_users": len(active_users),
                "today_orders": total_orders_today,
                "today_revenue": total_revenue_today,
                "total_customers": total_customers
            },
            recent_orders=recent_orders,
            analytics={
                "workspace_performance": {
                    "total_venues": len(venues),
                    "revenue_trend": "up",  # TODO: Calculate actual trend
                    "order_trend": "up",
                    "customer_growth": "stable"
                }
            },
            alerts=alerts,
            quick_actions=quick_actions,
            all_venues=venue_summaries,
            workspace_analytics={
                "subscription_status": workspace.get('subscription_plan'),
                "trial_ends_at": workspace.get('trial_ends_at'),
                "features_used": len(workspace.get('features_enabled', [])),
                "storage_used": "45%",  # TODO: Calculate actual usage
                "api_calls_today": 1250  # TODO: Track actual API usage
            },
            user_management={
                "total_users": len(users),
                "pending_invitations": 0,  # TODO: Track invitations
                "role_distribution": self._calculate_role_distribution(users)
            }
        )
    
    async def _get_admin_dashboard(self, user_id: str, workspace_id: str, venue_id: str) -> AdminDashboard:
        """Generate Admin dashboard with venue-specific analytics"""
        
        if not venue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin user must be assigned to a venue"
            )
        
        # Get venue information
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Generate venue analytics
        venue_analytics = await self._generate_venue_analytics(venue_id)
        
        # Get recent orders for this venue
        recent_orders = await self._get_venue_recent_orders(venue_id, limit=10)
        
        # Get staff performance (operators in this venue)
        staff_performance = await self._get_staff_performance(venue_id)
        
        # Generate inventory alerts (mock for now)
        inventory_alerts = [
            {"item": "Tomatoes", "level": "low", "action": "reorder"},
            {"item": "Chicken", "level": "medium", "action": "monitor"}
        ]
        
        # Generate alerts
        alerts = await self._generate_admin_alerts(venue_id)
        
        # Quick actions for Admin
        quick_actions = [
            {"action": "view_orders", "label": "View Orders", "icon": "list"},
            {"action": "manage_menu", "label": "Manage Menu", "icon": "menu"},
            {"action": "manage_tables", "label": "Manage Tables", "icon": "table"},
            {"action": "add_operator", "label": "Add Operator", "icon": "user-plus"}
        ]
        
        return AdminDashboard(
            user_role=UserRole.ADMIN,
            workspace_id=workspace_id,
            venue_id=venue_id,
            summary={
                "venue_name": venue['name'],
                "today_orders": venue_analytics.total_orders,
                "today_revenue": venue_analytics.total_revenue,
                "active_tables": await self._get_active_tables_count(venue_id),
                "staff_count": len(await self.user_repo.query([
                    ('venue_id', '==', venue_id),
                    ('is_active', '==', True)
                ]))
            },
            recent_orders=recent_orders,
            analytics={
                "venue_performance": {
                    "revenue_trend": "up",
                    "order_trend": "stable",
                    "customer_satisfaction": venue_analytics.customer_satisfaction,
                    "table_utilization": venue_analytics.table_utilization
                }
            },
            alerts=alerts,
            quick_actions=quick_actions,
            venue_analytics=venue_analytics,
            staff_performance=staff_performance,
            inventory_alerts=inventory_alerts
        )
    
    async def _get_operator_dashboard(self, user_id: str, workspace_id: str, venue_id: str) -> OperatorDashboard:
        """Generate Operator dashboard with limited, operational data"""
        
        if not venue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operator user must be assigned to a venue"
            )
        
        # Get active orders for the venue
        active_orders = await self._get_active_orders(venue_id)
        
        # Get table status
        table_status = await self._get_table_status(venue_id)
        
        # Get today's summary
        today_summary = await self._get_today_summary(venue_id)
        
        # Generate alerts for operator
        alerts = [
            {"type": "info", "message": f"{len(active_orders)} active orders"},
            {"type": "warning", "message": "Table 5 needs cleaning"}
        ]
        
        # Quick actions for Operator
        quick_actions = [
            {"action": "view_orders", "label": "View Orders", "icon": "list"},
            {"action": "update_tables", "label": "Update Tables", "icon": "table"},
            {"action": "mark_ready", "label": "Mark Order Ready", "icon": "check"}
        ]
        
        return OperatorDashboard(
            user_role=UserRole.OPERATOR,
            workspace_id=workspace_id,
            venue_id=venue_id,
            summary={
                "active_orders": len(active_orders),
                "pending_orders": len([o for o in active_orders if o.get('status') == 'pending']),
                "ready_orders": len([o for o in active_orders if o.get('status') == 'ready']),
                "occupied_tables": len([t for t in table_status if t.get('status') == 'occupied'])
            },
            recent_orders=[],  # Operators don't need recent orders history
            analytics={},  # Limited analytics for operators
            alerts=alerts,
            quick_actions=quick_actions,
            active_orders=active_orders,
            table_status=table_status,
            today_summary=today_summary
        )
    
    async def _generate_venue_analytics(self, venue_id: str) -> VenueAnalytics:
        """Generate comprehensive venue analytics"""
        
        venue = await self.venue_repo.get_by_id(venue_id)
        
        # Get orders for analysis (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        orders = await self.order_repo.get_by_venue(venue_id, limit=1000)
        period_orders = [
            order for order in orders
            if order.get('created_at') and start_date <= order['created_at'] <= end_date
        ]
        
        # Calculate metrics
        total_orders = len(period_orders)
        total_revenue = sum(
            order.get('total_amount', 0) for order in period_orders
            if order.get('payment_status') == 'paid'
        )
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Customer metrics
        customers = await self.customer_repo.get_by_venue(venue_id)
        new_customers = len([
            c for c in customers
            if c.get('created_at') and c['created_at'] >= start_date
        ])
        returning_customers = len(customers) - new_customers
        
        # Popular items analysis
        item_counts = {}
        for order in period_orders:
            for item in order.get('items', []):
                item_name = item.get('menu_item_name', 'Unknown')
                item_counts[item_name] = item_counts.get(item_name, 0) + item.get('quantity', 1)
        
        popular_items = [
            {"name": name, "orders": count}
            for name, count in sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Peak hours analysis (mock for now)
        peak_hours = [
            {"hour": "12:00-13:00", "orders": 25},
            {"hour": "19:00-20:00", "orders": 30},
            {"hour": "20:00-21:00", "orders": 28}
        ]
        
        # Order status breakdown
        status_breakdown = {}
        for order in period_orders:
            status = order.get('status', 'unknown')
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        return VenueAnalytics(
            venue_id=venue_id,
            venue_name=venue.get('name', 'Unknown'),
            period=f"{start_date.date()} to {end_date.date()}",
            total_orders=total_orders,
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            total_customers=len(customers),
            new_customers=new_customers,
            returning_customers=returning_customers,
            popular_items=popular_items,
            peak_hours=peak_hours,
            table_utilization=75.0,  # TODO: Calculate actual utilization
            customer_satisfaction=4.2,  # TODO: Calculate from feedback
            order_status_breakdown=status_breakdown
        )
    
    async def _get_venue_recent_orders(self, venue_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent orders for a venue"""
        
        orders = await self.order_repo.get_by_venue(venue_id, limit=limit)
        
        recent_orders = []
        for order in orders:
            recent_orders.append({
                "order_id": order['id'],
                "order_number": order.get('order_number'),
                "customer_name": "Customer",  # TODO: Get from customer record
                "total_amount": order.get('total_amount', 0),
                "status": order.get('status'),
                "created_at": order.get('created_at'),
                "table_number": None  # TODO: Get from table record
            })
        
        return recent_orders
    
    async def _get_active_orders(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get active orders for venue"""
        
        orders = await self.order_repo.get_by_venue(venue_id, limit=100)
        
        active_statuses = ['pending', 'confirmed', 'preparing', 'ready']
        active_orders = [
            {
                "order_id": order['id'],
                "order_number": order.get('order_number'),
                "status": order.get('status'),
                "total_amount": order.get('total_amount', 0),
                "created_at": order.get('created_at'),
                "estimated_ready_time": order.get('estimated_ready_time'),
                "table_number": None,  # TODO: Get from table
                "items_count": len(order.get('items', []))
            }
            for order in orders
            if order.get('status') in active_statuses
        ]
        
        return active_orders
    
    async def _get_table_status(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get table status for venue"""
        
        tables = await self.table_repo.get_by_venue(venue_id)
        
        table_status = []
        for table in tables:
            if table.get('is_active', False):
                table_status.append({
                    "table_id": table['id'],
                    "table_number": table.get('table_number'),
                    "capacity": table.get('capacity', 4),
                    "status": table.get('table_status', 'available'),
                    "location": table.get('location', ''),
                    "last_occupied": table.get('last_occupied')
                })
        
        return table_status
    
    async def _get_today_summary(self, venue_id: str) -> Dict[str, Any]:
        """Get today's summary for venue"""
        
        today = datetime.utcnow().date()
        orders = await self.order_repo.get_by_venue(venue_id, limit=200)
        
        today_orders = [
            order for order in orders
            if order.get('created_at') and order['created_at'].date() == today
        ]
        
        today_revenue = sum(
            order.get('total_amount', 0) for order in today_orders
            if order.get('payment_status') == 'paid'
        )
        
        return {
            "date": today.isoformat(),
            "total_orders": len(today_orders),
            "total_revenue": today_revenue,
            "average_order_value": today_revenue / len(today_orders) if today_orders else 0,
            "peak_hour": "12:00-13:00",  # TODO: Calculate actual peak
            "busiest_table": "Table 5"  # TODO: Calculate actual busiest
        }
    
    async def _get_staff_performance(self, venue_id: str) -> Dict[str, Any]:
        """Get staff performance metrics"""
        
        staff = await self.user_repo.query([
            ('venue_id', '==', venue_id),
            ('role', '==', 'operator'),
            ('is_active', '==', True)
        ])
        
        return {
            "total_staff": len(staff),
            "active_today": len(staff),  # TODO: Track actual activity
            "performance_metrics": [
                {"name": "John Doe", "orders_handled": 25, "rating": 4.5},
                {"name": "Jane Smith", "orders_handled": 30, "rating": 4.8}
            ]
        }
    
    async def _get_active_tables_count(self, venue_id: str) -> int:
        """Get count of active tables"""
        
        tables = await self.table_repo.get_by_venue(venue_id)
        return len([t for t in tables if t.get('is_active', False)])
    
    async def _generate_superadmin_alerts(self, workspace_id: str, venues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate alerts for SuperAdmin"""
        
        alerts = []
        
        # Check for inactive venues
        inactive_venues = [v for v in venues if not v.get('is_active', False)]
        if inactive_venues:
            alerts.append({
                "type": "warning",
                "message": f"{len(inactive_venues)} venues are inactive",
                "action": "review_venues"
            })
        
        # Check subscription status
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if workspace and workspace.get('subscription_plan') == 'trial':
            trial_ends = workspace.get('trial_ends_at')
            if trial_ends and trial_ends <= datetime.utcnow() + timedelta(days=7):
                alerts.append({
                    "type": "urgent",
                    "message": "Trial period ending soon",
                    "action": "upgrade_subscription"
                })
        
        return alerts
    
    async def _generate_admin_alerts(self, venue_id: str) -> List[Dict[str, Any]]:
        """Generate alerts for Admin"""
        
        alerts = []
        
        # Check for pending orders
        orders = await self.order_repo.get_by_venue(venue_id, limit=50)
        pending_orders = [o for o in orders if o.get('status') == 'pending']
        
        if len(pending_orders) > 5:
            alerts.append({
                "type": "warning",
                "message": f"{len(pending_orders)} orders pending confirmation",
                "action": "review_orders"
            })
        
        return alerts
    
    def _calculate_role_distribution(self, users: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate role distribution in workspace"""
        
        distribution = {"superadmin": 0, "admin": 0, "operator": 0}
        
        for user in users:
            role = user.get('role', 'operator')
            if role in distribution:
                distribution[role] += 1
        
        return distribution


# Service instance
dashboard_analytics_service = DashboardAnalyticsService()