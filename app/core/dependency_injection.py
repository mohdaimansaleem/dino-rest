"""
Dependency Injection Container
Centralized service management and dependency resolution
"""
from typing import Dict, Any, Type, TypeVar, Optional, Callable
from functools import lru_cache
import asyncio
from contextlib import asynccontextmanager

from app.core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class DIContainer:
    """Dependency injection container for service management"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._scoped: Dict[str, Any] = {}
        
    def register_singleton(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a singleton service"""
        service_name = service_type.__name__
        self._factories[service_name] = factory
        logger.debug(f"Registered singleton: {service_name}")
    
    def register_transient(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a transient service (new instance each time)"""
        service_name = service_type.__name__
        self._services[service_name] = factory
        logger.debug(f"Registered transient: {service_name}")
    
    def register_scoped(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a scoped service (one instance per scope)"""
        service_name = service_type.__name__
        self._scoped[service_name] = factory
        logger.debug(f"Registered scoped: {service_name}")
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get service instance"""
        service_name = service_type.__name__
        
        # Check singletons first
        if service_name in self._factories:
            if service_name not in self._singletons:
                self._singletons[service_name] = self._factories[service_name]()
            return self._singletons[service_name]
        
        # Check transient services
        if service_name in self._services:
            return self._services[service_name]()
        
        # Check scoped services
        if service_name in self._scoped:
            scope_key = f"scope_{asyncio.current_task()}"
            if scope_key not in self._scoped:
                self._scoped[scope_key] = {}
            
            if service_name not in self._scoped[scope_key]:
                self._scoped[scope_key][service_name] = self._scoped[service_name]()
            
            return self._scoped[scope_key][service_name]
        
        raise ValueError(f"Service {service_name} not registered")
    
    def clear_scope(self) -> None:
        """Clear scoped services for current task"""
        scope_key = f"scope_{asyncio.current_task()}"
        if scope_key in self._scoped:
            del self._scoped[scope_key]
    
    def get_all_services(self) -> Dict[str, str]:
        """Get list of all registered services"""
        return {
            "singletons": list(self._factories.keys()),
            "transients": list(self._services.keys()),
            "scoped": list(self._scoped.keys())
        }


# Global DI container
container = DIContainer()


def register_services():
    """Register all application services"""
    
    # Repository Manager (Singleton)
    def create_repository_manager():
        from app.database.repository_manager import RepositoryManager
        return RepositoryManager()
    
    container.register_singleton(
        type("RepositoryManager", (), {}),
        create_repository_manager
    )
    
    # Auth Service (Singleton)
    def create_auth_service():
        from app.services.auth_service import AuthService
        return AuthService()
    
    container.register_singleton(
        type("AuthService", (), {}),
        create_auth_service
    )
    
    # Validation Service (Singleton)
    def create_validation_service():
        from app.services.validation_service import ValidationService
        return ValidationService()
    
    container.register_singleton(
        type("ValidationService", (), {}),
        create_validation_service
    )
    
    # Role Permission Service (Singleton)
    def create_role_permission_service():
        from app.services.role_permission_service import RolePermissionService
        return RolePermissionService()
    
    container.register_singleton(
        type("RolePermissionService", (), {}),
        create_role_permission_service
    )
    
    # Workspace Onboarding Service (Transient)
    def create_workspace_service():
        from app.services.workspace_onboarding_service import WorkspaceOnboardingService
        return WorkspaceOnboardingService()
    
    container.register_transient(
        type("WorkspaceOnboardingService", (), {}),
        create_workspace_service
    )
    
    logger.info("All services registered in DI container")


# Service accessor functions
@lru_cache(maxsize=1)
def get_repository_manager():
    """Get repository manager instance"""
    return container.get_service(type("RepositoryManager", (), {}))


@lru_cache(maxsize=1)
def get_auth_service():
    """Get auth service instance"""
    return container.get_service(type("AuthService", (), {}))


@lru_cache(maxsize=1)
def get_validation_service():
    """Get validation service instance"""
    return container.get_service(type("ValidationService", (), {}))


@lru_cache(maxsize=1)
def get_role_permission_service():
    """Get role permission service instance"""
    return container.get_service(type("RolePermissionService", (), {}))


def get_workspace_service():
    """Get workspace onboarding service instance (transient)"""
    return container.get_service(type("WorkspaceOnboardingService", (), {}))


# Context manager for scoped services
@asynccontextmanager
async def service_scope():
    """Context manager for scoped services"""
    try:
        yield container
    finally:
        container.clear_scope()


# Dependency injection for FastAPI
def get_container() -> DIContainer:
    """FastAPI dependency to get DI container"""
    return container


# Initialize services on module import
def initialize_di():
    """Initialize dependency injection container"""
    try:
        register_services()
        logger.info("Dependency injection container initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DI container: {e}")
        raise


# Service health check
def check_services_health() -> Dict[str, Any]:
    """Check health of all registered services"""
    health_status = {
        "container_status": "healthy",
        "services": container.get_all_services(),
        "total_services": 0
    }
    
    try:
        services = container.get_all_services()
        health_status["total_services"] = (
            len(services["singletons"]) + 
            len(services["transients"]) + 
            len(services["scoped"])
        )
        
        # Test key services
        try:
            repo_manager = get_repository_manager()
            health_status["repository_manager"] = "healthy"
        except Exception as e:
            health_status["repository_manager"] = f"error: {str(e)}"
        
        try:
            auth_service = get_auth_service()
            health_status["auth_service"] = "healthy"
        except Exception as e:
            health_status["auth_service"] = f"error: {str(e)}"
            
    except Exception as e:
        health_status["container_status"] = f"error: {str(e)}"
    
    return health_status


# Auto-initialize when module is imported
initialize_di()