"""
═══════════════════════════════════════════════════════════════════════════════
    🍋 LEMONADE TYCOON - FastAPI → Google Cloud Run Auto-Deploy Demo
═══════════════════════════════════════════════════════════════════════════════

This single file demonstrates:
✓ FastAPI web application with embedded HTML/CSS/JS
✓ Automatic deployment to Google Cloud Run via GitHub Actions
✓ Workload Identity Federation (no service account keys!)
✓ Docker containerization
✓ Auto-scaling serverless infrastructure

Live Demo: https://lemonade-stand-api-eu4n5wumba-uc.a.run.app
GitHub: https://github.com/williamedwardhahn/lemonade

═══════════════════════════════════════════════════════════════════════════════
    📋 QUICK START - Deploy Your Own
═══════════════════════════════════════════════════════════════════════════════

1️⃣  INSTALL GCLOUD CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud auth login

2️⃣  SET VARIABLES (customize these!)
   export PROJECT_ID="your-app-$(date +%s)"
   export REGION="us-central1"
   export SERVICE_NAME="your-service-name"
   export GITHUB_USERNAME="your-github-username"
   export GITHUB_REPO="your-repo-name"

3️⃣  CREATE GCP PROJECT
   gcloud projects create $PROJECT_ID --name="My FastAPI App"
   gcloud config set project $PROJECT_ID
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

   # Enable billing at:
   # https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID

4️⃣  ENABLE APIS
   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     cloudbuild.googleapis.com \
     iamcredentials.googleapis.com

5️⃣  CREATE ARTIFACT REGISTRY
   gcloud artifacts repositories create $SERVICE_NAME \
     --repository-format=docker \
     --location=$REGION \
     --description="Docker repository"

6️⃣  SETUP WORKLOAD IDENTITY (Secure GitHub → GCP auth)
   # Create identity pool
   gcloud iam workload-identity-pools create "github-pool" \
     --location="global" \
     --display-name="GitHub Actions Pool"

   # Create OIDC provider
   gcloud iam workload-identity-pools providers create-oidc "github-provider" \
     --location="global" \
     --workload-identity-pool="github-pool" \
     --display-name="GitHub provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
     --attribute-condition="assertion.repository_owner=='$GITHUB_USERNAME'" \
     --issuer-uri="https://token.actions.githubusercontent.com"

7️⃣  CREATE SERVICE ACCOUNT
   gcloud iam service-accounts create github-actions-sa \
     --display-name="GitHub Actions SA"

   # Grant permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin" --condition=None

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer" --condition=None

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser" --condition=None

   # Allow GitHub to impersonate service account
   WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
     --location="global" --format="value(name)")

   gcloud iam service-accounts add-iam-policy-binding \
     "github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_USERNAME}/${GITHUB_REPO}"

8️⃣  ADD GITHUB SECRETS (go to Settings → Secrets → Actions)
   # Print values to add:
   echo "GCP_PROJECT_ID: $PROJECT_ID"
   echo "WIF_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
   echo "WIF_SERVICE_ACCOUNT: github-actions-sa@$PROJECT_ID.iam.gserviceaccount.com"

9️⃣  PUSH TO GITHUB
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/$GITHUB_USERNAME/$GITHUB_REPO.git
   git branch -M main
   git push -u origin main

🎉  DONE! GitHub Actions will auto-deploy on every push to main.

═══════════════════════════════════════════════════════════════════════════════
    📁 REQUIRED FILES
═══════════════════════════════════════════════════════════════════════════════

This repo needs:
├── main.py (this file)
├── requirements.txt
├── Dockerfile
├── .github/workflows/deploy.yml
├── .gitignore
└── .gcloudignore

═══════════════════════════════════════════════════════════════════════════════
    🧪 LOCAL TESTING
═══════════════════════════════════════════════════════════════════════════════

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# Visit http://localhost:8000

═══════════════════════════════════════════════════════════════════════════════
    💰 COST
═══════════════════════════════════════════════════════════════════════════════

Cloud Run pricing:
- 2M requests/month FREE
- Auto-scales to 0 (no cost when idle)
- Typical cost for hobby projects: $0-2/month
- New GCP users get $300 in free credits

═══════════════════════════════════════════════════════════════════════════════
    🎮 ABOUT THIS DEMO
═══════════════════════════════════════════════════════════════════════════════

Lemonade Tycoon Deluxe v2.0
- Full business simulator game
- 8 achievements with cash rewards
- Random events (celebrities, festivals, rivals)
- Recipe experimentation system
- Marketing upgrades
- Analytics charts
- CSV state persistence
- All in one Python file!

═══════════════════════════════════════════════════════════════════════════════
"""

import random
import os
import csv
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Lemonade Tycoon Deluxe", version="2.0.0")

# ==========================================
#            GAME CONFIGURATION
# ==========================================

COSTS = {
    "lemons": 0.50,
    "sugar": 0.20,
    "cups": 0.10,
    "ice": 0.05
}

UPGRADES = {
    "juicer": [
        {"name": "Hand Squeezer", "cost": 0, "speed": 1.0, "quality": 1.0},
        {"name": "Metal Press", "cost": 50, "speed": 1.5, "quality": 1.2},
        {"name": "Industrial Juicer", "cost": 200, "speed": 3.0, "quality": 1.5}
    ],
    "stand": [
        {"name": "Cardboard Box", "cost": 0, "rep_cap": 30, "appeal": 1.0},
        {"name": "Wooden Stand", "cost": 100, "rep_cap": 60, "appeal": 1.3},
        {"name": "Food Truck", "cost": 500, "rep_cap": 100, "appeal": 2.0}
    ],
    "fridge": [
        {"name": "Cooler Box", "cost": 0, "ice_save": 0.0},
        {"name": "Mini Fridge", "cost": 150, "ice_save": 0.4},
        {"name": "Deep Freezer", "cost": 400, "ice_save": 0.8}
    ],
    "marketing": [
        {"name": "Word of Mouth", "cost": 0, "boost": 0},
        {"name": "Flyers", "cost": 75, "boost": 5},
        {"name": "Social Media", "cost": 300, "boost": 15},
        {"name": "Billboard", "cost": 800, "boost": 30}
    ]
}

