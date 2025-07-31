"""
Validation Middleware
Automatically validates data before database operations
"""
from typing import Dict, Any, Optional, List
from functools import wraps
from fastapi import HTTPException, status

from app.services.validation_service import get_validation_service, ValidationError
from app.core.logging_config import LoggerMixin


class ValidationMiddleware(LoggerMixin):
    """Middleware to validate data before database operations"""
    
    def __init__(self):
        super().__init__()
        self.validation_service = get_validation_service()
    
    def validate_before_create(self, collection_name: str):
        """Decorator to validate data before creation"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract data from arguments
                data = None
                if args and isinstance(args[0], dict):
                    data = args[0]
                elif 'data' in kwargs:
                    data = kwargs['data']
                
                if data:
                    # Validate data
                    errors = await self.validation_service.validate_collection_data(
                        collection_name, data, is_update=False
                    )
                    
                    if errors:
                        self.validation_service.raise_validation_exception(errors)
                
                # Call original function
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def validate_before_update(self, collection_name: str):
        """Decorator to validate data before update"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract data and item_id from arguments
                data = None
                item_id = None
                
                if len(args) >= 2:
                    item_id = args[0] if isinstance(args[0], str) else None
                    data = args[1] if isinstance(args[1], dict) else None
                
                if 'doc_id' in kwargs:
                    item_id = kwargs['doc_id']
                if 'data' in kwargs:
                    data = kwargs['data']
                
                if data:
                    # Validate data
                    errors = await self.validation_service.validate_collection_data(
                        collection_name, data, is_update=True, item_id=item_id
                    )
                    
                    if errors:
                        self.validation_service.raise_validation_exception(errors)
                
                # Call original function
                return await func(*args, **kwargs)
            return wrapper
        return decorator


# Global middleware instance
validation_middleware = ValidationMiddleware()


def get_validation_middleware() -> ValidationMiddleware:
    """Get validation middleware instance"""
    return validation_middleware


# Decorator functions for easy use
def validate_create(collection_name: str):
    """Decorator to validate data before creation"""
    return validation_middleware.validate_before_create(collection_name)


def validate_update(collection_name: str):
    """Decorator to validate data before update"""
    return validation_middleware.validate_before_update(collection_name)