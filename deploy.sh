#!/bin/bash
. .env.production.sh

echo "🚀 Deploying Dino Backend API to Cloud Run..."

gcloud run deploy ${CLOUD_RUN_SERVICE_NAME} \
  --image ${CLOUD_RUN_IMAGE_NAME} \
  --platform managed \
  --no-allow-unauthenticated \
  --region ${GCP_REGION} \
  --project ${GCP_PROJECT_ID} \
  --memory 2G \
  --cpu 1 \
  --concurrency 20 \
  --max-instances 40 \
  --min-instances 0 \
  --timeout 900 \
  --ingress all \
  --port 8080 \
  --execution-environment gen2 \
  --cpu-boost \
  --update-env-vars "ENVIRONMENT=${ENVIRONMENT},GCP_PROJECT_ID=${GCP_PROJECT_ID},DATABASE_NAME=${DATABASE_NAME},GCS_BUCKET_NAME=${GCS_BUCKET_NAME},SECRET_KEY=${SECRET_KEY},QR_CODE_BASE_URL=${QR_CODE_BASE_URL},CORS_ORIGINS=${CORS_ORIGINS},PYTHONUNBUFFERED=1"

echo "✅ Deployment completed!"