EVENTS = [
    {"name": "Food Critic Visit", "emoji": "📰", "type": "critic", "chance": 0.15},
    {"name": "Celebrity Spotted", "emoji": "⭐", "type": "celebrity", "chance": 0.08},
    {"name": "Health Inspector", "emoji": "🔍", "type": "inspector", "chance": 0.12},
    {"name": "Rival Stand Opens", "emoji": "🏪", "type": "rival", "chance": 0.10},
    {"name": "School Bus Arrives", "emoji": "🚌", "type": "rush", "chance": 0.20},
    {"name": "Power Outage", "emoji": "⚡", "type": "outage", "chance": 0.08},
    {"name": "Festival Nearby", "emoji": "🎪", "type": "festival", "chance": 0.10}
]

ACHIEVEMENTS = {
    "first_sale": {"name": "First Sale!", "desc": "Sell your first lemonade", "reward": 5},
    "hundred_sales": {"name": "Century", "desc": "Make 100 sales", "reward": 50},
    "thousand_sales": {"name": "Legendary", "desc": "Make 1000 sales", "reward": 200},
    "profit_master": {"name": "Profit Master", "desc": "Earn $100 in one day", "reward": 100},
    "five_star": {"name": "Five Star", "desc": "Reach 100 reputation", "reward": 150},
    "tycoon": {"name": "Tycoon", "desc": "Accumulate $1000 cash", "reward": 300},
    "perfect_day": {"name": "Perfect Day", "desc": "100% conversion rate", "reward": 75},
    "ice_king": {"name": "Ice King", "desc": "Never run out of ice in hot weather", "reward": 50}
}

CSV_FILE = "gamestate.csv"

# ==========================================
#                GAME STATE
# ==========================================

