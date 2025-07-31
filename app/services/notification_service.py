"""
Real-time Notification Service
Handles creation, delivery, and management of notifications for users and admins
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

from app.database.firestore import FirestoreRepository
from app.models.schemas import (
    Notification, NotificationCreate, NotificationType, 
    Order, OrderStatus, PaymentStatus
)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Store active connections by user type and ID
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {
            "users": {},      # user_id -> websocket
            "cafes": {},      # cafe_id -> websocket  
            "admins": {}      # admin_id -> websocket
        }
        
        # Store connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_type: str, connection_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if connection_type not in self.active_connections:
            self.active_connections[connection_type] = {}
        
        # Disconnect existing connection if any
        if connection_id in self.active_connections[connection_type]:
            try:
                await self.active_connections[connection_type][connection_id].close()
            except:
                pass
        
        self.active_connections[connection_type][connection_id] = websocket
        self.connection_metadata[f"{connection_type}:{connection_id}"] = {
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        print(f"✅ WebSocket connected: {connection_type}:{connection_id}")
    
    def disconnect(self, connection_type: str, connection_id: str):
        """Remove a WebSocket connection"""
        if (connection_type in self.active_connections and 
            connection_id in self.active_connections[connection_type]):
            del self.active_connections[connection_type][connection_id]
            
        metadata_key = f"{connection_type}:{connection_id}"
        if metadata_key in self.connection_metadata:
            del self.connection_metadata[metadata_key]
            
        print(f"❌ WebSocket disconnected: {connection_type}:{connection_id}")
    
    async def send_personal_message(self, message: dict, connection_type: str, connection_id: str):
        """Send a message to a specific connection"""
        if (connection_type in self.active_connections and 
            connection_id in self.active_connections[connection_type]):
            try:
                websocket = self.active_connections[connection_type][connection_id]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                print(f"Error sending message to {connection_type}:{connection_id}: {e}")
                self.disconnect(connection_type, connection_id)
                return False
        return False
    
    async def broadcast_to_type(self, message: dict, connection_type: str):
        """Broadcast a message to all connections of a specific type"""
        if connection_type not in self.active_connections:
            return
        
        disconnected = []
        for connection_id, websocket in self.active_connections[connection_type].items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {connection_type}:{connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_type, connection_id)
    
    async def broadcast_to_cafe_staff(self, message: dict, cafe_id: str):
        """Broadcast a message to all staff members of a specific cafe"""
        # This would require additional logic to track which users are staff of which cafe
        # For now, we'll broadcast to all cafe connections
        await self.broadcast_to_type(message, "cafes")
    
    def get_active_connections_count(self) -> Dict[str, int]:
        """Get count of active connections by type"""
        return {
            connection_type: len(connections) 
            for connection_type, connections in self.active_connections.items()
        }
    
    async def ping_all_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection_type in self.active_connections:
            await self.broadcast_to_type(ping_message, connection_type)


class NotificationRepository(FirestoreRepository):
    """Repository for notification data operations"""
    
    def __init__(self):
        super().__init__("notifications")
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a specific user"""
        filters = [("recipient_id", "==", user_id)]
        
        if unread_only:
            filters.append(("is_read", "==", False))
        
        return await self.query(
            filters=filters,
            order_by="created_at",
            limit=limit
        )
    
    async def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        return await self.update(notification_id, {
            "is_read": True,
            "read_at": datetime.utcnow()
        })
    
    async def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user"""
        try:
            notifications = await self.get_user_notifications(user_id, unread_only=True)
            
            for notification in notifications:
                await self.mark_as_read(notification["id"])
            
            return True
        except Exception as e:
            print(f"Error marking all notifications as read: {e}")
            return False
    
    async def delete_old_notifications(self, days_old: int = 30) -> int:
        """Delete notifications older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_notifications = await self.query([
                ("created_at", "<", cutoff_date)
            ])
            
            deleted_count = 0
            for notification in old_notifications:
                await self.delete(notification["id"])
                deleted_count += 1
            
            return deleted_count
        except Exception as e:
            print(f"Error deleting old notifications: {e}")
            return 0


