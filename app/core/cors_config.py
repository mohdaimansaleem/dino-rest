"""
CORS configuration for production deployment
"""
import os
from typing import List
from fastapi.middleware.cors import CORSMiddleware

def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    
    # Base origins for development
    development_origins = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    # Production origins
    project_id = os.getenv("PROJECT_ID", "")
    frontend_url = os.getenv("FRONTEND_URL", "")
    custom_domain = os.getenv("CUSTOM_DOMAIN", "")
    cdn_url = os.getenv("CDN_URL", "")
    
    production_origins = [
        frontend_url,
        f"https://storage.googleapis.com/{project_id}-dino-frontend",
        f"https://{project_id}-dino-frontend.storage.googleapis.com",
        custom_domain,
        cdn_url,
        # Add common GCP storage patterns
        f"https://storage.cloud.google.com/{project_id}-dino-frontend",
    ]
    
    # Filter out empty values
    production_origins = [origin for origin in production_origins if origin]
    
    # Determine environment
    env = os.getenv("NODE_ENV", "development").lower()
    
    if env == "production":
        # In production, use production origins + localhost for testing
        return production_origins + development_origins
    else:
        # In development, use development origins
        return development_origins

def configure_cors(app):
    """Configure CORS middleware for FastAPI app"""
    
    origins = get_cors_origins()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "Cache-Control",
            "X-Requested-With",
            "X-Access-Token",
            "Origin",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
        ],
        expose_headers=[
            "Content-Range",
            "X-Content-Range",
            "X-Total-Count",
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )
    
    return app

# Environment-specific CORS settings
CORS_SETTINGS = {
    "development": {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
    "production": {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "Cache-Control",
            "X-Requested-With",
            "X-Access-Token",
            "Origin",
        ],
    }
}