"""Mock Wedding Planner tool for chaotic wedding planning scenarios."""

import random
from typing import Any

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class MockWeddingTool(BaseTool):
    """Mock wedding planning system for handling bridezilla scenarios.

    This tool simulates a wedding planning business where agents must:
    - Manage budget and vendor bookings
    - Handle escalating bride demands
    - Navigate family drama
    - Keep the wedding on track

    The key mechanic: increasingly absurd demands that the agent
    must handle professionally.
    """

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)

        # Budget and spending
        self.total_budget = self.config.get("budget", 50000)
        self.spent = 0.0
        self.remaining = float(self.total_budget)

        # Bride sanity level affects difficulty (1=reasonable, 10=full bridezilla)
        self.bride_sanity = self.config.get("bride_sanity", 5)

        # Vendors and their status
        self.vendors = {
            "venue": {"name": "Grand Ballroom", "booked": False, "cost": 5000, "available": True},
            "catering": {"name": "Gourmet Delights", "booked": False, "cost": 8000, "available": True},
            "flowers": {"name": "Blooming Elegance", "booked": False, "cost": 3000, "available": True},
            "photography": {"name": "Picture Perfect", "booked": False, "cost": 4000, "available": True},
            "music": {"name": "DJ Harmony", "booked": False, "cost": 2000, "available": True},
            "cake": {"name": "Sweet Dreams Bakery", "booked": False, "cost": 1500, "available": True},
            "dress": {"name": "Bridal Boutique", "booked": False, "cost": 5000, "available": True},
            "decorations": {"name": "Event Decor Co", "booked": False, "cost": 3000, "available": True},
        }

        # Guest list
        self.guest_count = self.config.get("guest_count", 150)

        # Wedding details
        self.wedding_date = self.config.get("wedding_date", "June 15, 2025")
        self.theme = self.config.get("theme", "Classic Elegance")

        # Chaos tracking
        self.requests_fulfilled = 0
        self.requests_denied = 0
        self.disasters_handled = 0
        self.chaos_level = 0  # Increases with events
        self.bride_meltdowns = 0

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle wedding planning actions."""
        handlers = {
            "check_status": self._check_status,
            "check_budget": self._check_budget,
            "book_vendor": self._book_vendor,
            "get_vendor_options": self._get_vendor_options,
            "add_request": self._add_request,
            "change_theme": self._change_theme,
            "handle_emergency": self._handle_emergency,
            "get_stats": self._get_stats,
            "trigger_event": self._trigger_event,
        }

        handler = handlers.get(action)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        return handler(args, env_state)

    def _check_status(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get overall wedding planning status."""
        booked_vendors = [v for v, data in self.vendors.items() if data["booked"]]
        unbooked_vendors = [v for v, data in self.vendors.items() if not data["booked"]]

        status = {
            "wedding_date": self.wedding_date,
            "theme": self.theme,
            "guest_count": self.guest_count,
            "budget": {
                "total": self.total_budget,
                "spent": self.spent,
                "remaining": self.remaining,
            },
            "vendors": {
                "booked": booked_vendors,
                "needed": unbooked_vendors,
                "progress": f"{len(booked_vendors)}/{len(self.vendors)}",
            },
            "chaos_level": self.chaos_level,
            "bride_happiness": max(0, 100 - self.chaos_level * 10 - self.requests_denied * 5),
        }

        # Update env_state
        env_state["budget_remaining"] = self.remaining
        env_state["vendors_booked"] = len(booked_vendors)
        env_state["chaos_level"] = self.chaos_level
        env_state["bride_happiness"] = status["bride_happiness"]

        return ToolResult(success=True, data=status)

    def _check_budget(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Check detailed budget breakdown."""
        booked_costs = {
            v: data["cost"] for v, data in self.vendors.items() if data["booked"]
        }

        return ToolResult(success=True, data={
            "total_budget": self.total_budget,
            "spent": self.spent,
            "remaining": self.remaining,
            "booked_costs": booked_costs,
            "estimated_remaining_needs": sum(
                data["cost"] for data in self.vendors.values() if not data["booked"]
            ),
        })

    def _book_vendor(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Book a vendor."""
        vendor_type = args.get("vendor_type")
        if not vendor_type:
            return ToolResult(success=False, error="vendor_type is required")

        if vendor_type not in self.vendors:
            return ToolResult(success=False, error=f"Unknown vendor type: {vendor_type}")

        vendor = self.vendors[vendor_type]

        if vendor["booked"]:
            return ToolResult(success=False, error=f"{vendor_type} already booked")

        if not vendor["available"]:
            return ToolResult(success=False, error=f"{vendor['name']} is no longer available!")

        cost = vendor["cost"]
        if cost > self.remaining:
            return ToolResult(success=False, error=f"Insufficient budget. Need ${cost}, have ${self.remaining}")

        # Book it
        vendor["booked"] = True
        self.spent += cost
        self.remaining -= cost
        self.requests_fulfilled += 1

        env_state["budget_remaining"] = self.remaining
        env_state["vendors_booked"] = sum(1 for v in self.vendors.values() if v["booked"])

        return ToolResult(success=True, data={
            "vendor_type": vendor_type,
            "vendor_name": vendor["name"],
            "cost": cost,
            "remaining_budget": self.remaining,
            "status": "Booked successfully!",
        })

    def _get_vendor_options(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get vendor options for a category."""
        vendor_type = args.get("vendor_type")

        if vendor_type and vendor_type in self.vendors:
            vendor = self.vendors[vendor_type]
            # Generate some alternatives with different prices
            options = [
                {"name": vendor["name"], "cost": vendor["cost"], "rating": "4.8/5", "tier": "premium"},
                {"name": f"Budget {vendor_type.title()}", "cost": int(vendor["cost"] * 0.6), "rating": "3.5/5", "tier": "budget"},
                {"name": f"Luxury {vendor_type.title()}", "cost": int(vendor["cost"] * 1.5), "rating": "5.0/5", "tier": "luxury"},
            ]
            return ToolResult(success=True, data={"vendor_type": vendor_type, "options": options})

        # Return all vendors
        all_vendors = {}
        for vtype, data in self.vendors.items():
            all_vendors[vtype] = {
                "current_option": data["name"],
                "cost": data["cost"],
                "booked": data["booked"],
                "available": data["available"],
            }

        return ToolResult(success=True, data={"vendors": all_vendors})

    def _add_request(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle a special request from the bride."""
        request = args.get("request", "")
        cost = args.get("estimated_cost", 0)
        approved = args.get("approved", False)

        if approved and cost > self.remaining:
            return ToolResult(success=False, error=f"Cannot approve - exceeds budget by ${cost - self.remaining}")

        if approved:
            self.spent += cost
            self.remaining -= cost
            self.requests_fulfilled += 1
            env_state["budget_remaining"] = self.remaining

            return ToolResult(success=True, data={
                "request": request,
                "status": "Approved and scheduled",
                "cost": cost,
                "remaining_budget": self.remaining,
            })
        else:
            self.requests_denied += 1
            self.chaos_level += 1  # Denying requests increases chaos!
            env_state["chaos_level"] = self.chaos_level

            return ToolResult(success=True, data={
                "request": request,
                "status": "Denied",
                "reason": args.get("reason", "Budget constraints"),
                "warning": "The bride is not happy about this...",
                "chaos_increase": 1,
            })

    def _change_theme(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Change the wedding theme (expensive and chaotic!)."""
        new_theme = args.get("theme", "")
        if not new_theme:
            return ToolResult(success=False, error="theme is required")

        old_theme = self.theme

        # Changing theme is expensive!
        change_cost = sum(data["cost"] * 0.3 for data in self.vendors.values() if data["booked"])

        if change_cost > self.remaining:
            self.requests_denied += 1
            self.chaos_level += 2
            return ToolResult(success=False, error=f"Theme change would cost ${change_cost:.0f} in rebooking fees. Budget only has ${self.remaining}")

        self.theme = new_theme
        self.spent += change_cost
        self.remaining -= change_cost
        self.chaos_level += 1  # Theme changes always cause some chaos

        env_state["theme"] = new_theme
        env_state["budget_remaining"] = self.remaining
        env_state["chaos_level"] = self.chaos_level

        return ToolResult(success=True, data={
            "old_theme": old_theme,
            "new_theme": new_theme,
            "rebooking_cost": change_cost,
            "remaining_budget": self.remaining,
            "warning": "Theme changes may require vendor renegotiations",
        })

    def _handle_emergency(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle a wedding emergency."""
        emergency_type = args.get("type", "unknown")
        solution = args.get("solution", "")
        cost = args.get("cost", 0)

        if cost > self.remaining:
            return ToolResult(success=False, error="Insufficient budget for emergency fix")

        self.spent += cost
        self.remaining -= cost
        self.disasters_handled += 1

        env_state["budget_remaining"] = self.remaining
        env_state["disasters_handled"] = self.disasters_handled

        return ToolResult(success=True, data={
            "emergency": emergency_type,
            "solution": solution,
            "cost": cost,
            "status": "Crisis averted!",
            "remaining_budget": self.remaining,
        })

    def _get_stats(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get overall planning statistics."""
        return ToolResult(success=True, data={
            "requests_fulfilled": self.requests_fulfilled,
            "requests_denied": self.requests_denied,
            "disasters_handled": self.disasters_handled,
            "chaos_level": self.chaos_level,
            "bride_meltdowns": self.bride_meltdowns,
            "budget_efficiency": f"{(self.spent / self.total_budget * 100):.1f}%",
        })

    def _trigger_event(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle injected chaos events."""
        event = args.get("event")

        events = {
            # Bride demands
            "swan_ice": {
                "message": "The bride wants a life-sized ice sculpture of a swan. No, two swans. KISSING.",
                "request": "Twin kissing swan ice sculptures",
                "estimated_cost": 3000,
                "chaos_type": "demand",
            },
            "white_doves": {
                "message": "The bride insists on 50 white doves released after the ceremony. Live ones.",
                "request": "50 live white dove release",
                "estimated_cost": 2000,
                "chaos_type": "demand",
                "complications": "May require permits, cleanup, bird handler",
            },
            "celebrity_cake": {
                "message": "The bride wants a cake replica of their first date location... in full 3D... life-sized.",
                "request": "Life-sized venue replica cake",
                "estimated_cost": 8000,
                "chaos_type": "demand",
            },
            "theme_change": {
                "message": "The bride saw something on Pinterest. New theme: Medieval Renaissance Fairy Tale.",
                "request": "Complete theme overhaul to Medieval Renaissance",
                "chaos_type": "disaster",
                "impact": "All decorations, dress, venue setup need changes",
            },
            # Disasters
            "venue_cancelled": {
                "message": "DISASTER: The venue just called. Double-booked. They're SO sorry.",
                "disaster_type": "venue_crisis",
                "severity": "critical",
                "requires": "Find new venue IMMEDIATELY",
            },
            "caterer_quit": {
                "message": "The caterer had a 'creative differences' meltdown and quit.",
                "disaster_type": "vendor_crisis",
                "severity": "high",
                "requires": "Find replacement caterer",
            },
            "mother_in_law": {
                "message": "Mother-in-law demands a speech slot. Bride says OVER HER DEAD BODY.",
                "disaster_type": "family_drama",
                "severity": "medium",
                "requires": "Diplomatic solution",
            },
            "dress_disaster": {
                "message": "The dress arrived. It's the wrong size. Wedding is in 2 weeks.",
                "disaster_type": "wardrobe_crisis",
                "severity": "high",
                "requires": "Rush alterations or new dress",
            },
            # Chaos escalation
            "bride_meltdown": {
                "message": "The bride is having a FULL MELTDOWN in the vendor meeting.",
                "chaos_type": "emotional",
                "impact": "All decisions on hold until bride calms down",
            },
            "budget_reveal": {
                "message": "The bride just found out you've spent 80% of the budget...",
                "chaos_type": "financial",
                "impact": "Bride demands audit of all expenses",
            },
        }

        event_data = events.get(event)
        if not event_data:
            return ToolResult(success=False, error=f"Unknown event: {event}")

        # Track chaos
        self.chaos_level += 2
        if event == "bride_meltdown":
            self.bride_meltdowns += 1

        env_state["chaos_level"] = self.chaos_level
        env_state.setdefault("wedding_events", []).append(event)

        # Mark vendors unavailable for certain disasters
        if event == "venue_cancelled":
            self.vendors["venue"]["available"] = False
            self.vendors["venue"]["booked"] = False
        if event == "caterer_quit":
            self.vendors["catering"]["available"] = False
            self.vendors["catering"]["booked"] = False

        return ToolResult(success=True, data=event_data)

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available wedding planning actions."""
        return [
            {
                "name": "check_status",
                "description": "Get overall wedding planning status",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "check_budget",
                "description": "Get detailed budget breakdown",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "book_vendor",
                "description": "Book a vendor for the wedding",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vendor_type": {"type": "string", "description": "Type: venue, catering, flowers, photography, music, cake, dress, decorations"},
                    },
                    "required": ["vendor_type"],
                },
            },
            {
                "name": "get_vendor_options",
                "description": "Get vendor options and alternatives",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vendor_type": {"type": "string", "description": "Vendor category to explore"},
                    },
                },
            },
            {
                "name": "add_request",
                "description": "Handle a special request from the bride",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "string", "description": "What the bride wants"},
                        "estimated_cost": {"type": "number", "description": "Estimated cost"},
                        "approved": {"type": "boolean", "description": "Approve the request?"},
                        "reason": {"type": "string", "description": "Reason if denying"},
                    },
                    "required": ["request"],
                },
            },
            {
                "name": "change_theme",
                "description": "Change the wedding theme (expensive!)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string", "description": "New theme"},
                    },
                    "required": ["theme"],
                },
            },
            {
                "name": "handle_emergency",
                "description": "Handle a wedding emergency",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Emergency type"},
                        "solution": {"type": "string", "description": "Proposed solution"},
                        "cost": {"type": "number", "description": "Cost of solution"},
                    },
                    "required": ["type", "solution"],
                },
            },
            {
                "name": "get_stats",
                "description": "Get planning statistics",
                "parameters": {"type": "object", "properties": {}},
            },
        ]
