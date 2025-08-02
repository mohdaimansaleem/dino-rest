# Dino E-Menu Backend API

A simplified, production-ready FastAPI application for restaurant e-menu management with comprehensive role-based access control.

## 🚀 Features

- **Core API Endpoints**: Complete restaurant management functionality
- **Role-Based Access Control**: Three-tier hierarchy (SuperAdmin/Admin/Operator)
- **Multi-Tenant Support**: Workspace-based isolation
- **JWT Authentication**: Secure token-based authentication
- **Google Cloud Integration**: Firestore database and Cloud Storage
- **Production Ready**: Optimized for Google Cloud Run deployment

## 📋 API Endpoints

### Core Management
- **Users**: `/api/v1/users/` - User management with role assignments
- **Venues**: `/api/v1/venues/` - Restaurant/cafe management
- **Workspaces**: `/api/v1/workspaces/` - Multi-tenant workspace management
- **Menu**: `/api/v1/menu/` - Menu categories and items
- **Tables**: `/api/v1/tables/` - Table management with QR codes
- **Orders**: `/api/v1/orders/` - Order lifecycle management

### Authentication
- **Auth**: `/api/v1/auth/` - Login, registration, token management

### Role Management
- **Roles**: `/api/v1/roles/` - Role management and assignment
- **Permissions**: `/api/v1/permissions/` - Permission management and mapping

### Health & Monitoring
- **Health**: `/api/v1/health/` - Health checks and system status

## 🔐 Role Hierarchy

### SuperAdmin
- Complete system access across all workspaces and venues
- User and workspace management
- System-wide analytics and reporting

### Admin
- Full venue management within assigned workspace
- User creation and management for operators
- Business operations and analytics

### Operator
- Day-to-day operations (orders, tables)
- Limited read access to venue information
- Order status updates and table management

## 🛠️ Setup & Deployment

### Prerequisites
- Python 3.9+
- Google Cloud Project with Firestore and Cloud Storage
- Docker (for containerized deployment)

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd backend
   cp example.env.simple .env
   # Edit .env with your configuration
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**:
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --reload --port 8080
   ```

### Google Cloud Run Deployment

1. **Build and deploy**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. **Setup roles and permissions**:
   ```bash
   chmod +x scripts/complete_roles_permissions_setup.sh
   ./scripts/complete_roles_permissions_setup.sh --url YOUR_API_URL
   ```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/     # API endpoint definitions
│   ├── core/                 # Core configuration and utilities
│   ├── database/             # Database connections and repositories
│   ├── models/               # Pydantic schemas and data models
│   ├── services/             # Business logic services
│   └── utils/                # Helper utilities
├── scripts/                  # Deployment and setup scripts
├── example.env.simple        # Environment configuration template
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🔧 Configuration

### Environment Variables

Copy `example.env.simple` to `.env` and configure:

```bash
# Environment
ENVIRONMENT=development
DEBUG=true

# Security
SECRET_KEY=your-secret-key-change-in-production-at-least-32-characters-long

# Google Cloud
GCP_PROJECT_ID=your-gcp-project-id
DATABASE_NAME=(default)
GCS_BUCKET_NAME=your-gcs-bucket-name

# Application
QR_CODE_BASE_URL=http://localhost:8000
DEFAULT_CURRENCY=INR
```

## 🧪 Testing

### API Health Check
```bash
curl http://localhost:8080/health
```

### Authentication Test
```bash
# Register a user
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","first_name":"Test","last_name":"User"}'

# Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Roles and Permissions
```bash
# List roles
curl http://localhost:8080/api/v1/roles/

# List permissions
curl http://localhost:8080/api/v1/permissions/
```

## 📚 API Documentation

When running in development mode, interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Granular permission system
- **Input Validation**: Comprehensive data validation
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Environment-based Security**: Different security levels for dev/prod

## 🚀 Production Considerations

- **Environment Variables**: Ensure all production secrets are properly configured
- **Database Security**: Use Firestore security rules
- **HTTPS**: Always use HTTPS in production
- **Monitoring**: Set up proper logging and monitoring
- **Backup**: Regular database backups

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the API health endpoint: `/health`
2. Review the logs for error details
3. Ensure all environment variables are configured
4. Verify Google Cloud services are accessible

## 🔄 Version History

- **v2.0.0**: Simplified architecture with core functionality and roles/permissions
- **v1.0.0**: Initial release with full feature set