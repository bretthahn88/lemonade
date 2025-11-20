#!/bin/bash

# FastAPI to Cloud Run - Automated GCP Setup Script
# This script automates the Google Cloud Platform setup with automatic unique project ID

set -e

echo "=========================================="
echo "FastAPI Cloud Run - Automated Setup"
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

# Check if user is authenticated
if ! $GCLOUD auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "Error: Not authenticated with Google Cloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

ACTIVE_ACCOUNT=$($GCLOUD auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
echo "Authenticated as: $ACTIVE_ACCOUNT"
echo ""

# Auto-detect GitHub info from git remote (if available)
if git remote get-url origin &> /dev/null; then
    REMOTE_URL=$(git remote get-url origin)
    if [[ $REMOTE_URL =~ github\.com[:/]([^/]+)/([^/\.]+) ]]; then
        GITHUB_USERNAME="${BASH_REMATCH[1]}"
        GITHUB_REPO="${BASH_REMATCH[2]}"
        echo "Detected GitHub: $GITHUB_USERNAME/$GITHUB_REPO"
    fi
fi

# Prompt for missing info
if [ -z "$GITHUB_USERNAME" ]; then
    read -p "Enter your GitHub username: " GITHUB_USERNAME
fi

if [ -z "$GITHUB_REPO" ]; then
    read -p "Enter your GitHub repository name: " GITHUB_REPO
fi

# Generate unique project ID
TIMESTAMP=$(date +%s)
RANDOM_SUFFIX=$((RANDOM % 10000))
PROJECT_ID="${GITHUB_REPO}-${RANDOM_SUFFIX}"

# Ensure project ID meets requirements (lowercase, max 30 chars)
PROJECT_ID=$(echo "$PROJECT_ID" | tr '[:upper:]' '[:lower:]' | cut -c 1-30)

echo ""
echo "Auto-generated Project ID: $PROJECT_ID"
echo ""

REGION="us-central1"
SERVICE_NAME="lemonade-stand-api"

echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  GitHub: $GITHUB_USERNAME/$GITHUB_REPO"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Account: $ACTIVE_ACCOUNT"
echo ""

read -p "Continue with this configuration? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

echo ""
echo "Step 1: Creating GCP project..."
if $GCLOUD projects create $PROJECT_ID --name="FastAPI Cloud Run - $GITHUB_REPO" 2>&1 | tee /tmp/gcloud_create.log; then
    echo "Project created successfully!"
else
    if grep -q "already exists" /tmp/gcloud_create.log; then
        echo "Project ID taken, trying with different suffix..."
        RANDOM_SUFFIX=$((RANDOM % 100000))
        PROJECT_ID="${GITHUB_REPO}-${RANDOM_SUFFIX}"
        PROJECT_ID=$(echo "$PROJECT_ID" | tr '[:upper:]' '[:lower:]' | cut -c 1-30)
        echo "New Project ID: $PROJECT_ID"
        $GCLOUD projects create $PROJECT_ID --name="FastAPI Cloud Run - $GITHUB_REPO"
    else
        echo "Error creating project. Exiting."
        exit 1
    fi
fi

echo ""
echo "Step 2: Setting active project..."
$GCLOUD config set project $PROJECT_ID

echo ""
echo "Step 3: Getting project number..."
PROJECT_NUMBER=$($GCLOUD projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Project number: $PROJECT_NUMBER"

echo ""
echo "Step 3.5: Enabling billing for new project..."
# Get the first billing account
BILLING_ACCOUNT=$($GCLOUD billing accounts list --filter=open=true --format='value(ACCOUNT_ID)' --limit=1 2>/dev/null || echo "")

if [ -n "$BILLING_ACCOUNT" ]; then
    echo "Found billing account: $BILLING_ACCOUNT"
    echo "Linking billing account to project..."
    $GCLOUD billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT || {
        echo "Failed to automatically link billing account."
        echo "Please enable billing manually:"
        echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
        read -p "Press Enter after enabling billing..."
    }
else
    echo "No billing account found. Opening billing setup..."
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID" &
    elif command -v open &> /dev/null; then
        open "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID" &
    fi
    echo "Please enable billing at:"
    echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    read -p "Press Enter after enabling billing..."
fi

echo ""
echo "Step 4: Enabling required APIs (this may take 1-2 minutes)..."
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

# Wait a bit for the pool to be ready
sleep 3

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

# Wait a bit for service account to be ready
sleep 3

echo ""
echo "Step 9: Granting permissions to service account..."
$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin" \
  --condition=None

$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer" \
  --condition=None

$GCLOUD projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --condition=None

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
echo "PROJECT DETAILS:"
echo "  Project ID: $PROJECT_ID"
echo "  Project Number: $PROJECT_NUMBER"
echo "  Region: $REGION"
echo ""
echo "GITHUB SECRETS (Add these to your repo):"
echo "https://github.com/$GITHUB_USERNAME/$GITHUB_REPO/settings/secrets/actions"
echo ""
echo "Secret 1 - GCP_PROJECT_ID"
echo "$PROJECT_ID"
echo ""
echo "Secret 2 - WIF_PROVIDER"
echo "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "Secret 3 - WIF_SERVICE_ACCOUNT"
echo "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "=========================================="
echo ""

# Save secrets to a file for easy reference
cat > gcp-secrets.txt << EOF
GitHub Secrets Configuration
=============================

Add these three secrets to your GitHub repository:
https://github.com/$GITHUB_USERNAME/$GITHUB_REPO/settings/secrets/actions

1. Secret Name: GCP_PROJECT_ID
   Value: $PROJECT_ID

2. Secret Name: WIF_PROVIDER
   Value: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider

3. Secret Name: WIF_SERVICE_ACCOUNT
   Value: github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com

=============================

IMPORTANT NEXT STEPS:

1. Enable billing for this project (required for Cloud Run):
   https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID

   New users get \$300 in free credits!

2. Add the three secrets above to your GitHub repository

3. Push your code to GitHub:
   git add .
   git commit -m "Initial FastAPI Cloud Run setup"
   git push origin main

4. Watch your deployment in GitHub Actions:
   https://github.com/$GITHUB_USERNAME/$GITHUB_REPO/actions

5. After deployment, find your app URL:
   gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'

=============================
EOF

echo "Secrets also saved to: gcp-secrets.txt"
echo ""
echo "IMPORTANT: Enable billing at:"
echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo ""
echo "Then push to GitHub to deploy!"
echo ""
