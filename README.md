# 🍋 Lemonade Tycoon Deluxe

A full-featured browser business simulator game built as a **single Python file** — demonstrating a complete FastAPI web app with embedded HTML/CSS/JS, containerized with Docker and auto-deployed to **Google Cloud Run** via **GitHub Actions** using keyless Workload Identity Federation.

**Live Demo:** https://lemonade-stand-api-eu4n5wumba-uc.a.run.app

---

## What It Is

Lemonade Tycoon Deluxe is a day-by-day business management game where you run a lemonade stand. Each day you:

1. Buy supplies (lemons, sugar, cups, ice)
2. Set your price and tweak your recipe
3. Invest in upgrades to attract more customers
4. Start the day and watch a simulated customer queue play out in real time
5. Review your profit, reputation change, and any random events that occurred

The entire application — game logic, REST API, and frontend — lives in `main.py`.

---

## Features

### Gameplay
- **Weather system** — Sunny, cloudy, rainy, and hot days each affect foot traffic differently (hot days drive 1.8x customers; rainy days only 0.4x)
- **Dynamic pricing** — Set your cup price from $0.25 to $5.00; customers have individual price tolerances based on quality and weather
- **Recipe Laboratory** — Adjust lemon juice and sweetness ratios (50%–150%) to affect product quality and reputation
- **Random events** — 7 event types fire each day based on probability:

  | Event | Effect |
  |---|---|
  | 🚌 School Bus | 2× customer surge |
  | 🎪 Festival Nearby | 1.5× customers, 1.2× price tolerance |
  | ⭐ Celebrity Spotted | Instant $50 tip |
  | 🏪 Rival Stand Opens | 0.6× customers |
  | ⚡ Power Outage | All ice lost (unless fridge upgrade) |
  | 📰 Food Critic Visit | Reputation impact |
  | 🔍 Health Inspector | Reputation impact |

- **Reputation & star rating** — Conversion rate and recipe quality drive reputation (0–100). Your stand upgrade caps the maximum reputation you can reach. Stars = 1.0 + (reputation / 25)
- **Profit streak tracker** — Consecutive profitable days shown in the header

### Upgrades (3–4 tiers each)

| Track | Levels | Effect |
|---|---|---|
| Juicer | Hand Squeezer → Metal Press → Industrial Juicer | Speed + quality multiplier |
| Stand | Cardboard Box → Wooden Stand → Food Truck | Reputation cap + customer appeal |
| Fridge | Cooler Box → Mini Fridge → Deep Freezer | Ice preservation rate (0–80%) |
| Marketing | Word of Mouth → Flyers → Social Media → Billboard | +0 to +30 customer boost |

### Achievements (8 total, each with a cash reward)

| Achievement | Condition | Reward |
|---|---|---|
| First Sale! | Make 1 sale | $5 |
| Century | 100 total sales | $50 |
| Legendary | 1,000 total sales | $200 |
| Profit Master | $100 net profit in one day | $100 |
| Five Star | Reach 100 reputation | $150 |
| Tycoon | Accumulate $1,000 cash | $300 |
| Perfect Day | 100% conversion rate | $75 |
| Ice King | Never run out of ice in hot weather | $50 |

### Analytics
- **Cash Growth chart** — Area line chart of total cash across all days
- **Daily Net Profit chart** — Bar chart with green/red coloring for profit/loss days
- Summary stats: average profit, total revenue, growth rate

### Persistence
Game state is saved to `gamestate.csv` after every action (buy, upgrade, day end). The app reloads it on startup so progress survives restarts.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI 0.115, Uvicorn |
| Frontend | HTML/JS embedded in Python string, Tailwind CSS (CDN), Alpine.js (CDN), Chart.js (CDN) |
| Validation | Pydantic v2 |
| Persistence | CSV (stdlib) |
| Container | Docker (python:3.11-slim, non-root user) |
| CI/CD | GitHub Actions → Google Cloud Run |
| Auth | Workload Identity Federation (no service account key files) |

---

## Project Structure

