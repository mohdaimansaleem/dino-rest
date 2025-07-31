#!/bin/bash
. .env.production.sh
 
gcloud builds submit . --tag ${CLOUD_RUN_IMAGE_NAME}
 
  
#gcloud builds submit . --tag us-central1-docker.pkg.dev/gcp-dino-prod/gcp-dino-prod/dino-backend-api
 