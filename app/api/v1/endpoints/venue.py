"""
Enhanced Venue Management API Endpoints
Refactored with standardized patterns, workspace isolation, and comprehensive CRUD
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query

from app.models.schemas import (
    VenueCreate, VenueUpdate, Venue, ApiResponse, PaginatedResponse,
    VenueOperatingHours, SubscriptionPlan, SubscriptionStatus
)
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.firestore import get_venue_repo, VenueRepository
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class VenuesEndpoint(WorkspaceIsolatedEndpoint[Venue, VenueCreate, VenueUpdate]):
    """Enhanced Venues endpoint with workspace isolation and comprehensive CRUD"""
    
    def __init__(self):
        super().__init__(
            model_class=Venue,
            create_schema=VenueCreate,
            update_schema=VenueUpdate,
            collection_name="venues",
            require_auth=True,
            require_admin=True
        )
    
    def get_repository(self) -> VenueRepository:
        return get_venue_repo()
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare venue data before creation"""
        # Set owner and admin
        if current_user:
            data['owner_id'] = current_user['id']
            data['admin_id'] = current_user['id']
            
            # Set workspace from current user if not provided
            if not data.get('workspace_id'):
                data['workspace_id'] = current_user.get('workspace_id')
        
        # Set default values
        data['is_active'] = True
        data['is_verified'] = False
        data['rating'] = 0.0
        data['total_reviews'] = 0
        
        return data
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate venue creation permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Check workspace permissions
        target_workspace_id = data.get('workspace_id')
        user_workspace_id = current_user.get('workspace_id')
        
        if target_workspace_id and user_workspace_id != target_workspace_id:
            if current_user.get('role') != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create venues in different workspace"
                )
    
    async def _validate_access_permissions(self, 
                                         item: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate venue access permissions"""
        if not current_user:
            return  # Public access allowed for venue details
        
        # Call parent workspace validation
        await super()._validate_access_permissions(item, current_user)
        
        # Additional venue-specific validation
        if current_user.get('role') not in ['admin']:
            # Check if user is venue owner/admin
            if (item.get('owner_id') != current_user['id'] and 
                item.get('admin_id') != current_user['id']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Not authorized for this venue"
                )
    
    async def _build_query_filters(self, 
                                  filters: Optional[Dict[str, Any]], 
                                  search: Optional[str],
                                  current_user: Optional[Dict[str, Any]]) -> List[tuple]:
        """Build query filters for venue search"""
        query_filters = []
        
        # Add workspace filter for non-admin users
        if current_user and current_user.get('role') != 'admin':
            workspace_id = current_user.get('workspace_id')
            if workspace_id:
                query_filters.append(('workspace_id', '==', workspace_id))
        
        # Add additional filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    query_filters.append((field, '==', value))
        
        return query_filters
    
    async def search_venues_by_text(self, 
                                  search_term: str,
                                  current_user: Optional[Dict[str, Any]] = None) -> List[Venue]:
        """Search venues by name, description, or cuisine"""
        repo = self.get_repository()
        
        # Build base filters
        base_filters = await self._build_query_filters(None, None, current_user)
        
        # Search in multiple fields
        search_fields = ['name', 'description', 'address', 'cuisine_types']
        matching_venues = await repo.search_text(
            search_fields=search_fields,
            search_term=search_term,
            additional_filters=base_filters,
            limit=50
        )
        
        return [Venue(**venue) for venue in matching_venues]
    
    async def get_venues_by_subscription_status(self, 
                                             status: SubscriptionStatus,
                                             current_user: Dict[str, Any]) -> List[Venue]:
        """Get venues by subscription status"""
        repo = self.get_repository()
        
        # Build filters
        filters = [('subscription_status', '==', status.value)]
        
        # Add workspace filter for non-admin users
        if current_user.get('role') != 'admin':
            workspace_id = current_user.get('workspace_id')
            if workspace_id:
                filters.append(('workspace_id', '==', workspace_id))
        
        venues_data = await repo.query(filters)
        return [Venue(**venue) for venue in venues_data]
    
    async def get_venue_analytics(self, 
                               venue_id: str,
                               current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get basic analytics for a venue"""
        repo = self.get_repository()
        
        # Validate access
        venue_data = await repo.get_by_id(venue_id)
        if not venue_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        await self._validate_access_permissions(venue_data, current_user)
        
        # Get related data counts
        from app.database.firestore import (
            get_menu_item_repo, get_table_repo, get_order_repo, get_customer_repo
        )
        
        menu_repo = get_menu_item_repo()
        table_repo = get_table_repo()
        order_repo = get_order_repo()
        customer_repo = get_customer_repo()
        
        # Count items
        menu_items = await menu_repo.get_by_venue(venue_id)
        tables = await table_repo.get_by_venue(venue_id)
        orders = await order_repo.get_by_venue(venue_id, limit=100)  # Recent orders
        customers = await customer_repo.get_by_venue(venue_id)
        
        return {
            "venue_id": venue_id,
            "total_menu_items": len(menu_items),
            "total_tables": len(tables),
            "recent_orders": len(orders),
            "total_customers": len(customers),
            "rating": venue_data.get('rating', 0.0),
            "total_reviews": venue_data.get('total_reviews', 0),
            "subscription_status": venue_data.get('subscription_status'),
            "is_active": venue_data.get('is_active', False)
        }


# Initialize endpoint
venues_endpoint = VenuesEndpoint()


# =============================================================================
# PUBLIC ENDPOINTS (No Authentication Required)
# =============================================================================

@router.get("/public", 
            response_model=PaginatedResponse,
            summary="Get public venues",
            description="Get paginated list of active venues (public endpoint)")
async def get_public_venues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or cuisine"),
    cuisine_type: Optional[str] = Query(None, description="Filter by cuisine type"),
    price_range: Optional[str] = Query(None, description="Filter by price range")
):
    """Get public venues (no authentication required)"""
    try:
        repo = get_venue_repo()
        
        # Build filters for public venues
        filters = [('is_active', '==', True)]
        
        if cuisine_type:
            # Note: This is a simplified filter - in practice, you'd need array-contains
            filters.append(('cuisine_types', 'array-contains', cuisine_type))
        
        if price_range:
            filters.append(('price_range', '==', price_range))
        
        # Get filtered venues
        all_venues = await repo.query(filters)
        
        # Apply text search if provided
        if search:
            search_lower = search.lower()
            all_venues = [
                venue for venue in all_venues
                if (search_lower in venue.get('name', '').lower() or
                    search_lower in venue.get('description', '').lower() or
                    any(search_lower in cuisine.lower() for cuisine in venue.get('cuisine_types', [])))
            ]
        
        # Calculate pagination
        total = len(all_venues)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        venues_page = all_venues[start_idx:end_idx]
        
        # Convert to Venue objects
        venues = [Venue(**venue) for venue in venues_page]
        
        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        logger.info(f"Public venues retrieved: {len(venues)} of {total}")
        
        return PaginatedResponse(
            success=True,
            data=venues,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        logger.error(f"Error getting public venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venues"
        )


@router.get("/public/{venue_id}", 
            response_model=Venue,
            summary="Get public venue details",
            description="Get venue details by ID (public endpoint)")
async def get_public_venue(venue_id: str):
    """Get venue by ID (public endpoint)"""
    try:
        repo = get_venue_repo()
        venue = await repo.get_by_id(venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Only return active venues for public access
        if not venue.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        logger.info(f"Public venue retrieved: {venue_id}")
        return Venue(**venue)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue"
        )


# =============================================================================
# AUTHENTICATED ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get venues",
            description="Get paginated list of venues (authenticated)")