class GameState:
    def __init__(self):
        self.cash = 25.0
        self.day = 1
        self.reputation = 10
        self.stars = 1.0  # Star rating (1-5)
        self.inventory = {
            "lemons": 5,
            "sugar": 5,
            "cups": 10,
            "ice": 0
        }
        self.price = 1.00
        self.recipe = {"lemon_ratio": 1.0, "sugar_ratio": 1.0}  # Quality modifiers
        self.upgrades = {
            "juicer": 0,
            "stand": 0,
            "fridge": 0,
            "marketing": 0
        }
        self.stats = {
            "total_sales": 0,
            "total_revenue": 0.0,
            "best_day": 0,
            "perfect_days": 0
        }
        self.achievements = []
        self.history = []
        self.weather = "sunny"
        self.next_weather = "cloudy"
        self.active_event = None
        self.streak = 0  # Days with profit

        self.load_from_csv()

    def reset(self):
        self.cash = 25.0
        self.day = 1
        self.reputation = 10
        self.stars = 1.0
        self.inventory = {"lemons": 5, "sugar": 5, "cups": 10, "ice": 0}
        self.price = 1.00
        self.recipe = {"lemon_ratio": 1.0, "sugar_ratio": 1.0}
        self.upgrades = {"juicer": 0, "stand": 0, "fridge": 0, "marketing": 0}
        self.stats = {"total_sales": 0, "total_revenue": 0.0, "best_day": 0, "perfect_days": 0}
        self.achievements = []
        self.history = []
        self.weather = "sunny"
        self.next_weather = "cloudy"
        self.active_event = None
        self.streak = 0
        self.save_to_csv()

    def save_to_csv(self):
        data = {
            "cash": self.cash,
            "day": self.day,
            "reputation": self.reputation,
            "stars": self.stars,
            "inv_lemons": self.inventory["lemons"],
            "inv_sugar": self.inventory["sugar"],
            "inv_cups": self.inventory["cups"],
            "inv_ice": self.inventory["ice"],
            "price": self.price,
            "recipe_lemon": self.recipe["lemon_ratio"],
            "recipe_sugar": self.recipe["sugar_ratio"],
            "upg_juicer": self.upgrades["juicer"],
            "upg_stand": self.upgrades["stand"],
            "upg_fridge": self.upgrades["fridge"],
            "upg_marketing": self.upgrades["marketing"],
            "stat_sales": self.stats["total_sales"],
            "stat_rev": self.stats["total_revenue"],
            "stat_best": self.stats["best_day"],
            "stat_perfect": self.stats["perfect_days"],
            "weather": self.weather,
            "next_weather": self.next_weather,
            "streak": self.streak,
            "achievements": json.dumps(self.achievements),
            "history": json.dumps(self.history)
        }

        try:
            with open(CSV_FILE, "w", newline="", encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                writer.writeheader()
                writer.writerow(data)
        except Exception as e:
            print(f"Error saving CSV: {e}")

    def load_from_csv(self):
        if not os.path.exists(CSV_FILE):
            return

        try:
            with open(CSV_FILE, "r", encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.cash = float(row.get("cash", 25.0))
                    self.day = int(row.get("day", 1))
                    self.reputation = float(row.get("reputation", 10))
                    self.stars = float(row.get("stars", 1.0))
                    self.inventory["lemons"] = int(row.get("inv_lemons", 5))
                    self.inventory["sugar"] = int(row.get("inv_sugar", 5))
                    self.inventory["cups"] = int(row.get("inv_cups", 10))
                    self.inventory["ice"] = int(row.get("inv_ice", 0))
                    self.price = float(row.get("price", 1.0))
                    self.recipe["lemon_ratio"] = float(row.get("recipe_lemon", 1.0))
                    self.recipe["sugar_ratio"] = float(row.get("recipe_sugar", 1.0))
                    self.upgrades["juicer"] = int(row.get("upg_juicer", 0))
                    self.upgrades["stand"] = int(row.get("upg_stand", 0))
                    self.upgrades["fridge"] = int(row.get("upg_fridge", 0))
                    self.upgrades["marketing"] = int(row.get("upg_marketing", 0))
                    self.stats["total_sales"] = int(row.get("stat_sales", 0))
                    self.stats["total_revenue"] = float(row.get("stat_rev", 0.0))
                    self.stats["best_day"] = int(row.get("stat_best", 0))
                    self.stats["perfect_days"] = int(row.get("stat_perfect", 0))
                    self.weather = row.get("weather", "sunny")
                    self.next_weather = row.get("next_weather", "cloudy")
                    self.streak = int(row.get("streak", 0))

                    ach_str = row.get("achievements")
                    if ach_str:
                        try:
                            self.achievements = json.loads(ach_str)
                        except:
                            self.achievements = []

                    hist_str = row.get("history")
                    if hist_str:
                        try:
                            self.history = json.loads(hist_str)
                        except:
                            self.history = []
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def check_achievement(self, achievement_id):
        """Check and award achievement if not already earned"""
        if achievement_id in self.achievements:
            return None

        earned = False
        ach = ACHIEVEMENTS.get(achievement_id)

        if achievement_id == "first_sale" and self.stats["total_sales"] >= 1:
            earned = True
        elif achievement_id == "hundred_sales" and self.stats["total_sales"] >= 100:
            earned = True
        elif achievement_id == "thousand_sales" and self.stats["total_sales"] >= 1000:
            earned = True
        elif achievement_id == "tycoon" and self.cash >= 1000:
            earned = True
        elif achievement_id == "five_star" and self.reputation >= 100:
            earned = True

        if earned:
            self.achievements.append(achievement_id)
            self.cash += ach["reward"]
            return ach
        return None

game = GameState()

# ==========================================
#             PYDANTIC MODELS
# ==========================================

class PurchaseRequest(BaseModel):
    item: str
    quantity: int

class PriceUpdate(BaseModel):
    price: float

class RecipeUpdate(BaseModel):
    lemon_ratio: float
    sugar_ratio: float

class UpgradeRequest(BaseModel):
    type: str

# ==========================================
#             FRONTEND (HTML/JS)
# ==========================================

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍋 Lemonade Tycoon Deluxe</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        [x-cloak] { display: none !important; }
        @keyframes bounce-in {
            0% { transform: scale(0); opacity: 0; }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        @keyframes slide-up {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .bounce-in { animation: bounce-in 0.5s ease-out; }
        .slide-up { animation: slide-up 0.3s ease-out; }
        .stars-display { background: linear-gradient(45deg, #fbbf24, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body class="bg-gradient-to-br from-yellow-50 via-orange-50 to-pink-50 text-slate-800 font-sans min-h-screen" x-data="gameApp()" x-init="init()">

    <!-- Achievement Toast -->
    <div x-show="achievementToast" x-transition
         class="fixed top-20 right-4 bg-gradient-to-r from-yellow-400 to-orange-400 text-white px-6 py-4 rounded-xl shadow-2xl z-[200] max-w-sm bounce-in">
        <div class="flex items-center gap-3">
            <span class="text-3xl">🏆</span>
            <div>
                <div class="font-bold text-lg" x-text="achievementData?.name"></div>
                <div class="text-sm opacity-90" x-text="achievementData?.desc"></div>
                <div class="text-xs mt-1 font-bold">+$<span x-text="achievementData?.reward"></span> Bonus!</div>
            </div>
        </div>
    </div>

    <!-- Event Alert -->
    <div x-show="eventAlert" x-transition
         class="fixed top-4 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white px-8 py-4 rounded-2xl shadow-2xl z-[200] max-w-lg text-center bounce-in">
        <div class="text-4xl mb-2" x-text="eventData?.emoji"></div>
        <div class="font-bold text-xl" x-text="eventData?.name"></div>
        <div class="text-sm opacity-90 mt-1" x-text="eventData?.effect"></div>
    </div>

    <!-- TOP BAR -->
    <div class="bg-white/90 backdrop-blur shadow-lg sticky top-0 z-50 border-b-4 border-yellow-400">
        <div class="max-w-7xl mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <span class="text-4xl">🍋</span>
                    <div>
                        <h1 class="font-black text-2xl bg-gradient-to-r from-yellow-500 to-orange-500 bg-clip-text text-transparent">Lemonade Tycoon</h1>
                        <div class="text-xs text-slate-500 flex items-center gap-2">
                            <span>Day <span class="font-bold" x-text="state.day"></span></span>
                            <span class="text-yellow-500">•</span>
                            <span class="stars-display font-bold" x-text="'★'.repeat(Math.floor(state.stars)) + ' ' + state.stars.toFixed(1)"></span>
                        </div>
                    </div>
                </div>
                <div class="flex gap-6 items-center">
                    <div class="text-center">
                        <div class="text-[10px] uppercase font-bold text-slate-400">Streak</div>
                        <div class="font-bold text-orange-600 flex items-center gap-1">
                            <span x-text="state.streak"></span>
                            <span class="text-lg">🔥</span>
                        </div>
                    </div>
                    <div class="text-center">
                        <div class="text-[10px] uppercase font-bold text-purple-700">Reputation</div>
                        <div class="font-bold text-purple-600" x-text="state.reputation + '%'"></div>
                    </div>
                    <div class="text-center bg-gradient-to-br from-green-400 to-emerald-500 text-white px-4 py-2 rounded-xl shadow-lg">
                        <div class="text-[10px] uppercase font-bold">Cash</div>
                        <div class="font-black text-xl" x-text="'$' + state.cash.toFixed(2)"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="max-w-7xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-3 gap-6" x-cloak>

        <!-- LEFT COLUMN -->
        <div class="lg:col-span-2 space-y-6">

            <!-- Achievements -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-xl border-2 border-yellow-300 p-6" x-show="state.achievements && state.achievements.length > 0">
                <h2 class="font-bold text-lg mb-4 flex items-center gap-2">
                    <span class="text-2xl">🏆</span>
                    <span>Achievements (<span x-text="state.achievements.length"></span>/8)</span>
                </h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <template x-for="achId in state.achievements" :key="achId">
                        <div class="bg-gradient-to-br from-yellow-100 to-orange-100 p-3 rounded-xl border-2 border-yellow-300 text-center">
                            <div class="text-2xl mb-1">🏆</div>
                            <div class="text-xs font-bold" x-text="achievementNames[achId]"></div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Charts -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-xl border border-slate-200 p-6" x-show="state.day > 1 && state.history && state.history.length > 0" x-transition>
                <h2 class="font-bold text-lg mb-4 flex items-center gap-2">
                    📊 Performance Analytics
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4">
                        <div class="h-56 relative">
                            <canvas id="cashChart"></canvas>
                        </div>
                    </div>
                    <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4">
                        <div class="h-56 relative">
                            <canvas id="salesChart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="mt-4 grid grid-cols-3 gap-3 text-center text-sm">
                    <div class="bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg p-3">
                        <div class="text-xs text-green-700 font-bold mb-1">Avg Profit</div>
                        <div class="text-lg font-black text-green-600" x-text="'$' + (state.history.reduce((sum, h) => sum + h.net_profit, 0) / state.history.length).toFixed(2)"></div>
                    </div>
                    <div class="bg-gradient-to-br from-blue-100 to-indigo-100 rounded-lg p-3">
                        <div class="text-xs text-blue-700 font-bold mb-1">Total Revenue</div>
                        <div class="text-lg font-black text-blue-600" x-text="'$' + state.stats.total_revenue.toFixed(2)"></div>
                    </div>
                    <div class="bg-gradient-to-br from-purple-100 to-pink-100 rounded-lg p-3">
                        <div class="text-xs text-purple-700 font-bold mb-1">Growth Rate</div>
                        <div class="text-lg font-black text-purple-600" x-text="state.history.length > 1 ? '+' + (((state.history[state.history.length-1].cash / state.history[0].cash - 1) * 100).toFixed(0)) + '%' : '0%'"></div>
                    </div>
                </div>
            </div>

            <!-- Weather & Event -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-2xl p-6 shadow-xl relative overflow-hidden">
                    <div class="relative z-10">
                        <div class="text-xs font-bold opacity-75 uppercase">Today</div>
                        <div class="text-3xl font-black capitalize flex items-center gap-2 my-2">
                            <span x-text="weatherIcons[state.weather]"></span>
                            <span x-text="state.weather"></span>
                        </div>
                        <div class="text-xs opacity-90 font-medium">
                            Tomorrow: <span class="capitalize font-bold" x-text="state.next_weather"></span>
                        </div>
                    </div>
                    <div class="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-10 -mt-10"></div>
                </div>

                <div x-show="state.active_event"
                     class="bg-gradient-to-br from-purple-500 to-pink-600 text-white rounded-2xl p-6 shadow-xl">
                    <div class="text-xs font-bold opacity-75 uppercase">Special Event!</div>
                    <div class="text-4xl my-2" x-text="state.active_event?.emoji"></div>
                    <div class="font-bold text-lg" x-text="state.active_event?.name"></div>
                </div>
            </div>

            <!-- Recipe Lab -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-xl border border-slate-200 p-6">
                <h2 class="font-bold text-lg mb-4 flex items-center gap-2">
                    <span class="text-2xl">🔬</span>
                    Recipe Laboratory
                </h2>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-sm font-bold text-slate-600 mb-2 block">🍋 Lemon Strength</label>
                        <input type="range" min="0.5" max="1.5" step="0.1"
                               x-model.number="state.recipe.lemon_ratio"
                               @change="updateRecipe()"
                               class="w-full accent-yellow-500">
                        <div class="text-xs text-center mt-1" x-text="(state.recipe.lemon_ratio * 100) + '%'"></div>
                    </div>
                    <div>
                        <label class="text-sm font-bold text-slate-600 mb-2 block">🍬 Sweetness</label>
                        <input type="range" min="0.5" max="1.5" step="0.1"
                               x-model.number="state.recipe.sugar_ratio"
                               @change="updateRecipe()"
                               class="w-full accent-pink-500">
                        <div class="text-xs text-center mt-1" x-text="(state.recipe.sugar_ratio * 100) + '%'"></div>
                    </div>
                </div>
                <div class="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                    💡 Experiment with ratios! Perfect balance = Happy customers
                </div>
            </div>

            <!-- Supplies -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-xl border border-slate-200 p-6">
                <h2 class="font-bold text-lg mb-4 flex items-center gap-2">
                    🛒 Supplies
                </h2>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <template x-for="(cost, item) in state.costs" :key="item">
                        <div class="border-2 border-slate-100 rounded-xl p-4 hover:border-yellow-400 hover:shadow-lg transition-all group bg-gradient-to-br from-white to-slate-50">
                            <div class="flex justify-between items-start mb-2">
                                <div class="text-3xl" x-text="itemIcons[item]"></div>
                                <div class="text-sm font-bold text-slate-400 bg-slate-100 px-2 py-1 rounded-full" x-text="'x' + state.inventory[item]"></div>
                            </div>
                            <div class="font-bold capitalize text-sm mb-1" x-text="item"></div>
                            <div class="text-xs text-slate-500 mb-3" x-text="'$' + cost.toFixed(2) + ' each'"></div>

                            <div class="flex flex-col gap-2">
                                <button @click="buy(item, 10)"
                                    :disabled="state.cash < cost * 10"
                                    class="w-full py-2 bg-gradient-to-r from-green-400 to-emerald-500 text-white text-xs font-bold rounded-lg hover:from-green-500 hover:to-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed transform active:scale-95 transition-all shadow-md">
                                    +10 <span x-text="'($' + (cost*10).toFixed(2) + ')'"></span>
                                </button>
                                <button @click="buy(item, 50)"
                                    :disabled="state.cash < cost * 50"
                                    class="w-full py-1.5 bg-slate-600 text-white text-xs font-bold rounded-lg hover:bg-slate-700 disabled:opacity-40 transition-all">
                                    +50 (Bulk)
                                </button>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Upgrades -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-xl border border-slate-200 p-6">
                <h2 class="font-bold text-lg mb-4 flex items-center gap-2">
                    ⚡ Upgrades
                </h2>
                <div class="space-y-3">
                    <template x-for="(lvl, type) in state.upgrades" :key="type">
                        <div class="flex items-center justify-between p-4 bg-gradient-to-r from-slate-50 to-slate-100 rounded-xl border-2 border-slate-200 hover:border-yellow-400 transition-all">
                            <div>
                                <div class="font-bold capitalize text-sm text-slate-700 mb-1" x-text="type"></div>
                                <div class="text-xs text-slate-500" x-text="state.upgrade_info[type][lvl].name"></div>
                                <div class="text-xs text-purple-600 font-bold mt-1">
                                    Level <span x-text="lvl + 1"></span>/<span x-text="state.upgrade_info[type].length"></span>
                                </div>
                            </div>

                            <div x-data="{ next: state.upgrade_info[type][lvl+1] }">
                                <button x-show="next"
                                        @click="upgrade(type)"
                                        :disabled="state.cash < next.cost"
                                        class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-sm font-bold rounded-lg hover:from-indigo-600 hover:to-purple-700 disabled:opacity-40 transition-all transform active:scale-95 shadow-md">
                                    <div x-text="next.name"></div>
                                    <div class="text-yellow-300 text-xs" x-text="'$' + next.cost"></div>
                                </button>
                                <span x-show="!next" class="px-4 py-2 bg-gradient-to-r from-green-400 to-emerald-500 text-white text-sm font-bold rounded-lg">
                                    ✓ MAXED
                                </span>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- RIGHT COLUMN -->
        <div class="space-y-6">

            <!-- Stats Dashboard -->
            <div class="bg-gradient-to-br from-purple-500 to-indigo-600 text-white rounded-2xl shadow-2xl p-6">
                <h2 class="font-bold text-xl mb-4">📈 Career Stats</h2>
                <div class="space-y-3">
                    <div class="flex justify-between items-center">
                        <span class="text-sm opacity-90">Total Sales</span>
                        <span class="font-bold text-lg" x-text="state.stats.total_sales"></span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm opacity-90">Total Revenue</span>
                        <span class="font-bold text-lg" x-text="'$' + state.stats.total_revenue.toFixed(2)"></span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm opacity-90">Best Day</span>
                        <span class="font-bold text-lg" x-text="state.stats.best_day + ' sales'"></span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-sm opacity-90">Perfect Days</span>
                        <span class="font-bold text-lg" x-text="state.stats.perfect_days"></span>
                    </div>
                </div>
            </div>

            <!-- Strategy Card -->
            <div class="bg-white/90 backdrop-blur rounded-2xl shadow-2xl border-4 border-yellow-400 p-6 sticky top-24">
                <h2 class="font-bold text-xl mb-4 flex items-center gap-2">
                    <span class="text-2xl">🎯</span>
                    Daily Strategy
                </h2>

                <div class="mb-6 p-4 bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl">
                    <div class="flex justify-between items-end mb-2">
                        <label class="text-sm font-bold text-slate-600">Price per Cup</label>
                        <span class="text-3xl font-black text-slate-800" x-text="'$' + state.price.toFixed(2)"></span>
                    </div>
                    <input type="range" min="0.25" max="5.00" step="0.25"
                           x-model.number="state.price"
                           @change="updatePrice()"
                           class="w-full h-3 bg-slate-200 rounded-lg cursor-pointer accent-yellow-500">
                    <div class="flex justify-between items-center text-xs mt-2">
                        <span class="text-slate-500">Cheap</span>
                        <span class="text-green-600 font-bold">Profit: $<span x-text="(state.price - 0.85).toFixed(2)"></span>/cup</span>
                        <span class="text-slate-500">Premium</span>
                    </div>
                </div>

                <!-- Warnings -->
                <div class="space-y-2 mb-6">
                    <div x-show="state.inventory.lemons < 5" class="text-red-500 text-sm font-bold flex items-center gap-2 p-2 bg-red-50 rounded-lg">
                        ⚠️ Low on Lemons!
                    </div>
                    <div x-show="state.inventory.sugar < 5" class="text-red-500 text-sm font-bold flex items-center gap-2 p-2 bg-red-50 rounded-lg">
                        ⚠️ Low on Sugar!
                    </div>
                    <div x-show="state.inventory.cups < 10" class="text-red-500 text-sm font-bold flex items-center gap-2 p-2 bg-red-50 rounded-lg">
                        ⚠️ Low on Cups!
                    </div>
                    <div x-show="state.weather === 'hot' && state.inventory.ice < 10" class="text-orange-500 text-sm font-bold flex items-center gap-2 p-2 bg-orange-50 rounded-lg">
                        🔥 Stock up on ice!
                    </div>
                </div>

                <button @click="startDay()"
                        :disabled="isPlaying || state.inventory.lemons < 1 || state.inventory.sugar < 1 || state.inventory.cups < 1"
                        class="w-full py-4 bg-gradient-to-r from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600 text-white font-black text-xl rounded-2xl shadow-2xl shadow-green-200 transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none">
                    <span x-show="!isPlaying" class="flex items-center justify-center gap-2">
                        <span>🚀</span>
                        <span>START DAY</span>
                    </span>
                    <span x-show="isPlaying">⏳ Serving...</span>
                </button>

                <button @click="resetGame()" class="w-full mt-4 text-sm text-slate-400 underline hover:text-red-500 transition-colors">
                    Reset Game
                </button>
            </div>
        </div>
    </div>

    <!-- DAY RESULT MODAL -->
    <div x-show="showResult" class="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-[100] p-4" x-cloak x-transition>
        <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden transform" @click.away="closeModal()">
            <div class="bg-gradient-to-r from-yellow-400 to-orange-500 text-white p-6 text-center">
                <h2 class="text-4xl font-black mb-2">Day Complete!</h2>
                <div class="text-lg opacity-90">Let's see how you did...</div>
            </div>

            <div class="p-6">
                <!-- Simulation Log -->
                <div class="bg-slate-900 rounded-xl p-4 h-64 overflow-y-auto mb-6 font-mono text-xs space-y-1 shadow-inner" id="simLog">
                    <template x-for="(entry, idx) in simLog" :key="idx">
                        <div class="slide-up" :style="'animation-delay: ' + (idx * 0.05) + 's'">
                            <div :class="entry.type === 'sale' ? 'text-green-400' : entry.type === 'special' ? 'text-yellow-400' : 'text-red-400'"
                                 class="flex justify-between items-center">
                                <span x-text="entry.msg"></span>
                                <span x-show="entry.price" class="font-bold" x-text="'+$' + entry.price?.toFixed(2)"></span>
                            </div>
                        </div>
                    </template>
                </div>

                <!-- Summary -->
                <div x-show="summary" class="space-y-4">
                    <div class="grid grid-cols-3 gap-4">
                        <div class="bg-gradient-to-br from-green-400 to-emerald-500 text-white p-4 rounded-xl text-center shadow-lg">
                            <div class="text-xs font-bold opacity-75 uppercase">Revenue</div>
                            <div class="text-2xl font-black" x-text="'$' + summary?.revenue.toFixed(2)"></div>
                        </div>
                        <div class="bg-gradient-to-br from-blue-400 to-indigo-500 text-white p-4 rounded-xl text-center shadow-lg">
                            <div class="text-xs font-bold opacity-75 uppercase">Profit</div>
                            <div class="text-2xl font-black" :class="summary?.net_profit >= 0 ? '' : 'text-red-300'"
                                 x-text="(summary?.net_profit >= 0 ? '$' : '-$') + Math.abs(summary?.net_profit).toFixed(2)"></div>
                        </div>
                        <div class="bg-gradient-to-br from-purple-400 to-pink-500 text-white p-4 rounded-xl text-center shadow-lg">
                            <div class="text-xs font-bold opacity-75 uppercase">Sold</div>
                            <div class="text-2xl font-black" x-text="summary?.sold"></div>
                        </div>
                    </div>

                    <div class="bg-slate-50 rounded-xl p-4 space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-slate-600">Cost of Goods:</span>
                            <span class="font-bold text-red-600" x-text="'-$' + summary?.cogs.toFixed(2)"></span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-slate-600">Reputation Change:</span>
                            <span class="font-bold" :class="summary?.rep_change >= 0 ? 'text-green-600' : 'text-red-600'"
                                  x-text="(summary?.rep_change > 0 ? '+' : '') + summary?.rep_change"></span>
                        </div>
                        <div x-show="summary?.event_bonus" class="flex justify-between">
                            <span class="text-slate-600">Event Bonus:</span>
                            <span class="font-bold text-purple-600" x-text="summary?.event_bonus"></span>
                        </div>
                    </div>

                    <button @click="closeModal()"
                            class="w-full py-4 bg-gradient-to-r from-slate-700 to-slate-900 text-white font-bold text-lg rounded-xl hover:from-slate-800 hover:to-black transition-all transform active:scale-95 shadow-xl">
                        Continue to Day <span x-text="state.day"></span> →
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function gameApp() {
            return {
                state: {},
                isPlaying: false,
                showResult: false,
                simLog: [],
                summary: null,
                charts: { cash: null, sales: null },
                achievementToast: false,
                achievementData: null,
                eventAlert: false,
                eventData: null,

                itemIcons: { lemons: '🍋', sugar: '🧂', cups: '🥤', ice: '🧊' },
                weatherIcons: { sunny: '☀️', cloudy: '☁️', rainy: '🌧️', hot: '🔥' },
                achievementNames: {
                    first_sale: "First Sale!",
                    hundred_sales: "Century",
                    thousand_sales: "Legendary",
                    profit_master: "Profit Master",
                    five_star: "Five Star",
                    tycoon: "Tycoon",
                    perfect_day: "Perfect Day",
                    ice_king: "Ice King"
                },

                async init() {
                    await this.refreshState();
                    this.$nextTick(() => this.initCharts());
                },

                initCharts() {
                    const cashEl = document.getElementById('cashChart');
                    const salesEl = document.getElementById('salesChart');
                    if (!cashEl || !salesEl) {
                        console.log('Chart elements not found');
                        return;
                    }

                    // Destroy existing charts
                    if (this.charts.cash) {
                        this.charts.cash.destroy();
                        this.charts.cash = null;
                    }
                    if (this.charts.sales) {
                        this.charts.sales.destroy();
                        this.charts.sales = null;
                    }

                    // Cash Growth Chart (Area Chart)
                    this.charts.cash = new Chart(cashEl.getContext('2d'), {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Total Cash',
                                data: [],
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 4,
                                pointBackgroundColor: '#10b981',
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                                pointHoverRadius: 6
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                intersect: false,
                                mode: 'index'
                            },
                            plugins: {
                                legend: { display: false },
                                title: {
                                    display: true,
                                    text: '💰 Cash Growth',
                                    color: '#1f2937',
                                    font: { size: 14, weight: 'bold' }
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                    displayColors: false,
                                    callbacks: {
                                        label: function(context) {
                                            return '$' + context.parsed.y.toFixed(2);
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(value) {
                                            return '$' + value;
                                        },
                                        color: '#6b7280'
                                    },
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }
                                },
                                x: {
                                    ticks: { color: '#6b7280' },
                                    grid: { display: false }
                                }
                            }
                        }
                    });

                    // Daily Profit Chart (Bar Chart)
                    this.charts.sales = new Chart(salesEl.getContext('2d'), {
                        type: 'bar',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Daily Profit',
                                data: [],
                                backgroundColor: '#3b82f6',
                                borderRadius: 6,
                                borderSkipped: false
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                intersect: false,
                                mode: 'index'
                            },
                            plugins: {
                                legend: { display: false },
                                title: {
                                    display: true,
                                    text: '📊 Daily Net Profit',
                                    color: '#1f2937',
                                    font: { size: 14, weight: 'bold' }
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                    displayColors: false,
                                    callbacks: {
                                        label: function(context) {
                                            const value = context.parsed.y;
                                            return (value >= 0 ? '+$' : '-$') + Math.abs(value).toFixed(2);
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(value) {
                                            return '$' + value;
                                        },
                                        color: '#6b7280'
                                    },
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }
                                },
                                x: {
                                    ticks: { color: '#6b7280' },
                                    grid: { display: false }
                                }
                            }
                        }
                    });

                    this.updateCharts();
                },

                updateCharts() {
                    if (!this.state.history || this.state.history.length === 0) {
                        console.log('No history data available');
                        return;
                    }

                    if (!this.charts.cash || !this.charts.sales) {
                        console.log('Charts not initialized');
                        return;
                    }

                    try {
                        const labels = this.state.history.map(h => 'Day ' + h.day);
                        const cashData = this.state.history.map(h => h.cash);
                        const profitData = this.state.history.map(h => h.net_profit);

                        // Update Cash Chart
                        this.charts.cash.data.labels = labels;
                        this.charts.cash.data.datasets[0].data = cashData;
                        this.charts.cash.update('none'); // No animation for smoother updates

                        // Update Profit Chart with dynamic colors
                        this.charts.sales.data.labels = labels;
                        this.charts.sales.data.datasets[0].data = profitData;
                        this.charts.sales.data.datasets[0].backgroundColor = profitData.map(v =>
                            v >= 0 ? '#10b981' : '#ef4444'
                        );
                        this.charts.sales.update('none');
                    } catch (error) {
                        console.error('Error updating charts:', error);
                    }
                },

                async refreshState() {
                    const res = await fetch('/api/state');
                    this.state = await res.json();
                    this.$nextTick(() => {
                        if (this.state.day > 1) {
                            if (!this.charts.cash) this.initCharts();
                            else this.updateCharts();
                        }
                    });
                },

                showAchievement(ach) {
                    this.achievementData = ach;
                    this.achievementToast = true;
                    setTimeout(() => this.achievementToast = false, 4000);
                },

                showEvent(event) {
                    this.eventData = event;
                    this.eventAlert = true;
                    setTimeout(() => this.eventAlert = false, 5000);
                },

                async updatePrice() {
                    await fetch('/api/price', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ price: this.state.price })
                    });
                },

                async updateRecipe() {
                    await fetch('/api/recipe', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(this.state.recipe)
                    });
                },

                async buy(item, quantity) {
                    const res = await fetch('/api/buy', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ item, quantity })
                    });
                    const data = await res.json();
                    if(data.success) {
                        this.state = data.state;
                    } else {
                        alert(data.message);
                    }
                },

                async upgrade(type) {
                    const res = await fetch('/api/upgrade', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ type })
                    });
                    const data = await res.json();
                    if(data.success) {
                        this.state = data.state;
                    } else {
                        alert(data.message);
                    }
                },

                async startDay() {
                    if(this.state.inventory.lemons < 1 || this.state.inventory.sugar < 1 || this.state.inventory.cups < 1) {
                        alert("You need ingredients to start!");
                        return;
                    }

                    this.isPlaying = true;
                    this.showResult = true;
                    this.simLog = [];
                    this.summary = null;

                    const res = await fetch('/api/start-day', { method: 'POST' });
                    const data = await res.json();

                    // Show event if any
                    if (data.event) {
                        this.showEvent(data.event);
                    }

                    // Animate log
                    for (const entry of data.log) {
                        await new Promise(r => setTimeout(r, 80));
                        this.simLog.push(entry);
                        this.$nextTick(() => {
                            const el = document.getElementById('simLog');
                            if(el) el.scrollTop = el.scrollHeight;
                        });
                    }

                    await new Promise(r => setTimeout(r, 500));
                    this.summary = data.summary;
                    this.state = data.new_state;

                    // Show achievements
                    if (data.achievements && data.achievements.length > 0) {
                        for (const ach of data.achievements) {
                            await new Promise(r => setTimeout(r, 1000));
                            this.showAchievement(ach);
                        }
                    }

                    this.isPlaying = false;
                },

                async closeModal() {
                    this.showResult = false;
                    this.$nextTick(() => this.refreshState());
                },

                async resetGame() {
                    if(!confirm("Reset all progress? This cannot be undone!")) return;
                    await fetch('/api/reset', { method: 'POST' });
                    await this.refreshState();
                    location.reload();
                }
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
#              API ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTMLResponse(content=html_content)

