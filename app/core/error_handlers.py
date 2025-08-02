"""
Centralized Error Handling
Consistent error responses and logging across the application
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import traceback

from app.core.logging_config import get_logger
from app.models.schemas import ErrorResponse

logger = get_logger(__name__)


class APIError(Exception):
    """Custom API error with structured information"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ErrorHandler:
    """Centralized error handling with consistent responses"""
    
    @staticmethod
    def create_error_response(
        error: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """Create standardized error response"""
        return ErrorResponse(
            success=False,
            error=error,
            error_code=error_code,
            details=details
        )
    
    @staticmethod
    def log_error(
        error: Exception,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error with context"""
        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        
        if request:
            context.update({
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
            })
        
        if user_id:
            context["user_id"] = user_id
        
        if additional_context:
            context.update(additional_context)
        
        if isinstance(error, (HTTPException, APIError)):
            logger.warning("API Error occurred", extra=context)
        else:
            logger.error("Unexpected error occurred", extra=context, exc_info=True)


# Global error handler instance
error_handler = ErrorHandler()


# Exception handlers for FastAPI
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    error_handler.log_error(exc, request)
    
    error_response = error_handler.create_error_response(
        error=exc.detail,
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    error_handler.log_error(exc, request)
    
    # Extract validation error details
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = error_handler.create_error_response(
        error="Validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        details={"validation_errors": error_details}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )


async def api_exception_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API exceptions"""
    error_handler.log_error(exc, request)
    
    error_response = error_handler.create_error_response(
        error=exc.message,
        status_code=exc.status_code,
        error_code=exc.error_code,
        details=exc.details
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    error_handler.log_error(exc, request)
    
    # Don't expose internal error details in production
    error_message = "Internal server error"
    error_details = None
    
    # In development, provide more details
    if hasattr(request.app.state, 'debug') and request.app.state.debug:
        error_message = str(exc)
        error_details = {
            "traceback": traceback.format_exc(),
            "type": type(exc).__name__
        }
    
    error_response = error_handler.create_error_response(
        error=error_message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        details=error_details
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


# Common error responses
class CommonErrors:
    """Common error responses for reuse"""
    
    @staticmethod
    def not_found(resource: str = "Resource") -> APIError:
        return APIError(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND"
        )
    
    @staticmethod
    def unauthorized() -> APIError:
        return APIError(
            message="Authentication required",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED"
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> APIError:
        return APIError(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN"
        )
    
    @staticmethod
    def bad_request(message: str = "Bad request") -> APIError:
        return APIError(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST"
        )
    
    @staticmethod
    def conflict(message: str = "Resource already exists") -> APIError:
        return APIError(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT"
        )
    
    @staticmethod
    def validation_error(message: str = "Validation failed", details: Optional[Dict] = None) -> APIError:
        return APIError(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


def get_error_handler() -> ErrorHandler:
    """Get error handler instance"""
    return error_handler