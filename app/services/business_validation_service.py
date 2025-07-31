"""
Business Validation Service
Handles business logic validation for orders, operating hours, etc.
"""
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.core.logging_config import LoggerMixin
from app.database.firestore import get_venue_repo, get_table_repo
from app.models.schemas import Venue, Table, OrderType


class BusinessValidationService(LoggerMixin):
    """Service for business logic validation"""
    
    async def validate_venue_operational(self, venue_id: str) -> Tuple[bool, str]:
        """Validate if venue is operational and accepting orders"""
        try:
            venue_repo = get_venue_repo()
            venue_data = await venue_repo.get_by_id(venue_id)
            
            if not venue_data:
                return False, "Venue not found"
            
            venue = Venue(**venue_data)
            
            # Check if venue is active
            if not venue.is_active:
                return False, "Venue is currently inactive"
            
            # Check subscription status
            if venue.subscription_status != "active":
                return False, "Venue subscription is not active"
            
            # Check if venue is accepting orders (manual override)
            # This would be a field we add to venue settings
            # For now, we'll assume it's always accepting if active
            
            self.log_operation("validate_venue_operational", 
                             venue_id=venue_id, 
                             is_operational=True)
            return True, "Venue is operational"
            
        except Exception as e:
            self.log_error(e, "validate_venue_operational", venue_id=venue_id)
            return False, "Failed to validate venue status"
    
    async def validate_operating_hours(self, venue_id: str) -> Tuple[bool, str]:
        """Validate if venue is within operating hours"""
        try:
            venue_repo = get_venue_repo()
            venue_data = await venue_repo.get_by_id(venue_id)
            
            if not venue_data:
                return False, "Venue not found"
            
            venue = Venue(**venue_data)
            
            # Get current day and time
            now = datetime.now()
            current_day = now.strftime("%A").lower()
            current_time = now.time()
            
            # Find operating hours for current day
            day_hours = None
            for hours in venue.operating_hours:
                if hours.day.lower() == current_day:
                    day_hours = hours
                    break
            
            if not day_hours:
                return False, f"No operating hours defined for {current_day}"
            
            if day_hours.is_closed:
                return False, f"Venue is closed on {current_day}"
            
            # Parse time strings
            open_time = time.fromisoformat(day_hours.open_time)
            close_time = time.fromisoformat(day_hours.close_time)
            
            # Handle overnight hours (e.g., 22:00 to 02:00)
            if close_time < open_time:
                # Overnight operation
                is_open = current_time >= open_time or current_time <= close_time
            else:
                # Same day operation
                is_open = open_time <= current_time <= close_time
            
            if not is_open:
                return False, f"Venue is closed. Operating hours: {day_hours.open_time} - {day_hours.close_time}"
            
            self.log_operation("validate_operating_hours", 
                             venue_id=venue_id, 
                             is_open=True,
                             current_time=current_time.isoformat())
            return True, "Venue is open"
            
        except Exception as e:
            self.log_error(e, "validate_operating_hours", venue_id=venue_id)
            return False, "Failed to validate operating hours"
    
    async def validate_table_access(self, venue_id: str, table_number: int) -> Tuple[bool, str, Optional[Dict]]:
        """Validate table access for ordering"""
        try:
            table_repo = get_table_repo()
            table_data = await table_repo.get_by_table_number(venue_id, table_number)
            
            if not table_data:
                return False, "Table not found", None
            
            table = Table(**table_data)
            
            # Check if table is active
            if not table.is_active:
                return False, "Table is not active", None
            
            # Check table status
            if table.table_status == "maintenance":
                return False, "Table is under maintenance", None
            elif table.table_status == "out_of_service":
                return False, "Table is out of service", None
            
            # Table is available for ordering
            self.log_operation("validate_table_access", 
                             venue_id=venue_id, 
                             table_number=table_number,
                             table_status=table.table_status)
            return True, "Table is available", table_data
            
        except Exception as e:
            self.log_error(e, "validate_table_access", 
                          venue_id=venue_id, 
                          table_number=table_number)
            return False, "Failed to validate table access", None
    
    async def validate_order_placement(self, venue_id: str, order_type: OrderType, 
                                     table_id: Optional[str] = None) -> Tuple[bool, str]:
        """Validate if order can be placed"""
        try:
            # First validate venue operational status
            is_operational, message = await self.validate_venue_operational(venue_id)
            if not is_operational:
                return False, message
            
            # Validate operating hours
            is_open, message = await self.validate_operating_hours(venue_id)
            if not is_open:
                return False, message
            
            # For dine-in orders, validate table
            if order_type == OrderType.DINE_IN and table_id:
                table_repo = get_table_repo()
                table_data = await table_repo.get_by_id(table_id)
                
                if not table_data:
                    return False, "Table not found"
                
                table = Table(**table_data)
                if table.venue_id != venue_id:
                    return False, "Table does not belong to this venue"
                
                is_table_valid, table_message, _ = await self.validate_table_access(
                    venue_id, table.table_number
                )
                if not is_table_valid:
                    return False, table_message
            
            self.log_operation("validate_order_placement", 
                             venue_id=venue_id, 
                             order_type=order_type,
                             table_id=table_id)
            return True, "Order can be placed"
            
        except Exception as e:
            self.log_error(e, "validate_order_placement", 
                          venue_id=venue_id, 
                          order_type=order_type)
            return False, "Failed to validate order placement"
    
    async def get_venue_availability_info(self, venue_id: str) -> Dict[str, any]:
        """Get comprehensive venue availability information"""
        try:
            venue_repo = get_venue_repo()
            venue_data = await venue_repo.get_by_id(venue_id)
            
            if not venue_data:
                return {
                    "is_available": False,
                    "message": "Venue not found",
                    "details": {}
                }
            
            venue = Venue(**venue_data)
            
            # Check operational status
            is_operational, operational_message = await self.validate_venue_operational(venue_id)
            
            # Check operating hours
            is_open, hours_message = await self.validate_operating_hours(venue_id)
            
            # Get current day's hours
            now = datetime.now()
            current_day = now.strftime("%A").lower()
            
            day_hours = None
            for hours in venue.operating_hours:
                if hours.day.lower() == current_day:
                    day_hours = hours
                    break
            
            availability_info = {
                "is_available": is_operational and is_open,
                "is_operational": is_operational,
                "is_open": is_open,
                "operational_message": operational_message,
                "hours_message": hours_message,
                "details": {
                    "venue_name": venue.name,
                    "subscription_status": venue.subscription_status,
                    "is_active": venue.is_active,
                    "current_day": current_day,
                    "today_hours": {
                        "open_time": day_hours.open_time if day_hours else None,
                        "close_time": day_hours.close_time if day_hours else None,
                        "is_closed": day_hours.is_closed if day_hours else True
                    } if day_hours else None
                }
            }
            
            self.log_operation("get_venue_availability_info", 
                             venue_id=venue_id,
                             is_available=availability_info["is_available"])
            
            return availability_info
            
        except Exception as e:
            self.log_error(e, "get_venue_availability_info", venue_id=venue_id)
            return {
                "is_available": False,
                "message": "Failed to check venue availability",
                "details": {}
            }


# Service instance
business_validation_service = BusinessValidationService()