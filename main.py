import random
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Lemonade Tycoon Single File", version="1.0.0")

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

# ==========================================
#                GAME STATE
# ==========================================

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

# Initialize Global State
game = GameState()

# ==========================================
#             PYDANTIC MODELS
# ==========================================

class PurchaseRequest(BaseModel):
    item: str
    quantity: int

class PriceUpdate(BaseModel):
    price: float

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
    <title>FastAPI Lemonade Tycoon</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="bg-slate-100 text-slate-800 font-sans min-h-screen" x-data="gameApp()" x-init="init()">

    <!-- TOP BAR -->
    <div class="bg-white shadow-sm sticky top-0 z-50 border-b border-slate-200">
        <div class="max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center gap-2">
                <span class="text-2xl">🍋</span>
                <div>
                    <h1 class="font-bold text-lg leading-tight">Lemonade Tycoon</h1>
                    <div class="text-xs text-slate-500">Day <span x-text="state.day"></span></div>
                </div>
            </div>
            <div class="flex gap-6 text-sm">
                <div class="text-center">
                    <div class="text-[10px] uppercase font-bold text-slate-400">Reputation</div>
                    <div class="font-bold text-purple-600" x-text="state.reputation + '%'"></div>
                </div>
                <div class="text-center bg-green-50 px-3 rounded border border-green-100">
                    <div class="text-[10px] uppercase font-bold text-green-700">Cash</div>
                    <div class="font-bold text-green-600 text-lg" x-text="'$' + state.cash.toFixed(2)"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="max-w-4xl mx-auto p-4 grid grid-cols-1 md:grid-cols-3 gap-6" x-cloak>
        
        <!-- LEFT COLUMN: SUPPLIES & UPGRADES -->
        <div class="md:col-span-2 space-y-6">
            
            <!-- Weather Widget -->
            <div class="bg-blue-600 text-white rounded-xl p-6 flex justify-between items-center shadow-lg relative overflow-hidden">
                <div class="relative z-10">
                    <div class="uppercase text-xs font-bold opacity-75">Current Weather</div>
                    <div class="text-3xl font-bold capitalize flex items-center gap-2">
                        <span x-text="weatherIcons[state.weather]"></span>
                        <span x-text="state.weather"></span>
                    </div>
                    <div class="text-sm mt-1 opacity-90" x-show="state.weather === 'hot'">🔥 Ice sells out fast!</div>
                    <div class="text-sm mt-1 opacity-90" x-show="state.weather === 'rainy'">🌧️ Demand is low.</div>
                </div>
                <div class="text-right relative z-10">
                    <div class="uppercase text-xs font-bold opacity-75">Tomorrow</div>
                    <div class="font-medium capitalize" x-text="state.next_weather"></div>
                </div>
                <!-- Decor -->
                <div class="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-10 -mt-10"></div>
            </div>

            <!-- Inventory Store -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
                <h2 class="font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" /></svg>
                    Supplies
                </h2>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <template x-for="(cost, item) in state.costs" :key="item">
                        <div class="border border-slate-100 rounded-lg p-3 hover:border-yellow-400 transition-colors group">
                            <div class="flex justify-between items-start mb-1">
                                <div class="text-2xl" x-text="itemIcons[item]"></div>
                                <div class="text-xs font-bold text-slate-400" x-text="'x' + state.inventory[item]"></div>
                            </div>
                            <div class="font-bold capitalize text-sm" x-text="item"></div>
                            <div class="text-xs text-slate-500 mb-2" x-text="'$' + cost.toFixed(2) + ' ea'"></div>
                            
                            <div class="flex flex-col gap-1">
                                <button @click="buy(item, 5)" 
                                    :disabled="state.cash < cost * 5"
                                    class="w-full py-1 bg-green-50 text-green-700 text-xs font-bold rounded hover:bg-green-100 disabled:opacity-50">
                                    +5 <span x-text="'($' + (cost*5).toFixed(2) + ')'"></span>
                                </button>
                                <button @click="buy(item, 10)" 
                                    :disabled="state.cash < cost * 10"
                                    class="w-full py-1 bg-slate-50 text-slate-600 text-xs font-bold rounded hover:bg-slate-100 disabled:opacity-50">
                                    +10
                                </button>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Upgrades -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
                <h2 class="font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd" /></svg>
                    Upgrades
                </h2>
                <div class="space-y-3">
                    <template x-for="(lvl, type) in state.upgrades" :key="type">
                        <div class="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-100">
                            <div>
                                <div class="font-bold capitalize text-sm text-slate-700" x-text="type"></div>
                                <div class="text-xs text-slate-500" x-text="state.upgrade_info[type][lvl].name"></div>
                            </div>
                            
                            <!-- Next Upgrade Button -->
                            <div x-data="{ next: state.upgrade_info[type][lvl+1] }">
                                <button x-show="next" 
                                        @click="upgrade(type)"
                                        :disabled="state.cash < next.cost"
                                        class="px-3 py-1.5 bg-slate-800 text-white text-xs font-bold rounded hover:bg-slate-700 disabled:opacity-50 transition-colors flex flex-col items-end">
                                    <span x-text="'Upgrade to ' + next.name"></span>
                                    <span class="text-yellow-400" x-text="'$' + next.cost"></span>
                                </button>
                                <span x-show="!next" class="px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded">MAX LEVEL</span>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- RIGHT COLUMN: STRATEGY -->
        <div class="space-y-6">
            <div class="bg-white rounded-xl shadow-lg border-2 border-yellow-400 p-5 sticky top-24">
                <h2 class="font-bold text-lg mb-4">Daily Strategy</h2>
                
                <div class="mb-6">
                    <div class="flex justify-between items-end mb-2">
                        <label class="text-sm font-bold text-slate-500">Price per Cup</label>
                        <span class="text-2xl font-black text-slate-800" x-text="'$' + state.price.toFixed(2)"></span>
                    </div>
                    <input type="range" min="0.10" max="5.00" step="0.05"
                           x-model.number="state.price"
                           @change="updatePrice()"
                           class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-yellow-500">
                </div>

                <!-- Warnings -->
                <div class="space-y-2 mb-4">
                    <div x-show="state.inventory.lemons < 1" class="text-red-500 text-xs font-bold flex items-center gap-1">⚠️ Out of Lemons!</div>
                    <div x-show="state.inventory.sugar < 1" class="text-red-500 text-xs font-bold flex items-center gap-1">⚠️ Out of Sugar!</div>
                    <div x-show="state.inventory.cups < 1" class="text-red-500 text-xs font-bold flex items-center gap-1">⚠️ Out of Cups!</div>
                    <div x-show="state.weather === 'hot' && state.inventory.ice < 1" class="text-orange-500 text-xs font-bold flex items-center gap-1">🔥 Tip: Buy ice for hot days!</div>
                </div>

                <button @click="startDay()"
                        :disabled="isPlaying"
                        class="w-full py-3 bg-green-500 hover:bg-green-600 text-white font-bold text-lg rounded-xl shadow-lg shadow-green-200 transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
                    <span x-show="!isPlaying">Start Day</span>
                    <span x-show="isPlaying">Serving Customers...</span>
                </button>

                <button @click="resetGame()" class="w-full mt-4 text-xs text-slate-400 underline hover:text-red-500">Reset Game</button>
            </div>
        </div>

    </div>

    <!-- DAY SIMULATION MODAL -->
    <div x-show="showResult" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100]" x-cloak x-transition>
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden p-6">
            <h2 class="text-2xl font-black text-center mb-4 text-slate-800">Day Complete!</h2>
            
            <!-- Animation Canvas / Log -->
            <div class="bg-slate-100 rounded-lg p-4 h-48 overflow-y-auto mb-4 border border-slate-200 font-mono text-xs space-y-1" id="simLog">
                <template x-for="entry in simLog" :key="entry.tick">
                    <div :class="entry.type === 'sale' ? 'text-green-600' : 'text-red-400'" class="flex justify-between">
                        <span x-text="entry.msg"></span>
                        <span x-show="entry.price" x-text="'+$' + entry.price.toFixed(2)"></span>
                    </div>
                </template>
                <div x-show="simLog.length === 0" class="text-center text-slate-400 py-10 italic">Simulating day...</div>
            </div>

            <!-- Summary Stats -->
            <div class="grid grid-cols-2 gap-4 mb-6" x-show="summary">
                <div class="bg-green-50 p-3 rounded-lg text-center">
                    <div class="text-xs font-bold text-green-700">Revenue</div>
                    <div class="text-xl font-bold text-green-600" x-text="'$' + summary?.revenue.toFixed(2)"></div>
                </div>
                <div class="bg-blue-50 p-3 rounded-lg text-center">
                    <div class="text-xs font-bold text-blue-700">Customers</div>
                    <div class="text-xl font-bold text-blue-600" x-text="summary?.sold + ' / ' + (summary?.sold + summary?.missed)"></div>
                </div>
            </div>

            <div class="space-y-2 text-sm text-slate-500 mb-6" x-show="summary">
                <div class="flex justify-between">
                    <span>Ice Melted:</span>
                    <span class="font-bold text-blue-400" x-text="'-' + summary?.melted"></span>
                </div>
                <div class="flex justify-between">
                    <span>Reputation:</span>
                    <span class="font-bold" :class="summary?.rep_change >= 0 ? 'text-green-500' : 'text-red-500'" x-text="(summary?.rep_change > 0 ? '+' : '') + summary?.rep_change"></span>
                </div>
            </div>

            <button @click="showResult = false" class="w-full py-3 bg-slate-800 text-white font-bold rounded-lg hover:bg-slate-700">
                Next Day
            </button>
        </div>
    </div>

    <script>
        function gameApp() {
            return {
                state: {
                    cash: 0, inventory: {}, upgrades: {}, upgrade_info: {juicer:[], stand:[], fridge:[]}, costs: {}, weather: 'sunny'
                },
                isPlaying: false,
                showResult: false,
                simLog: [],
                summary: null,
                
                itemIcons: { lemons: '🍋', sugar: '🧂', cups: '🥤', ice: '🧊' },
                weatherIcons: { sunny: '☀️', cloudy: '☁️', rainy: '🌧️', hot: '🔥' },

                async init() {
                    await this.refreshState();
                },

                async refreshState() {
                    const res = await fetch('/api/state');
                    this.state = await res.json();
                },

                async updatePrice() {
                    await fetch('/api/price', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ price: this.state.price })
                    });
                },

                async buy(item, quantity) {
                    const res = await fetch('/api/buy', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ item, quantity })
                    });
                    const data = await res.json();
                    if(data.success) this.state = data.state;
                    else alert(data.message);
                },

                async upgrade(type) {
                    const res = await fetch('/api/upgrade', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ type })
                    });
                    const data = await res.json();
                    if(data.success) this.state = data.state;
                    else alert(data.message);
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

                    // Animate the log
                    for (const entry of data.log) {
                        await new Promise(r => setTimeout(r, 100)); // Delay for effect
                        this.simLog.push(entry);
                        // Auto scroll
                        this.$nextTick(() => {
                            const el = document.getElementById('simLog');
                            if(el) el.scrollTop = el.scrollHeight;
                        });
                    }

                    await new Promise(r => setTimeout(r, 500));
                    this.summary = data.summary;
                    this.state = data.new_state;
                    this.isPlaying = false;
                },

                async resetGame() {
                    if(!confirm("Reset progress?")) return;
                    await fetch('/api/reset', { method: 'POST' });
                    await this.refreshState();
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
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
