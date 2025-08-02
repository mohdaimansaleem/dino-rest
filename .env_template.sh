# Production environment variables for backend
NODE_ENV=production
ENVIRONMENT=production
PORT=8080

# GCP Configuration
PROJECT_ID=your-project-id
GCP_PROJECT_ID=your-project-id
DATABASE_NAME=dino_db

# Frontend URLs for CORS
FRONTEND_URL=https://storage.googleapis.com/your-project-id-dino-frontend
CUSTOM_DOMAIN=
CDN_URL=

# Database Configuration (Cloud SQL)
DB_HOST=your-db-ip
DB_PORT=5432
DB_NAME=dino_db
DB_USER=dino_user
DB_PASSWORD=your-secure-password

# Security
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Logging
LOG_LEVEL=INFO

# Feature Flags
DEBUG=false
ENABLE_DOCS=false

# Cloud Storage
STORAGE_BUCKET=your-project-id-dino-storage

# Firestore
FIRESTORE_DATABASE_ID=(default)