@app.get("/api/state")
async def get_state():
    return {
        "cash": round(game.cash, 2),
        "day": game.day,
        "reputation": game.reputation,
        "stars": round(game.stars, 1),
        "inventory": game.inventory,
        "price": game.price,
        "recipe": game.recipe,
        "upgrades": game.upgrades,
        "upgrade_info": UPGRADES,
        "weather": game.weather,
        "next_weather": game.next_weather,
        "active_event": game.active_event,
        "costs": COSTS,
        "history": game.history,
        "stats": game.stats,
        "achievements": game.achievements,
        "streak": game.streak
    }

@app.post("/api/price")
async def set_price(data: PriceUpdate):
    if 0.01 <= data.price <= 10.00:
        game.price = data.price
        game.save_to_csv()
        return {"success": True}
    return {"success": False, "message": "Invalid price"}

@app.post("/api/recipe")
async def set_recipe(data: RecipeUpdate):
    game.recipe["lemon_ratio"] = max(0.5, min(1.5, data.lemon_ratio))
    game.recipe["sugar_ratio"] = max(0.5, min(1.5, data.sugar_ratio))
    game.save_to_csv()
    return {"success": True}

@app.post("/api/buy")
async def buy_item(data: PurchaseRequest):
    if data.item not in COSTS:
        raise HTTPException(status_code=400, detail="Invalid item")

    cost = COSTS[data.item] * data.quantity
    if game.cash >= cost:
        game.cash -= cost
        game.inventory[data.item] += data.quantity
        game.save_to_csv()
        return {"success": True, "state": await get_state()}
    return {"success": False, "message": "Not enough cash!"}

