"""
Workspace Onboarding Service
Handles complete workspace creation with venue setup and user management
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets
from fastapi import HTTPException, status

from app.models.schemas import (
    WorkspaceCreate, WorkspaceOnboardingResponse, VenueCreationResponse,
    UserRole, WorkspaceStatus, VenueStatus, OwnerDetails
)
from app.database.firestore import (
    get_workspace_repo, get_cafe_repo, get_user_repo, get_table_repo
)
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class WorkspaceOnboardingService:
    """Service for handling complete workspace onboarding process"""
    
    def __init__(self):
        self.workspace_repo = get_workspace_repo()
        self.venue_repo = get_cafe_repo()
        self.user_repo = get_user_repo()
        self.table_repo = get_table_repo()
    
    async def create_workspace_with_venue(self, onboarding_data: WorkspaceCreate) -> WorkspaceOnboardingResponse:
        """
        Complete workspace onboarding process:
        1. Validate data and check uniqueness
        2. Create workspace
        3. Create default venue
        4. Create superadmin user
        5. Generate initial tables with QR codes
        6. Setup default permissions
        """
        try:
            # Step 1: Validate and prepare data
            await self._validate_onboarding_data(onboarding_data)
            
            # Step 2: Create workspace
            workspace_id = await self._create_workspace(onboarding_data)
            
            # Step 3: Create default venue
            venue_id = await self._create_default_venue(workspace_id, onboarding_data)
            
            # Step 4: Create superadmin user
            user_id, tokens = await self._create_superadmin_user(
                workspace_id, venue_id, onboarding_data.owner_details
            )
            
            # Step 5: Generate initial tables
            tables_created = await self._generate_initial_tables(venue_id)
            
            # Step 6: Setup default permissions and roles
            await self._setup_default_permissions(workspace_id, user_id)
            
            # Step 7: Send welcome notifications (if needed)
            await self._send_welcome_notifications(workspace_id, user_id)
            
            logger.info(f"Workspace onboarding completed: {workspace_id}")
            
            return WorkspaceOnboardingResponse(
                success=True,
                workspace_id=workspace_id,
                default_venue_id=venue_id,
                superadmin_user_id=user_id,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                message="Workspace created successfully! Welcome to Dino Platform.",
                next_steps=[
                    "Complete your venue menu setup",
                    "Configure table layouts and QR codes",
                    "Add staff members (Admin/Operator roles)",
                    "Test your first order flow",
                    "Customize venue settings and operating hours"
                ]
            )
            
        except Exception as e:
            logger.error(f"Workspace onboarding failed: {e}")
            # Cleanup any partially created data
            await self._cleanup_failed_onboarding(locals().get('workspace_id'))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workspace onboarding failed: {str(e)}"
            )
    
    async def _validate_onboarding_data(self, data: WorkspaceCreate) -> None:
        """Validate onboarding data and check for duplicates"""
        
        # Check if workspace name is unique
        existing_workspace = await self.workspace_repo.query([
            ('name', '==', data.workspace_name.lower().strip())
        ])
        if existing_workspace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace name already exists"
            )
        
        # Check if owner email is unique
        existing_user = await self.user_repo.query([
            ('email', '==', data.owner_details.email.lower())
        ])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered"
            )
        
        # Check if owner phone is unique
        if data.owner_details.phone:
            existing_phone = await self.user_repo.query([
                ('phone', '==', data.owner_details.phone)
            ])
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
        
        # Validate venue operating hours (must have 7 days)
        if len(data.default_venue.operating_hours) != 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operating hours must be provided for all 7 days"
            )
        
        # Validate terms acceptance
        if not data.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Terms and conditions must be accepted"
            )
    
    async def _create_workspace(self, data: WorkspaceCreate) -> str:
        """Create workspace with initial configuration"""
        
        workspace_id = str(uuid.uuid4())
        
        workspace_data = {
            "id": workspace_id,
            "name": data.workspace_name.lower().strip(),
            "business_type": data.business_type,
            "business_registration_number": data.business_registration_number,
            "tax_id": data.tax_id,
            "status": WorkspaceStatus.TRIAL.value,
            "subscription_plan": data.subscription_plan,
            "billing_address": data.billing_address.dict() if data.billing_address else None,
            "venue_ids": [],  # Will be populated when venues are created
            "total_venues": 0,
            "max_venues": 1 if data.subscription_plan == "trial" else 10,
            "total_users": 0,
            "max_users": 3 if data.subscription_plan == "trial" else 50,
            "features_enabled": self._get_plan_features(data.subscription_plan),
            "trial_ends_at": datetime.utcnow() + timedelta(days=30) if data.subscription_plan == "trial" else None,
            "marketing_consent": data.marketing_consent,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }
        
        await self.workspace_repo.create(workspace_data)
        logger.info(f"Workspace created: {workspace_id}")
        
        return workspace_id
    
    async def _create_default_venue(self, workspace_id: str, data: WorkspaceCreate) -> str:
        """Create the default venue for the workspace"""
        
        venue_id = str(uuid.uuid4())
        venue_data = data.default_venue
        
        venue_record = {
            "id": venue_id,
            "workspace_id": workspace_id,
            "name": venue_data.name,
            "description": venue_data.description,
            "cuisine_types": venue_data.cuisine_types,
            "location": venue_data.location.dict(),
            "operating_hours": [hours.dict() for hours in venue_data.operating_hours],
            "phone": venue_data.phone,
            "email": venue_data.email,
            "website": venue_data.website,
            "capacity": venue_data.capacity,
            "price_range": venue_data.price_range,
            "features": venue_data.features,
            "social_media": venue_data.social_media,
            "status": VenueStatus.ACTIVE.value,
            "is_default": True,
            "is_active": True,
            "is_verified": False,
            "rating": 0.0,
            "total_reviews": 0,
            "total_orders": 0,
            "total_revenue": 0.0,
            "logo_url": None,
            "cover_image_url": None,
            "gallery_urls": [],
            "subscription_status": "active",
            "subscription_plan": data.subscription_plan,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.venue_repo.create(venue_record)
        
        # Update workspace with venue ID
        await self.workspace_repo.update(workspace_id, {
            "venue_ids": [venue_id],
            "total_venues": 1,
            "default_venue_id": venue_id
        })
        
        logger.info(f"Default venue created: {venue_id} for workspace: {workspace_id}")
        
        return venue_id
    
    async def _create_superadmin_user(self, workspace_id: str, venue_id: str, owner_data: OwnerDetails) -> Tuple[str, Dict[str, str]]:
        """Create superadmin user and generate tokens"""
        
        user_id = str(uuid.uuid4())
        
        # Hash password
        hashed_password = get_password_hash(owner_data.password)
        
        user_record = {
            "id": user_id,
            "workspace_id": workspace_id,
            "venue_id": venue_id,  # Primary venue
            "email": owner_data.email.lower(),
            "phone": owner_data.phone,
            "full_name": owner_data.full_name,
            "role": UserRole.SUPERADMIN.value,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_verified": True,
            "is_owner": True,
            "permissions": self._get_superadmin_permissions(),
            "venue_access": [venue_id],  # Can access all venues in workspace
            "date_of_birth": owner_data.date_of_birth,
            "address": owner_data.address,
            "emergency_contact": owner_data.emergency_contact,
            "id_proof_type": owner_data.id_proof_type,
            "id_proof_number": owner_data.id_proof_number,
            "last_login": None,
            "login_count": 0,
            "password_changed_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.user_repo.create(user_record)
        
        # Generate tokens
        token_data = {
            "sub": user_id,
            "email": owner_data.email.lower(),
            "role": UserRole.SUPERADMIN.value,
            "workspace_id": workspace_id,
            "venue_id": venue_id
        }
        
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        # Update workspace with user count
        await self.workspace_repo.update(workspace_id, {
            "total_users": 1,
            "owner_id": user_id
        })
        
        logger.info(f"Superadmin user created: {user_id}")
        
        return user_id, {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    async def _generate_initial_tables(self, venue_id: str, table_count: int = 10) -> int:
        """Generate initial tables with QR codes for the venue"""
        
        tables_created = 0
        
        for table_number in range(1, table_count + 1):
            table_id = str(uuid.uuid4())
            
            # Generate QR code
            qr_code = self._generate_table_qr_code(venue_id, table_number)
            
            table_data = {
                "id": table_id,
                "venue_id": venue_id,
                "table_number": table_number,
                "capacity": 4,  # Default capacity
                "location": f"Table {table_number}",
                "qr_code": qr_code,
                "qr_code_url": None,  # Will be generated later
                "table_status": "available",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.table_repo.create(table_data)
            tables_created += 1
        
        logger.info(f"Generated {tables_created} tables for venue: {venue_id}")
        
        return tables_created
    
    def _generate_table_qr_code(self, venue_id: str, table_number: int) -> str:
        """Generate encrypted QR code for table"""
        import json
        import base64
        
        qr_data = {
            "venue_id": venue_id,
            "table_number": table_number,
            "type": "table_access",
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Convert to JSON and encode
        qr_json = json.dumps(qr_data, sort_keys=True)
        qr_bytes = qr_json.encode('utf-8')
        
        # Create hash for verification
        hash_object = hashlib.sha256(qr_bytes)
        qr_hash = hash_object.hexdigest()[:16]
        
        # Encode with base64
        qr_encoded = base64.b64encode(qr_bytes).decode('utf-8')
        
        return f"{qr_encoded}.{qr_hash}"
    
    async def _setup_default_permissions(self, workspace_id: str, user_id: str) -> None:
        """Setup default permissions and roles for the workspace"""
        
        # Create default role definitions
        roles_data = [
            {
                "id": str(uuid.uuid4()),
                "workspace_id": workspace_id,
                "name": "superadmin",
                "display_name": "Super Administrator",
                "description": "Full access to workspace, can create venues and manage all users",
                "permissions": self._get_superadmin_permissions(),
                "is_system_role": True,
                "created_by": user_id,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "workspace_id": workspace_id,
                "name": "admin",
                "display_name": "Venue Administrator",
                "description": "Full access to venue, can manage operators",
                "permissions": self._get_admin_permissions(),
                "is_system_role": True,
                "created_by": user_id,
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "workspace_id": workspace_id,
                "name": "operator",
                "display_name": "Venue Operator",
                "description": "Limited access to view orders and update table status",
                "permissions": self._get_operator_permissions(),
                "is_system_role": True,
                "created_by": user_id,
                "created_at": datetime.utcnow()
            }
        ]
        
        # Store roles (you might want to create a roles repository)
        # For now, we'll store in workspace metadata
        await self.workspace_repo.update(workspace_id, {
            "default_roles": roles_data
        })
    
    async def _send_welcome_notifications(self, workspace_id: str, user_id: str) -> None:
        """Send welcome notifications and setup guides"""
        # TODO: Implement notification service
        logger.info(f"Welcome notifications sent for workspace: {workspace_id}")
    
    async def _cleanup_failed_onboarding(self, workspace_id: Optional[str]) -> None:
        """Cleanup any partially created data if onboarding fails"""
        if workspace_id:
            try:
                # Delete workspace and related data
                await self.workspace_repo.delete(workspace_id)
                logger.info(f"Cleaned up failed onboarding for workspace: {workspace_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup workspace {workspace_id}: {e}")
    
    def _get_plan_features(self, plan: str) -> List[str]:
        """Get features enabled for subscription plan"""
        features_map = {
            "trial": [
                "basic_menu", "qr_ordering", "table_management", 
                "basic_analytics", "customer_management"
            ],
            "basic": [
                "basic_menu", "qr_ordering", "table_management", 
                "basic_analytics", "customer_management", "staff_management"
            ],
            "premium": [
                "advanced_menu", "qr_ordering", "table_management", 
                "advanced_analytics", "customer_management", "staff_management",
                "inventory_management", "loyalty_program", "marketing_tools"
            ]
        }
        return features_map.get(plan, features_map["trial"])
    
    def _get_superadmin_permissions(self) -> List[str]:
        """Get all permissions for superadmin role"""
        return [
            # Workspace permissions
            "workspace:read", "workspace:update", "workspace:delete",
            "workspace:analytics", "workspace:settings",
            
            # Venue permissions
            "venue:create", "venue:read", "venue:update", "venue:delete",
            "venue:switch", "venue:analytics", "venue:settings",
            
            # User management
            "user:create", "user:read", "user:update", "user:delete",
            "user:change_password", "role:manage",
            
            # Menu management
            "menu:create", "menu:read", "menu:update", "menu:delete",
            "menu:bulk_operations",
            
            # Order management
            "order:read", "order:update", "order:analytics",
            
            # Table management
            "table:create", "table:read", "table:update", "table:delete",
            "table:qr_generate",
            
            # Customer management
            "customer:read", "customer:analytics",
            
            # System permissions
            "system:backup", "system:export", "system:import"
        ]
    
    def _get_admin_permissions(self) -> List[str]:
        """Get permissions for admin role (venue-specific)"""
        return [
            # Venue permissions (own venue only)
            "venue:read", "venue:update", "venue:analytics", "venue:settings",
            
            # User management (venue staff only)
            "user:create_operator", "user:read", "user:update_operator",
            "user:change_operator_password",
            
            # Menu management
            "menu:create", "menu:read", "menu:update", "menu:delete",
            "menu:bulk_operations",
            
            # Order management
            "order:read", "order:update", "order:analytics",
            
            # Table management
            "table:create", "table:read", "table:update", "table:delete",
            "table:qr_generate",
            
            # Customer management
            "customer:read", "customer:analytics"
        ]
    
    def _get_operator_permissions(self) -> List[str]:
        """Get permissions for operator role (limited access)"""
        return [
            # Basic venue access
            "venue:read",
            
            # Order management (limited)
            "order:read", "order:update_status",
            
            # Table management (limited)
            "table:read", "table:update_status",
            
            # Customer management (read only)
            "customer:read"
        ]


# Service instance
workspace_onboarding_service = WorkspaceOnboardingService()