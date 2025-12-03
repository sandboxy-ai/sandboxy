"""Mock Shopify tool for testing e-commerce scenarios."""

from typing import Any

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class MockShopifyTool(BaseTool):
    """Mock Shopify store for orders, refunds, and customer management."""

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)
        # Initialize in-memory store with default data
        self.store: dict[str, Any] = {
            "orders": self.config.get("initial_orders", {
                "ORD123": {
                    "id": "ORD123",
                    "status": "Delivered",
                    "refunded": False,
                    "total": 99.99,
                    "customer_email": "customer@example.com",
                    "items": [{"name": "Widget", "quantity": 1, "price": 99.99}],
                    "created_at": "2024-01-15T10:00:00Z",
                },
            }),
            "customers": self.config.get("initial_customers", {
                "CUST001": {
                    "id": "CUST001",
                    "email": "customer@example.com",
                    "name": "John Doe",
                    "total_orders": 5,
                    "total_spent": 450.00,
                },
            }),
        }

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle Shopify actions."""
        handlers = {
            "get_order": self._get_order,
            "refund_order": self._refund_order,
            "list_orders": self._list_orders,
            "get_customer": self._get_customer,
            "update_order_status": self._update_order_status,
        }

        handler = handlers.get(action)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        return handler(args, env_state)

    def _get_order(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get order details by ID."""
        order_id = args.get("order_id")
        if not order_id:
            return ToolResult(success=False, error="order_id is required")

        order = self.store["orders"].get(order_id)
        if not order:
            return ToolResult(success=False, error=f"Order not found: {order_id}")

        return ToolResult(success=True, data=order)

    def _refund_order(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Process a refund for an order."""
        order_id = args.get("order_id")
        reason = args.get("reason", "Customer request")

        if not order_id:
            return ToolResult(success=False, error="order_id is required")

        order = self.store["orders"].get(order_id)
        if not order:
            return ToolResult(success=False, error=f"Order not found: {order_id}")

        if order["refunded"]:
            return ToolResult(success=False, error="Order already refunded")

        # Process refund
        order["refunded"] = True
        order["status"] = "Refunded"
        order["refund_reason"] = reason
        refund_amount = order["total"]

        # Update cash balance in env_state if it exists
        if "cash_balance" in env_state:
            env_state["cash_balance"] -= refund_amount

        return ToolResult(
            success=True,
            data={
                "order_id": order_id,
                "status": "Refunded",
                "refund_amount": refund_amount,
                "reason": reason,
            },
        )

    def _list_orders(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """List all orders, optionally filtered."""
        status_filter = args.get("status")
        customer_email = args.get("customer_email")

        orders = list(self.store["orders"].values())

        if status_filter:
            orders = [o for o in orders if o["status"] == status_filter]
        if customer_email:
            orders = [o for o in orders if o["customer_email"] == customer_email]

        return ToolResult(success=True, data={"orders": orders, "count": len(orders)})

    def _get_customer(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get customer details."""
        customer_id = args.get("customer_id")
        email = args.get("email")

        if customer_id:
            customer = self.store["customers"].get(customer_id)
        elif email:
            customer = next(
                (c for c in self.store["customers"].values() if c["email"] == email),
                None,
            )
        else:
            return ToolResult(success=False, error="customer_id or email is required")

        if not customer:
            return ToolResult(success=False, error="Customer not found")

        return ToolResult(success=True, data=customer)

    def _update_order_status(
        self, args: dict[str, Any], env_state: dict[str, Any]
    ) -> ToolResult:
        """Update order status."""
        order_id = args.get("order_id")
        new_status = args.get("status")

        if not order_id:
            return ToolResult(success=False, error="order_id is required")
        if not new_status:
            return ToolResult(success=False, error="status is required")

        order = self.store["orders"].get(order_id)
        if not order:
            return ToolResult(success=False, error=f"Order not found: {order_id}")

        order["status"] = new_status
        return ToolResult(
            success=True,
            data={"order_id": order_id, "status": new_status},
        )

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available Shopify actions."""
        return [
            {
                "name": "get_order",
                "description": "Get details of an order by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The order ID"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "refund_order",
                "description": "Process a refund for an order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The order ID to refund"},
                        "reason": {"type": "string", "description": "Reason for refund"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "list_orders",
                "description": "List orders with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Filter by status"},
                        "customer_email": {"type": "string", "description": "Filter by customer"},
                    },
                },
            },
            {
                "name": "get_customer",
                "description": "Get customer details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "description": "The customer ID"},
                        "email": {"type": "string", "description": "The customer email"},
                    },
                },
            },
            {
                "name": "update_order_status",
                "description": "Update the status of an order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "The order ID"},
                        "status": {"type": "string", "description": "New status"},
                    },
                    "required": ["order_id", "status"],
                },
            },
        ]
