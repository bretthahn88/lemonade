from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import random
import os

app = FastAPI(title="Lemonade Stand Simulator", version="1.0.0")

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# ===========================
# Game State
# ===========================
class LemonadeStand:
    def __init__(self):
        self.cash = 10.0
        self.lemons = 5
        self.sugar = 5
        self.cups = 10
        self.price = 0.50
        self.reputation = 50
        self.day = 1
        self.total_sales = 0

stand = LemonadeStand()

# ===========================
# Request Models
# ===========================
class PurchaseRequest(BaseModel):
    lemons: int = 0
    sugar: int = 0
    cups: int = 0

class PriceUpdate(BaseModel):
    price: float

# ===========================
# Routes
# ===========================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the dashboard HTML"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """Get current stand status"""
    return {
        "cash": round(stand.cash, 2),
        "lemons": stand.lemons,
        "sugar": stand.sugar,
        "cups": stand.cups,
        "price": round(stand.price, 2),
        "reputation": stand.reputation,
        "day": stand.day,
        "total_sales": stand.total_sales
    }

@app.post("/api/purchase")
async def purchase_supplies(purchase: PurchaseRequest):
    """Purchase supplies for the stand"""
    cost = (purchase.lemons * 0.50) + (purchase.sugar * 0.30) + (purchase.cups * 0.10)
    if cost > stand.cash:
        return {"success": False, "message": "Not enough cash!"}
    stand.cash -= cost
    stand.lemons += purchase.lemons
    stand.sugar += purchase.sugar
    stand.cups += purchase.cups
    return {
        "success": True,
        "message": f"Purchased supplies for ${cost:.2f}",
        "status": await get_status()
    }

@app.post("/api/set-price")
async def set_price(price_update: PriceUpdate):
    """Update lemonade price"""
    if price_update.price < 0.10 or price_update.price > 5.00:
        return {"success": False, "message": "Price must be between $0.10 and $5.00"}
    stand.price = price_update.price
    return {
        "success": True,
        "message": f"Price updated to ${stand.price:.2f}",
        "status": await get_status()
    }

@app.post("/api/sell-day")
async def sell_for_day():
    """Simulate a day of selling lemonade"""
    if stand.lemons < 1 or stand.sugar < 1 or stand.cups < 1:
        return {
            "success": False,
            "message": "Not enough supplies to sell! Buy more lemons, sugar, or cups."
        }

    # Weather affects sales
    weather = random.choice(["sunny", "cloudy", "hot", "rainy"])
    weather_multiplier = {
        "sunny": 1.0,
        "cloudy": 0.7,
        "hot": 1.5,
        "rainy": 0.3
    }[weather]

    # Calculate potential customers
    base_customers = random.randint(10, 30)
    price_factor = max(0.1, 2.0 - stand.price)  # Lower price = more customers
    reputation_factor = stand.reputation / 50
    potential_customers = int(base_customers * price_factor * reputation_factor * weather_multiplier)

    # Limited by supplies
    max_servable = min(stand.lemons, stand.sugar, stand.cups)
    actual_sales = min(potential_customers, max_servable)

    # Update inventory
    stand.lemons -= actual_sales
    stand.sugar -= actual_sales
    stand.cups -= actual_sales

    # Revenue
    revenue = actual_sales * stand.price
    stand.cash += revenue
    stand.total_sales += actual_sales

    # Reputation change
    if stand.price < 0.30:
        reputation_change = -5
    elif stand.price > 2.00:
        reputation_change = -10
    elif 0.40 <= stand.price <= 1.00:
        reputation_change = random.randint(1, 5)
    else:
        reputation_change = random.randint(-2, 2)

    stand.reputation = max(0, min(100, stand.reputation + reputation_change))
    stand.day += 1

    weather_emoji = {
        "sunny": "Sunny",
        "cloudy": "Cloudy",
        "hot": "Fire",
        "rainy": "Rain"
    }[weather]

    return {
        "success": True,
        "message": f"Day {stand.day - 1} complete! Weather: {weather} {weather_emoji}",
        "details": {
            "weather": weather,
            "customers": actual_sales,
            "revenue": round(revenue, 2),
            "reputation_change": reputation_change
        },
        "status": await get_status()
    }

@app.post("/api/reset")
async def reset_game():
    """Reset the game to initial state"""
    stand.__init__()  # Reset all values
    return {
        "success": True,
        "message": "Game reset to day 1!",
        "status": await get_status()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# THIS IS THE ONLY CHANGE YOU NEED FOR CLOUD RUN
# Remove the old if __name__ == "__main__" block and use this:
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