async def get_venues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    subscription_status: Optional[SubscriptionStatus] = Query(None, description="Filter by subscription status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get venues with pagination and filtering"""
    filters = {}
    if subscription_status:
        filters['subscription_status'] = subscription_status.value
    if is_active is not None:
        filters['is_active'] = is_active
    
    return await venues_endpoint.get_items(
        page=page,
        page_size=page_size,
        search=search,
        filters=filters,
        current_user=current_user
    )


@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create venue",
             description="Create a new venue")
async def create_venue(
    venue_data: VenueCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new venue"""
    return await venues_endpoint.create_item(venue_data, current_user)


@router.get("/my-venues", 
            response_model=List[Venue],
            summary="Get my venues",
            description="Get venues owned by current user")
async def get_my_venues(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Get current user's venues"""
    try:
        repo = get_venue_repo()
        venues_data = await repo.get_by_owner(current_user["id"])
        
        venues = [Venue(**venue) for venue in venues_data]
        
        logger.info(f"Retrieved {len(venues)} venues for user {current_user['id']}")
        return venues
        
    except Exception as e:
        logger.error(f"Error getting user venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venues"
        )


@router.get("/{venue_id}", 
            response_model=Venue,
            summary="Get venue by ID",
            description="Get specific venue by ID")
async def get_venue(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get venue by ID"""
    return await venues_endpoint.get_item(venue_id, current_user)


@router.put("/{venue_id}", 
            response_model=ApiResponse,
            summary="Update venue",
            description="Update venue information")
async def update_venue(
    venue_id: str,
    venue_update: VenueUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update venue information"""
    return await venues_endpoint.update_item(venue_id, venue_update, current_user)


@router.delete("/{venue_id}", 
               response_model=ApiResponse,
               summary="Delete venue",
               description="Deactivate venue (soft delete)")
async def delete_venue(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete venue (soft delete by deactivating)"""
    return await venues_endpoint.delete_item(venue_id, current_user, soft_delete=True)


@router.post("/{venue_id}/activate", 
             response_model=ApiResponse,
             summary="Activate venue",
             description="Activate deactivated venue")
async def activate_venue(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Activate venue"""
    try:
        repo = get_venue_repo()
        
        # Check if venue exists
        venue = await repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Validate permissions
        await venues_endpoint._validate_access_permissions(venue, current_user)
        
        # Activate venue
        await repo.update(venue_id, {"is_active": True})
        
        logger.info(f"Venue activated: {venue_id}")
        return ApiResponse(
            success=True,
            message="Venue activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating venue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate venue"
        )


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.get("/search/text", 
            response_model=List[Venue],
            summary="Search venues",
            description="Search venues by name, description, or cuisine")
async def search_venues(
    q: str = Query(..., min_length=2, description="Search query"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Search venues by text"""
    try:
        venues = await venues_endpoint.search_venues_by_text(q, current_user)
        
        logger.info(f"Venue search performed: '{q}' - {len(venues)} results")
        return venues
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching venues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/filter/subscription/{status}", 
            response_model=List[Venue],
            summary="Get venues by subscription status",
            description="Get venues filtered by subscription status")
async def get_venues_by_subscription(
    status: SubscriptionStatus,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get venues by subscription status"""
    try:
        venues = await venues_endpoint.get_venues_by_subscription_status(status, current_user)
        
        logger.info(f"Venues retrieved by subscription status '{status}': {len(venues)}")
        return venues
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venues by subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venues"
        )


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/{venue_id}/analytics", 
            response_model=Dict[str, Any],
            summary="Get venue analytics",
            description="Get basic analytics for a venue")
async def get_venue_analytics(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get venue analytics"""
    try:
        analytics = await venues_endpoint.get_venue_analytics(venue_id, current_user)
        
        logger.info(f"Analytics retrieved for venue: {venue_id}")
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )


# =============================================================================
# MEDIA UPLOAD ENDPOINTS
# =============================================================================

@router.post("/{venue_id}/logo", 
             response_model=ApiResponse,
             summary="Upload venue logo",
             description="Upload venue logo image")
async def upload_venue_logo(
    venue_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Upload venue logo to Cloud Storage"""
    try:
        # Validate venue access
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        # TODO: Implement storage service
        # storage_service = get_storage_service()
        # logo_url = await storage_service.upload_image(...)
        
        # Mock implementation for now
        logo_url = f"https://example.com/venues/{venue_id}/logo.jpg"
        
        # Update venue with logo URL
        repo = get_venue_repo()
        await repo.update(venue_id, {"logo_url": logo_url})
        
        logger.info(f"Logo uploaded for venue: {venue_id}")
        return ApiResponse(
            success=True,
            message="Logo uploaded successfully",
            data={"logo_url": logo_url}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading logo for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload logo"
        )


# =============================================================================
# OPERATING HOURS ENDPOINTS
# =============================================================================

@router.put("/{venue_id}/hours", 
            response_model=ApiResponse,
            summary="Update operating hours",
            description="Update venue operating hours")
async def update_operating_hours(
    venue_id: str,
    operating_hours: List[VenueOperatingHours],
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update venue operating hours"""
    try:
        # Validate venue access
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        # Update operating hours
        repo = get_venue_repo()
        hours_data = [hours.dict() for hours in operating_hours]
        await repo.update(venue_id, {"operating_hours": hours_data})
        
        logger.info(f"Operating hours updated for venue: {venue_id}")
        return ApiResponse(
            success=True,
            message="Operating hours updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating operating hours for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update operating hours"
        )


@router.get("/{venue_id}/hours", 
            response_model=List[VenueOperatingHours],
            summary="Get operating hours",
            description="Get venue operating hours")
async def get_operating_hours(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get venue operating hours"""
    try:
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        operating_hours = venue.operating_hours or []
        return operating_hours
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting operating hours for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get operating hours"
        )


# =============================================================================
# SUBSCRIPTION MANAGEMENT ENDPOINTS
# =============================================================================

@router.put("/{venue_id}/subscription", 
            response_model=ApiResponse,
            summary="Update subscription",
            description="Update venue subscription plan and status")
async def update_subscription(
    venue_id: str,
    subscription_plan: SubscriptionPlan,
    subscription_status: SubscriptionStatus,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update venue subscription"""
    try:
        # Validate venue access
        venue = await venues_endpoint.get_item(venue_id, current_user)
        
        # Update subscription
        repo = get_venue_repo()
        await repo.update(venue_id, {
            "subscription_plan": subscription_plan.value,
            "subscription_status": subscription_status.value
        })
        
        logger.info(f"Subscription updated for venue: {venue_id}")
        return ApiResponse(
            success=True,
            message="Subscription updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription for venue {venue_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )