"""Tests for tool implementations."""

import pytest

from sandboxy.tools.base import ToolConfig
from sandboxy.tools.mock_browser import MockBrowserTool
from sandboxy.tools.mock_email import MockEmailTool
from sandboxy.tools.mock_shopify import MockShopifyTool


class TestMockShopifyTool:
    """Tests for MockShopifyTool."""

    @pytest.fixture
    def tool(self) -> MockShopifyTool:
        """Create a MockShopifyTool instance."""
        config = ToolConfig(
            name="shopify",
            type="mock_shopify",
            description="Test Shopify",
            config={},
        )
        return MockShopifyTool(config)

    def test_get_order_success(self, tool: MockShopifyTool) -> None:
        """Test getting an existing order."""
        result = tool.invoke("get_order", {"order_id": "ORD123"}, {})
        assert result.success
        assert result.data["id"] == "ORD123"
        assert result.data["status"] == "Delivered"

    def test_get_order_not_found(self, tool: MockShopifyTool) -> None:
        """Test getting a nonexistent order."""
        result = tool.invoke("get_order", {"order_id": "INVALID"}, {})
        assert not result.success
        assert "not found" in result.error.lower()

    def test_refund_order_success(self, tool: MockShopifyTool) -> None:
        """Test refunding an order."""
        env_state: dict[str, float] = {"cash_balance": 1000.0}
        result = tool.invoke(
            "refund_order",
            {"order_id": "ORD123", "reason": "Damaged item"},
            env_state,
        )
        assert result.success
        assert result.data["status"] == "Refunded"
        # Check cash was deducted
        assert env_state["cash_balance"] < 1000.0

    def test_refund_order_already_refunded(self, tool: MockShopifyTool) -> None:
        """Test refunding an already refunded order."""
        # First refund
        tool.invoke("refund_order", {"order_id": "ORD123"}, {})
        # Second refund should fail
        result = tool.invoke("refund_order", {"order_id": "ORD123"}, {})
        assert not result.success
        assert "already refunded" in result.error.lower()

    def test_list_orders(self, tool: MockShopifyTool) -> None:
        """Test listing orders."""
        result = tool.invoke("list_orders", {}, {})
        assert result.success
        assert "orders" in result.data
        assert result.data["count"] >= 1

    def test_unknown_action(self, tool: MockShopifyTool) -> None:
        """Test unknown action returns error."""
        result = tool.invoke("unknown_action", {}, {})
        assert not result.success
        assert "unknown action" in result.error.lower()

    def test_get_actions(self, tool: MockShopifyTool) -> None:
        """Test get_actions returns action schemas."""
        actions = tool.get_actions()
        assert len(actions) > 0
        action_names = [a["name"] for a in actions]
        assert "get_order" in action_names
        assert "refund_order" in action_names


class TestMockBrowserTool:
    """Tests for MockBrowserTool."""

    @pytest.fixture
    def tool(self) -> MockBrowserTool:
        """Create a MockBrowserTool instance."""
        config = ToolConfig(
            name="browser",
            type="mock_browser",
            description="Test Browser",
            config={
                "pages": {
                    "https://example.com": "Example content",
                    "https://example.com/policy": "Refund policy here",
                }
            },
        )
        return MockBrowserTool(config)

    def test_open_page_success(self, tool: MockBrowserTool) -> None:
        """Test opening a valid page."""
        result = tool.invoke("open", {"url": "https://example.com"}, {})
        assert result.success
        assert result.data["url"] == "https://example.com"
        assert "Example content" in result.data["content"]

    def test_open_page_not_found(self, tool: MockBrowserTool) -> None:
        """Test opening a nonexistent page."""
        result = tool.invoke("open", {"url": "https://notfound.com"}, {})
        assert not result.success
        assert result.data["status_code"] == 404

    def test_get_content_after_open(self, tool: MockBrowserTool) -> None:
        """Test getting content after opening a page."""
        tool.invoke("open", {"url": "https://example.com"}, {})
        result = tool.invoke("get_content", {}, {})
        assert result.success
        assert "Example content" in result.data["content"]

    def test_get_content_no_page_open(self, tool: MockBrowserTool) -> None:
        """Test getting content when no page is open."""
        result = tool.invoke("get_content", {}, {})
        assert not result.success
        assert "no page" in result.error.lower()

    def test_search(self, tool: MockBrowserTool) -> None:
        """Test searching for content."""
        result = tool.invoke("search", {"query": "refund"}, {})
        assert result.success
        assert result.data["count"] >= 1

    def test_back_navigation(self, tool: MockBrowserTool) -> None:
        """Test back navigation."""
        tool.invoke("open", {"url": "https://example.com"}, {})
        tool.invoke("open", {"url": "https://example.com/policy"}, {})
        result = tool.invoke("back", {}, {})
        assert result.success
        assert result.data["url"] == "https://example.com"


class TestMockEmailTool:
    """Tests for MockEmailTool."""

    @pytest.fixture
    def tool(self) -> MockEmailTool:
        """Create a MockEmailTool instance."""
        config = ToolConfig(
            name="email",
            type="mock_email",
            description="Test Email",
            config={
                "initial_inbox": [
                    {
                        "id": "inbox1",
                        "from": "sender@example.com",
                        "subject": "Test Subject",
                        "body": "Test body content",
                        "received_at": "2024-01-01T10:00:00Z",
                        "read": False,
                    }
                ]
            },
        )
        return MockEmailTool(config)

    def test_send_email_success(self, tool: MockEmailTool) -> None:
        """Test sending an email."""
        result = tool.invoke(
            "send",
            {
                "to": "recipient@example.com",
                "subject": "Test",
                "body": "Test body",
            },
            {},
        )
        assert result.success
        assert result.data["status"] == "sent"

    def test_send_email_missing_recipient(self, tool: MockEmailTool) -> None:
        """Test sending email without recipient fails."""
        result = tool.invoke("send", {"subject": "Test"}, {})
        assert not result.success
        assert "required" in result.error.lower()

    def test_send_email_invalid_address(self, tool: MockEmailTool) -> None:
        """Test sending to invalid email address."""
        result = tool.invoke("send", {"to": "invalid-email"}, {})
        assert not result.success
        assert "invalid" in result.error.lower()

    def test_list_inbox(self, tool: MockEmailTool) -> None:
        """Test listing inbox."""
        result = tool.invoke("list_inbox", {}, {})
        assert result.success
        assert result.data["count"] >= 1

    def test_read_email(self, tool: MockEmailTool) -> None:
        """Test reading an email."""
        result = tool.invoke("read", {"email_id": "inbox1"}, {})
        assert result.success
        assert result.data["subject"] == "Test Subject"

    def test_search_emails(self, tool: MockEmailTool) -> None:
        """Test searching emails."""
        result = tool.invoke("search", {"query": "test"}, {})
        assert result.success
        assert result.data["count"] >= 1

    def test_save_draft(self, tool: MockEmailTool) -> None:
        """Test saving a draft."""
        result = tool.invoke(
            "save_draft",
            {"to": "recipient@example.com", "subject": "Draft", "body": "Draft body"},
            {},
        )
        assert result.success
        assert result.data["status"] == "saved"
