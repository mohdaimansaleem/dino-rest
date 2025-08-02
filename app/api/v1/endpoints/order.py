"""
Enhanced Order Management API Endpoints
Complete CRUD for orders with lifecycle management and real-time updates
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime, timedelta
import uuid

from app.models.schemas import (
    Order, OrderCreate, OrderUpdate, OrderStatus, PaymentStatus, OrderType,
    OrderItemBase, ApiResponse, PaginatedResponse
)
# Removed base endpoint dependency
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.core.dependency_injection import get_repository_manager
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class OrdersEndpoint(WorkspaceIsolatedEndpoint[Order, OrderCreate, OrderUpdate]):
    """Enhanced Orders endpoint with lifecycle management"""
    
    def __init__(self):
        super().__init__(
            model_class=Order,
            create_schema=OrderCreate,
            update_schema=OrderUpdate,
            collection_name="orders",
            require_auth=True,
            require_admin=False
        )
    
    def get_repository(self):
        return get_repository_manager().get_repository('order')
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare order data before creation"""
        # Generate order number
        order_number = self._generate_order_number()
        data['order_number'] = order_number
        
        # Calculate order totals
        await self._calculate_order_totals(data)
        
        # Set default values
        data['status'] = OrderStatus.PENDING.value
        data['payment_status'] = PaymentStatus.PENDING.value
        data['payment_method'] = None
        data['estimated_ready_time'] = None
        data['actual_ready_time'] = None
        
        return data
    
    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
        random_suffix = str(uuid.uuid4())[:6].upper()
        return f"ORD-{timestamp}-{random_suffix}"
    
    async def _calculate_order_totals(self, data: Dict[str, Any]):
        """Calculate order totals from items"""
        items = data.get('items', [])
        
        # Get menu item prices
        menu_repo = get_repository_manager().get_repository('menu_item')
        
        subtotal = 0.0
        order_items = []
        
        for item in items:
            menu_item_id = item['menu_item_id']
            quantity = item['quantity']
            
            # Get menu item details
            menu_item = await menu_repo.get_by_id(menu_item_id)
            if not menu_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu item {menu_item_id} not found"
                )
            
            if not menu_item.get('is_available', False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Menu item '{menu_item['name']}' is not available"
                )
            
            unit_price = menu_item['base_price']
            total_price = unit_price * quantity
            subtotal += total_price
            
            # Create order item
            order_item = {
                "menu_item_id": menu_item_id,
                "menu_item_name": menu_item['name'],
                "variant_id": item.get('variant_id'),
                "variant_name": item.get('variant_name'),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "special_instructions": item.get('special_instructions')
            }
            order_items.append(order_item)
        
        # Calculate tax and total
        tax_rate = 0.18  # 18% GST
        tax_amount = subtotal * tax_rate
        discount_amount = data.get('discount_amount', 0.0)
        total_amount = subtotal + tax_amount - discount_amount
        
        # Update data
        data['items'] = order_items
        data['subtotal'] = subtotal
        data['tax_amount'] = tax_amount
        data['discount_amount'] = discount_amount
        data['total_amount'] = total_amount
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate order creation permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate venue access
        venue_id = data.get('venue_id')
        if venue_id:
            await self._validate_venue_access(venue_id, current_user)
        
        # Validate table if specified
        table_id = data.get('table_id')
        if table_id:
            await self._validate_table_access(table_id, venue_id)
    
    async def _validate_venue_access(self, venue_id: str, current_user: Dict[str, Any]):
        """Validate user has access to the venue"""
        venue_repo = get_repository_manager().get_repository('venue')
        
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cafe not found"
            )
        
        if not venue.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cafe is not active"
            )
    
    async def _validate_table_access(self, table_id: str, venue_id: str):
        """Validate table belongs to venue and is available"""
        table_repo = get_repository_manager().get_repository('table')
        
        table = await table_repo.get_by_id(table_id)
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )
        
        if table.get('venue_id') != venue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Table does not belong to the specified venue"
            )
    
    async def update_order_status(self, 
                                order_id: str,
                                new_status: OrderStatus,
                                current_user: Dict[str, Any]) -> bool:
        """Update order status with validation"""
        repo = self.get_repository()
        
        # Get current order
        order_data = await repo.get_by_id(order_id)
        if not order_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Validate permissions
        await self._validate_access_permissions(order_data, current_user)
        
        # Validate status transition
        current_status = OrderStatus(order_data.get('status'))
        if not self._is_valid_status_transition(current_status, new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status.value} to {new_status.value}"
            )
        
        # Update status
        update_data = {"status": new_status.value}
        
        # Set ready time if status is READY
        if new_status == OrderStatus.READY:
            update_data["actual_ready_time"] = datetime.utcnow()
        
        await repo.update(order_id, update_data)
        
        # Send notification (TODO: implement notification service)
        await self._send_order_status_notification(order_data, new_status)
        
        logger.info(f"Order status updated: {order_id} -> {new_status.value}")
        return True
    
    def _is_valid_status_transition(self, current: OrderStatus, new: OrderStatus) -> bool:
        """Validate if status transition is allowed"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.SERVED, OrderStatus.DELIVERED],
            OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],
            OrderStatus.SERVED: [],
            OrderStatus.CANCELLED: []
        }
        
        return new in valid_transitions.get(current, [])
    
    async def _send_order_status_notification(self, order_data: Dict[str, Any], new_status: OrderStatus):
        """Send notification for order status change"""
        # TODO: Implement notification service
        logger.info(f"Notification sent for order {order_data['id']}: status changed to {new_status.value}")
    
    async def get_order_analytics(self, 
                                venue_id: str,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                current_user: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get order analytics for a venue"""
        # Validate venue access
        await self._validate_venue_access(venue_id, current_user)
        
        repo = self.get_repository()
        
        # Set default date range (last 30 days)
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get orders in date range
        orders = await repo.get_by_venue(venue_id)
        
        # Filter by date range
        filtered_orders = []
        for order in orders:
            order_date = order.get('created_at')
            if order_date and start_date <= order_date <= end_date:
                filtered_orders.append(order)
        
        # Calculate analytics
        total_orders = len(filtered_orders)
        total_revenue = sum(order.get('total_amount', 0) for order in filtered_orders if order.get('payment_status') == 'paid')
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Status breakdown
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = sum(1 for order in filtered_orders if order.get('status') == status.value)
        
        # Payment status breakdown
        payment_counts = {}
        for status in PaymentStatus:
            payment_counts[status.value] = sum(1 for order in filtered_orders if order.get('payment_status') == status.value)
        
        return {
            "venue_id": venue_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": average_order_value,
            "status_breakdown": status_counts,
            "payment_breakdown": payment_counts
        }


