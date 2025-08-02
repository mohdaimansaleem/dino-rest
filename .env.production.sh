# Dino E-Menu Backend Production Environment
# Generated on Fri Jul 25 13:31:28 IST 2025

# =============================================================================
# ENVIRONMENT
# =============================================================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY=Y8npVmKu/qrRjgl6hISI8d66FxFPjFYZAiax9WDpXh0=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# =============================================================================
# CORS
# =============================================================================
CORS_ORIGINS=*

# =============================================================================
# GOOGLE CLOUD PLATFORM
# =============================================================================
GCP_PROJECT_ID=edl-idaas-fdev-platform-2c85
GCP_REGION=us-central1

# =============================================================================
# FIRESTORE
# =============================================================================
DATABASE_NAME=jm-dino

# =============================================================================
# CLOUD STORAGE
# =============================================================================
GCS_BUCKET_NAME=edl-idaas-fdev-platform-2c85-dino-storage
GCS_BUCKET_REGION=us-central1
GCS_IMAGES_FOLDER=images
GCS_DOCUMENTS_FOLDER=documents
GCS_QR_CODES_FOLDER=qr-codes
GCS_SIGNED_URL_EXPIRATION=3600

# =============================================================================
# FILE UPLOAD
# =============================================================================
MAX_FILE_SIZE=5242880
MAX_IMAGE_SIZE_MB=5
MAX_DOCUMENT_SIZE_MB=10
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp,image/gif

# =============================================================================
# APPLICATION
# =============================================================================
QR_CODE_BASE_URL=https://yourdomain.com/menu
ENABLE_REAL_TIME_NOTIFICATIONS=true
WEBSOCKET_PING_INTERVAL=30
DEFAULT_CURRENCY=INR
PAYMENT_GATEWAY=razorpay
RATE_LIMIT_PER_MINUTE=60

# =============================================================================
# CLOUD RUN
# =============================================================================
CLOUD_RUN_SERVICE_NAME=dino-backend-api
CLOUD_RUN_IMAGE_NAME=us-central1-docker.pkg.dev/edl-idaas-fdev-platform-2c85/job-manager-artifacts/dino-backend-api
CLOUD_RUN_REGION=us-central1
CLOUD_RUN_MEMORY=512Mi
CLOUD_RUN_CPU=1
CLOUD_RUN_MAX_INSTANCES=10
CLOUD_RUN_MIN_INSTANCES=0
