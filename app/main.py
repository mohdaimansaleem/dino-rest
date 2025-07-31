"""
Dino E-Menu Backend API
Production-ready FastAPI application for Google Cloud Run
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

# Setup basic logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import app components, but don't fail if they have issues
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
    settings = MinimalSettings()

try:
    from app.core.logging_config import setup_logging, get_logger
    setup_logging(settings.LOG_LEVEL)
    logger = get_logger(__name__)
    logger.info("✅ Logging configured successfully")
except Exception as e:
    logger.warning(f"⚠️ Advanced logging setup failed: {e}")

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
    logger.info(f"GCP_PROJECT_ID: {os.environ.get('GCP_PROJECT_ID', 'not set')}")
    
    # Skip complex initialization for faster startup
    logger.info("✅ Dino E-Menu API startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("🦕 Shutting down Dino E-Menu API")


# Create FastAPI application
app = FastAPI(
    title="Dino E-Menu API",
    description="A comprehensive e-menu solution for restaurants and cafes",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS middleware with basic configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes if available
if api_router_available:
    try:
        app.include_router(api_router, prefix="/api/v1")
        logger.info("✅ API routes included successfully")
    except Exception as e:
        logger.warning(f"⚠️ Failed to include API routes: {e}")

# Try to setup API documentation
try:
    from app.core.api_docs import setup_api_documentation
    setup_api_documentation(app)
    logger.info("✅ API documentation setup successfully")
except Exception as e:
    logger.warning(f"⚠️ API documentation setup failed: {e}")


# =============================================================================
# HEALTH CHECK ENDPOINTS (Required for Cloud Run)
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dino E-Menu API",
        "version": "1.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    # Simple health check without cloud service dependencies
    health_status = {
        "status": "healthy",
        "service": "dino-api",
        "version": "1.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "project_id": getattr(settings, 'GCP_PROJECT_ID', 'unknown'),
        "database_id": getattr(settings, 'DATABASE_NAME', 'unknown'),
        "api_router": "available" if api_router_available else "unavailable"
    }
    
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