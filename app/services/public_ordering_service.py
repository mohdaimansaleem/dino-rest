"""
Public Ordering Service
Handles QR-based ordering, customer management, and venue validation
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, time, timedelta
import uuid
import json
import base64
import hashlib
from fastapi import HTTPException, status

from app.models.schemas import (
    PublicOrderCreate, OrderValidationResponse, OrderCreationResponse,
    CustomerCreate, Customer, VenuePublicInfo, MenuPublicAccess,
    QRCodeData, VenueOperatingStatus, OrderSource, CustomerType
)
from app.database.firestore import (
    get_venue_repo, get_table_repo, get_menu_item_repo, get_menu_category_repo,
    get_order_repo, get_customer_repo
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PublicOrderingService:
    """Service for handling public ordering through QR codes"""
    
    def __init__(self):
        self.venue_repo = get_venue_repo()
        self.table_repo = get_table_repo()
        self.menu_item_repo = get_menu_item_repo()
        self.menu_category_repo = get_menu_category_repo()
        self.order_repo = get_order_repo()
        self.customer_repo = get_customer_repo()
    
    async def verify_qr_code_and_get_menu(self, qr_code: str) -> MenuPublicAccess:
        """
        Verify QR code and return venue menu for public access
        """
        try:
            # Decode and verify QR code
            qr_data = self._verify_qr_code(qr_code)
            if not qr_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired QR code"
                )
            
            # Get venue information
            venue = await self.venue_repo.get_by_id(qr_data.venue_id)
            if not venue:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Venue not found"
                )
            
            # Check if venue is active
            if not venue.get('is_active', False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Venue is currently inactive"
                )
            
            # Get table information
            table = await self.table_repo.get_by_id(qr_data.table_id)
            if not table:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Table not found"
                )
            
            # Check venue operating status
            operating_status = await self.check_venue_operating_status(qr_data.venue_id)
            
            # Get venue public info
            venue_info = self._build_venue_public_info(venue, operating_status.is_open)
            
            # Get menu data
            categories = await self._get_venue_categories(qr_data.venue_id)
            items = await self._get_venue_menu_items(qr_data.venue_id)
            
            # Get special offers (if any)
            special_offers = await self._get_special_offers(qr_data.venue_id)
            
            # Calculate preparation times
            prep_times = self._calculate_preparation_times(items)
            
            logger.info(f"QR menu access: venue {qr_data.venue_id}, table {qr_data.table_number}")
            
            return MenuPublicAccess(
                venue=venue_info,
                table={
                    "id": table["id"],
                    "number": table["table_number"],
                    "capacity": table.get("capacity", 4),
                    "location": table.get("location", ""),
                    "status": table.get("table_status", "available")
                },
                categories=categories,
                items=items,
                special_offers=special_offers,
                estimated_preparation_times=prep_times
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"QR menu access error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load menu"
            )
    
    async def validate_order(self, order_data: PublicOrderCreate) -> OrderValidationResponse:
        """
        Validate order before creation - check venue hours, item availability, etc.
        """
        try:
            # Check venue operating status
            operating_status = await self.check_venue_operating_status(order_data.venue_id)
            
            if not operating_status.is_open:
                return OrderValidationResponse(
                    is_valid=False,
                    venue_open=False,
                    message=operating_status.message,
                    errors=["Venue is currently closed"]
                )
            
            # Validate menu items
            available_items = []
            unavailable_items = []
            total_amount = 0.0
            max_prep_time = 0
            
            for order_item in order_data.items:
                menu_item = await self.menu_item_repo.get_by_id(order_item.menu_item_id)
                
                if not menu_item:
                    unavailable_items.append(f"Item not found: {order_item.menu_item_id}")
                    continue
                
                if not menu_item.get('is_available', False):
                    unavailable_items.append(f"{menu_item['name']} is currently unavailable")
                    continue
                
                # Check if item belongs to the venue
                if menu_item.get('venue_id') != order_data.venue_id:
                    unavailable_items.append(f"{menu_item['name']} is not available at this venue")
                    continue
                
                available_items.append(menu_item['name'])
                
                # Calculate pricing
                item_price = menu_item.get('base_price', 0.0)
                total_amount += item_price * order_item.quantity
                
                # Track preparation time
                prep_time = menu_item.get('preparation_time_minutes', 15)
                max_prep_time = max(max_prep_time, prep_time)
            
            # Add taxes
            tax_rate = 0.18  # 18% GST
            total_amount = total_amount * (1 + tax_rate)
            
            is_valid = len(unavailable_items) == 0 and len(available_items) > 0
            
            return OrderValidationResponse(
                is_valid=is_valid,
                venue_open=operating_status.is_open,
                items_available=available_items,
                items_unavailable=unavailable_items,
                estimated_total=round(total_amount, 2),
                estimated_preparation_time=max_prep_time,
                message="Order validation completed",
                errors=unavailable_items
            )
            
        except Exception as e:
            logger.error(f"Order validation error: {e}")
            return OrderValidationResponse(
                is_valid=False,
                venue_open=False,
                message="Order validation failed",
                errors=[str(e)]
            )
    
    async def create_public_order(self, order_data: PublicOrderCreate) -> OrderCreationResponse:
        """
        Create order from public interface with customer management
        """
        try:
            # First validate the order
            validation = await self.validate_order(order_data)
            if not validation.is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Order validation failed: {', '.join(validation.errors)}"
                )
            
            # Handle customer creation/update
            customer_id = await self._handle_customer(order_data.customer, order_data.venue_id)
            
            # Create order
            order_id = await self._create_order(order_data, customer_id, validation)
            
            # Update table status if applicable
            if order_data.table_id:
                await self._update_table_status(order_data.table_id, "occupied")
            
            # Update customer statistics
            await self._update_customer_stats(customer_id, validation.estimated_total)
            
            logger.info(f"Public order created: {order_id} for customer {customer_id}")
            
            return OrderCreationResponse(
                success=True,
                order_id=order_id,
                order_number=f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{order_id[:6].upper()}",
                estimated_preparation_time=validation.estimated_preparation_time,
                total_amount=validation.estimated_total,
                payment_required=True,
                message="Order placed successfully! Please proceed to payment.",
                customer_id=customer_id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Public order creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order"
            )
    
    async def check_venue_operating_status(self, venue_id: str) -> VenueOperatingStatus:
        """
        Check if venue is currently open based on operating hours
        """
        try:
            venue = await self.venue_repo.get_by_id(venue_id)
            if not venue:
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=False,
                    current_status="closed",
                    message="Venue not found"
                )
            
            if not venue.get('is_active', False):
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=False,
                    current_status="inactive",
                    message="Venue is currently inactive"
                )
            
            # Get current time and day
            now = datetime.utcnow()
            current_day = now.weekday()  # 0 = Monday, 6 = Sunday
            current_time = now.time()
            
            # Get operating hours for current day
            operating_hours = venue.get('operating_hours', [])
            today_hours = None
            
            for hours in operating_hours:
                if hours.get('day_of_week') == current_day:
                    today_hours = hours
                    break
            
            if not today_hours:
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=False,
                    current_status="closed",
                    message="No operating hours defined for today"
                )
            
            if not today_hours.get('is_open', False):
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=False,
                    current_status="closed",
                    message="Venue is closed today"
                )
            
            # Check if 24 hours
            if today_hours.get('is_24_hours', False):
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=True,
                    current_status="open",
                    message="Venue is open 24 hours"
                )
            
            # Parse opening and closing times
            open_time_str = today_hours.get('open_time')
            close_time_str = today_hours.get('close_time')
            
            if not open_time_str or not close_time_str:
                return VenueOperatingStatus(
                    venue_id=venue_id,
                    is_open=False,
                    current_status="closed",
                    message="Operating hours not properly configured"
                )
            
            # Convert to time objects
            open_time = datetime.strptime(open_time_str, "%H:%M:%S").time()
            close_time = datetime.strptime(close_time_str, "%H:%M:%S").time()
            
            # Check if currently open
            is_open = False
            if close_time > open_time:
                # Same day operation
                is_open = open_time <= current_time <= close_time
            else:
                # Crosses midnight
                is_open = current_time >= open_time or current_time <= close_time
            
            # Check break time
            break_start_str = today_hours.get('break_start')
            break_end_str = today_hours.get('break_end')
            
            if is_open and break_start_str and break_end_str:
                break_start = datetime.strptime(break_start_str, "%H:%M:%S").time()
                break_end = datetime.strptime(break_end_str, "%H:%M:%S").time()
                
                if break_start <= current_time <= break_end:
                    is_open = False
                    next_opening = datetime.combine(now.date(), break_end)
                    return VenueOperatingStatus(
                        venue_id=venue_id,
                        is_open=False,
                        current_status="break",
                        next_opening=next_opening,
                        message=f"Venue is on break. Opens at {break_end_str}"
                    )
            
            # Calculate next opening/closing time
            next_opening = None
            next_closing = None
            
            if is_open:
                if close_time > open_time:
                    next_closing = datetime.combine(now.date(), close_time)
                else:
                    # Closes next day
                    next_closing = datetime.combine(now.date() + timedelta(days=1), close_time)
            else:
                if current_time < open_time:
                    next_opening = datetime.combine(now.date(), open_time)
                else:
                    # Opens next day
                    next_opening = datetime.combine(now.date() + timedelta(days=1), open_time)
            
            status_message = "Venue is open" if is_open else f"Venue is closed. Opens at {open_time_str}"
            
            return VenueOperatingStatus(
                venue_id=venue_id,
                is_open=is_open,
                current_status="open" if is_open else "closed",
                next_opening=next_opening,
                next_closing=next_closing,
                message=status_message
            )
            
        except Exception as e:
            logger.error(f"Operating status check error: {e}")
            return VenueOperatingStatus(
                venue_id=venue_id,
                is_open=False,
                current_status="error",
                message="Unable to check venue status"
            )
    
    def _verify_qr_code(self, qr_code: str) -> Optional[QRCodeData]:
        """Verify and decode QR code"""
        try:
            # Split encoded data and hash
            parts = qr_code.split('.')
            if len(parts) != 2:
                return None
            
            qr_encoded, qr_hash = parts
            
            # Decode data
            qr_bytes = base64.b64decode(qr_encoded.encode('utf-8'))
            
            # Verify hash
            hash_object = hashlib.sha256(qr_bytes)
            expected_hash = hash_object.hexdigest()[:16]
            
            if qr_hash != expected_hash:
                return None
            
            # Parse JSON
            qr_json = qr_bytes.decode('utf-8')
            qr_data = json.loads(qr_json)
            
            return QRCodeData(
                venue_id=qr_data['venue_id'],
                table_id=qr_data.get('table_id', ''),
                table_number=qr_data['table_number'],
                encrypted_token=qr_code,
                generated_at=datetime.fromisoformat(qr_data['generated_at'])
            )
            
        except Exception:
            return None
    
    def _build_venue_public_info(self, venue: Dict[str, Any], is_open: bool) -> VenuePublicInfo:
        """Build public venue information"""
        return VenuePublicInfo(
            id=venue['id'],
            name=venue['name'],
            description=venue.get('description'),
            cuisine_types=venue.get('cuisine_types', []),
            location=venue.get('location', {}),
            phone=venue.get('phone', ''),
            website=venue.get('website'),
            price_range=venue.get('price_range'),
            features=venue.get('features', []),
            is_open=is_open,
            current_wait_time=venue.get('current_wait_time'),
            rating=venue.get('rating', 0.0),
            total_reviews=venue.get('total_reviews', 0)
        )
    
    async def _get_venue_categories(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get active menu categories for venue"""
        categories = await self.menu_category_repo.get_by_venue(venue_id)
        return [
            {
                "id": cat["id"],
                "name": cat["name"],
                "description": cat.get("description"),
                "image_url": cat.get("image_url"),
                "sort_order": cat.get("sort_order", 0)
            }
            for cat in categories
            if cat.get("is_active", False)
        ]
    
    async def _get_venue_menu_items(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get available menu items for venue"""
        items = await self.menu_item_repo.get_by_venue(venue_id)
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "description": item.get("description"),
                "base_price": item.get("base_price", 0.0),
                "category_id": item.get("category_id"),
                "image_urls": item.get("image_urls", []),
                "is_vegetarian": item.get("is_vegetarian", False),
                "is_vegan": item.get("is_vegan", False),
                "spice_level": item.get("spice_level"),
                "allergens": item.get("allergens", []),
                "preparation_time_minutes": item.get("preparation_time_minutes", 15),
                "calories": item.get("calories"),
                "rating": item.get("rating", 0.0)
            }
            for item in items
            if item.get("is_available", False)
        ]
    
    async def _get_special_offers(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get special offers for venue"""
        # TODO: Implement special offers/promotions
        return []
    
    def _calculate_preparation_times(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate estimated preparation times by category"""
        prep_times = {}
        for item in items:
            category_id = item.get("category_id", "default")
            prep_time = item.get("preparation_time_minutes", 15)
            
            if category_id not in prep_times:
                prep_times[category_id] = prep_time
            else:
                prep_times[category_id] = max(prep_times[category_id], prep_time)
        
        return prep_times
    
    async def _handle_customer(self, customer_data: CustomerCreate, venue_id: str) -> str:
        """Handle customer creation or update"""
        
        # Check if customer exists by phone
        existing_customers = await self.customer_repo.query([
            ('phone', '==', customer_data.phone)
        ])
        
        if existing_customers:
            # Update existing customer
            customer = existing_customers[0]
            customer_id = customer['id']
            
            # Update customer data
            update_data = {
                'name': customer_data.name,
                'updated_at': datetime.utcnow(),
                'last_venue_id': venue_id
            }
            
            if customer_data.email:
                update_data['email'] = customer_data.email
            
            if customer_data.preferences:
                current_prefs = customer.get('preferences', {})
                current_prefs.update(customer_data.preferences)
                update_data['preferences'] = current_prefs
            
            await self.customer_repo.update(customer_id, update_data)
            
        else:
            # Create new customer
            customer_id = str(uuid.uuid4())
            
            customer_record = {
                'id': customer_id,
                'phone': customer_data.phone,
                'name': customer_data.name,
                'email': customer_data.email,
                'customer_type': CustomerType.NEW.value,
                'total_orders': 0,
                'total_spent': 0.0,
                'last_order_date': None,
                'favorite_venue_id': venue_id,
                'last_venue_id': venue_id,
                'preferences': customer_data.preferences or {},
                'dietary_restrictions': customer_data.dietary_restrictions or [],
                'loyalty_points': 0,
                'marketing_consent': customer_data.marketing_consent,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            await self.customer_repo.create(customer_record)
        
        return customer_id
    
    async def _create_order(
        self, 
        order_data: PublicOrderCreate, 
        customer_id: str, 
        validation: OrderValidationResponse
    ) -> str:
        """Create the actual order"""
        
        order_id = str(uuid.uuid4())
        
        # Build order items with pricing
        order_items = []
        for order_item in order_data.items:
            menu_item = await self.menu_item_repo.get_by_id(order_item.menu_item_id)
            
            unit_price = menu_item.get('base_price', 0.0)
            total_price = unit_price * order_item.quantity
            
            order_items.append({
                'menu_item_id': order_item.menu_item_id,
                'menu_item_name': menu_item['name'],
                'quantity': order_item.quantity,
                'unit_price': unit_price,
                'total_price': total_price,
                'variant_id': order_item.variant_id,
                'customizations': order_item.customizations,
                'special_instructions': order_item.special_instructions
            })
        
        # Calculate totals
        subtotal = sum(item['total_price'] for item in order_items)
        tax_amount = subtotal * 0.18  # 18% GST
        total_amount = subtotal + tax_amount
        
        order_record = {
            'id': order_id,
            'order_number': f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{order_id[:6].upper()}",
            'venue_id': order_data.venue_id,
            'table_id': order_data.table_id,
            'customer_id': customer_id,
            'items': order_items,
            'order_type': order_data.order_type.value,
            'order_source': OrderSource.QR_SCAN.value,
            'status': 'pending',
            'payment_status': 'pending',
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total_amount': total_amount,
            'estimated_preparation_time': validation.estimated_preparation_time,
            'special_instructions': order_data.special_instructions,
            'estimated_guests': order_data.estimated_guests,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        await self.order_repo.create(order_record)
        
        return order_id
    
    async def _update_table_status(self, table_id: str, status: str) -> None:
        """Update table status"""
        await self.table_repo.update(table_id, {
            'table_status': status,
            'last_occupied': datetime.utcnow()
        })
    
    async def _update_customer_stats(self, customer_id: str, order_amount: float) -> None:
        """Update customer statistics"""
        customer = await self.customer_repo.get_by_id(customer_id)
        if customer:
            total_orders = customer.get('total_orders', 0) + 1
            total_spent = customer.get('total_spent', 0.0) + order_amount
            
            # Determine customer type
            customer_type = CustomerType.NEW.value
            if total_orders > 1:
                customer_type = CustomerType.RETURNING.value
            if total_spent > 5000:  # VIP threshold
                customer_type = CustomerType.VIP.value
            
            await self.customer_repo.update(customer_id, {
                'total_orders': total_orders,
                'total_spent': total_spent,
                'last_order_date': datetime.utcnow(),
                'customer_type': customer_type
            })


# Service instance
public_ordering_service = PublicOrderingService()