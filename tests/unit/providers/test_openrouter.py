"""Tests for OpenRouter provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sandboxy.providers.base import ModelResponse, ProviderError
from sandboxy.providers.openrouter import OPENROUTER_MODELS, OpenRouterProvider


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider."""

    @pytest.fixture
    def provider(self, monkeypatch: pytest.MonkeyPatch) -> OpenRouterProvider:
        """Create provider with mocked API key."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        return OpenRouterProvider()

    @pytest.fixture
    def mock_http_response(self) -> dict:
        """Create mock HTTP response."""
        return {
            "id": "gen-123",
            "model": "openai/gpt-4o",
            "choices": [
                {
                    "message": {"content": "Test response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            },
        }

    # -------------------------------------------------------------------------
    # Initialization tests
    # -------------------------------------------------------------------------

    def test_init_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that initialization requires API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(ProviderError, match="API key required"):
            OpenRouterProvider()

    def test_init_with_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with environment variable."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-test-key")
        provider = OpenRouterProvider()
        assert provider.api_key == "env-test-key"

    def test_init_with_explicit_key(self) -> None:
        """Test initialization with explicit API key."""
        provider = OpenRouterProvider(api_key="explicit-key")
        assert provider.api_key == "explicit-key"

    def test_explicit_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test explicit key overrides environment variable."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
        provider = OpenRouterProvider(api_key="explicit-key")
        assert provider.api_key == "explicit-key"

    # -------------------------------------------------------------------------
    # Complete method tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_complete_success(
        self,
        provider: OpenRouterProvider,
        mock_http_response: dict,
    ) -> None:
        """Test successful completion request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_http_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            result = await provider.complete(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert isinstance(result, ModelResponse)
            assert result.content == "Test response"
            assert result.input_tokens == 100
            assert result.output_tokens == 50

    @pytest.mark.asyncio
    async def test_complete_with_parameters(
        self,
        provider: OpenRouterProvider,
        mock_http_response: dict,
    ) -> None:
        """Test completion with custom parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_http_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            await provider.complete(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.5,
                max_tokens=500,
            )

            # Verify parameters were passed
            call_args = mock_client_instance.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["temperature"] == 0.5
            assert payload["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_complete_handles_http_error(
        self,
        provider: OpenRouterProvider,
    ) -> None:
        """Test handling of HTTP errors."""
        import httpx

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_error_response,
        )

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(side_effect=error)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            with pytest.raises(ProviderError, match="HTTP 500"):
                await provider.complete(
                    model="openai/gpt-4o",
                    messages=[{"role": "user", "content": "Hello"}],
                )

    @pytest.mark.asyncio
    async def test_complete_handles_request_error(
        self,
        provider: OpenRouterProvider,
    ) -> None:
        """Test handling of network errors."""
        import httpx

        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_instance):
            with pytest.raises(ProviderError, match="Request failed"):
                await provider.complete(
                    model="openai/gpt-4o",
                    messages=[{"role": "user", "content": "Hello"}],
                )

    # -------------------------------------------------------------------------
    # list_models tests
    # -------------------------------------------------------------------------

    def test_list_models(self, provider: OpenRouterProvider) -> None:
        """Test listing available models."""
        models = provider.list_models()

        assert len(models) > 0
        assert all(hasattr(m, "id") for m in models)
        assert all(hasattr(m, "provider") for m in models)

    def test_list_models_includes_major_providers(
        self,
        provider: OpenRouterProvider,
    ) -> None:
        """Test that major providers are included."""
        models = provider.list_models()
        providers = {m.provider for m in models}

        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    # -------------------------------------------------------------------------
    # Cost calculation tests
    # -------------------------------------------------------------------------

    def test_calculate_cost(self, provider: OpenRouterProvider) -> None:
        """Test cost calculation."""
        cost = provider._calculate_cost("openai/gpt-4o", 1000, 500)

        assert cost is not None
        assert cost > 0

    def test_calculate_cost_unknown_model(
        self,
        provider: OpenRouterProvider,
    ) -> None:
        """Test cost calculation for unknown model returns None."""
        cost = provider._calculate_cost("unknown/model", 1000, 500)
        assert cost is None

    def test_calculate_cost_zero_tokens(
        self,
        provider: OpenRouterProvider,
    ) -> None:
        """Test cost calculation with zero tokens."""
        cost = provider._calculate_cost("openai/gpt-4o", 0, 0)
        assert cost == 0.0

    # -------------------------------------------------------------------------
    # Headers tests
    # -------------------------------------------------------------------------

    def test_get_headers(self, provider: OpenRouterProvider) -> None:
        """Test headers include required fields."""
        headers = provider._get_headers()

        assert "Authorization" in headers
        assert "Bearer test-key" in headers["Authorization"]
        assert headers["Content-Type"] == "application/json"


class TestOpenRouterModels:
    """Tests for OpenRouter model definitions."""

    def test_model_definitions_have_required_fields(self) -> None:
        """Test that all model definitions have required fields."""
        for model_id, info in OPENROUTER_MODELS.items():
            assert info.id == model_id
            assert info.name
            assert info.provider
            assert info.context_length > 0

    def test_models_have_pricing(self) -> None:
        """Test that models have pricing information."""
        for _model_id, info in OPENROUTER_MODELS.items():
            # Input cost should be defined
            assert info.input_cost_per_million is not None
            assert info.input_cost_per_million >= 0

    @pytest.mark.parametrize(
        "model_id",
        [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-chat",
        ],
    )
    def test_key_models_defined(self, model_id: str) -> None:
        """Test that key models are defined."""
        assert model_id in OPENROUTER_MODELS
        info = OPENROUTER_MODELS[model_id]
        assert info.name
        assert info.context_length > 0

    def test_free_models_have_zero_cost(self) -> None:
        """Test that free models have zero cost."""
        free_models = [model_id for model_id in OPENROUTER_MODELS if ":free" in model_id]
        for model_id in free_models:
            info = OPENROUTER_MODELS[model_id]
            assert info.input_cost_per_million == 0.0
            assert info.output_cost_per_million == 0.0
