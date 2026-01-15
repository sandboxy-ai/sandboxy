"""Tests for tool base module."""

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult
from tests.factories import ToolConfigFactory, ToolResultFactory


class TestToolConfig:
    """Tests for ToolConfig model."""

    def test_create_basic_config(self) -> None:
        """Test creating a basic tool config."""
        config = ToolConfig(
            name="test_tool",
            type="mock_test",
            description="Test tool",
        )
        assert config.name == "test_tool"
        assert config.type == "mock_test"
        assert config.description == "Test tool"

    def test_create_config_with_options(self) -> None:
        """Test creating config with tool-specific options."""
        config = ToolConfig(
            name="shopify",
            type="mock_shopify",
            description="Shopify store",
            config={
                "api_key": "test-key",
                "store_id": "12345",
            },
        )
        assert config.config["api_key"] == "test-key"
        assert config.config["store_id"] == "12345"

    def test_config_defaults(self) -> None:
        """Test tool config default values."""
        config = ToolConfig(name="test", type="mock")
        assert config.description == ""
        assert config.config == {}

    def test_config_serialization(self) -> None:
        """Test config serializes to dict."""
        config = ToolConfig(
            name="test",
            type="mock",
            description="Test",
            config={"key": "value"},
        )
        data = config.model_dump()
        assert data["name"] == "test"
        assert data["config"]["key"] == "value"


class TestToolResult:
    """Tests for ToolResult model."""

    def test_create_success_result(self) -> None:
        """Test creating a successful result."""
        result = ToolResult(
            success=True,
            data={"order_id": "123", "status": "shipped"},
        )
        assert result.success is True
        assert result.data["order_id"] == "123"
        assert result.error is None

    def test_create_error_result(self) -> None:
        """Test creating an error result."""
        result = ToolResult(
            success=False,
            error="Order not found",
        )
        assert result.success is False
        assert result.error == "Order not found"
        assert result.data is None

    def test_result_defaults(self) -> None:
        """Test tool result defaults."""
        result = ToolResult(success=True)
        assert result.data is None
        assert result.error is None

    def test_result_serialization(self) -> None:
        """Test result serializes to dict."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
        )
        data = result.model_dump()
        assert data["success"] is True
        assert data["data"]["key"] == "value"

    def test_factory_success(self) -> None:
        """Test factory creates success result."""
        result = ToolResultFactory.success({"item": "test"})
        assert result.success is True
        assert result.data["item"] == "test"

    def test_factory_error(self) -> None:
        """Test factory creates error result."""
        result = ToolResultFactory.error("Something failed")
        assert result.success is False
        assert result.error == "Something failed"


class TestBaseTool:
    """Tests for BaseTool class."""

    def test_create_base_tool(self) -> None:
        """Test creating a base tool."""
        config = ToolConfig(
            name="test_tool",
            type="mock",
            description="Test description",
            config={"setting": "value"},
        )
        tool = BaseTool(config)

        assert tool.name == "test_tool"
        assert tool.description == "Test description"
        assert tool.config["setting"] == "value"

    def test_base_tool_invoke_returns_error(self) -> None:
        """Test base tool invoke returns unknown action error."""
        config = ToolConfig(name="test", type="mock")
        tool = BaseTool(config)

        result = tool.invoke("some_action", {}, {})

        assert result.success is False
        assert "unknown action" in result.error.lower()

    def test_base_tool_get_actions_empty(self) -> None:
        """Test base tool get_actions returns empty list."""
        config = ToolConfig(name="test", type="mock")
        tool = BaseTool(config)

        actions = tool.get_actions()

        assert actions == []

    def test_base_tool_invoke_with_args(self) -> None:
        """Test base tool invoke accepts args."""
        config = ToolConfig(name="test", type="mock")
        tool = BaseTool(config)

        result = tool.invoke(
            "action",
            {"arg1": "value1"},
            {"state_key": "state_value"},
        )

        assert result.success is False  # Still fails because action unknown


class TestToolConfigFactory:
    """Tests for ToolConfigFactory."""

    def test_factory_creates_config(self) -> None:
        """Test factory creates valid config."""
        config = ToolConfigFactory.create()
        assert config.name is not None
        assert config.type == "mock_test"

    def test_factory_accepts_custom_values(self) -> None:
        """Test factory accepts custom values."""
        config = ToolConfigFactory.create(
            name="custom_tool",
            type="custom_type",
            description="Custom description",
            config={"custom_key": "custom_value"},
        )
        assert config.name == "custom_tool"
        assert config.type == "custom_type"
        assert config.description == "Custom description"
        assert config.config["custom_key"] == "custom_value"

    def test_factory_increments_counter(self) -> None:
        """Test factory creates unique names."""
        ToolConfigFactory.reset_counter()
        config1 = ToolConfigFactory.create()
        config2 = ToolConfigFactory.create()
        assert config1.name != config2.name