@app.post("/api/upgrade")
async def buy_upgrade(data: UpgradeRequest):
    u_type = data.type
    if u_type not in UPGRADES:
        raise HTTPException(status_code=400, detail="Invalid upgrade type")

    current_level = game.upgrades[u_type]
    if current_level >= len(UPGRADES[u_type]) - 1:
        return {"success": False, "message": "Max level reached"}

    next_level_idx = current_level + 1
    cost = UPGRADES[u_type][next_level_idx]["cost"]

    if game.cash >= cost:
        game.cash -= cost
        game.upgrades[u_type] = next_level_idx
        game.save_to_csv()
        return {"success": True, "state": await get_state()}
    return {"success": False, "message": "Not enough cash!"}

@app.post("/api/start-day")
async def start_day():
    log = []
    sold_count = 0
    missed_count = 0
    revenue = 0.0
    daily_cogs = 0.0
    special_sales = 0

    # Check for random event
    triggered_event = None
    for event in EVENTS:
        if random.random() < event["chance"]:
            triggered_event = event
            game.active_event = event
            break

    # Calculate quality from recipe & upgrades
    recipe_quality = (game.recipe["lemon_ratio"] + game.recipe["sugar_ratio"]) / 2
    juicer_quality = UPGRADES["juicer"][game.upgrades["juicer"]].get("quality", 1.0)
    overall_quality = recipe_quality * juicer_quality

    # Stand appeal
    stand_appeal = UPGRADES["stand"][game.upgrades["stand"]].get("appeal", 1.0)
    marketing_boost = UPGRADES["marketing"][game.upgrades["marketing"]].get("boost", 0)

    # Weather modifier
    w_mod = {"sunny": 1.0, "cloudy": 0.7, "rainy": 0.4, "hot": 1.8}.get(game.weather, 1.0)

    # Event modifiers
    event_customer_mod = 1.0
    event_price_mod = 1.0
    event_message = ""

    if triggered_event:
        if triggered_event["type"] == "rush":
            event_customer_mod = 2.0
            event_message = "School bus brought tons of customers!"
        elif triggered_event["type"] == "festival":
            event_customer_mod = 1.5
            event_price_mod = 1.2
            event_message = "Festival crowd loves premium lemonade!"
        elif triggered_event["type"] == "rival":
            event_customer_mod = 0.6
            event_message = "Rival stand stealing customers!"
        elif triggered_event["type"] == "celebrity":
            special_sales = 1
            event_message = "Celebrity bought your lemonade!"
        elif triggered_event["type"] == "outage":
            if game.upgrades["fridge"] > 0:
                event_message = "Your fridge saved the day!"
            else:
                game.inventory["ice"] = 0
                event_message = "Power outage! All ice melted!"

    # Calculate customers
    base_customers = random.randint(15, 35)
    rep_factor = 1 + (game.reputation / 100)
    potential_customers = int(base_customers * w_mod * rep_factor * stand_appeal * event_customer_mod * (1 + marketing_boost / 100))

    # Simulation loop
    for i in range(potential_customers):
        has_basics = game.inventory["lemons"] >= 1 and game.inventory["sugar"] >= 1 and game.inventory["cups"] >= 1
        has_ice = game.inventory["ice"] >= 1

        if not has_basics:
            log.append({"tick": i, "type": "miss", "msg": "⛔ SOLD OUT"})
            missed_count += 1
            continue

        wants_ice = (game.weather == "hot") or (random.random() > 0.6)

        # Dynamic max price based on quality
        max_price = random.uniform(0.80, 2.00) * overall_quality * event_price_mod
        if game.weather == "hot":
            max_price += 0.50
        if game.reputation > 60:
            max_price += 0.40

        sale_made = False
        used_ice = False

        if wants_ice and not has_ice:
            if random.random() > 0.6:
                log.append({"tick": i, "type": "miss", "msg": "❌ No ice!"})
                missed_count += 1
                continue
            else:
                sale_made = True
                log.append({"tick": i, "type": "sale", "msg": "😐 Warm sale", "price": game.price * 0.8})
                revenue += game.price * 0.8
        elif game.price > max_price:
            log.append({"tick": i, "type": "miss", "msg": "💸 Too expensive"})
            missed_count += 1
        else:
            sale_made = True
            used_ice = has_ice

            # Quality bonus
            if overall_quality > 1.2:
                log.append({"tick": i, "type": "sale", "msg": "⭐ PREMIUM sale!", "price": game.price * 1.1})
                revenue += game.price * 1.1
            else:
                log.append({"tick": i, "type": "sale", "msg": "✅ Sold!", "price": game.price})
                revenue += game.price

        if sale_made:
            sold_count += 1
            game.inventory["lemons"] -= 1
            game.inventory["sugar"] -= 1
            game.inventory["cups"] -= 1
            daily_cogs += COSTS["lemons"] + COSTS["sugar"] + COSTS["cups"]

            if used_ice:
                game.inventory["ice"] -= 1
                daily_cogs += COSTS["ice"]

    # Celebrity special sale
    if special_sales > 0:
        celebrity_payment = 50.0
        revenue += celebrity_payment
        log.append({"tick": len(log), "type": "special", "msg": "🌟 CELEBRITY TIP!", "price": celebrity_payment})

    # End of day calculations
    conversion_rate = sold_count / potential_customers if potential_customers > 0 else 0

    # Reputation update
    rep_change = 0
    if conversion_rate >= 1.0:
        rep_change = random.randint(8, 12)
        game.stats["perfect_days"] += 1
        new_ach = game.check_achievement("perfect_day")
    elif conversion_rate > 0.75:
        rep_change = random.randint(3, 6)
    elif conversion_rate < 0.4:
        rep_change = random.randint(-8, -3)

    # Quality affects reputation
    if overall_quality > 1.3:
        rep_change += 3
    elif overall_quality < 0.8:
        rep_change -= 3

    stand_cap = UPGRADES["stand"][game.upgrades["stand"]]["rep_cap"]
    game.reputation = max(0, min(stand_cap, game.reputation + rep_change))

    # Update star rating
    game.stars = 1.0 + (game.reputation / 25)

    # Ice melt
    fridge_level = game.upgrades["fridge"]
    save_rate = UPGRADES["fridge"][fridge_level]["ice_save"]
    ice_melted_count = int(game.inventory["ice"] * (1 - save_rate))
    game.inventory["ice"] -= ice_melted_count
    ice_loss_cost = ice_melted_count * COSTS["ice"]

    # Financials
    net_profit = revenue - daily_cogs - ice_loss_cost
    game.cash += revenue

    # Update streak
    if net_profit > 0:
        game.streak += 1
    else:
        game.streak = 0

    # Update stats
    game.stats["total_sales"] += sold_count
    game.stats["total_revenue"] += revenue
    if sold_count > game.stats["best_day"]:
        game.stats["best_day"] = sold_count

    # History
    game.history.append({
        "day": game.day,
        "cash": round(game.cash, 2),
        "revenue": round(revenue, 2),
        "net_profit": round(net_profit, 2),
        "sales": sold_count
    })

    game.day += 1
    game.weather = game.next_weather
    game.next_weather = random.choice(["sunny", "cloudy", "rainy", "hot"])

    # Check achievements
    achievements_earned = []
    for ach_id in ["first_sale", "hundred_sales", "thousand_sales", "profit_master", "tycoon", "five_star"]:
        result = game.check_achievement(ach_id)
        if result:
            achievements_earned.append(result)

    # Check profit master
    if net_profit >= 100:
        result = game.check_achievement("profit_master")
        if result:
            achievements_earned.append(result)

    game.save_to_csv()

    response = {
        "log": log,
        "summary": {
            "sold": sold_count,
            "missed": missed_count,
            "revenue": round(revenue, 2),
            "cogs": round(daily_cogs, 2),
            "ice_loss": round(ice_loss_cost, 2),
            "net_profit": round(net_profit, 2),
            "rep_change": rep_change,
            "event_bonus": event_message if event_message else None
        },
        "new_state": await get_state(),
        "achievements": achievements_earned
    }

    if triggered_event:
        response["event"] = {
            "name": triggered_event["name"],
            "emoji": triggered_event["emoji"],
            "effect": event_message
        }

    return response

@app.post("/api/reset")
def reset_game():
    game.reset()
    return {"success": True}

@app.get("/health")
async def health():
    return {"status": "healthy", "game": "Lemonade Tycoon Deluxe", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
