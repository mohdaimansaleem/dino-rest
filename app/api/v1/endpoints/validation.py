"""
Validation API Endpoints
Test and validate data without creating records
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.models.schemas import ApiResponse
from app.services.validation_service import get_validation_service
from app.core.security import get_current_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/validate-user", 
             response_model=Dict[str, Any],
             summary="Validate user data",
             description="Validate user data without creating the user")
async def validate_user_data(
    user_data: Dict[str, Any],
    is_update: bool = Query(False, description="Whether this is for update operation"),
    user_id: Optional[str] = Query(None, description="User ID for update validation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate user data without creating the user"""
    try:
        validation_service = get_validation_service()
        
        errors = await validation_service.validate_user_data(
            user_data, is_update=is_update, user_id=user_id
        )
        
        result = validation_service.format_validation_errors(errors)
        
        logger.info(f"User data validation performed by {current_user.get('id')}: {result['valid']}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.post("/validate-workspace", 
             response_model=Dict[str, Any],
             summary="Validate workspace data",
             description="Validate workspace data without creating the workspace")
async def validate_workspace_data(
    workspace_data: Dict[str, Any],
    is_update: bool = Query(False, description="Whether this is for update operation"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID for update validation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate workspace data without creating the workspace"""
    try:
        validation_service = get_validation_service()
        
        errors = await validation_service.validate_workspace_data(
            workspace_data, is_update=is_update, workspace_id=workspace_id
        )
        
        result = validation_service.format_validation_errors(errors)
        
        logger.info(f"Workspace data validation performed by {current_user.get('id')}: {result['valid']}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating workspace data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.post("/validate-venue", 
             response_model=Dict[str, Any],
             summary="Validate venue data",
             description="Validate venue data without creating the venue")
async def validate_venue_data(
    venue_data: Dict[str, Any],
    is_update: bool = Query(False, description="Whether this is for update operation"),
    venue_id: Optional[str] = Query(None, description="Venue ID for update validation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate venue data without creating the venue"""
    try:
        validation_service = get_validation_service()
        
        errors = await validation_service.validate_venue_data(
            venue_data, is_update=is_update, venue_id=venue_id
        )
        
        result = validation_service.format_validation_errors(errors)
        
        logger.info(f"Venue data validation performed by {current_user.get('id')}: {result['valid']}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating venue data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.post("/validate-order", 
             response_model=Dict[str, Any],
             summary="Validate order data",
             description="Validate order data without creating the order")
async def validate_order_data(
    order_data: Dict[str, Any],
    is_update: bool = Query(False, description="Whether this is for update operation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate order data without creating the order"""
    try:
        validation_service = get_validation_service()
        
        errors = await validation_service.validate_order_data(
            order_data, is_update=is_update
        )
        
        result = validation_service.format_validation_errors(errors)
        
        logger.info(f"Order data validation performed by {current_user.get('id')}: {result['valid']}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating order data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.post("/validate-collection/{collection_name}", 
             response_model=Dict[str, Any],
             summary="Validate data for any collection",
             description="Generic validation endpoint for any collection")
async def validate_collection_data(
    collection_name: str,
    data: Dict[str, Any],
    is_update: bool = Query(False, description="Whether this is for update operation"),
    item_id: Optional[str] = Query(None, description="Item ID for update validation"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate data for any collection"""
    try:
        validation_service = get_validation_service()
        
        # Validate collection name
        valid_collections = [
            "users", "workspaces", "venues", "orders", "menu_items", 
            "menu_categories", "tables", "customers", "roles", "permissions"
        ]
        
        if collection_name not in valid_collections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid collection name. Must be one of: {', '.join(valid_collections)}"
            )
        
        errors = await validation_service.validate_collection_data(
            collection_name, data, is_update=is_update, item_id=item_id
        )
        
        result = validation_service.format_validation_errors(errors)
        
        logger.info(f"Collection {collection_name} data validation performed by {current_user.get('id')}: {result['valid']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating {collection_name} data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation failed"
        )


@router.get("/validation-rules/{collection_name}", 
            response_model=Dict[str, Any],
            summary="Get validation rules for a collection",
            description="Get detailed validation rules and requirements for a collection")
async def get_validation_rules(
    collection_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get validation rules for a collection"""
    try:
        # Define validation rules for each collection
        validation_rules = {
            "users": {
                "required_fields": ["email", "phone", "first_name", "last_name", "password"],
                "field_rules": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "unique": True,
                        "description": "Valid email address, must be unique"
                    },
                    "phone": {
                        "type": "string",
                        "pattern": "^[+]?[1-9]?[0-9]{7,15}$",
                        "unique": True,
                        "description": "Phone number with 7-15 digits, optional + prefix, must be unique"
                    },
                    "first_name": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 50,
                        "description": "First name, 1-50 characters"
                    },
                    "last_name": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 50,
                        "description": "Last name, 1-50 characters"
                    },
                    "password": {
                        "type": "string",
                        "min_length": 8,
                        "max_length": 128,
                        "requirements": [
                            "At least one uppercase letter",
                            "At least one lowercase letter",
                            "At least one digit"
                        ],
                        "description": "Strong password with mixed case, numbers"
                    },
                    "role_id": {
                        "type": "string",
                        "reference": "roles",
                        "description": "Must reference an existing role"
                    },
                    "workspace_id": {
                        "type": "string",
                        "reference": "workspaces",
                        "description": "Must reference an existing active workspace"
                    },
                    "venue_id": {
                        "type": "string",
                        "reference": "venues",
                        "description": "Must reference an existing active venue"
                    },
                    "gender": {
                        "type": "enum",
                        "values": ["male", "female", "other", "prefer_not_to_say"],
                        "description": "Gender selection"
                    }
                }
            },
            "workspaces": {
                "required_fields": ["display_name", "business_type"],
                "field_rules": {
                    "display_name": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 100,
                        "description": "Workspace display name, 1-100 characters"
                    },
                    "description": {
                        "type": "string",
                        "max_length": 500,
                        "description": "Optional description, max 500 characters"
                    },
                    "business_type": {
                        "type": "enum",
                        "values": ["venue", "restaurant", "both"],
                        "description": "Type of business"
                    },
                    "owner_id": {
                        "type": "string",
                        "reference": "users",
                        "description": "Must reference an existing active user"
                    }
                }
            },
            "venues": {
                "required_fields": ["name", "description", "location", "phone", "email", "price_range", "workspace_id"],
                "field_rules": {
                    "name": {
                        "type": "string",
                        "min_length": 1,
                        "max_length": 100,
                        "description": "Venue name, 1-100 characters"
                    },
                    "description": {
                        "type": "string",
                        "max_length": 1000,
                        "description": "Venue description, max 1000 characters"
                    },
                    "phone": {
                        "type": "string",
                        "pattern": "^[+]?[1-9]?[0-9]{7,15}$",
                        "description": "Phone number with 7-15 digits, optional + prefix"
                    },
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "Valid email address"
                    },
                    "price_range": {
                        "type": "enum",
                        "values": ["budget", "mid_range", "premium", "luxury"],
                        "description": "Price range category"
                    },
                    "workspace_id": {
                        "type": "string",
                        "reference": "workspaces",
                        "description": "Must reference an existing active workspace"
                    },
                    "location": {
                        "type": "object",
                        "required_fields": ["address", "city", "state", "country", "postal_code"],
                        "description": "Complete address information"
                    }
                }
            },
            "orders": {
                "required_fields": ["venue_id", "customer_id", "order_type", "items"],
                "field_rules": {
                    "venue_id": {
                        "type": "string",
                        "reference": "venues",
                        "description": "Must reference an existing active venue"
                    },
                    "customer_id": {
                        "type": "string",
                        "reference": "customers",
                        "description": "Must reference an existing customer"
                    },
                    "order_type": {
                        "type": "enum",
                        "values": ["dine_in", "takeaway", "delivery"],
                        "description": "Type of order"
                    },
                    "items": {
                        "type": "array",
                        "min_items": 1,
                        "max_items": 50,
                        "description": "Order items, 1-50 items required"
                    },
                    "table_id": {
                        "type": "string",
                        "reference": "tables",
                        "description": "Must reference an existing table in the venue"
                    }
                }
            }
        }
        
        if collection_name not in validation_rules:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation rules not found for collection: {collection_name}"
            )
        
        logger.info(f"Validation rules requested for {collection_name} by {current_user.get('id')}")
        return {
            "collection": collection_name,
            "rules": validation_rules[collection_name]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation rules for {collection_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation rules"
        )


@router.get("/validation-examples/{collection_name}", 
            response_model=Dict[str, Any],
            summary="Get validation examples for a collection",
            description="Get example valid and invalid data for a collection")
async def get_validation_examples(
    collection_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get validation examples for a collection"""
    try:
        examples = {
            "users": {
                "valid_example": {
                    "email": "john.doe@example.com",
                    "phone": "+1234567890",
                    "first_name": "John",
                    "last_name": "Doe",
                    "password": "SecurePass123",
                    "gender": "male",
                    "date_of_birth": "1990-01-01"
                },
                "invalid_examples": [
                    {
                        "data": {
                            "email": "invalid-email",
                            "phone": "123",
                            "first_name": "",
                            "password": "weak"
                        },
                        "errors": [
                            "Invalid email format",
                            "Phone number too short",
                            "First name cannot be empty",
                            "Last name is required",
                            "Password must be at least 8 characters",
                            "Password must contain uppercase letter",
                            "Password must contain digit"
                        ]
                    }
                ]
            },
            "workspaces": {
                "valid_example": {
                    "display_name": "My Restaurant Chain",
                    "description": "A chain of family restaurants",
                    "business_type": "restaurant"
                },
                "invalid_examples": [
                    {
                        "data": {
                            "display_name": "",
                            "business_type": "invalid_type"
                        },
                        "errors": [
                            "Display name cannot be empty",
                            "Business type must be one of: venue, restaurant, both"
                        ]
                    }
                ]
            }
        }
        
        if collection_name not in examples:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Examples not found for collection: {collection_name}"
            )
        
        logger.info(f"Validation examples requested for {collection_name} by {current_user.get('id')}")
        return {
            "collection": collection_name,
            "examples": examples[collection_name]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation examples for {collection_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation examples"
        )