```
.
├── main.py            # Entire application: game logic + API routes + HTML frontend
├── requirements.txt   # Python dependencies
├── Dockerfile         # Container definition
└── .github/
    └── workflows/
        └── deploy.yml # GitHub Actions CI/CD pipeline (not included in repo root)
```

> **Note:** A `.github/workflows/deploy.yml` is required for auto-deployment. See the deployment section below.

---

## Running Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open http://localhost:8000 in your browser.

### Running with Docker

```bash
docker build -t lemonade-tycoon .
docker run -p 8000:8080 lemonade-tycoon
```

Open http://localhost:8000.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the game UI |
| `GET` | `/api/state` | Returns full game state as JSON |
| `POST` | `/api/price` | Set cup price `{ "price": 1.50 }` |
| `POST` | `/api/recipe` | Update recipe `{ "lemon_ratio": 1.2, "sugar_ratio": 0.9 }` |
| `POST` | `/api/buy` | Purchase supplies `{ "item": "lemons", "quantity": 10 }` |
| `POST` | `/api/upgrade` | Buy next upgrade tier `{ "type": "juicer" }` |
| `POST` | `/api/start-day` | Simulate a full day; returns log, summary, achievements |
| `POST` | `/api/reset` | Reset all game progress |
| `GET` | `/health` | Health check for Cloud Run |

### Supply Costs

| Item | Cost |
|---|---|
| Lemons | $0.50 each |
| Sugar | $0.20 each |
| Cups | $0.10 each |
| Ice | $0.05 each |

---

## Deploying to Google Cloud Run

### Prerequisites
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A GitHub account with this repo forked/pushed

### Step-by-step Setup

```bash
# 1. Set your variables
export PROJECT_ID="your-app-$(date +%s)"
export REGION="us-central1"
export SERVICE_NAME="lemonade-stand"
export GITHUB_USERNAME="your-github-username"
export GITHUB_REPO="your-repo-name"

# 2. Create and configure GCP project
gcloud projects create $PROJECT_ID --name="Lemonade Stand"
gcloud config set project $PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
# Enable billing at: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID

# 3. Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com

# 4. Create Artifact Registry repository
gcloud artifacts repositories create $SERVICE_NAME \
  --repository-format=docker \
  --location=$REGION

# 5. Set up Workload Identity Federation (keyless GitHub → GCP auth)
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner=='$GITHUB_USERNAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 6. Create service account and grant permissions
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions SA"

for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="$ROLE" --condition=None
done

WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
  --location="global" --format="value(name)")

gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_USERNAME}/${GITHUB_REPO}"

# 7. Print the values you need for GitHub Secrets
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "WIF_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "WIF_SERVICE_ACCOUNT: github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com"
```

### GitHub Secrets

Add these three secrets to your repo under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `WIF_PROVIDER` | Full Workload Identity Provider resource name |
| `WIF_SERVICE_ACCOUNT` | `github-actions-sa@<PROJECT_ID>.iam.gserviceaccount.com` |

### Deploy

Push to `main` — GitHub Actions will build the Docker image, push it to Artifact Registry, and deploy to Cloud Run automatically.

```bash
git add .
git commit -m "Deploy Lemonade Tycoon"
git push origin main
```

---

## Cost

Google Cloud Run pricing for this type of app:
- **2 million requests/month free**
- **Scales to zero** — no cost when idle
- Typical hobby project cost: **$0–$2/month**
- New GCP accounts receive **$300 in free credits**

---

## How the Day Simulation Works

When you click **Start Day**, the backend:

1. Rolls for a random event (each has an independent trigger probability)
2. Computes `overall_quality` from recipe ratios × juicer upgrade multiplier
3. Computes `potential_customers` = `base (15–35)` × weather mod × reputation factor × stand appeal × event modifier × marketing boost
4. Simulates each customer individually:
   - Checks if supplies are available
   - Determines if they want ice
   - Rolls a random `max_price` based on quality and weather
   - Compares your price to their max — sells or walks away
   - Premium quality (>1.2) earns a 10% price bonus
5. At day end: calculates reputation change from conversion rate and quality, melts unused ice based on fridge level, updates all stats and history
6. Returns an animated log entry per customer, a day summary, and any achievements earned