class NotificationService:
    """Service for managing notifications and real-time communication"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.notification_repo = NotificationRepository()
    
    async def create_notification(
        self, 
        notification_data: NotificationCreate
    ) -> Notification:
        """Create a new notification"""
        try:
            # Create notification in database
            notification_dict = notification_data.dict()
            notification_id = await self.notification_repo.create(notification_dict)
            
            # Get created notification
            created_notification = await self.notification_repo.get_by_id(notification_id)
            notification = Notification(**created_notification)
            
            # Send real-time notification
            await self._send_real_time_notification(notification)
            
            return notification
            
        except Exception as e:
            print(f"Error creating notification: {e}")
            raise
    
    async def _send_real_time_notification(self, notification: Notification):
        """Send real-time notification via WebSocket"""
        message = {
            "type": "notification",
            "data": notification.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine connection type based on recipient type
        connection_type = notification.recipient_type
        if connection_type == "user":
            connection_type = "users"
        elif connection_type == "cafe":
            connection_type = "cafes"
        elif connection_type == "admin":
            connection_type = "admins"
        
        # Send to specific recipient
        await self.connection_manager.send_personal_message(
            message, connection_type, notification.recipient_id
        )
    
    async def notify_order_placed(self, order: Order):
        """Send notification when a new order is placed"""
        # Notify cafe/admin
        await self.create_notification(NotificationCreate(
            recipient_id=order.cafe_id,
            recipient_type="cafe",
            notification_type=NotificationType.ORDER_PLACED,
            title="New Order Received!",
            message=f"Order #{order.order_number} from {order.customer_name} - ₹{order.total_amount}",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "total_amount": order.total_amount,
                "order_type": order.order_type
            },
            priority="high"
        ))
        
        # Notify customer if they have an account
        if order.customer_id:
            await self.create_notification(NotificationCreate(
                recipient_id=order.customer_id,
                recipient_type="user",
                notification_type=NotificationType.ORDER_PLACED,
                title="Order Placed Successfully!",
                message=f"Your order #{order.order_number} has been placed and is being prepared.",
                data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "estimated_time": order.estimated_ready_time.isoformat() if order.estimated_ready_time else None
                }
            ))
    
    async def notify_order_status_change(self, order: Order, old_status: OrderStatus):
        """Send notification when order status changes"""
        status_messages = {
            OrderStatus.CONFIRMED: "Your order has been confirmed and is being prepared.",
            OrderStatus.PREPARING: "Your order is now being prepared by our kitchen.",
            OrderStatus.READY: "Your order is ready for pickup/delivery!",
            OrderStatus.OUT_FOR_DELIVERY: "Your order is out for delivery.",
            OrderStatus.DELIVERED: "Your order has been delivered. Enjoy your meal!",
            OrderStatus.SERVED: "Your order has been served. Enjoy your meal!",
            OrderStatus.CANCELLED: "Your order has been cancelled."
        }
        
        if order.status in status_messages and order.customer_id:
            notification_type = {
                OrderStatus.CONFIRMED: NotificationType.ORDER_CONFIRMED,
                OrderStatus.READY: NotificationType.ORDER_READY,
                OrderStatus.DELIVERED: NotificationType.ORDER_DELIVERED,
                OrderStatus.SERVED: NotificationType.ORDER_DELIVERED,
            }.get(order.status, NotificationType.ORDER_CONFIRMED)
            
            await self.create_notification(NotificationCreate(
                recipient_id=order.customer_id,
                recipient_type="user",
                notification_type=notification_type,
                title=f"Order #{order.order_number} Update",
                message=status_messages[order.status],
                data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "old_status": old_status
                }
            ))
    
    async def notify_payment_received(self, order: Order):
        """Send notification when payment is received"""
        # Notify cafe
        await self.create_notification(NotificationCreate(
            recipient_id=order.cafe_id,
            recipient_type="cafe",
            notification_type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Received",
            message=f"Payment of ₹{order.total_amount} received for order #{order.order_number}",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "amount": order.total_amount
            }
        ))
        
        # Notify customer
        if order.customer_id:
            await self.create_notification(NotificationCreate(
                recipient_id=order.customer_id,
                recipient_type="user",
                notification_type=NotificationType.PAYMENT_RECEIVED,
                title="Payment Confirmed",
                message=f"Your payment of ₹{order.total_amount} has been confirmed.",
                data={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "amount": order.total_amount
                }
            ))
    
    async def send_system_alert(self, message: str, recipient_type: str = "admin", priority: str = "normal"):
        """Send system alert to admins or specific user type"""
        if recipient_type == "admin":
            # In a real system, you'd get all admin user IDs
            admin_ids = ["admin_1"]  # Placeholder
            
            for admin_id in admin_ids:
                await self.create_notification(NotificationCreate(
                    recipient_id=admin_id,
                    recipient_type="admin",
                    notification_type=NotificationType.SYSTEM_ALERT,
                    title="System Alert",
                    message=message,
                    priority=priority
                ))
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        notifications_data = await self.notification_repo.get_user_notifications(
            user_id, unread_only, limit
        )
        return [Notification(**data) for data in notifications_data]
    
    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        return await self.notification_repo.mark_as_read(notification_id)
    
    async def mark_all_notifications_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user"""
        return await self.notification_repo.mark_all_as_read(user_id)
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user"""
        unread_notifications = await self.get_user_notifications(user_id, unread_only=True)
        return len(unread_notifications)
    
    # WebSocket connection management
    async def connect_websocket(self, websocket: WebSocket, connection_type: str, connection_id: str):
        """Handle new WebSocket connection"""
        await self.connection_manager.connect(websocket, connection_type, connection_id)
    
    def disconnect_websocket(self, connection_type: str, connection_id: str):
        """Handle WebSocket disconnection"""
        self.connection_manager.disconnect(connection_type, connection_id)
    
    async def handle_websocket_message(self, websocket: WebSocket, message: dict):
        """Handle incoming WebSocket message"""
        message_type = message.get("type")
        
        if message_type == "ping":
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))
        elif message_type == "mark_read":
            notification_id = message.get("notification_id")
            if notification_id:
                await self.mark_notification_read(notification_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "active_connections": self.connection_manager.get_active_connections_count(),
            "total_connections": sum(self.connection_manager.get_active_connections_count().values())
        }
    
    async def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """Clean up old notifications"""
        return await self.notification_repo.delete_old_notifications(days_old)


# Global service instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    return notification_service


# Background task to keep WebSocket connections alive
async def websocket_keepalive_task():
    """Background task to ping WebSocket connections"""
    while True:
        try:
            await notification_service.connection_manager.ping_all_connections()
            await asyncio.sleep(30)  # Ping every 30 seconds
        except Exception as e:
            print(f"Error in WebSocket keepalive: {e}")
            await asyncio.sleep(30)