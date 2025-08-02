# Dino E-Menu API Collection

A comprehensive Postman collection for the Dino E-Menu Backend API with all endpoints, authentication, and testing capabilities.

## 📁 Collection Structure

The API collection is organized into logical sections:

1. **🔐 Authentication** - User registration, login, token management
2. **👥 User Management** - User CRUD operations and role assignments
3. **🏢 Workspace Management** - Multi-tenant workspace operations
4. **🏪 Venue Management** - Restaurant/cafe management
5. **🍽️ Menu Management** - Menu categories and items
6. **🪑 Table Management** - Table operations with QR codes
7. **🛒 Order Management** - Order lifecycle and tracking
8. **👑 Role Management** - Role creation and permission assignment
9. **🔐 Permission Management** - Granular permission system
10. **🏥 Health & Monitoring** - Health checks and system status

## 🚀 Quick Start

### 1. Generate the Collection

```bash
cd api-collection
./merge-collection.sh
```

This will create `dino-emenu-api-collection.json` from all the chunk files.

### 2. Import into Postman

1. Open Postman
2. Click **Import**
3. Select `dino-emenu-api-collection.json`
4. The collection will be imported with all folders and requests

### 3. Set Up Environment

Create a new environment in Postman with these variables:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `base_url` | API base URL | `http://localhost:8080` |
| `access_token` | JWT access token | (auto-set after login) |
| `refresh_token` | JWT refresh token | (auto-set after login) |
| `user_id` | Current user ID | (auto-set after login) |
| `workspace_id` | Current workspace ID | (set manually) |
| `venue_id` | Current venue ID | (set manually) |

### 4. Test the API

1. **Start with Health Check**: Run "Root Health Check" (no auth required)
2. **Register/Login**: Use authentication endpoints to get tokens
3. **Explore**: Test other endpoints based on your role

## 🔧 Collection Features

### Auto-Token Management
- Tokens are automatically extracted and stored after login
- Bearer token authentication is pre-configured
- Refresh token handling included

### Comprehensive Testing
- Each request includes test scripts
- Response validation and status code checks
- Automatic variable extraction for chaining requests

### Environment Variables
- Dynamic base URL configuration
- Auto-extraction of IDs for request chaining
- Support for different environments (dev, staging, prod)

### Role-Based Testing
- Endpoints organized by permission requirements
- Examples for different user roles
- Permission testing scenarios

## 📋 Endpoint Categories

### Core Management (Always Available)
- User management
- Venue operations
- Workspace management
- Menu and table management
- Order processing

### Role & Permission System
- Role creation and management
- Permission assignment
- User role assignments
- Permission validation

### Public Endpoints (No Auth Required)
- Health checks
- Public order creation (QR scan)
- API statistics
- System information

## 🔐 Authentication Flow

1. **Register User** → Get user account
2. **Login** → Get access_token and refresh_token
3. **Use Protected Endpoints** → Include Bearer token
4. **Refresh Token** → When access_token expires

## 🎯 Testing Scenarios

### Basic Flow
1. Health check
2. User registration
3. Login
4. Create workspace/venue
5. Manage menu items
6. Create orders

### Role Management Flow
1. Login as admin
2. Create roles
3. Create permissions
4. Assign permissions to roles
5. Assign roles to users
6. Test permission validation

### Public Ordering Flow
1. Get venue menu (public)
2. Create order via QR scan (no auth)
3. Track order status
4. Payment processing

## 🛠️ Customization

### Adding New Endpoints
1. Create a new chunk file (e.g., `12-new-feature.json`)
2. Follow the existing format
3. Add to `COLLECTION_FILES` array in `merge-collection.sh`
4. Re-run the merge script

### Environment Configuration
- **Development**: `http://localhost:8080`
- **Staging**: `https://staging-api.yourdomain.com`
- **Production**: `https://api.yourdomain.com`

## 📊 Collection Statistics

- **Total Endpoints**: 100+ API endpoints
- **Folders**: 10 organized sections
- **Authentication**: JWT-based with auto-token management
- **Testing**: Comprehensive test scripts for all endpoints
- **Documentation**: Detailed descriptions and examples

## 🔍 Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Ensure you're logged in and have a valid access_token
   - Check if token has expired and refresh if needed

2. **403 Forbidden**
   - Verify your user role has required permissions
   - Check role-permission assignments

3. **404 Not Found**
   - Verify the endpoint URL is correct
   - Ensure required IDs are set in environment variables

4. **500 Internal Server Error**
   - Check API server logs
   - Verify database connectivity
   - Run health check endpoints

### Debug Tips

- Use the health check endpoints to verify API status
- Check environment variables are properly set
- Review test results in Postman console
- Enable request/response logging for debugging

## 📝 Notes

- Collection includes both authenticated and public endpoints
- Automatic token management reduces manual work
- Comprehensive test coverage for all scenarios
- Organized structure for easy navigation
- Production-ready with proper error handling

## 🤝 Contributing

To add new endpoints or improve the collection:

1. Create new chunk files following the existing pattern
2. Update the merge script if needed
3. Test the merged collection thoroughly
4. Update this documentation

## 📄 License

This API collection is part of the Dino E-Menu project and follows the same license terms.