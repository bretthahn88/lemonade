#!/bin/bash

# FastAPI to Cloud Run - GCP Setup Script
# This script automates the Google Cloud Platform setup

set -e

echo "=========================================="
echo "FastAPI Cloud Run Setup Script"
echo "=========================================="
echo ""

# Check if gcloud is installed and set GCLOUD variable
if command -v gcloud &> /dev/null; then
    GCLOUD="gcloud"
elif [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
    GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
    echo "Using gcloud from: $HOME/google-cloud-sdk/bin"
    echo ""
else
    echo "Error: gcloud CLI is not installed"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get user inputs
read -p "Enter your GCP Project ID (must be unique): " PROJECT_ID
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your GitHub repository name: " GITHUB_REPO
read -p "Enter your preferred region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

SERVICE_NAME="lemonade-stand-api"

echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  GitHub: $GITHUB_USERNAME/$GITHUB_REPO"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo ""
read -p "Continue with this configuration? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Setup cancelled"
    exit 0
fi

echo ""
echo "Step 1: Creating GCP project..."
$GCLOUD projects create $PROJECT_ID --name="FastAPI Cloud Run" || echo "Project may already exist"

echo ""
echo "Step 2: Setting active project..."
$GCLOUD config set project $PROJECT_ID

echo ""
echo "Step 3: Getting project number..."
PROJECT_NUMBER=$($GCLOUD projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Project number: $PROJECT_NUMBER"

echo ""
echo "Step 4: Enabling required APIs..."
$GCLOUD services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com

echo ""
echo "Step 5: Creating Artifact Registry repository..."
$GCLOUD artifacts repositories create $SERVICE_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for FastAPI app" || echo "Repository may already exist"

echo ""
echo "Step 6: Creating Workload Identity Pool..."
$GCLOUD iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool" || echo "Pool may already exist"

WORKLOAD_IDENTITY_POOL_ID=$($GCLOUD iam workload-identity-pools describe "github-pool" \
  --location="global" \
  --format="value(name)")

echo ""
echo "Step 7: Creating Workload Identity Provider..."
$GCLOUD iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner=='$GITHUB_USERNAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com" || echo "Provider may already exist"

echo ""
echo "Step 8: Creating service account..."
$GCLOUD iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account" || echo "Service account may already exist"

echo ""
echo "Step 9: Granting permissions to service account..."
$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

echo ""
echo "Step 10: Allowing GitHub Actions to use service account..."
$GCLOUD iam service-accounts add-iam-policy-binding \
  "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_USERNAME}/${GITHUB_REPO}"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Add these secrets to your GitHub repository:"
echo "https://github.com/$GITHUB_USERNAME/$GITHUB_REPO/settings/secrets/actions"
echo ""
echo "Secret 1 - GCP_PROJECT_ID:"
echo "$PROJECT_ID"
echo ""
echo "Secret 2 - WIF_PROVIDER:"
echo "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "Secret 3 - WIF_SERVICE_ACCOUNT:"
echo "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "=========================================="
echo ""
echo "IMPORTANT: You must enable billing for this project:"
echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo ""
echo "After adding the secrets and enabling billing,"
echo "push your code to trigger the deployment!"
echo ""
