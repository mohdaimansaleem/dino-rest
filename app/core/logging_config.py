"""
Production Logging Configuration
Structured logging for Google Cloud Run deployment
"""
import logging
import logging.config
import sys
from typing import Dict, Any
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging compatible with Google Cloud Logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup production logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured",
                "stream": sys.stdout
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
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
            }
        }
    }
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """
        Log an operation with additional context
        
        Args:
            operation: Operation name
            **kwargs: Additional context to log
        """
        extra = {"operation": operation}
        extra.update(kwargs)
        self.logger.info(f"Operation: {operation}", extra=extra)
    
    def log_error(self, error: Exception, operation: str = None, **kwargs) -> None:
        """
        Log an error with context
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            **kwargs: Additional context
        """
        extra = {}
        if operation:
            extra["operation"] = operation
        extra.update(kwargs)
        
        self.logger.error(
            f"Error in {operation or 'operation'}: {str(error)}", 
            exc_info=True, 
            extra=extra
        )