"""Mock Lemonade Stand tool for business simulation scenarios.

A simple but deep business simulation where an AI agent runs a lemonade stand.
Designed for viral "catastrophic failure" moments and user-injectable chaos events.

Game Mechanics:
- Demand is driven by: weather, price, reputation, time of day
- Ice melts in hot weather (resource drain)
- Customers have patience (queue management)
- Quality affects reputation over time
- Random events can disrupt everything
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import random
import math

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class Weather(str, Enum):
    """Weather conditions affecting the stand."""
    SUNNY = "sunny"
    HOT = "hot"  # Heatwave - high demand, ice melts fast
    CLOUDY = "cloudy"
    RAINY = "rainy"  # Low demand
    PERFECT = "perfect"  # Ideal conditions


class TimeOfDay(str, Enum):
    """Time periods affecting customer flow."""
    MORNING = "morning"  # 8am-11am, slow start
    MIDDAY = "midday"  # 11am-2pm, peak lunch rush
    AFTERNOON = "afternoon"  # 2pm-5pm, steady
    EVENING = "evening"  # 5pm-7pm, winding down


@dataclass
class Supplies:
    """Inventory of supplies."""
    cups: int = 0  # Ready-to-sell cups of lemonade
    lemons: int = 0  # Raw lemons
    sugar: int = 0  # Sugar packets
    ice: int = 0  # Ice cubes (melts!)
    cups_empty: int = 0  # Empty cups for serving

    def to_dict(self) -> dict[str, int]:
        return {
            "cups_ready": self.cups,
            "lemons": self.lemons,
            "sugar": self.sugar,
            "ice": self.ice,
            "cups_empty": self.cups_empty,
        }


@dataclass
class CustomerQueue:
    """Customers waiting to be served."""
    count: int = 0
    patience: int = 3  # Turns before they leave
    vip: bool = False  # Special customer (influencer, critic, etc.)
    vip_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "waiting": self.count,
            "patience_remaining": self.patience,
        }
        if self.vip:
            result["special_customer"] = self.vip_type
        return result


@dataclass
class Statistics:
    """Running statistics for the stand."""
    customers_served: int = 0
    customers_lost: int = 0  # Left due to no stock or impatience
    revenue: float = 0.0
    costs: float = 0.0
    cups_sold: int = 0
    peak_queue: int = 0
    reputation: float = 50.0  # 0-100 scale

    @property
    def profit(self) -> float:
        return self.revenue - self.costs

    def to_dict(self) -> dict[str, Any]:
        return {
            "customers_served": self.customers_served,
            "customers_lost": self.customers_lost,
            "cups_sold": self.cups_sold,
            "revenue": round(self.revenue, 2),
            "costs": round(self.costs, 2),
            "profit": round(self.profit, 2),
            "reputation": round(self.reputation, 1),
            "peak_queue": self.peak_queue,
        }


@dataclass
class GameState:
    """Complete game state for the lemonade stand."""
    cash: float = 50.0
    supplies: Supplies = field(default_factory=Supplies)
    price_per_cup: float = 2.0
    weather: Weather = Weather.SUNNY
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    turn: int = 1
    day: int = 1
    queue: CustomerQueue = field(default_factory=CustomerQueue)
    stats: Statistics = field(default_factory=Statistics)
    is_open: bool = True
    events_today: list[str] = field(default_factory=list)
    # Recipe quality (affects taste and reputation)
    recipe_lemons: int = 2  # Lemons per batch
    recipe_sugar: int = 2  # Sugar per batch
    recipe_ice: int = 4  # Ice per cup served
    cups_per_batch: int = 4  # Cups produced per batch


# Supply costs (what the agent pays to restock)
SUPPLY_COSTS = {
    "lemons": 0.50,  # per lemon
    "sugar": 0.25,  # per packet
    "ice": 0.10,  # per 10 cubes
    "cups_empty": 0.15,  # per cup
}

# Weather multipliers for demand
WEATHER_DEMAND = {
    Weather.HOT: 2.5,
    Weather.SUNNY: 1.5,
    Weather.PERFECT: 2.0,
    Weather.CLOUDY: 0.8,
    Weather.RAINY: 0.3,
}

# Weather multipliers for ice melt
WEATHER_ICE_MELT = {
    Weather.HOT: 0.3,  # Lose 30% of ice per turn
    Weather.SUNNY: 0.1,
    Weather.PERFECT: 0.05,
    Weather.CLOUDY: 0.02,
    Weather.RAINY: 0.0,
}

# Time of day multipliers
TIME_DEMAND = {
    TimeOfDay.MORNING: 0.6,
    TimeOfDay.MIDDAY: 1.5,
    TimeOfDay.AFTERNOON: 1.0,
    TimeOfDay.EVENING: 0.4,
}


class MockLemonadeTool(BaseTool):
    """Mock lemonade stand for business simulation scenarios.

    This tool simulates running a lemonade stand with:
    - Inventory management (lemons, sugar, ice, cups)
    - Dynamic pricing
    - Weather and time-based demand
    - Customer queue management
    - Reputation system
    - Random/injected events
    """

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)

        # Initialize game state from config
        self.state = GameState(
            cash=float(self.config.get("starting_cash", 50.0)),
            price_per_cup=float(self.config.get("starting_price", 2.0)),
        )

        # Set initial supplies
        initial_supplies = self.config.get("initial_supplies", {})
        self.state.supplies = Supplies(
            cups=int(initial_supplies.get("cups_ready", 0)),
            lemons=int(initial_supplies.get("lemons", 20)),
            sugar=int(initial_supplies.get("sugar", 20)),
            ice=int(initial_supplies.get("ice", 50)),
            cups_empty=int(initial_supplies.get("cups_empty", 30)),
        )

        # Difficulty affects base demand and event frequency
        self.difficulty = int(self.config.get("difficulty", 5))

        # Random seed for reproducibility
        seed = self.config.get("seed")
        if seed is not None:
            random.seed(int(seed))

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle lemonade stand actions."""
        handlers = {
            # Information actions
            "check_status": self._check_status,
            "check_inventory": self._check_inventory,
            "check_customers": self._check_customers,

            # Business actions
            "set_price": self._set_price,
            "make_lemonade": self._make_lemonade,
            "serve_customers": self._serve_customers,
            "buy_supplies": self._buy_supplies,

            # Advanced actions
            "adjust_recipe": self._adjust_recipe,
            "close_stand": self._close_stand,
            "open_stand": self._open_stand,

            # Event injection (called by system, not agent)
            "trigger_event": self._trigger_event,
            "advance_time": self._advance_time,
        }

        handler = handlers.get(action)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        result = handler(args, env_state)

        # Sync cash to env_state for evaluation
        env_state["cash_balance"] = self.state.cash
        env_state["lemonade_stats"] = self.state.stats.to_dict()

        return result

    def _check_status(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get overall status of the lemonade stand."""
        status = {
            "cash": round(self.state.cash, 2),
            "price_per_cup": self.state.price_per_cup,
            "weather": self.state.weather.value,
            "time": self.state.time_of_day.value,
            "day": self.state.day,
            "turn": self.state.turn,
            "is_open": self.state.is_open,
            "inventory": self.state.supplies.to_dict(),
            "customers": self.state.queue.to_dict(),
            "stats": self.state.stats.to_dict(),
            "events_today": self.state.events_today,
        }

        # Add contextual advice based on situation
        warnings = []
        if self.state.supplies.cups == 0 and self.state.queue.count > 0:
            warnings.append("No lemonade ready! Customers are waiting!")
        if self.state.supplies.ice < 10:
            warnings.append("Ice is running low!")
        if self.state.weather == Weather.HOT and self.state.supplies.ice > 0:
            warnings.append("Hot weather - ice is melting fast!")
        if self.state.queue.patience <= 1:
            warnings.append("Customers are getting impatient!")

        if warnings:
            status["warnings"] = warnings

        return ToolResult(success=True, data=status)

    def _check_inventory(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get detailed inventory information."""
        inventory = self.state.supplies.to_dict()

        # Add production capacity info
        s = self.state.supplies
        r = self.state
        batches_possible = min(
            s.lemons // r.recipe_lemons if r.recipe_lemons > 0 else 999,
            s.sugar // r.recipe_sugar if r.recipe_sugar > 0 else 999,
            s.cups_empty // r.cups_per_batch if r.cups_per_batch > 0 else 999,
        )

        inventory["batches_can_make"] = batches_possible
        inventory["cups_per_batch"] = r.cups_per_batch
        inventory["recipe"] = {
            "lemons_per_batch": r.recipe_lemons,
            "sugar_per_batch": r.recipe_sugar,
            "ice_per_cup": r.recipe_ice,
        }
        inventory["supply_costs"] = SUPPLY_COSTS

        return ToolResult(success=True, data=inventory)

    def _check_customers(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Check customer queue and demand forecast."""
        queue_info = self.state.queue.to_dict()

        # Calculate current demand multiplier
        weather_mult = WEATHER_DEMAND.get(self.state.weather, 1.0)
        time_mult = TIME_DEMAND.get(self.state.time_of_day, 1.0)
        price_mult = max(0.1, 2.0 - (self.state.price_per_cup / 3.0))  # Higher price = lower demand
        rep_mult = self.state.stats.reputation / 50.0  # 50 rep = 1.0x, 100 rep = 2.0x

        queue_info["demand_forecast"] = {
            "weather_effect": f"{weather_mult:.1f}x ({self.state.weather.value})",
            "time_effect": f"{time_mult:.1f}x ({self.state.time_of_day.value})",
            "price_effect": f"{price_mult:.1f}x (${self.state.price_per_cup})",
            "reputation_effect": f"{rep_mult:.1f}x ({self.state.stats.reputation:.0f}/100)",
            "combined_multiplier": round(weather_mult * time_mult * price_mult * rep_mult, 2),
        }

        return ToolResult(success=True, data=queue_info)

    def _set_price(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Set the price per cup of lemonade."""
        new_price = args.get("price")
        if new_price is None:
            return ToolResult(success=False, error="price is required")

        try:
            new_price = float(new_price)
        except (ValueError, TypeError):
            return ToolResult(success=False, error="price must be a number")

        if new_price < 0:
            return ToolResult(success=False, error="price cannot be negative")
        if new_price > 100:
            return ToolResult(success=False, error="price cannot exceed $100 (be reasonable!)")

        old_price = self.state.price_per_cup
        self.state.price_per_cup = round(new_price, 2)

        # Extreme prices affect reputation
        message = f"Price changed from ${old_price:.2f} to ${new_price:.2f}"
        if new_price > 10:
            self.state.stats.reputation = max(0, self.state.stats.reputation - 5)
            message += " (Warning: High prices may hurt reputation)"
        elif new_price < 0.5 and new_price > 0:
            message += " (Very low price - good for attracting customers!)"
        elif new_price == 0:
            message += " (Free lemonade! Customers will love it, but you won't make money)"

        return ToolResult(success=True, data={"message": message, "new_price": new_price})

    def _make_lemonade(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Make batches of lemonade from supplies."""
        batches = args.get("batches", 1)

        try:
            batches = int(batches)
        except (ValueError, TypeError):
            return ToolResult(success=False, error="batches must be a number")

        if batches < 1:
            return ToolResult(success=False, error="must make at least 1 batch")

        s = self.state.supplies
        r = self.state

        # Check if we have enough supplies
        lemons_needed = batches * r.recipe_lemons
        sugar_needed = batches * r.recipe_sugar
        cups_needed = batches * r.cups_per_batch

        if s.lemons < lemons_needed:
            return ToolResult(
                success=False,
                error=f"Not enough lemons! Need {lemons_needed}, have {s.lemons}"
            )
        if s.sugar < sugar_needed:
            return ToolResult(
                success=False,
                error=f"Not enough sugar! Need {sugar_needed}, have {s.sugar}"
            )
        if s.cups_empty < cups_needed:
            return ToolResult(
                success=False,
                error=f"Not enough empty cups! Need {cups_needed}, have {s.cups_empty}"
            )

        # Make the lemonade
        s.lemons -= lemons_needed
        s.sugar -= sugar_needed
        s.cups_empty -= cups_needed
        cups_made = batches * r.cups_per_batch
        s.cups += cups_made

        return ToolResult(
            success=True,
            data={
                "batches_made": batches,
                "cups_made": cups_made,
                "cups_ready": s.cups,
                "supplies_remaining": s.to_dict(),
            }
        )

    def _serve_customers(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Serve waiting customers."""
        if not self.state.is_open:
            return ToolResult(success=False, error="Stand is closed! Open it first.")

        max_serve = args.get("count", self.state.queue.count)
        try:
            max_serve = int(max_serve)
        except (ValueError, TypeError):
            max_serve = self.state.queue.count

        queue = self.state.queue
        supplies = self.state.supplies
        stats = self.state.stats

        if queue.count == 0:
            return ToolResult(success=True, data={"message": "No customers waiting", "served": 0})

        customers_to_serve = min(max_serve, queue.count, supplies.cups)

        if customers_to_serve == 0 and queue.count > 0:
            # Customers waiting but no lemonade!
            lost = queue.count
            queue.count = 0
            stats.customers_lost += lost
            stats.reputation = max(0, stats.reputation - (lost * 2))
            return ToolResult(
                success=False,
                error=f"No lemonade to serve! {lost} customers left angry. Reputation dropped!"
            )

        # Check ice for serving
        ice_needed = customers_to_serve * self.state.recipe_ice
        ice_available = min(ice_needed, supplies.ice)

        # Serve customers
        revenue = customers_to_serve * self.state.price_per_cup
        supplies.cups -= customers_to_serve
        supplies.ice -= ice_available
        queue.count -= customers_to_serve

        self.state.cash += revenue
        stats.revenue += revenue
        stats.customers_served += customers_to_serve
        stats.cups_sold += customers_to_serve

        # Ice affects quality/reputation
        if ice_available < ice_needed:
            # Warm lemonade! Reputation hit
            stats.reputation = max(0, stats.reputation - 3)
            ice_message = "Some customers got warm lemonade (no ice). Reputation dropped slightly."
        else:
            # Good service
            stats.reputation = min(100, stats.reputation + 0.5)
            ice_message = None

        # VIP customer bonus
        vip_message = None
        if queue.vip and customers_to_serve > 0:
            if queue.vip_type == "influencer":
                stats.reputation = min(100, stats.reputation + 10)
                vip_message = "An influencer loved your lemonade! +10 reputation!"
            elif queue.vip_type == "food_critic":
                if ice_available >= ice_needed and self.state.price_per_cup <= 5:
                    stats.reputation = min(100, stats.reputation + 15)
                    vip_message = "Food critic gave you a great review! +15 reputation!"
                else:
                    stats.reputation = max(0, stats.reputation - 10)
                    vip_message = "Food critic was not impressed. -10 reputation."
            queue.vip = False
            queue.vip_type = None

        result = {
            "served": customers_to_serve,
            "revenue": round(revenue, 2),
            "cash": round(self.state.cash, 2),
            "cups_remaining": supplies.cups,
            "customers_still_waiting": queue.count,
        }

        messages = []
        if ice_message:
            messages.append(ice_message)
        if vip_message:
            messages.append(vip_message)
        if messages:
            result["notes"] = messages

        return ToolResult(success=True, data=result)

    def _buy_supplies(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Buy supplies for the stand."""
        supplies_to_buy = {}
        total_cost = 0.0

        for supply, cost_per in SUPPLY_COSTS.items():
            amount = args.get(supply, 0)
            if amount:
                try:
                    amount = int(amount)
                    if amount < 0:
                        return ToolResult(success=False, error=f"Cannot buy negative {supply}")
                    supplies_to_buy[supply] = amount
                    # Ice is sold in bags of 10
                    if supply == "ice":
                        total_cost += (amount // 10) * cost_per * 10
                    else:
                        total_cost += amount * cost_per
                except (ValueError, TypeError):
                    return ToolResult(success=False, error=f"Invalid amount for {supply}")

        if not supplies_to_buy:
            return ToolResult(
                success=False,
                error=f"Specify supplies to buy. Available: {list(SUPPLY_COSTS.keys())}. Costs: {SUPPLY_COSTS}"
            )

        if total_cost > self.state.cash:
            return ToolResult(
                success=False,
                error=f"Not enough cash! Need ${total_cost:.2f}, have ${self.state.cash:.2f}"
            )

        # Process purchase
        self.state.cash -= total_cost
        self.state.stats.costs += total_cost

        s = self.state.supplies
        for supply, amount in supplies_to_buy.items():
            if supply == "lemons":
                s.lemons += amount
            elif supply == "sugar":
                s.sugar += amount
            elif supply == "ice":
                s.ice += amount
            elif supply == "cups_empty":
                s.cups_empty += amount

        return ToolResult(
            success=True,
            data={
                "purchased": supplies_to_buy,
                "total_cost": round(total_cost, 2),
                "cash_remaining": round(self.state.cash, 2),
                "inventory": s.to_dict(),
            }
        )

    def _adjust_recipe(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Adjust the lemonade recipe."""
        changes = {}

        if "lemons_per_batch" in args:
            val = int(args["lemons_per_batch"])
            if val < 1 or val > 10:
                return ToolResult(success=False, error="lemons_per_batch must be 1-10")
            self.state.recipe_lemons = val
            changes["lemons_per_batch"] = val

        if "sugar_per_batch" in args:
            val = int(args["sugar_per_batch"])
            if val < 0 or val > 10:
                return ToolResult(success=False, error="sugar_per_batch must be 0-10")
            self.state.recipe_sugar = val
            changes["sugar_per_batch"] = val

        if "ice_per_cup" in args:
            val = int(args["ice_per_cup"])
            if val < 0 or val > 10:
                return ToolResult(success=False, error="ice_per_cup must be 0-10")
            self.state.recipe_ice = val
            changes["ice_per_cup"] = val

        if not changes:
            return ToolResult(
                success=True,
                data={
                    "current_recipe": {
                        "lemons_per_batch": self.state.recipe_lemons,
                        "sugar_per_batch": self.state.recipe_sugar,
                        "ice_per_cup": self.state.recipe_ice,
                        "cups_per_batch": self.state.cups_per_batch,
                    }
                }
            )

        # Recipe quality affects reputation over time
        quality_score = (self.state.recipe_lemons * 2 + self.state.recipe_sugar) / 6
        quality_msg = "balanced" if 0.8 <= quality_score <= 1.2 else (
            "too sour" if quality_score > 1.2 else "too sweet"
        )

        return ToolResult(
            success=True,
            data={
                "changes": changes,
                "quality_assessment": quality_msg,
                "note": "Recipe affects taste and reputation over time",
            }
        )

    def _close_stand(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Close the stand (stop accepting customers)."""
        if not self.state.is_open:
            return ToolResult(success=False, error="Stand is already closed")

        self.state.is_open = False

        # Remaining customers leave
        lost = self.state.queue.count
        self.state.queue.count = 0
        self.state.stats.customers_lost += lost

        return ToolResult(
            success=True,
            data={
                "message": "Stand closed for the day",
                "customers_turned_away": lost,
                "final_stats": self.state.stats.to_dict(),
            }
        )

    def _open_stand(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Open the stand (start accepting customers)."""
        if self.state.is_open:
            return ToolResult(success=False, error="Stand is already open")

        self.state.is_open = True
        return ToolResult(success=True, data={"message": "Stand is now open for business!"})

    def _trigger_event(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Trigger a game event (usually called by system, not agent).

        This is the key method for chaos injection from the frontend.
        """
        event_type = args.get("event")
        if not event_type:
            return ToolResult(success=False, error="event type is required")

        event_handlers = {
            # Weather events
            "heatwave": self._event_heatwave,
            "rain": self._event_rain,
            "perfect_weather": self._event_perfect_weather,

            # Customer events
            "rush_hour": self._event_rush_hour,
            "slow_period": self._event_slow_period,
            "influencer": self._event_influencer,
            "food_critic": self._event_food_critic,
            "kid_birthday_party": self._event_birthday_party,

            # Disaster events
            "health_inspector": self._event_health_inspector,
            "competitor": self._event_competitor,
            "supply_truck": self._event_supply_truck,
            "ice_melted": self._event_ice_melted,
            "spill": self._event_spill,

            # Opportunity events
            "tip_jar": self._event_tip_jar,
            "bulk_order": self._event_bulk_order,
        }

        handler = event_handlers.get(event_type)
        if handler is None:
            return ToolResult(
                success=False,
                error=f"Unknown event: {event_type}. Available: {list(event_handlers.keys())}"
            )

        result = handler(args)
        self.state.events_today.append(event_type)
        return result

    def _advance_time(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Advance time (generates customers, melts ice, etc.)."""
        # Ice melting
        melt_rate = WEATHER_ICE_MELT.get(self.state.weather, 0.05)
        ice_lost = int(self.state.supplies.ice * melt_rate)
        self.state.supplies.ice = max(0, self.state.supplies.ice - ice_lost)

        # Generate new customers based on demand
        if self.state.is_open:
            base_customers = random.randint(1, 3 + self.difficulty)
            weather_mult = WEATHER_DEMAND.get(self.state.weather, 1.0)
            time_mult = TIME_DEMAND.get(self.state.time_of_day, 1.0)
            price_mult = max(0.1, 2.0 - (self.state.price_per_cup / 3.0))
            rep_mult = self.state.stats.reputation / 50.0

            new_customers = int(base_customers * weather_mult * time_mult * price_mult * rep_mult)
            new_customers = max(0, new_customers)
            self.state.queue.count += new_customers
            self.state.queue.patience = 3  # Reset patience for new arrivals

            if self.state.queue.count > self.state.stats.peak_queue:
                self.state.stats.peak_queue = self.state.queue.count
        else:
            new_customers = 0

        # Patience decreases for waiting customers
        if self.state.queue.count > 0:
            self.state.queue.patience -= 1
            if self.state.queue.patience <= 0:
                # Customers leave
                lost = self.state.queue.count
                self.state.queue.count = 0
                self.state.queue.patience = 3
                self.state.stats.customers_lost += lost
                self.state.stats.reputation = max(0, self.state.stats.reputation - lost)

        # Advance turn
        self.state.turn += 1

        # Advance time of day every 3 turns
        if self.state.turn % 3 == 0:
            times = list(TimeOfDay)
            current_idx = times.index(self.state.time_of_day)
            if current_idx < len(times) - 1:
                self.state.time_of_day = times[current_idx + 1]
            else:
                # End of day
                self.state.day += 1
                self.state.time_of_day = TimeOfDay.MORNING
                self.state.events_today = []

        return ToolResult(
            success=True,
            data={
                "turn": self.state.turn,
                "time": self.state.time_of_day.value,
                "day": self.state.day,
                "new_customers": new_customers,
                "ice_melted": ice_lost,
                "queue": self.state.queue.to_dict(),
            }
        )

    # ============ Event Implementations ============

    def _event_heatwave(self, args: dict[str, Any]) -> ToolResult:
        """Heatwave! High demand, ice melts fast."""
        self.state.weather = Weather.HOT
        ice_lost = int(self.state.supplies.ice * 0.2)
        self.state.supplies.ice = max(0, self.state.supplies.ice - ice_lost)

        # Surge of customers
        surge = random.randint(3, 8)
        self.state.queue.count += surge

        return ToolResult(
            success=True,
            data={
                "event": "HEATWAVE",
                "message": f"A heatwave hits! Temperature soars to 105°F. {surge} thirsty customers rush over!",
                "effects": {
                    "weather": "hot",
                    "new_customers": surge,
                    "ice_melted": ice_lost,
                    "demand_multiplier": "2.5x",
                },
                "warning": "Ice will melt faster! Stock up or serve quickly!",
            }
        )

    def _event_rain(self, args: dict[str, Any]) -> ToolResult:
        """Rain! Low demand."""
        self.state.weather = Weather.RAINY

        # Some customers leave
        left = min(self.state.queue.count, random.randint(1, 3))
        self.state.queue.count -= left

        return ToolResult(
            success=True,
            data={
                "event": "RAIN",
                "message": f"It starts raining! {left} customers leave to find shelter.",
                "effects": {
                    "weather": "rainy",
                    "customers_left": left,
                    "demand_multiplier": "0.3x",
                },
                "silver_lining": "At least your ice won't melt!",
            }
        )

    def _event_perfect_weather(self, args: dict[str, Any]) -> ToolResult:
        """Perfect weather! Great for business."""
        self.state.weather = Weather.PERFECT
        return ToolResult(
            success=True,
            data={
                "event": "PERFECT WEATHER",
                "message": "Beautiful day! 75°F with a light breeze. Perfect lemonade weather!",
                "effects": {
                    "weather": "perfect",
                    "demand_multiplier": "2.0x",
                },
            }
        )

    def _event_rush_hour(self, args: dict[str, Any]) -> ToolResult:
        """Rush hour! Lots of customers at once."""
        surge = random.randint(5, 12)
        self.state.queue.count += surge

        return ToolResult(
            success=True,
            data={
                "event": "RUSH HOUR",
                "message": f"A crowd of {surge} people suddenly arrives! They all want lemonade!",
                "effects": {"new_customers": surge},
                "warning": "Serve them quickly or they'll leave!",
            }
        )

    def _event_slow_period(self, args: dict[str, Any]) -> ToolResult:
        """Slow period - good time to prepare."""
        self.state.queue.count = 0
        self.state.queue.patience = 3

        return ToolResult(
            success=True,
            data={
                "event": "SLOW PERIOD",
                "message": "Business has slowed down. No customers at the moment.",
                "opportunity": "Good time to make more lemonade or restock supplies!",
            }
        )

    def _event_influencer(self, args: dict[str, Any]) -> ToolResult:
        """An influencer arrives!"""
        self.state.queue.count += 1
        self.state.queue.vip = True
        self.state.queue.vip_type = "influencer"

        return ToolResult(
            success=True,
            data={
                "event": "INFLUENCER SPOTTED",
                "message": "A local influencer with 100k followers just walked up! They're filming!",
                "stakes": "Serve them well for a reputation boost! Mess up and it goes viral (badly).",
            }
        )

    def _event_food_critic(self, args: dict[str, Any]) -> ToolResult:
        """A food critic arrives!"""
        self.state.queue.count += 1
        self.state.queue.vip = True
        self.state.queue.vip_type = "food_critic"

        return ToolResult(
            success=True,
            data={
                "event": "FOOD CRITIC",
                "message": "A food critic from the local newspaper is here to review your stand!",
                "stakes": "Quality and price matter! A good review = major reputation boost.",
            }
        )

    def _event_birthday_party(self, args: dict[str, Any]) -> ToolResult:
        """A kid's birthday party wants bulk order."""
        party_size = random.randint(8, 15)
        self.state.queue.count += party_size

        return ToolResult(
            success=True,
            data={
                "event": "BIRTHDAY PARTY",
                "message": f"A birthday party of {party_size} kids wants lemonade for everyone!",
                "opportunity": "Big sale opportunity! Make sure you have enough cups ready.",
            }
        )

    def _event_health_inspector(self, args: dict[str, Any]) -> ToolResult:
        """Health inspector arrives!"""
        # Check cleanliness (simplified: based on supplies organization)
        issues = []
        if self.state.supplies.ice < 5:
            issues.append("Insufficient ice storage")
        if self.state.stats.reputation < 30:
            issues.append("Multiple customer complaints on file")

        if issues:
            fine = 20.0 * len(issues)
            self.state.cash -= fine
            self.state.stats.costs += fine
            self.state.is_open = False

            return ToolResult(
                success=True,
                data={
                    "event": "HEALTH INSPECTOR - FAILED",
                    "message": f"Health inspector found violations! Fined ${fine:.2f}. Stand closed temporarily.",
                    "violations": issues,
                    "action_required": "Fix issues and reopen the stand.",
                }
            )
        else:
            self.state.stats.reputation = min(100, self.state.stats.reputation + 5)
            return ToolResult(
                success=True,
                data={
                    "event": "HEALTH INSPECTOR - PASSED",
                    "message": "Health inspector approved! Everything looks good. +5 reputation!",
                }
            )

    def _event_competitor(self, args: dict[str, Any]) -> ToolResult:
        """Competitor opens nearby!"""
        competitor_price = round(self.state.price_per_cup * random.uniform(0.5, 0.9), 2)

        # Lose some customers
        lost = min(self.state.queue.count, random.randint(2, 5))
        self.state.queue.count -= lost

        return ToolResult(
            success=True,
            data={
                "event": "COMPETITOR",
                "message": f"A competitor just opened across the street! They're selling lemonade for ${competitor_price}!",
                "effects": {
                    "customers_lost": lost,
                    "competitor_price": competitor_price,
                },
                "advice": "Consider adjusting your price or emphasizing quality!",
            }
        )

    def _event_supply_truck(self, args: dict[str, Any]) -> ToolResult:
        """Supply truck offers discount!"""
        discount = random.randint(20, 50)

        return ToolResult(
            success=True,
            data={
                "event": "SUPPLY TRUCK",
                "message": f"A supply truck is offering {discount}% off bulk supplies! Limited time!",
                "deal": {
                    "discount_percent": discount,
                    "discounted_costs": {k: round(v * (1 - discount/100), 2) for k, v in SUPPLY_COSTS.items()},
                },
                "note": "This is a limited-time event. Buy now or miss out!",
            }
        )

    def _event_ice_melted(self, args: dict[str, Any]) -> ToolResult:
        """Ice machine breaks / all ice melts!"""
        ice_lost = self.state.supplies.ice
        self.state.supplies.ice = 0

        return ToolResult(
            success=True,
            data={
                "event": "ICE DISASTER",
                "message": f"Oh no! Your ice cooler broke and all {ice_lost} ice cubes melted!",
                "effects": {"ice_lost": ice_lost},
                "urgent": "You need to buy more ice immediately or serve warm lemonade!",
            }
        )

    def _event_spill(self, args: dict[str, Any]) -> ToolResult:
        """Accident - some lemonade spills!"""
        cups_lost = min(self.state.supplies.cups, random.randint(2, 6))
        self.state.supplies.cups -= cups_lost

        return ToolResult(
            success=True,
            data={
                "event": "SPILL",
                "message": f"Oops! You accidentally knocked over {cups_lost} cups of lemonade!",
                "effects": {"cups_lost": cups_lost, "cups_remaining": self.state.supplies.cups},
            }
        )

    def _event_tip_jar(self, args: dict[str, Any]) -> ToolResult:
        """Someone leaves a big tip!"""
        tip = round(random.uniform(5, 20), 2)
        self.state.cash += tip
        self.state.stats.revenue += tip

        return ToolResult(
            success=True,
            data={
                "event": "BIG TIP",
                "message": f"A generous customer left a ${tip:.2f} tip! 'Keep up the great work!'",
                "effects": {"tip_received": tip, "new_cash": round(self.state.cash, 2)},
            }
        )

    def _event_bulk_order(self, args: dict[str, Any]) -> ToolResult:
        """Office wants to place a bulk order."""
        cups_wanted = random.randint(15, 30)

        return ToolResult(
            success=True,
            data={
                "event": "BULK ORDER REQUEST",
                "message": f"An office nearby wants to order {cups_wanted} cups for their meeting!",
                "request": {
                    "cups_wanted": cups_wanted,
                    "potential_revenue": round(cups_wanted * self.state.price_per_cup, 2),
                },
                "note": "You need enough cups ready to fulfill this order!",
            }
        )

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available lemonade stand actions for the agent."""
        return [
            {
                "name": "check_status",
                "description": "Get overall status of your lemonade stand (cash, inventory, customers, weather)",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "check_inventory",
                "description": "Get detailed inventory and see how many batches you can make",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "check_customers",
                "description": "Check customer queue and demand forecast",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "set_price",
                "description": "Set the price per cup of lemonade",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "New price per cup in dollars"},
                    },
                    "required": ["price"],
                },
            },
            {
                "name": "make_lemonade",
                "description": "Make batches of lemonade from supplies (lemons + sugar + empty cups → ready cups)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batches": {"type": "integer", "description": "Number of batches to make (default: 1)", "default": 1},
                    },
                },
            },
            {
                "name": "serve_customers",
                "description": "Serve waiting customers (requires ready cups and ice)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Max customers to serve (default: all waiting)"},
                    },
                },
            },
            {
                "name": "buy_supplies",
                "description": "Buy supplies: lemons ($0.50), sugar ($0.25), ice ($0.10/10), cups_empty ($0.15)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lemons": {"type": "integer", "description": "Number of lemons to buy"},
                        "sugar": {"type": "integer", "description": "Sugar packets to buy"},
                        "ice": {"type": "integer", "description": "Ice cubes to buy (sold in 10s)"},
                        "cups_empty": {"type": "integer", "description": "Empty cups to buy"},
                    },
                },
            },
            {
                "name": "adjust_recipe",
                "description": "Adjust lemonade recipe (affects taste and resource usage)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lemons_per_batch": {"type": "integer", "description": "Lemons per batch (1-10)"},
                        "sugar_per_batch": {"type": "integer", "description": "Sugar per batch (0-10)"},
                        "ice_per_cup": {"type": "integer", "description": "Ice per cup served (0-10)"},
                    },
                },
            },
            {
                "name": "close_stand",
                "description": "Close the stand for the day",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "open_stand",
                "description": "Open the stand for business",
                "parameters": {"type": "object", "properties": {}},
            },
        ]
