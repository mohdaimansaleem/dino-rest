"""
Enhanced Production Logging Configuration
Comprehensive structured logging for debugging and monitoring
"""
import logging
import logging.config
import sys
import uuid
import time
import traceback
from typing import Dict, Any, Optional
import json
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
operation_var: ContextVar[Optional[str]] = ContextVar('operation', default=None)


class EnhancedStructuredFormatter(logging.Formatter):
    """
    Enhanced formatter for structured logging with request correlation
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON with enhanced context"""
        
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        operation = operation_var.get()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add context information
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = user_id
        if operation:
            log_entry["operation"] = operation
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add performance metrics if available
        if hasattr(record, 'duration'):
            log_entry["performance"] = {
                "duration_ms": record.duration,
                "slow_query": record.duration > 1000 if hasattr(record, 'duration') else False
            }
        
        return json.dumps(log_entry, default=str)


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def filter(self, record):
        # Add timestamp for performance tracking
        if not hasattr(record, 'start_time'):
            record.start_time = time.time()
        return True


def setup_enhanced_logging(log_level: str = "INFO", enable_debug: bool = False) -> None:
    """
    Setup enhanced production logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_debug: Enable debug logging features
    """
    
    # Determine if we're in development mode
    is_development = log_level == "DEBUG" or enable_debug
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "enhanced_structured": {
                "()": EnhancedStructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
            }
        },
        "filters": {
            "performance": {
                "()": PerformanceFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "enhanced_structured" if not is_development else "detailed",
                "stream": sys.stdout,
                "filters": ["performance"]
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "enhanced_structured",
                "stream": sys.stderr,
                "filters": ["performance"]
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "error_console"] if not is_development else ["console"]
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "app.database": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.services": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.api": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.core": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO" if is_development else "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "google.cloud": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "google.auth": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Log the logging configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Enhanced logging configured - Level: {log_level}, Debug: {enable_debug}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str = None, user_id: str = None, operation: str = None):
    """
    Set request context for logging correlation
    
    Args:
        request_id: Unique request identifier
        user_id: User identifier
        operation: Operation being performed
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if operation:
        operation_var.set(operation)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)
    operation_var.set(None)


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())


class EnhancedLoggerMixin:
    """
    Enhanced mixin class to add comprehensive logging capabilities to any class
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    def log_operation(self, operation: str, level: str = "INFO", **kwargs) -> None:
        """
        Log an operation with additional context
        
        Args:
            operation: Operation name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            **kwargs: Additional context to log
        """
        extra = {"operation": operation}
        extra.update(kwargs)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, f"Operation: {operation}", extra=extra)
    
    def log_error(self, error: Exception, operation: str = None, level: str = "ERROR", **kwargs) -> None:
        """
        Log an error with context
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            level: Log level
            **kwargs: Additional context
        """
        extra = {}
        if operation:
            extra["operation"] = operation
        extra.update(kwargs)
        
        # Add error details
        extra["error_type"] = type(error).__name__
        extra["error_message"] = str(error)
        
        log_level = getattr(logging, level.upper(), logging.ERROR)
        self.logger.log(
            log_level,
            f"Error in {operation or 'operation'}: {str(error)}", 
            exc_info=True, 
            extra=extra
        )
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs) -> None:
        """
        Log performance metrics
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            **kwargs: Additional context
        """
        extra = {
            "operation": operation,
            "duration": duration_ms,
            "performance_category": "slow" if duration_ms > 1000 else "normal"
        }
        extra.update(kwargs)
        
        level = logging.WARNING if duration_ms > 1000 else logging.INFO
        self.logger.log(
            level,
            f"Performance: {operation} took {duration_ms:.2f}ms",
            extra=extra
        )
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message with context"""
        self.logger.debug(message, extra=kwargs)
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message with context"""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message with context"""
        self.logger.warning(message, extra=kwargs)
    
    def log_critical(self, message: str, **kwargs) -> None:
        """Log critical message with context"""
        self.logger.critical(message, extra=kwargs)


def log_function_call(include_args: bool = False, include_result: bool = False):
    """
    Decorator to log function calls with performance metrics
    
    Args:
        include_args: Whether to include function arguments in logs
        include_result: Whether to include function result in logs
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            # Log function entry
            log_data = {
                "function_name": func.__name__,
                "function_module": func.__module__,
                "operation": f"{func.__module__}.{func.__name__}"
            }
            
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            logger.debug(f"Entering function: {func.__name__}", extra=log_data)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful completion
                log_data["duration"] = duration_ms
                log_data["status"] = "success"
                
                if include_result:
                    log_data["result"] = str(result)[:500]  # Limit result size
                
                level = logging.WARNING if duration_ms > 1000 else logging.DEBUG
                logger.log(
                    level,
                    f"Function completed: {func.__name__} ({duration_ms:.2f}ms)",
                    extra=log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                log_data["duration"] = duration_ms
                log_data["status"] = "error"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                
                logger.error(
                    f"Function failed: {func.__name__} ({duration_ms:.2f}ms) - {str(e)}",
                    exc_info=True,
                    extra=log_data
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            # Log function entry
            log_data = {
                "function_name": func.__name__,
                "function_module": func.__module__,
                "operation": f"{func.__module__}.{func.__name__}"
            }
            
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            logger.debug(f"Entering function: {func.__name__}", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful completion
                log_data["duration"] = duration_ms
                log_data["status"] = "success"
                
                if include_result:
                    log_data["result"] = str(result)[:500]  # Limit result size
                
                level = logging.WARNING if duration_ms > 1000 else logging.DEBUG
                logger.log(
                    level,
                    f"Function completed: {func.__name__} ({duration_ms:.2f}ms)",
                    extra=log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                log_data["duration"] = duration_ms
                log_data["status"] = "error"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                
                logger.error(
                    f"Function failed: {func.__name__} ({duration_ms:.2f}ms) - {str(e)}",
                    exc_info=True,
                    extra=log_data
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Backward compatibility
LoggerMixin = EnhancedLoggerMixin
setup_logging = setup_enhanced_logging