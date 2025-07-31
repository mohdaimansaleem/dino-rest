"""
API Documentation Utilities
Auto-generates comprehensive OpenAPI documentation with examples
"""
from typing import Dict, Any, List, Optional, Type
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
import json

from app.models.schemas import *


class APIDocumentationGenerator:
    """
    Generates comprehensive API documentation with examples and usage guides
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.examples = self._generate_examples()
    
    def _generate_examples(self) -> Dict[str, Any]:
        """Generate example data for all schemas"""
        return {
            # Workspace Examples
            "workspace_create": {
                "display_name": "My Restaurant Chain",
                "description": "A chain of premium restaurants",
                "business_type": "restaurant"
            },
            "workspace_update": {
                "display_name": "Updated Restaurant Chain",
                "description": "Updated description",
                "is_active": True
            },
            
            # User Examples
            "user_create": {
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "first_name": "John",
                "last_name": "Doe",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "role_id": "role_admin_123",
                "workspace_id": "workspace_123",
                "date_of_birth": "1990-01-15",
                "gender": "male"
            },
            "user_login": {
                "email": "john.doe@example.com",
                "password": "SecurePass123!",
                "remember_me": False
            },
            "user_update": {
                "first_name": "John",
                "last_name": "Smith",
                "phone": "+1234567891",
                "is_active": True
            },
            
            # Cafe Examples
            "cafe_create": {
                "name": "The Coffee House",
                "description": "A cozy coffee shop with artisanal brews",
                "address": "123 Main Street, Downtown, City 12345",
                "phone": "+1234567890",
                "email": "info@coffeehouse.com",
                "website": "https://coffeehouse.com",
                "cuisine_types": ["Coffee", "Pastries", "Light Meals"],
                "price_range": "mid_range",
                "operating_hours": [
                    {
                        "day": "monday",
                        "open_time": "07:00",
                        "close_time": "20:00",
                        "is_closed": False
                    },
                    {
                        "day": "sunday",
                        "open_time": "08:00",
                        "close_time": "18:00",
                        "is_closed": False
                    }
                ],
                "subscription_plan": "premium",
                "workspace_id": "workspace_123"
            },
            "cafe_update": {
                "name": "The Premium Coffee House",
                "description": "Updated description with new offerings",
                "phone": "+1234567891",
                "website": "https://premiumcoffeehouse.com",
                "is_active": True
            },
            
            # Menu Category Examples
            "menu_category_create": {
                "name": "Hot Beverages",
                "description": "Freshly brewed hot drinks",
                "cafe_id": "cafe_123"
            },
            "menu_category_update": {
                "name": "Premium Hot Beverages",
                "description": "Premium freshly brewed hot drinks",
                "is_active": True
            },
            
            # Menu Item Examples
            "menu_item_create": {
                "name": "Cappuccino",
                "description": "Rich espresso with steamed milk and foam",
                "base_price": 4.50,
                "category_id": "category_123",
                "cafe_id": "cafe_123",
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": True,
                "spice_level": "mild",
                "preparation_time_minutes": 5,
                "nutritional_info": {
                    "calories": 120
                }
            },
            "menu_item_update": {
                "name": "Premium Cappuccino",
                "description": "Rich espresso with organic steamed milk and foam",
                "base_price": 5.00,
                "is_available": True
            },
            
            # Table Examples
            "table_create": {
                "table_number": 1,
                "capacity": 4,
                "location": "Window side",
                "cafe_id": "cafe_123"
            },
            "table_update": {
                "capacity": 6,
                "location": "Center area",
                "table_status": "available",
                "is_active": True
            },
            
            # Order Examples
            "order_create": {
                "cafe_id": "cafe_123",
                "customer_id": "customer_123",
                "order_type": "dine_in",
                "table_id": "table_123",
                "special_instructions": "Extra hot, no sugar",
                "items": [
                    {
                        "menu_item_id": "item_123",
                        "quantity": 2,
                        "special_instructions": "Extra foam"
                    },
                    {
                        "menu_item_id": "item_124",
                        "quantity": 1,
                        "special_instructions": "Decaf"
                    }
                ]
            },
            "order_update": {
                "status": "preparing",
                "payment_status": "paid",
                "estimated_ready_time": "2024-01-15T10:30:00Z",
                "special_instructions": "Updated instructions"
            },
            
            # Customer Examples
            "customer_create": {
                "name": "Jane Smith",
                "phone": "+1234567890",
                "email": "jane.smith@example.com",
                "cafe_id": "cafe_123"
            },
            "customer_update": {
                "name": "Jane Smith-Johnson",
                "email": "jane.johnson@example.com",
                "is_active": True
            },
            
            # Review Examples
            "review_create": {
                "cafe_id": "cafe_123",
                "order_id": "order_123",
                "customer_id": "customer_123",
                "rating": 5,
                "comment": "Excellent coffee and service!",
                "feedback_type": "overall"
            },
            "review_update": {
                "rating": 4,
                "comment": "Good coffee, could improve service speed",
                "is_verified": True
            },
            
            # Notification Examples
            "notification_create": {
                "recipient_id": "user_123",
                "recipient_type": "user",
                "notification_type": "order_ready",
                "title": "Your order is ready!",
                "message": "Order #12345 is ready for pickup",
                "data": {
                    "order_id": "order_123",
                    "table_number": 5
                },
                "priority": "high"
            },
            
            # Transaction Examples
            "transaction_create": {
                "cafe_id": "cafe_123",
                "order_id": "order_123",
                "amount": 15.50,
                "transaction_type": "payment",
                "payment_method": "card",
                "payment_gateway": "razorpay",
                "gateway_transaction_id": "txn_123456789",
                "status": "paid"
            },
            
            # Role Examples
            "role_create": {
                "name": "operator",
                "description": "Cafe operator with limited permissions",
                "permission_ids": ["perm_123", "perm_124", "perm_125"]
            },
            "role_update": {
                "description": "Updated cafe operator role",
                "permission_ids": ["perm_123", "perm_124", "perm_125", "perm_126"]
            },
            
            # Permission Examples
            "permission_create": {
                "name": "menu_read",
                "description": "Read access to menu items",
                "resource": "menu",
                "action": "read",
                "scope": "cafe"
            },
            "permission_update": {
                "description": "Updated read access to menu items"
            }
        }
    
    def generate_custom_openapi(self) -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema with examples"""
        if self.app.openapi_schema:
            return self.app.openapi_schema
        
        openapi_schema = get_openapi(
            title="Dino E-Menu API",
            version="1.0.0",
            description=self._get_api_description(),
            routes=self.app.routes,
        )
        
        # Add examples to schemas
        self._add_examples_to_schema(openapi_schema)
        
        # Add custom tags
        openapi_schema["tags"] = self._get_api_tags()
        
        # Add servers
        openapi_schema["servers"] = [
            {
                "url": "https://your-api-domain.com/api/v1",
                "description": "Production server"
            },
            {
                "url": "http://localhost:8080/api/v1",
                "description": "Development server"
            }
        ]
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        self.app.openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_api_description(self) -> str:
        """Get comprehensive API description"""
        return """
# Dino E-Menu API

A comprehensive e-menu solution for restaurants and cafes with multi-tenant workspace architecture.

## Features

- **Multi-tenant Workspaces**: Isolated environments for different restaurant chains
- **Role-based Access Control**: Granular permissions for different user types
- **Complete Menu Management**: Categories, items, variants, and pricing
- **Order Management**: Full order lifecycle from placement to completion
- **Table Management**: QR code generation and table status tracking
- **Customer Management**: Customer profiles and order history
- **Analytics**: Sales reports and business insights
- **Real-time Notifications**: Order updates and system alerts

## Authentication

All endpoints (except public ones) require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Error Handling

The API uses standard HTTP status codes and returns consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Pagination

List endpoints support pagination with the following parameters:
- `page`: Page number (starts from 1)
- `page_size`: Items per page (1-100)

Response includes pagination metadata:

```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "total_pages": 10,
  "has_next": true,
  "has_prev": false
}
```

## Rate Limiting

API requests are rate-limited to ensure fair usage:
- 1000 requests per hour for authenticated users
- 100 requests per hour for unauthenticated requests

## Webhooks

The API supports webhooks for real-time notifications:
- Order status changes
- Payment confirmations
- System alerts

Configure webhooks in your workspace settings.
        """
    
    def _get_api_tags(self) -> List[Dict[str, str]]:
        """Get API tags with descriptions"""
        return [
            {
                "name": "authentication",
                "description": "User authentication and authorization"
            },
            {
                "name": "workspaces",
                "description": "Multi-tenant workspace management"
            },
            {
                "name": "users",
                "description": "User profile and account management"
            },
            {
                "name": "user-management",
                "description": "Admin user management operations"
            },
            {
                "name": "roles",
                "description": "Role-based access control"
            },
            {
                "name": "permissions",
                "description": "Permission management"
            },
            {
                "name": "cafes",
                "description": "Restaurant and cafe management"
            },
            {
                "name": "menu",
                "description": "Menu categories and items"
            },
            {
                "name": "tables",
                "description": "Table management and QR codes"
            },
            {
                "name": "orders",
                "description": "Order management and tracking"
            },
            {
                "name": "customers",
                "description": "Customer profiles and management"
            },
            {
                "name": "reviews",
                "description": "Customer reviews and feedback"
            },
            {
                "name": "notifications",
                "description": "Real-time notifications"
            },
            {
                "name": "transactions",
                "description": "Payment and transaction management"
            },
            {
                "name": "analytics",
                "description": "Sales analytics and reporting"
            },
            {
                "name": "uploads",
                "description": "File upload and media management"
            }
        ]
    
    def _add_examples_to_schema(self, openapi_schema: Dict[str, Any]):
        """Add examples to OpenAPI schema"""
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        
        # Add examples to request/response schemas
        schemas = openapi_schema["components"]["schemas"]
        
        # Map schema names to examples
        schema_examples = {
            "WorkspaceCreate": self.examples["workspace_create"],
            "WorkspaceUpdate": self.examples["workspace_update"],
            "UserCreate": self.examples["user_create"],
            "UserLogin": self.examples["user_login"],
            "UserUpdate": self.examples["user_update"],
            "CafeCreate": self.examples["cafe_create"],
            "CafeUpdate": self.examples["cafe_update"],
            "MenuCategoryCreate": self.examples["menu_category_create"],
            "MenuCategoryUpdate": self.examples["menu_category_update"],
            "MenuItemCreate": self.examples["menu_item_create"],
            "MenuItemUpdate": self.examples["menu_item_update"],
            "TableCreate": self.examples["table_create"],
            "TableUpdate": self.examples["table_update"],
            "OrderCreate": self.examples["order_create"],
            "OrderUpdate": self.examples["order_update"],
            "CustomerCreate": self.examples["customer_create"],
            "CustomerUpdate": self.examples["customer_update"],
            "ReviewCreate": self.examples["review_create"],
            "ReviewUpdate": self.examples["review_update"],
            "NotificationCreate": self.examples["notification_create"],
            "TransactionCreate": self.examples["transaction_create"],
            "RoleCreate": self.examples["role_create"],
            "RoleUpdate": self.examples["role_update"],
            "PermissionCreate": self.examples["permission_create"],
            "PermissionUpdate": self.examples["permission_update"]
        }
        
        # Add examples to schemas
        for schema_name, example in schema_examples.items():
            if schema_name in schemas:
                schemas[schema_name]["example"] = example
    
    def generate_postman_collection(self) -> Dict[str, Any]:
        """Generate Postman collection for API testing"""
        collection = {
            "info": {
                "name": "Dino E-Menu API",
                "description": "Complete API collection for Dino E-Menu system",
                "version": "1.0.0",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{jwt_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost:8080/api/v1",
                    "type": "string"
                },
                {
                    "key": "jwt_token",
                    "value": "",
                    "type": "string"
                }
            ],
            "item": self._generate_postman_folders()
        }
        
        return collection
    
    def _generate_postman_folders(self) -> List[Dict[str, Any]]:
        """Generate Postman folders for each endpoint group"""
        folders = []
        
        # Authentication folder
        folders.append({
            "name": "Authentication",
            "item": [
                {
                    "name": "Register User",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps(self.examples["user_create"], indent=2)
                        },
                        "url": {
                            "raw": "{{base_url}}/users/register",
                            "host": ["{{base_url}}"],
                            "path": ["users", "register"]
                        }
                    }
                },
                {
                    "name": "Login User",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps(self.examples["user_login"], indent=2)
                        },
                        "url": {
                            "raw": "{{base_url}}/users/login",
                            "host": ["{{base_url}}"],
                            "path": ["users", "login"]
                        }
                    }
                }
            ]
        })
        
        # Add more folders for other endpoints...
        # This is a simplified version - full implementation would include all endpoints
        
        return folders
    
    def generate_sdk_documentation(self, language: str = "python") -> str:
        """Generate SDK documentation for specific language"""
        if language == "python":
            return self._generate_python_sdk_docs()
        elif language == "javascript":
            return self._generate_javascript_sdk_docs()
        else:
            return "SDK documentation not available for this language"
    
    def _generate_python_sdk_docs(self) -> str:
        """Generate Python SDK documentation"""
        return """
# Python SDK Usage

## Installation

```bash
pip install requests pydantic
```

## Basic Usage

```python
import requests
from typing import Dict, Any

class DinoAPIClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/users/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        
        # Set token for future requests
        self.session.headers.update({
            "Authorization": f"Bearer {data['access_token']}"
        })
        
        return data
    
    def create_cafe(self, cafe_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/cafes/",
            json=cafe_data
        )
        response.raise_for_status()
        return response.json()
    
    def get_cafes(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/cafes/",
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()

# Example usage
client = DinoAPIClient("http://localhost:8080/api/v1")

# Login
auth_data = client.login("user@example.com", "password")
print(f"Logged in as: {auth_data['user']['email']}")

# Create cafe
cafe_data = {
    "name": "My Cafe",
    "description": "A great cafe",
    "address": "123 Main St",
    "phone": "+1234567890",
    "email": "info@mycafe.com",
    "workspace_id": "workspace_123"
}
cafe = client.create_cafe(cafe_data)
print(f"Created cafe: {cafe['data']['name']}")

# Get cafes
cafes = client.get_cafes()
print(f"Found {cafes['total']} cafes")
```
        """
    
    def _generate_javascript_sdk_docs(self) -> str:
        """Generate JavaScript SDK documentation"""
        return """
# JavaScript SDK Usage

## Installation

```bash
npm install axios
```

## Basic Usage

```javascript
const axios = require('axios');

class DinoAPIClient {
    constructor(baseURL, apiKey = null) {
        this.client = axios.create({
            baseURL: baseURL,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (apiKey) {
            this.setAuthToken(apiKey);
        }
    }
    
    setAuthToken(token) {
        this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    
    async login(email, password) {
        try {
            const response = await this.client.post('/users/login', {
                email,
                password
            });
            
            // Set token for future requests
            this.setAuthToken(response.data.access_token);
            
            return response.data;
        } catch (error) {
            throw new Error(`Login failed: ${error.response?.data?.error || error.message}`);
        }
    }
    
    async createCafe(cafeData) {
        try {
            const response = await this.client.post('/cafes/', cafeData);
            return response.data;
        } catch (error) {
            throw new Error(`Create cafe failed: ${error.response?.data?.error || error.message}`);
        }
    }
    
    async getCafes(page = 1, pageSize = 10) {
        try {
            const response = await this.client.get('/cafes/', {
                params: { page, page_size: pageSize }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Get cafes failed: ${error.response?.data?.error || error.message}`);
        }
    }
}

// Example usage
const client = new DinoAPIClient('http://localhost:8080/api/v1');

async function example() {
    try {
        // Login
        const authData = await client.login('user@example.com', 'password');
        console.log(`Logged in as: ${authData.user.email}`);
        
        // Create cafe
        const cafeData = {
            name: 'My Cafe',
            description: 'A great cafe',
            address: '123 Main St',
            phone: '+1234567890',
            email: 'info@mycafe.com',
            workspace_id: 'workspace_123'
        };
        const cafe = await client.createCafe(cafeData);
        console.log(`Created cafe: ${cafe.data.name}`);
        
        // Get cafes
        const cafes = await client.getCafes();
        console.log(`Found ${cafes.total} cafes`);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

example();
```
        """


def setup_api_documentation(app: FastAPI) -> APIDocumentationGenerator:
    """Setup API documentation for the FastAPI app"""
    doc_generator = APIDocumentationGenerator(app)
    
    # Override the default OpenAPI schema
    app.openapi = doc_generator.generate_custom_openapi
    
    return doc_generator