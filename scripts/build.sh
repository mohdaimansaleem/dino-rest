#!/bin/bash
. .env.production.sh
 
gcloud builds submit . --tag us-central1-docker.pkg.dev/edl-idaas-fdev-platform-2c85/job-manager-artifacts/dino-backend-api
 
 