from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Optional
import random
import os
import math

app = FastAPI(title="Lemonade Tycoon API", version="2.0.0")

# Setup Templates
templates = Jinja2Templates(directory="templates")

# --- CONFIGURATION ---
COSTS = {
    "lemons": 0.50,
    "sugar": 0.20,
    "cups": 0.10,
    "ice": 0.05
}

UPGRADES = {
    "juicer": [
        {"name": "Hand Squeezer", "cost": 0, "speed": 1.0},
        {"name": "Metal Press", "cost": 50, "speed": 1.5},
        {"name": "Industrial Juicer", "cost": 200, "speed": 3.0}
    ],
    "stand": [
        {"name": "Cardboard Box", "cost": 0, "rep_cap": 30},
        {"name": "Wooden Stand", "cost": 100, "rep_cap": 60},
        {"name": "Food Truck", "cost": 500, "rep_cap": 100}
    ],
    "fridge": [
        {"name": "Cooler Box", "cost": 0, "ice_save": 0.0},
        {"name": "Mini Fridge", "cost": 150, "ice_save": 0.4},
        {"name": "Deep Freezer", "cost": 400, "ice_save": 0.8}
    ]
}

# --- STATE ---
class GameState:
    def __init__(self):
        self.cash = 25.0
        self.day = 1
        self.reputation = 10
        self.inventory = {
            "lemons": 5,
            "sugar": 5,
            "cups": 10,
            "ice": 0
        }
        self.price = 1.00
        self.upgrades = {
            "juicer": 0,
            "stand": 0,
            "fridge": 0
        }
        self.stats = {
            "total_sales": 0,
            "total_revenue": 0.0
        }
        self.weather = "sunny"
        self.next_weather = "cloudy"

    def reset(self):
        self.__init__()

game = GameState()

# --- MODELS ---
class PurchaseRequest(BaseModel):
    item: str
    quantity: int

class PriceUpdate(BaseModel):
    price: float

class UpgradeRequest(BaseModel):
    type: str

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/state")
async def get_state():
    return {
        "cash": round(game.cash, 2),
        "day": game.day,
        "reputation": game.reputation,
        "inventory": game.inventory,
        "price": game.price,
        "upgrades": game.upgrades,
        "upgrade_info": UPGRADES,
        "weather": game.weather,
        "next_weather": game.next_weather,
        "costs": COSTS
    }

@app.post("/api/price")
async def set_price(data: PriceUpdate):
    if 0.01 <= data.price <= 10.00:
        game.price = data.price
        return {"success": True, "price": game.price}
    return {"success": False, "message": "Invalid price"}

@app.post("/api/buy")
async def buy_item(data: PurchaseRequest):
    if data.item not in COSTS:
        raise HTTPException(status_code=400, detail="Invalid item")
    
    cost = COSTS[data.item] * data.quantity
    if game.cash >= cost:
        game.cash -= cost
        game.inventory[data.item] += data.quantity
        return {"success": True, "state": await get_state()}
    return {"success": False, "message": "Not enough cash!"}

@app.post("/api/upgrade")
async def buy_upgrade(data: UpgradeRequest):
    u_type = data.type
    if u_type not in UPGRADES:
        raise HTTPException(status_code=400, detail="Invalid upgrade type")
    
    current_level = game.upgrades[u_type]
    # Check if maxed
    if current_level >= len(UPGRADES[u_type]) - 1:
        return {"success": False, "message": "Max level reached"}
    
    next_level_idx = current_level + 1
    cost = UPGRADES[u_type][next_level_idx]["cost"]
    
    if game.cash >= cost:
        game.cash -= cost
        game.upgrades[u_type] = next_level_idx
        return {"success": True, "state": await get_state()}
    return {"success": False, "message": "Not enough cash!"}

@app.post("/api/start-day")
async def start_day():
    # 1. Setup Simulation
    log = []
    sold_count = 0
    missed_count = 0
    revenue = 0.0
    
    # Weather modifiers
    w_mod = {
        "sunny": 1.0, 
        "cloudy": 0.7, 
        "rainy": 0.4, 
        "hot": 1.8
    }.get(game.weather, 1.0)

    # Determine number of potential customers (Ticks)
    base_customers = random.randint(10, 25)
    potential_customers = int(base_customers * w_mod * (1 + (game.reputation / 100)))
    
    # 2. Run Simulation Loop
    for i in range(potential_customers):
        # Check Stock
        has_basics = game.inventory["lemons"] >= 1 and game.inventory["sugar"] >= 1 and game.inventory["cups"] >= 1
        has_ice = game.inventory["ice"] >= 1
        
        # Customer Preference
        wants_ice = (game.weather == "hot") or (random.random() > 0.5)
        max_price = random.uniform(0.50, 2.50)
        if game.weather == "hot": max_price += 0.50
        if game.reputation > 50: max_price += 0.50

        # Decision
        if not has_basics:
            log.append({"tick": i, "type": "miss", "msg": "Sold Out (Basics)"})
            missed_count += 1
        elif wants_ice and not has_ice:
            # 50% chance they leave if they wanted ice and you don't have it
            if random.random() > 0.5:
                log.append({"tick": i, "type": "miss", "msg": "No Ice!"})
                missed_count += 1
            else:
                # They buy anyway but are grumpy (handled in rep later)
                log.append({"tick": i, "type": "sale", "msg": "Sold (Warm)", "price": game.price})
                sold_count += 1
                revenue += game.price
                game.inventory["lemons"] -= 1
                game.inventory["sugar"] -= 1
                game.inventory["cups"] -= 1
        elif game.price > max_price:
            log.append({"tick": i, "type": "miss", "msg": "Too Expensive"})
            missed_count += 1
        else:
            # Successful Sale
            log.append({"tick": i, "type": "sale", "msg": "Sold!", "price": game.price})
            sold_count += 1
            revenue += game.price
            game.inventory["lemons"] -= 1
            game.inventory["sugar"] -= 1
            game.inventory["cups"] -= 1
            if has_ice: game.inventory["ice"] -= 1

    # 3. End of Day Calculations
    
    # Reputation Update
    conversion_rate = sold_count / potential_customers if potential_customers > 0 else 0
    rep_change = 0
    if conversion_rate > 0.7: rep_change = random.randint(2, 5)
    elif conversion_rate < 0.4: rep_change = random.randint(-5, -2)
    
    stand_cap = UPGRADES["stand"][game.upgrades["stand"]]["rep_cap"]
    game.reputation = max(0, min(stand_cap, game.reputation + rep_change))
    
    # Ice Melt
    fridge_level = game.upgrades["fridge"]
    save_rate = UPGRADES["fridge"][fridge_level]["ice_save"]
    melted = int(game.inventory["ice"] * (1 - save_rate))
    game.inventory["ice"] -= melted

    # Financials
    game.cash += revenue
    game.stats["total_sales"] += sold_count
    game.stats["total_revenue"] += revenue
    game.day += 1
    
    # Next Weather
    game.weather = game.next_weather
    game.next_weather = random.choice(["sunny", "cloudy", "rainy", "hot"])

    return {
        "log": log,
        "summary": {
            "sold": sold_count,
            "missed": missed_count,
            "revenue": round(revenue, 2),
            "melted": melted,
            "rep_change": rep_change,
            "weather_tomorrow": game.weather
        },
        "new_state": await get_state()
    }

@app.post("/api/reset")
def reset_game():
    game.reset()
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
