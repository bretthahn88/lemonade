from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import random
import os

app = FastAPI(title="🍋 Lemonade Tycoon: The Ultimate Stand-Off 🍋", version="2.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ===========================
# 🎮 EPIC GAME STATE
# ===========================
class LemonadeEmpire:
    def __init__(self):
        self.reset()

    def reset(self):
        self.cash = 20.0
        self.lemons = 10
        self.sugar = 10
        self.cups = 20
        self.ice = 0  # New!
        self.price = 1.00
        self.reputation = 50
        self.day = 1
        self.total_sales = 0
        self.streak = 0
        self.achievements = []
        self.events_log = []
        self.upgrades = {
            "sign": False,        # +20% customers
            "cooler": False,      # enables ice
            "fancy_pitcher": False, # +10 reputation per good day
            "celebrity_endorsement": False  # rare unlock
        }

empire = LemonadeEmpire()

# ===========================
# 🏆 ACHIEVEMENTS
# ===========================
ACHIEVEMENTS = {
    "first_sale": {"name": "First Drop", "desc": "Sell your first lemonade", "icon": "🥤"},
    "10_custom": {"name": "Crowd Pleaser", "desc": "Serve 10+ customers in one day", "icon": "🎉"},
    "100_sales": {"name": "Century Stand", "desc": "Sell 100 lemonades total", "icon": "💯"},
    "hot_streak": {"name": "Hot Streak", "desc": "5 perfect weather days in a row", "icon": "🔥"},
    "rich": {"name": "Lemon Millionaire", "desc": "Reach $500 cash", "icon": "💰"},
    "price_guru": {"name": "Price Wizard", "desc": "Find the perfect $0.75 price", "icon": "🧙‍♂️"},
    "rain_master": {"name": "Rain Dancer", "desc": "Sell 15+ on a rainy day", "icon": "☔"},
}

def check_achievements(sales_today, revenue):
    added = []
    if empire.total_sales >= 1 and "first_sale" not in empire.achievements:
        empire.achievements.append("first_sale")
        added.append(ACHIEVEMENTS["first_sale"])
    if sales_today >= 10 and "10_custom" not in empire.achievements:
        empire.achievements.append("10_custom")
        added.append(ACHIEVEMENTS["10_custom"])
    if empire.total_sales >= 100 and "100_sales" not in empire.achievements:
        empire.achievements.append("100_sales")
        added.append(ACHIEVEMENTS["100_sales"])
    if empire.cash >= 500 and "rich" not in empire.achievements:
        empire.achievements.append("rich")
        added.append(ACHIEVEMENTS["rich"])
    if abs(empire.price - 0.75) < 0.01 and "price_guru" not in empire.achievements:
        empire.achievements.append("price_guru")
        added.append(ACHIEVEMENTS["price_guru"])
    return added

# ===========================
# 🛒 MODELS
# ===========================
class PurchaseRequest(BaseModel):
    lemons: int = 0
    sugar: int = 0
    cups: int = 0
    ice: int = 0

class PriceUpdate(BaseModel):
    price: float

class UpgradePurchase(BaseModel):
    upgrade: str

# ===========================
# 🎯 ROUTES
# ===========================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    unlocked = [ACHIEVEMENTS[a] for a in empire.achievements]
    return {
        "cash": round(empire.cash, 2),
        "lemons": empire.lemons,
        "sugar": empire.sugar,
        "cups": empire.cups,
        "ice": empire.ice,
        "price": round(empire.price, 2),
        "reputation": empire.reputation,
        "day": empire.day,
        "total_sales": empire.total_sales,
        "streak": empire.streak,
        "achievements": unlocked,
        "events_log": empire.events_log[-5:],
        "upgrades": empire.upgrades,
        "can_buy_ice": empire.upgrades["cooler"]
    }

@app.post("/api/purchase")
async def buy_supplies(purchase: PurchaseRequest):
    cost = (purchase.lemons * 0.5) + (purchase.sugar * 0.3) + (purchase.cups * 0.1) + (purchase.ice * 0.2)
    if cost > empire.cash:
        return {"success": False, "message": "🤑 Not enough cash, capitalist!"}

    empire.cash -= cost
    empire.lemons += purchase.lemons
    empire.sugar += purchase.sugar
    empire.cups += purchase.cups
    empire.ice += purchase.ice

    return {"success": True, "message": "🛍️ Supplies secured!", "status": await get_status()}

@app.post("/api/set-price")
async def set_price(update: PriceUpdate):
    if not 0.10 <= update.price <= 10.0:
        return {"success": False, "message": "🤨 That price is criminal!"}
    empire.price = update.price
    return {"success": True, "message": f"💲 Price set to ${empire.price:.2f}", "status": await get_status()}

@app.post("/api/buy-upgrade")
async def buy_upgrade(req: UpgradePurchase):
    prices = {
        "sign": 50,
        "cooler": 120,
        "fancy_pitcher": 200,
        "celebrity_endorsement": 1000
    }
    if req.upgrade not in prices:
        return {"success": False, "message": "Upgrade not found!"}
    if empire.upgrades.get(req.upgrade, False):
        return {"success": False, "message": "You already own this!"}
    if empire.cash < prices[req.upgrade]:
        return {"success": False, "message": "Too expensive, dreamer!"}

    empire.cash -= prices[req.upgrade]
    empire.upgrades[req.upgrade] = True
    return {"success": True, "message": f"✨ {req.upgrade.replace('_', ' ').title()} UNLOCKED!", "status": await get_status()}

@app.post("/api/sell-day")
async def sell_day():
    if min(empire.lemons, empire.sugar, empire.cups) < 1:
        return {"success": False, "message": "😭 Out of ingredients! Buy supplies first!"}

    # === Random Events ===
    event = random.random()
    event_msg = ""
    multiplier = 1.0

    if event < 0.05:
        event_msg = "🎈 A festival is in town! +50% customers!"
        multiplier = 1.5
    elif event < 0.1:
        event_msg = "😱 Health inspector! Lost 10 reputation..."
        empire.reputation = max(0, empire.reputation - 10)
    elif event < 0.15 and empire.day > 10:
        event_msg = "🦨 Skunk sprayed your stand! Half customers today..."
        multiplier = 0.5

    # === Weather ===
    weather = random.choices(
        ["hot", "sunny", "cloudy", "rainy", "storm"],
        weights=[20, 40, 25, 10, 5], k=1)[0]

    weather_emoji = {"hot": "🔥", "sunny": "☀️", "cloudy": "☁️", "rainy": "🌧️", "storm": "⛈️"}
    weather_mult = {"hot": 1.8, "sunny": 1.2, "cloudy": 0.8, "rainy": 0.4, "storm": 0.1}[weather]

    if weather == "hot":
        empire.streak += 1
    else:
        empire.streak = 0

    # === Sales Calculation ===
    base = random.randint(15, 45)
    price_factor = max(0.2, 3.0 - empire.price * 1.5)
    rep_factor = empire.reputation / 50
    upgrade_bonus = 1.2 if empire.upgrades["sign"] else 1.0
    ice_bonus = 1.0 + (empire.ice // 10) * 0.2 if empire.upgrades["cooler"] else 1.0

    potential = int(base * price_factor * rep_factor * weather_mult * multiplier * upgrade_bonus * ice_bonus)
    max_can_serve = min(empire.lemons, empire.sugar, empire.cups)
    sales = min(potential, max_can_serve, 200)  # cap at 200

    revenue = sales * empire.price
    empire.cash += revenue
    empire.total_sales += sales

    # Consume supplies
    empire.lemons -= sales
    empire.sugar -= sales
    empire.cups -= sales
    empire.ice = max(0, empire.ice - sales // 3) if empire.upgrades["cooler"] else 0

    # Reputation change
    rep_change = 0
    if 0.60 <= empire.price <= 1.20:
        rep_change += random.randint(3, 8)
    if empire.price < 0.4:
        rep_change -= 7
    if empire.price > 3.0:
        rep_change -= 12
    if empire.upgrades["fancy_pitcher"] and sales > 15:
        rep_change += 5

    empire.reputation = max(0, min(100, empire.reputation + rep_change))
    empire.day += 1

    # Check achievements
    new_achs = check_achievements(sales, revenue)
    for a in new_achs:
        empire.events_log.append(f"🏆 ACHIEVEMENT UNLOCKED: {a['name']} {a['icon']}")

    if event_msg:
        empire.events_log.append(event_msg)
    if sales >= 15 and weather in ["rainy", "storm"] and "rain_master" not in empire.achievements:
        empire.achievements.append("rain_master")
        empire.events_log.append("☔ RAIN MASTER ACHIEVEMENT!")

    if empire.streak >= 5 and "hot_streak" not in empire.achievements:
        empire.achievements.append("hot_streak")
        empire.events_log.append("🔥 HOT STREAK x5! You're unstoppable!")

    empire.events_log.append(f"Day {empire.day-1}: {sales} sold for ${revenue:.2f} | Weather: {weather_emoji[weather]}")

    return {
        "success": True,
        "weather": weather,
        "weather_emoji": weather_emoji[weather],
        "sales": sales,
        "revenue": round(revenue, 2),
        "event": event_msg or "Just a regular day!",
        "rep_change": rep_change,
        "new_achievements": new_achs,
        "status": await get_status()
    }

@app.post("/api/reset")
async def reset():
    empire.reset()
    return {"success": True, "message": "🍋 Fresh start! Welcome back to Day 1!", "status": await get_status()}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
