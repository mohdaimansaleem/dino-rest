"""
Health Check API Endpoints
Simple endpoints to test API functionality
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
import time

from app.models.schemas import ApiResponse

router = APIRouter()


@router.get("/ping", response_model=ApiResponse)
async def ping():
    """Simple ping endpoint"""
    return ApiResponse(
        success=True,
        message="pong",
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy"
        }
    )


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """Basic health check"""
    start_time = time.time()
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": 0,
        "services": {
            "api": True,
            "database": False
        }
    }
    
    # Test database connection
    try:
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Simple database test - just check if we can connect
        await user_repo.exists("test-connection")
        health_data["services"]["database"] = True
        
    except Exception as e:
        health_data["services"]["database"] = False
        health_data["database_error"] = str(e)
    
    health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return ApiResponse(
        success=True,
        message="Health check completed",
        data=health_data
    )


@router.get("/test-auth", response_model=ApiResponse)
async def test_auth():
    """Test authentication system without actual login"""
    try:
        from app.database.firestore import get_user_repo, get_role_repo
        
        user_repo = get_user_repo()
        role_repo = get_role_repo()
        
        # Test basic database operations
        test_results = {
            "user_repo_available": False,
            "role_repo_available": False,
            "can_query_users": False,
            "can_query_roles": False
        }
        
        # Test user repository
        try:
            test_results["user_repo_available"] = True
            # Try a simple query
            users = await user_repo.query([("is_active", "==", True)], limit=1)
            test_results["can_query_users"] = True
            test_results["sample_users_found"] = len(users)
        except Exception as e:
            test_results["user_query_error"] = str(e)
        
        # Test role repository
        try:
            test_results["role_repo_available"] = True
            # Try a simple query
            roles = await role_repo.get_all()
            test_results["can_query_roles"] = True
            test_results["roles_found"] = len(roles)
        except Exception as e:
            test_results["role_query_error"] = str(e)
        
        return ApiResponse(
            success=True,
            message="Auth system test completed",
            data=test_results
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Auth system test failed: {str(e)}",
            data={"error": str(e)}
        )


@router.post("/test-login", response_model=ApiResponse)
async def test_login_process():
    """Test the login process without credentials"""
    try:
        from app.services.auth_service import auth_service
        
        # Test if auth service is available
        test_results = {
            "auth_service_available": True,
            "can_create_service": True,
            "service_methods": []
        }
        
        # Check available methods
        methods = [method for method in dir(auth_service) if not method.startswith('_')]
        test_results["service_methods"] = methods[:10]  # First 10 methods
        
        return ApiResponse(
            success=True,
            message="Login process test completed",
            data=test_results
        )
        
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Login process test failed: {str(e)}",
            data={"error": str(e)}
        )