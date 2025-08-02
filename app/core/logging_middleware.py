"""
Logging Middleware and Business Logger
Provides structured logging for business operations and API requests
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class BusinessLogger:
    """Logger for business operations and events"""
    
    def __init__(self):
        self.logger = get_logger("business")
    
    def log_business_operation(self, 
                             operation: str,
                             entity_type: str,
                             entity_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             details: Optional[Dict[str, Any]] = None):
        """Log a business operation"""
        log_data = {
            "operation": operation,
            "entity_type": entity_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if entity_id:
            log_data["entity_id"] = entity_id
        
        if user_id:
            log_data["user_id"] = user_id
        
        if details:
            log_data["details"] = details
        
        self.logger.info(f"Business Operation: {operation}", extra=log_data)
    
    def log_user_action(self, 
                       user_id: str,
                       action: str,
                       resource: str,
                       resource_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log a user action"""
        log_data = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if resource_id:
            log_data["resource_id"] = resource_id
        
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"User Action: {action} on {resource}", extra=log_data)
    
    def log_security_event(self, 
                          event_type: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None):
        """Log a security event"""
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        if details:
            log_data["details"] = details
        
        self.logger.warning(f"Security Event: {event_type}", extra=log_data)
    
    def log_error_event(self, 
                       error_type: str,
                       error_message: str,
                       user_id: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None):
        """Log an error event"""
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if context:
            log_data["context"] = context
        
        self.logger.error(f"Error Event: {error_type}", extra=log_data)
    
    def log_performance_metric(self, 
                             operation: str,
                             duration_ms: float,
                             user_id: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None):
        """Log a performance metric"""
        log_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"Performance: {operation} took {duration_ms:.2f}ms", extra=log_data)


class APIRequestLogger:
    """Logger for API requests and responses"""
    
    def __init__(self):
        self.logger = get_logger("api")
    
    def log_request(self, 
                   method: str,
                   path: str,
                   user_id: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
        """Log an API request"""
        log_data = {
            "method": method,
            "path": path,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        if user_agent:
            log_data["user_agent"] = user_agent
        
        self.logger.info(f"API Request: {method} {path}", extra=log_data)
    
    def log_response(self, 
                    method: str,
                    path: str,
                    status_code: int,
                    duration_ms: float,
                    user_id: Optional[str] = None):
        """Log an API response"""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        
        if level == "info":
            self.logger.info(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)
        elif level == "warning":
            self.logger.warning(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)
        else:
            self.logger.error(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)


class AuditLogger:
    """Logger for audit trail events"""
    
    def __init__(self):
        self.logger = get_logger("audit")
    
    def log_data_change(self, 
                       entity_type: str,
                       entity_id: str,
                       operation: str,
                       user_id: str,
                       old_values: Optional[Dict[str, Any]] = None,
                       new_values: Optional[Dict[str, Any]] = None):
        """Log a data change event"""
        log_data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if old_values:
            log_data["old_values"] = old_values
        
        if new_values:
            log_data["new_values"] = new_values
        
        self.logger.info(f"Data Change: {operation} {entity_type} {entity_id}", extra=log_data)
    
    def log_permission_change(self, 
                            user_id: str,
                            target_user_id: str,
                            permission_change: str,
                            admin_user_id: str):
        """Log a permission change event"""
        log_data = {
            "user_id": user_id,
            "target_user_id": target_user_id,
            "permission_change": permission_change,
            "admin_user_id": admin_user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.logger.info(f"Permission Change: {permission_change} for user {target_user_id}", extra=log_data)
    
    def log_access_attempt(self, 
                          user_id: str,
                          resource: str,
                          resource_id: str,
                          action: str,
                          allowed: bool,
                          reason: Optional[str] = None):
        """Log an access attempt"""
        log_data = {
            "user_id": user_id,
            "resource": resource,
            "resource_id": resource_id,
            "action": action,
            "allowed": allowed,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if reason:
            log_data["reason"] = reason
        
        level = "info" if allowed else "warning"
        message = f"Access {'Granted' if allowed else 'Denied'}: {action} on {resource} {resource_id}"
        
        if level == "info":
            self.logger.info(message, extra=log_data)
        else:
            self.logger.warning(message, extra=log_data)


class DatabaseLogger:
    """Logger for database operations"""
    
    def __init__(self):
        self.logger = get_logger("database")
    
    def log_query(self, 
                 operation: str,
                 collection: str,
                 duration_ms: float,
                 result_count: int = 0,
                 doc_id: Optional[str] = None):
        """Log a database query"""
        log_data = {
            "operation": operation,
            "collection": collection,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if doc_id:
            log_data["doc_id"] = doc_id
        
        self.logger.info(f"DB Query: {operation} on {collection} ({duration_ms:.2f}ms)", extra=log_data)
    
    def log_error(self, 
                 operation: str,
                 collection: str,
                 error: Exception,
                 doc_id: Optional[str] = None,
                 duration_ms: Optional[float] = None):
        """Log a database error"""
        log_data = {
            "operation": operation,
            "collection": collection,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if doc_id:
            log_data["doc_id"] = doc_id
        
        if duration_ms:
            log_data["duration_ms"] = duration_ms
        
        self.logger.error(f"DB Error: {operation} on {collection} - {error}", extra=log_data)


# Global instances
business_logger = BusinessLogger()
api_request_logger = APIRequestLogger()
audit_logger = AuditLogger()
db_logger = DatabaseLogger()


def get_business_logger() -> BusinessLogger:
    """Get business logger instance"""
    return business_logger


def get_api_request_logger() -> APIRequestLogger:
    """Get API request logger instance"""
    return api_request_logger


def get_audit_logger() -> AuditLogger:
    """Get audit logger instance"""
    return audit_logger


def get_db_logger() -> DatabaseLogger:
    """Get database logger instance"""
    return db_logger