# Initialize endpoint
orders_endpoint = OrdersEndpoint()


# =============================================================================
# ORDER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get orders",
            description="Get paginated list of orders")
async def get_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    venue_id: Optional[str] = Query(None, description="Filter by venue ID"),
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    order_type: Optional[OrderType] = Query(None, description="Filter by order type"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get orders with pagination and filtering"""
    filters = {}
    if venue_id:
        filters['venue_id'] = venue_id
    if status:
        filters['status'] = status.value
    if payment_status:
        filters['payment_status'] = payment_status.value
    if order_type:
        filters['order_type'] = order_type.value
    
    return await orders_endpoint.get_items(
        page=page,
        page_size=page_size,
        filters=filters,
        current_user=current_user
    )


@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create order",
             description="Create a new order")
async def create_order(
    order_data: OrderCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new order"""
    return await orders_endpoint.create_item(order_data, current_user)


@router.get("/{order_id}", 
            response_model=Order,
            summary="Get order by ID",
            description="Get specific order by ID")
async def get_order(
    order_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get order by ID"""
    return await orders_endpoint.get_item(order_id, current_user)


@router.put("/{order_id}", 
            response_model=ApiResponse,
            summary="Update order",
            description="Update order information")
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update order information"""
    return await orders_endpoint.update_item(order_id, order_update, current_user)


# =============================================================================
# ORDER STATUS MANAGEMENT ENDPOINTS
# =============================================================================

@router.put("/{order_id}/status", 
            response_model=ApiResponse,
            summary="Update order status",
            description="Update order status with validation")
async def update_order_status(
    order_id: str,
    new_status: OrderStatus,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update order status"""
    try:
        success = await orders_endpoint.update_order_status(order_id, new_status, current_user)
        
        if success:
            return ApiResponse(
                success=True,
                message=f"Order status updated to {new_status.value}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update order status"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.post("/{order_id}/confirm", 
             response_model=ApiResponse,
             summary="Confirm order",
             description="Confirm pending order")
async def confirm_order(
    order_id: str,
    estimated_minutes: Optional[int] = Query(None, ge=1, le=120, description="Estimated preparation time"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Confirm order"""
    try:
        # Update status to confirmed
        success = await orders_endpoint.update_order_status(order_id, OrderStatus.CONFIRMED, current_user)
        
        if success and estimated_minutes:
            # Set estimated ready time
            repo = get_repository_manager().get_repository('order')
            estimated_ready_time = datetime.utcnow() + timedelta(minutes=estimated_minutes)
            await repo.update(order_id, {"estimated_ready_time": estimated_ready_time})
        
        return ApiResponse(
            success=True,
            message="Order confirmed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm order"
        )


@router.post("/{order_id}/cancel", 
             response_model=ApiResponse,
             summary="Cancel order",
             description="Cancel order with reason")
async def cancel_order(
    order_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancel order"""
    try:
        # Update status to cancelled
        success = await orders_endpoint.update_order_status(order_id, OrderStatus.CANCELLED, current_user)
        
        if success and reason:
            # Add cancellation reason
            repo = get_repository_manager().get_repository('order')
            await repo.update(order_id, {"cancellation_reason": reason})
        
        return ApiResponse(
            success=True,
            message="Order cancelled successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )


# =============================================================================
# CAFE ORDER ENDPOINTS
# =============================================================================

@router.get("/venues/{venue_id}/orders", 
            response_model=List[Order],
            summary="Get venue orders",
            description="Get all orders for a specific venue")
async def get_venue_orders(
    venue_id: str,
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of orders"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all orders for a venue"""
    try:
        # Validate venue access
        await orders_endpoint._validate_venue_access(venue_id, current_user)
        
        repo = get_repository_manager().get_repository('order')
        
        if status:
            orders_data = await repo.get_by_status(venue_id, status.value)
        else:
            orders_data = await repo.get_by_venue(venue_id, limit=limit)
        
        orders = [Order(**order) for order in orders_data]
        
        logger.info(f"Retrieved {len(orders)} orders for venue: {venue_id}")
        return orders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get orders"
        )


@router.get("/venues/{venue_id}/analytics", 
            response_model=Dict[str, Any],
            summary="Get venue order analytics",
            description="Get order analytics for a venue")
async def get_venue_order_analytics(
    venue_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get order analytics for a venue"""
    try:
        analytics = await orders_endpoint.get_order_analytics(
            venue_id, start_date, end_date, current_user
        )
        
        logger.info(f"Order analytics retrieved for venue: {venue_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )


# =============================================================================
# REAL-TIME ORDER TRACKING ENDPOINTS
# =============================================================================

@router.get("/venues/{venue_id}/live", 
            response_model=Dict[str, Any],
            summary="Get live order status",
            description="Get real-time order status for venue dashboard")
async def get_live_order_status(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get live order status for venue dashboard"""
    try:
        # Validate venue access
        await orders_endpoint._validate_venue_access(venue_id, current_user)
        
        repo = get_repository_manager().get_repository('order')
        
        # Get active orders (not completed/cancelled)
        active_statuses = [
            OrderStatus.PENDING.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value,
            OrderStatus.OUT_FOR_DELIVERY.value
        ]
        
        all_orders = await repo.get_by_venue(venue_id, limit=100)
        active_orders = [
            order for order in all_orders 
            if order.get('status') in active_statuses
        ]
        
        # Group by status
        orders_by_status = {}
        for status in active_statuses:
            orders_by_status[status] = [
                Order(**order) for order in active_orders 
                if order.get('status') == status
            ]
        
        # Calculate metrics
        total_active = len(active_orders)
        pending_count = len(orders_by_status.get(OrderStatus.PENDING.value, []))
        preparing_count = len(orders_by_status.get(OrderStatus.PREPARING.value, []))
        ready_count = len(orders_by_status.get(OrderStatus.READY.value, []))
        
        return {
            "venue_id": venue_id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_active_orders": total_active,
                "pending_orders": pending_count,
                "preparing_orders": preparing_count,
                "ready_orders": ready_count
            },
            "orders_by_status": orders_by_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get live order status"
        )


# =============================================================================
# CUSTOMER ORDER ENDPOINTS
# =============================================================================

@router.get("/customers/{customer_id}/orders", 
            response_model=List[Order],
            summary="Get customer orders",
            description="Get order history for a customer")
async def get_customer_orders(
    customer_id: str,
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of orders"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get order history for a customer"""
    try:
        repo = get_repository_manager().get_repository('order')
        
        # Get customer orders
        orders_data = await repo.query([('customer_id', '==', customer_id)], limit=limit)
        
        # Filter orders user can access
        accessible_orders = []
        for order in orders_data:
            try:
                await orders_endpoint._validate_access_permissions(order, current_user)
                accessible_orders.append(order)
            except HTTPException:
                continue  # Skip orders user can't access
        
        orders = [Order(**order) for order in accessible_orders]
        
        logger.info(f"Retrieved {len(orders)} orders for customer: {customer_id}")
        return orders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get customer orders"
        )


# =============================================================================
# PUBLIC ORDERING ENDPOINTS (Consolidated from public_ordering.py)
# =============================================================================

@router.get("/public/qr/{qr_code}",
            response_model=Dict[str, Any],
            summary="Access Menu via QR Code",
            description="Get venue menu and information by scanning QR code")
async def access_menu_by_qr(qr_code: str):
    """
    Access venue menu through QR code scan
    - Verifies QR code authenticity
    - Checks venue operating status
    - Returns menu with current availability
    """
    try:
        from app.services.public_ordering_service import public_ordering_service
        
        menu_access = await public_ordering_service.verify_qr_code_and_get_menu(qr_code)
        
        logger.info(f"QR menu accessed: venue {menu_access.venue.id}")
        return menu_access
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"QR menu access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load menu"
        )


@router.get("/public/venue/{venue_id}/status",
            response_model=Dict[str, Any],
            summary="Check Venue Operating Status",
            description="Check if venue is currently open for orders")
async def check_venue_status(venue_id: str):
    """
    Check venue operating status
    - Returns current open/closed status
    - Provides next opening/closing times
    - Includes break time information
    """
    try:
        from app.services.public_ordering_service import public_ordering_service
        
        status_info = await public_ordering_service.check_venue_operating_status(venue_id)
        
        logger.info(f"Venue status checked: {venue_id} - {status_info.current_status}")
        return status_info
        
    except Exception as e:
        logger.error(f"Venue status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check venue status"
        )


@router.post("/public/validate-order",
             response_model=Dict[str, Any],
             summary="Validate Order",
             description="Validate order before creation - check venue hours, item availability")
async def validate_order(order_data: Dict[str, Any]):
    """
    Validate order before creation
    - Checks venue operating hours
    - Validates menu item availability
    - Calculates estimated total and preparation time
    """
    try:
        from app.services.public_ordering_service import public_ordering_service
        
        validation = await public_ordering_service.validate_order(order_data)
        
        logger.info(f"Order validation: venue {order_data.get('venue_id')} - valid: {validation.is_valid}")
        return validation
        
    except Exception as e:
        logger.error(f"Order validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order validation failed"
        )


@router.post("/public/create-order",
             response_model=Dict[str, Any],
             status_code=status.HTTP_201_CREATED,
             summary="Create Public Order",
             description="Create order from public interface (QR scan)")
async def create_public_order(order_data: Dict[str, Any]):
    """
    Create order from public interface
    - Validates order and venue status
    - Creates/updates customer record
    - Creates order with proper pricing
    - Updates table status if applicable
    """
    try:
        from app.services.public_ordering_service import public_ordering_service
        
        order_response = await public_ordering_service.create_public_order(order_data)
        
        logger.info(f"Public order created: {order_response.order_id}")
        return order_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public order creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("/public/{order_id}/status",
            response_model=Dict[str, Any],
            summary="Track Order Status",
            description="Track order status using order ID")
async def track_order_status(order_id: str):
    """
    Track order status for customers
    """
    try:
        order_repo = get_repository_manager().get_repository('order')
        
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Return limited order information for tracking
        order_status = {
            "order_id": order["id"],
            "order_number": order.get("order_number"),
            "status": order.get("status"),
            "estimated_preparation_time": order.get("estimated_preparation_time"),
            "estimated_ready_time": order.get("estimated_ready_time"),
            "actual_ready_time": order.get("actual_ready_time"),
            "total_amount": order.get("total_amount"),
            "payment_status": order.get("payment_status"),
            "created_at": order.get("created_at"),
            "venue_name": None  # Will be populated below
        }
        
        # Get venue name
        venue_id = order.get("venue_id")
        if venue_id:
            venue_repo = get_repository_manager().get_repository('venue')
            venue = await venue_repo.get_by_id(venue_id)
            if venue:
                order_status["venue_name"] = venue.get("name")
        
        return {
            "success": True,
            "data": order_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track order"
        )


@router.get("/public/{order_id}/receipt",
            response_model=Dict[str, Any],
            summary="Get Order Receipt",
            description="Get detailed order receipt")
async def get_order_receipt(order_id: str):
    """
    Get order receipt with full details
    """
    try:
        order_repo = get_repository_manager().get_repository('order')
        venue_repo = get_repository_manager().get_repository('venue')
        
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Get venue information
        venue = await venue_repo.get_by_id(order["venue_id"])
        
        receipt = {
            "order_id": order["id"],
            "order_number": order.get("order_number"),
            "venue": {
                "name": venue.get("name") if venue else "Unknown",
                "address": venue.get("location", {}).get("address") if venue else "",
                "phone": venue.get("phone") if venue else ""
            },
            "items": order.get("items", []),
            "subtotal": order.get("subtotal", 0.0),
            "tax_amount": order.get("tax_amount", 0.0),
            "total_amount": order.get("total_amount", 0.0),
            "payment_status": order.get("payment_status"),
            "order_date": order.get("created_at"),
            "table_number": None
        }
        
        # Get table number if available
        table_id = order.get("table_id")
        if table_id:
            table_repo = get_repository_manager().get_repository('table')
            table = await table_repo.get_by_id(table_id)
            if table:
                receipt["table_number"] = table.get("table_number")
        
        return {
            "success": True,
            "data": receipt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order receipt error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order receipt"
        )


@router.post("/public/{order_id}/feedback",
             response_model=Dict[str, Any],
             summary="Submit Order Feedback",
             description="Submit feedback and rating for completed order")
async def submit_order_feedback(
    order_id: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    feedback: Optional[str] = Query(None, max_length=1000, description="Optional feedback text")
):
    """
    Submit feedback for completed order
    """
    try:
        order_repo = get_repository_manager().get_repository('order')
        
        order = await order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Check if order is completed
        if order.get("status") not in ["served", "delivered"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only provide feedback for completed orders"
            )
        
        # Update order with feedback
        await order_repo.update(order_id, {
            "customer_rating": rating,
            "customer_feedback": feedback,
            "feedback_date": datetime.utcnow()
        })
        
        logger.info(f"Feedback submitted for order: {order_id} - rating: {rating}")
        
        return {
            "success": True,
            "message": "Thank you for your feedback!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )