# FastAPI to Google Cloud Run - Auto-Deploy Template

A complete template for deploying FastAPI applications to Google Cloud Run with automatic GitHub deployments. Includes a fun Lemonade Stand Simulator dashboard as a demo.

## Features

- FastAPI backend with automatic API documentation
- Beautiful responsive dashboard with emoji graphics
- Docker containerization
- Automatic deployment to Cloud Run on every push to main
- Workload Identity Federation (no service account keys needed!)
- Production-ready security settings
- Auto-scaling from 0 to 10 instances
- Health check endpoint

## Project Structure

```
.
├── main.py                      # FastAPI application
├── templates/
│   └── index.html              # Dashboard template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD
├── .gcloudignore              # Files to exclude from deployment
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## One-Time Setup

### 1. Prerequisites

- Google Cloud account
- GitHub account
- `gcloud` CLI installed ([Install Guide](https://cloud.google.com/sdk/docs/install))
- Git installed

### 2. Google Cloud Setup

#### Create a New Project

```bash
# Set your project ID (choose a unique name)
export PROJECT_ID="your-project-id"
export PROJECT_NUMBER="your-project-number"  # We'll get this after creating the project

# Create project
gcloud projects create $PROJECT_ID --name="FastAPI Cloud Run"

# Set as active project
gcloud config set project $PROJECT_ID

# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Enable billing (required - you'll need to link a billing account)
# Visit: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID
```

#### Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com
```

#### Create Artifact Registry Repository

```bash
# Set region (you can change this)
export REGION="us-central1"
export SERVICE_NAME="lemonade-stand-api"

# Create repository for Docker images
gcloud artifacts repositories create $SERVICE_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for FastAPI app"
```

#### Set Up Workload Identity Federation

This allows GitHub Actions to authenticate without service account keys (more secure).

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Get the Workload Identity Pool ID
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
  --location="global" \
  --format="value(name)")

# Create Workload Identity Provider for GitHub
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_USERNAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# IMPORTANT: Replace YOUR_GITHUB_USERNAME with your actual GitHub username in the command above
```

#### Create Service Account for Deployments

```bash
# Create service account
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Allow GitHub Actions to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"

# IMPORTANT: Replace YOUR_GITHUB_USERNAME and YOUR_REPO_NAME in the command above
```

#### Get Values for GitHub Secrets

```bash
# Print the values you'll need for GitHub secrets
echo "===== GitHub Secrets Values ====="
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo ""
echo "WIF_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "WIF_SERVICE_ACCOUNT: github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo "=================================="
```

### 3. GitHub Repository Setup

#### Create Repository

```bash
# Initialize git if not already done
git init

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
.env
.venv/
venv/
ENV/
.vscode/
.idea/
.DS_Store
EOF

# Add all files
git add .

# Commit
git commit -m "Initial commit: FastAPI Cloud Run template"

# Create GitHub repository (using GitHub CLI)
gh repo create YOUR_REPO_NAME --public --source=. --remote=origin --push

# Or manually create on GitHub and push:
# git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
# git branch -M main
# git push -u origin main
```

#### Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these three secrets using the values from the previous step:

1. **GCP_PROJECT_ID**: Your Google Cloud project ID
2. **WIF_PROVIDER**: The workload identity provider path
3. **WIF_SERVICE_ACCOUNT**: The service account email

### 4. First Deployment

Push to the main branch to trigger the first deployment:

```bash
git push origin main
```

Go to the "Actions" tab in your GitHub repository to watch the deployment progress.

### 5. Get Your App URL

After deployment completes, get your Cloud Run service URL:

```bash
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(status.url)'
```

Visit this URL to see your lemonade stand simulator!

## Local Development

### Run Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

Visit http://localhost:8080

### Test with Docker Locally

```bash
# Build image
docker build -t lemonade-stand .

# Run container
docker run -p 8080:8080 lemonade-stand
```

## Using This as a Template

To reuse this template for your own projects:

1. **Copy the template structure**:
   ```bash
   cp -r /path/to/this/project /path/to/new/project
   cd /path/to/new/project
   ```

2. **Modify the application**:
   - Update `main.py` with your API logic
   - Update `templates/` with your frontend
   - Update `requirements.txt` with your dependencies

3. **Update configuration**:
   - In `.github/workflows/deploy.yml`, change `SERVICE_NAME` to your app name
   - Update `README.md` with your project details

4. **Follow the setup steps** above to create a new GCP project and GitHub repository

5. **Push and deploy**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   # ... follow GitHub setup steps
   ```

## Customizing the Deployment

### Adjust Resources

Edit `.github/workflows/deploy.yml` to change:
- `--memory`: RAM allocation (512Mi, 1Gi, 2Gi, etc.)
- `--cpu`: CPU count (1, 2, 4)
- `--min-instances`: Minimum running instances (0 for auto-shutdown)
- `--max-instances`: Maximum instances for scaling
- `--timeout`: Request timeout in seconds

### Add Environment Variables

```bash
# In the deploy.yml, add to the deploy step:
--set-env-vars="KEY1=value1,KEY2=value2"

# Or use secrets:
--set-secrets="API_KEY=api-key:latest"
```

### Use a Custom Domain

```bash
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --add-custom-domain=yourdomain.com
```

## API Documentation

Once deployed, visit:
- `/docs` - Swagger UI interactive documentation
- `/redoc` - ReDoc alternative documentation
- `/health` - Health check endpoint

## Cost Optimization

Cloud Run pricing is very affordable:
- Free tier: 2 million requests/month
- Pay only when handling requests
- Auto-scales to zero (no cost when idle)
- Estimated cost for low traffic: $0-5/month

## Troubleshooting

### Deployment fails with "permission denied"

Make sure all IAM permissions are set correctly. Re-run the service account permission commands.

### "Repository not found" error

Create the Artifact Registry repository:
```bash
gcloud artifacts repositories create $SERVICE_NAME \
  --repository-format=docker \
  --location=$REGION
```

### GitHub Actions can't authenticate

Verify your GitHub secrets match the output from the "Get Values for GitHub Secrets" step.

### App won't start

Check logs:
```bash
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50
```

## Security Notes

- This setup uses Workload Identity Federation (no service account keys stored in GitHub)
- The app runs as a non-root user in the container
- CORS is not enabled by default (add if needed for external frontends)
- The demo app allows unauthenticated access (remove `--allow-unauthenticated` for private apps)

## Next Steps

- Add a database (Cloud SQL, Firestore)
- Set up custom domains
- Add authentication (Firebase Auth, Auth0)
- Implement monitoring (Cloud Monitoring, Sentry)
- Add automated testing in CI/CD
- Set up staging environments

## License

MIT - Feel free to use this template for your projects!

## Support

For issues or questions:
- Google Cloud Run docs: https://cloud.google.com/run/docs
- FastAPI docs: https://fastapi.tiangolo.com
- GitHub Actions docs: https://docs.github.com/en/actions
