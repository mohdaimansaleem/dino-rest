"""
Dino E-Menu Backend API
Simplified FastAPI application for Google Cloud Run
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

# Setup enhanced logging first
from app.core.logging_config import setup_enhanced_logging, get_logger

# Determine log level from environment
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
enable_debug = os.environ.get("DEBUG", "false").lower() == "true"

# Setup enhanced logging
setup_enhanced_logging(log_level=log_level, enable_debug=enable_debug)
logger = get_logger(__name__)

# Import app components
try:
    from app.core.config import settings
    logger.info("✅ Settings loaded successfully")
except Exception as e:
    logger.warning(f"⚠️ Settings loading failed: {e}")
    # Create minimal settings
    class MinimalSettings:
        ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")
        DEBUG = False
        LOG_LEVEL = "INFO"
        GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "unknown")
        DATABASE_NAME = os.environ.get("DATABASE_NAME", "unknown")
        is_production = True
        CORS_ORIGINS = ["*"]
        CORS_ALLOW_CREDENTIALS = True
        CORS_ALLOW_METHODS = ["*"]
        CORS_ALLOW_HEADERS = ["*"]
    settings = MinimalSettings()

# Initialize dependency injection
try:
    from app.core.dependency_injection import initialize_di, check_services_health
    logger.info("✅ Dependency injection initialized successfully")
    di_available = True
except Exception as e:
    logger.warning(f"⚠️ Dependency injection initialization failed: {e}")
    di_available = False

try:
    from app.api.v1.api import api_router
    logger.info("✅ API router loaded successfully")
    api_router_available = True
except Exception as e:
    logger.warning(f"⚠️ API router loading failed: {e}")
    api_router_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for Cloud Run deployment"""
    # Startup
    logger.info("🦕 Starting Dino E-Menu API...")
    logger.info("Environment Variables:")
    logger.info(f"PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'not set')}")
    logger.info(f"DATABASE_NAME: {os.environ.get('DATABASE_NAME', 'not set')}")
    logger.info(f"GCP_PROJECT_ID: {os.environ.get('GCP_PROJECT_ID', 'not set')}")
    
    logger.info("✅ Dino E-Menu API startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("🦕 Shutting down Dino E-Menu API")


# Create FastAPI application
docs_url = "/docs" if not settings.is_production else None
redoc_url = "/redoc" if not settings.is_production else None

app = FastAPI(
    title="Dino E-Menu API",
    description="A comprehensive e-menu solution for restaurants and cafes with role-based access control",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    redirect_slashes=False,
)

# =============================================================================
# MIDDLEWARE SETUP
# =============================================================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, 'CORS_ORIGINS', ["*"]),
    allow_credentials=getattr(settings, 'CORS_ALLOW_CREDENTIALS', True),
    allow_methods=getattr(settings, 'CORS_ALLOW_METHODS', ["*"]),
    allow_headers=getattr(settings, 'CORS_ALLOW_HEADERS', ["*"]),
)
logger.info("✅ CORS middleware enabled")

# Include API routes if available
if api_router_available:
    try:
        app.include_router(api_router, prefix="/api/v1")
        logger.info("✅ API routes included successfully")
    except Exception as e:
        logger.warning(f"⚠️ Failed to include API routes: {e}")


# =============================================================================
# HEALTH CHECK ENDPOINTS (Required for Cloud Run)
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dino E-Menu API",
        "version": "2.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "status": "healthy",
        "features": [
            "Core API endpoints",
            "Role-based access control",
            "Multi-tenant workspace support",
            "JWT authentication"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    health_status = {
        "status": "healthy",
        "service": "dino-api",
        "version": "2.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "project_id": getattr(settings, 'GCP_PROJECT_ID', 'unknown'),
        "database_id": getattr(settings, 'DATABASE_NAME', 'unknown'),
        "api_router": "available" if api_router_available else "unavailable",
        "dependency_injection": "available" if di_available else "unavailable",
        "features": {
            "authentication": "JWT-based",
            "authorization": "Role-based (SuperAdmin/Admin/Operator)",
            "multi_tenancy": "Workspace-based isolation",
            "role_management": "Comprehensive role and permission system",
            "performance_optimization": "Caching and query optimization",
            "repository_pattern": "Centralized with caching"
        }
    }
    
    # Add DI service health if available
    if di_available:
        try:
            services_health = check_services_health()
            health_status["services"] = services_health
        except Exception as e:
            health_status["services_error"] = str(e)
    
    return health_status


@app.get("/readiness")
async def readiness_check():
    """Readiness check for Kubernetes/Cloud Run"""
    return {
        "status": "ready",
        "service": "dino-api",
        "timestamp": os.environ.get("STARTUP_TIME", "unknown")
    }


@app.get("/liveness")
async def liveness_check():
    """Liveness check for Cloud Run"""
    return {"status": "alive", "service": "dino-api"}


@app.get("/metrics")
async def performance_metrics():
    """Performance metrics endpoint"""
    try:
        from app.services.performance_service import get_performance_service
        performance_service = get_performance_service()
        metrics = performance_service.get_performance_metrics()
        
        return {
            "status": "success",
            "service": "dino-api",
            "metrics": metrics,
            "timestamp": os.environ.get("STARTUP_TIME", "unknown")
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "service": "dino-api"
        }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(500)
async def internal_server_error(request, exc):
    """Handle internal server errors"""
    logger.error("Internal server error occurred", exc_info=True, extra={
        "request_url": str(request.url),
        "request_method": request.method
    })
    return {
        "error": "Internal server error",
        "message": "An unexpected error occurred",
        "status_code": 500
    }


# =============================================================================
# STARTUP FOR LOCAL DEVELOPMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting uvicorn on port {port}...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
        access_log=True,
        workers=1  # Single worker for Cloud Run
    )