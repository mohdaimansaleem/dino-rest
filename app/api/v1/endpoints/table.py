"""
Enhanced Table Management API Endpoints
Complete CRUD for tables with QR code generation and status management
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
import hashlib
import base64
import json

from app.models.schemas import (
    Table, TableCreate, TableUpdate, TableStatus,
    ApiResponse, PaginatedResponse, QRCodeData
)
# Removed base endpoint dependency
from app.core.base_endpoint import WorkspaceIsolatedEndpoint
from app.database.firestore import get_table_repo, TableRepository
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TablesEndpoint(WorkspaceIsolatedEndpoint[Table, TableCreate, TableUpdate]):
    """Enhanced Tables endpoint with QR code management and status tracking"""
    
    def __init__(self):
        super().__init__(
            model_class=Table,
            create_schema=TableCreate,
            update_schema=TableUpdate,
            collection_name="tables",
            require_auth=True,
            require_admin=True
        )
    
    def get_repository(self) -> TableRepository:
        return get_table_repo()
    
    async def _prepare_create_data(self, 
                                  data: Dict[str, Any], 
                                  current_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare table data before creation"""
        # Generate QR code
        venue_id = data['venue_id']
        table_number = data['table_number']
        qr_code = self._generate_qr_code(venue_id, table_number)
        
        data['qr_code'] = qr_code
        data['qr_code_url'] = None  # Will be set when QR image is generated
        data['table_status'] = TableStatus.AVAILABLE.value
        data['is_active'] = True
        
        return data
    
    def _generate_qr_code(self, venue_id: str, table_number: int) -> str:
        """Generate encrypted QR code for table"""
        # Create QR data
        qr_data = {
            "venue_id": venue_id,
            "table_number": table_number,
            "type": "table_access"
        }
        
        # Convert to JSON and encode
        qr_json = json.dumps(qr_data, sort_keys=True)
        qr_bytes = qr_json.encode('utf-8')
        
        # Create hash for verification
        hash_object = hashlib.sha256(qr_bytes)
        qr_hash = hash_object.hexdigest()[:16]  # Use first 16 chars
        
        # Encode with base64
        qr_encoded = base64.b64encode(qr_bytes).decode('utf-8')
        
        # Combine encoded data with hash
        return f"{qr_encoded}.{qr_hash}"
    
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
                table_number=qr_data['table_number'],
                encrypted_token=qr_code
            )
            
        except Exception:
            return None
    
    async def _validate_create_permissions(self, 
                                         data: Dict[str, Any], 
                                         current_user: Optional[Dict[str, Any]]):
        """Validate table creation permissions"""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate venue access
        venue_id = data.get('venue_id')
        if venue_id:
            await self._validate_venue_access(venue_id, current_user)
        
        # Check for duplicate table number in venue
        table_number = data.get('table_number')
        if venue_id and table_number:
            repo = self.get_repository()
            existing_table = await repo.get_by_table_number(venue_id, table_number)
            if existing_table:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table number {table_number} already exists in this venue"
                )
    
    async def _validate_venue_access(self, venue_id: str, current_user: Dict[str, Any]):
        """Validate user has access to the venue"""
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cafe not found"
            )
        
        # Check venue access permissions
        if current_user.get('role') != 'admin':
            user_workspace_id = current_user.get('workspace_id')
            venue_workspace_id = venue.get('workspace_id')
            
            if user_workspace_id != venue_workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cafe belongs to different workspace"
                )
    
    async def get_table_by_qr_code(self, qr_code: str) -> Optional[Table]:
        """Get table by QR code"""
        repo = self.get_repository()
        table_data = await repo.get_by_qr_code(qr_code)
        
        if table_data:
            return Table(**table_data)
        return None
    
    async def update_table_status(self, 
                                table_id: str,
                                new_status: TableStatus,
                                current_user: Dict[str, Any]) -> bool:
        """Update table status"""
        repo = self.get_repository()
        
        # Validate table exists and user has access
        table_data = await repo.get_by_id(table_id)
        if not table_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )
        
        await self._validate_access_permissions(table_data, current_user)
        
        # Update status
        await repo.update(table_id, {"table_status": new_status.value})
        
        logger.info(f"Table status updated: {table_id} -> {new_status.value}")
        return True
    
    async def get_venue_table_statistics(self, 
                                      venue_id: str,
                                      current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get table statistics for a venue"""
        # Validate venue access
        await self._validate_venue_access(venue_id, current_user)
        
        repo = self.get_repository()
        tables = await repo.get_by_venue(venue_id)
        
        # Count by status
        status_counts = {}
        for status in TableStatus:
            status_counts[status.value] = 0
        
        active_tables = 0
        for table in tables:
            if table.get('is_active', False):
                active_tables += 1
                table_status = table.get('table_status', TableStatus.AVAILABLE.value)
                status_counts[table_status] += 1
        
        return {
            "venue_id": venue_id,
            "total_tables": len(tables),
            "active_tables": active_tables,
            "status_breakdown": status_counts,
            "utilization_rate": (status_counts.get('occupied', 0) / active_tables * 100) if active_tables > 0 else 0
        }


# Initialize endpoint
tables_endpoint = TablesEndpoint()


# =============================================================================
# TABLE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/", 
            response_model=PaginatedResponse,
            summary="Get tables",
            description="Get paginated list of tables")
async def get_tables(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    venue_id: Optional[str] = Query(None, description="Filter by venue ID"),
    table_status: Optional[TableStatus] = Query(None, description="Filter by table status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get tables with pagination and filtering"""
    filters = {}
    if venue_id:
        filters['venue_id'] = venue_id
    if table_status:
        filters['table_status'] = table_status.value
    if is_active is not None:
        filters['is_active'] = is_active
    
    return await tables_endpoint.get_items(
        page=page,
        page_size=page_size,
        filters=filters,
        current_user=current_user
    )


@router.post("/", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create table",
             description="Create a new table with QR code")
async def create_table(
    table_data: TableCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new table"""
    return await tables_endpoint.create_item(table_data, current_user)


@router.get("/{table_id}", 
            response_model=Table,
            summary="Get table by ID",
            description="Get specific table by ID")
async def get_table(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get table by ID"""
    return await tables_endpoint.get_item(table_id, current_user)


@router.put("/{table_id}", 
            response_model=ApiResponse,
            summary="Update table",
            description="Update table information")
async def update_table(
    table_id: str,
    table_update: TableUpdate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update table information"""
    return await tables_endpoint.update_item(table_id, table_update, current_user)


@router.delete("/{table_id}", 
               response_model=ApiResponse,
               summary="Delete table",
               description="Deactivate table (soft delete)")
async def delete_table(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete table (soft delete by deactivating)"""
    return await tables_endpoint.delete_item(table_id, current_user, soft_delete=True)


# =============================================================================
# TABLE STATUS MANAGEMENT ENDPOINTS
# =============================================================================

@router.put("/{table_id}/status", 
            response_model=ApiResponse,
            summary="Update table status",
            description="Update table status (available, occupied, etc.)")
async def update_table_status(
    table_id: str,
    new_status: TableStatus,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update table status"""
    try:
        success = await tables_endpoint.update_table_status(table_id, new_status, current_user)
        
        if success:
            return ApiResponse(
                success=True,
                message=f"Table status updated to {new_status.value}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update table status"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating table status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update table status"
        )


@router.post("/{table_id}/occupy", 
             response_model=ApiResponse,
             summary="Occupy table",
             description="Mark table as occupied")
async def occupy_table(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mark table as occupied"""
    try:
        success = await tables_endpoint.update_table_status(
            table_id, TableStatus.OCCUPIED, current_user
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="Table marked as occupied"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to occupy table"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error occupying table: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to occupy table"
        )


@router.post("/{table_id}/free", 
             response_model=ApiResponse,
             summary="Free table",
             description="Mark table as available")
async def free_table(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mark table as available"""
    try:
        success = await tables_endpoint.update_table_status(
            table_id, TableStatus.AVAILABLE, current_user
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="Table marked as available"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to free table"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error freeing table: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to free table"
        )


# =============================================================================
# QR CODE ENDPOINTS
# =============================================================================

@router.get("/{table_id}/qr-code", 
            response_model=Dict[str, Any],
            summary="Get table QR code",
            description="Get QR code data for table")
async def get_table_qr_code(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get table QR code"""
    try:
        table = await tables_endpoint.get_item(table_id, current_user)
        
        # Decode QR code to get data
        qr_data = tables_endpoint._verify_qr_code(table.qr_code)
        
        if not qr_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid QR code data"
            )
        
        return {
            "table_id": table_id,
            "qr_code": table.qr_code,
            "qr_code_url": table.qr_code_url,
            "venue_id": qr_data.venue_id,
            "table_number": qr_data.table_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table QR code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get QR code"
        )


@router.post("/{table_id}/regenerate-qr", 
             response_model=ApiResponse,
             summary="Regenerate table QR code",
             description="Regenerate QR code for table")
async def regenerate_table_qr_code(
    table_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Regenerate table QR code"""
    try:
        table = await tables_endpoint.get_item(table_id, current_user)
        
        # Generate new QR code
        new_qr_code = tables_endpoint._generate_qr_code(table.venue_id, table.table_number)
        
        # Update table
        repo = get_table_repo()
        await repo.update(table_id, {
            "qr_code": new_qr_code,
            "qr_code_url": None  # Reset URL, will be regenerated
        })
        
        logger.info(f"QR code regenerated for table: {table_id}")
        return ApiResponse(
            success=True,
            message="QR code regenerated successfully",
            data={"qr_code": new_qr_code}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating QR code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate QR code"
        )


@router.post("/verify-qr", 
             response_model=Dict[str, Any],
             summary="Verify QR code",
             description="Verify and decode table QR code")
async def verify_qr_code(
    qr_code: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Verify QR code and return table information"""
    try:
        # Decode QR code
        qr_data = tables_endpoint._verify_qr_code(qr_code)
        
        if not qr_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid QR code"
            )
        
        # Get table information
        table = await tables_endpoint.get_table_by_qr_code(qr_code)
        
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )
        
        # Get venue information
        from app.database.firestore import get_venue_repo
        venue_repo = get_venue_repo()
        venue = await venue_repo.get_by_id(table.venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cafe not found"
            )
        
        return {
            "valid": True,
            "table": {
                "id": table.id,
                "table_number": table.table_number,
                "capacity": table.capacity,
                "location": table.location,
                "status": table.table_status
            },
            "venue": {
                "id": venue["id"],
                "name": venue["name"],
                "description": venue["description"],
                "is_active": venue.get("is_active", False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying QR code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify QR code"
        )


# =============================================================================
# CAFE TABLE ENDPOINTS
# =============================================================================

@router.get("/venues/{venue_id}/tables", 
            response_model=List[Table],
            summary="Get venue tables",
            description="Get all tables for a specific venue")
async def get_venue_tables(
    venue_id: str,
    status: Optional[TableStatus] = Query(None, description="Filter by status"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all tables for a venue"""
    try:
        # Validate venue access
        await tables_endpoint._validate_venue_access(venue_id, current_user)
        
        repo = get_table_repo()
        
        if status:
            tables_data = await repo.get_by_status(venue_id, status.value)
        else:
            tables_data = await repo.get_by_venue(venue_id)
        
        # Filter active tables for non-admin users
        if current_user.get('role') != 'admin':
            tables_data = [table for table in tables_data if table.get('is_active', False)]
        
        tables = [Table(**table) for table in tables_data]
        
        logger.info(f"Retrieved {len(tables)} tables for venue: {venue_id}")
        return tables
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tables"
        )


@router.get("/venues/{venue_id}/statistics", 
            response_model=Dict[str, Any],
            summary="Get venue table statistics",
            description="Get table statistics for a venue")
async def get_venue_table_statistics(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get table statistics for a venue"""
    try:
        statistics = await tables_endpoint.get_venue_table_statistics(venue_id, current_user)
        
        logger.info(f"Table statistics retrieved for venue: {venue_id}")
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get table statistics"
        )


# =============================================================================
# BULK OPERATIONS ENDPOINTS
# =============================================================================

@router.post("/bulk-create", 
             response_model=ApiResponse,
             summary="Bulk create tables",
             description="Create multiple tables at once")
async def bulk_create_tables(
    venue_id: str,
    start_number: int = Query(..., ge=1, description="Starting table number"),
    count: int = Query(..., ge=1, le=50, description="Number of tables to create"),
    capacity: int = Query(4, ge=1, le=20, description="Default capacity for all tables"),
    location: Optional[str] = Query(None, description="Default location for all tables"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Bulk create tables"""
    try:
        # Validate venue access
        await tables_endpoint._validate_venue_access(venue_id, current_user)
        
        # Check for existing table numbers
        repo = get_table_repo()
        existing_tables = await repo.get_by_venue(venue_id)
        existing_numbers = {table.get('table_number') for table in existing_tables}
        
        # Prepare table data
        tables_to_create = []
        for i in range(count):
            table_number = start_number + i
            
            if table_number in existing_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table number {table_number} already exists"
                )
            
            table_data = {
                "venue_id": venue_id,
                "table_number": table_number,
                "capacity": capacity,
                "location": location,
                "qr_code": tables_endpoint._generate_qr_code(venue_id, table_number),
                "table_status": TableStatus.AVAILABLE.value,
                "is_active": True
            }
            tables_to_create.append(table_data)
        
        # Bulk create
        created_ids = await repo.create_batch(tables_to_create)
        
        logger.info(f"Bulk created {len(created_ids)} tables for venue: {venue_id}")
        return ApiResponse(
            success=True,
            message=f"Created {len(created_ids)} tables successfully",
            data={"created_count": len(created_ids), "table_ids": created_ids}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk creating tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tables"
        )


@router.post("/bulk-update-status", 
             response_model=ApiResponse,
             summary="Bulk update table status",
             description="Update status for multiple tables")
async def bulk_update_table_status(
    table_ids: List[str],
    new_status: TableStatus,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Bulk update table status"""
    try:
        repo = get_table_repo()
        
        # Validate all tables exist and user has access
        for table_id in table_ids:
            table = await repo.get_by_id(table_id)
            if not table:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Table {table_id} not found"
                )
            
            await tables_endpoint._validate_access_permissions(table, current_user)
        
        # Bulk update
        updates = [(table_id, {"table_status": new_status.value}) for table_id in table_ids]
        await repo.update_batch(updates)
        
        logger.info(f"Bulk updated status for {len(table_ids)} tables to {new_status.value}")
        return ApiResponse(
            success=True,
            message=f"Updated status for {len(table_ids)} tables to {new_status.value}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk updating table status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update table status"
        )