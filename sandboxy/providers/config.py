"""Configuration models for local model providers."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from sandboxy.providers.base import ModelInfo

logger = logging.getLogger(__name__)

# Default config file location
DEFAULT_CONFIG_PATH = Path.home() / ".sandboxy" / "providers.json"


class ProviderStatusEnum(str, Enum):
    """Status of a local provider connection."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class LocalProviderConfig(BaseModel):
    """Configuration for a local model provider."""

    name: str = Field(
        ...,
        description="User-friendly name for this provider",
        examples=["ollama-local", "my-vllm-server"],
    )

    type: Literal["ollama", "lmstudio", "vllm", "openai-compatible"] = Field(
        default="openai-compatible",
        description="Provider type for specialized handling",
    )

    base_url: str = Field(
        ...,
        description="Base URL for the provider API",
        examples=["http://localhost:11434/v1", "http://localhost:1234/v1"],
    )

    api_key: str | None = Field(
        default=None,
        description="Optional API key for authenticated providers",
    )

    enabled: bool = Field(
        default=True,
        description="Whether this provider is active",
    )

    models: list[str] = Field(
        default_factory=list,
        description="Manually configured model IDs (overrides auto-discovery)",
    )

    default_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Default parameters for completions (temperature, max_tokens, etc.)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate provider name is alphanumeric with hyphens/underscores."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            msg = "Provider name must be alphanumeric with hyphens/underscores only"
            raise ValueError(msg)
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            msg = "Base URL must start with http:// or https://"
            raise ValueError(msg)
        # Remove trailing slash for consistency
        return v.rstrip("/")


class ProvidersConfigFile(BaseModel):
    """Root structure for ~/.sandboxy/providers.json."""

    version: int = Field(
        default=1,
        description="Config file schema version for migrations",
    )

    providers: list[LocalProviderConfig] = Field(
        default_factory=list,
        description="List of configured local providers",
    )

    def get_provider(self, name: str) -> LocalProviderConfig | None:
        """Get a provider by name."""
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None

    def add_provider(self, config: LocalProviderConfig) -> None:
        """Add a new provider configuration.

        Raises:
            ValueError: If provider with same name already exists

        """
        if self.get_provider(config.name):
            msg = f"Provider '{config.name}' already exists"
            raise ValueError(msg)
        self.providers.append(config)

    def remove_provider(self, name: str) -> bool:
        """Remove a provider by name.

        Returns:
            True if removed, False if not found

        """
        for i, provider in enumerate(self.providers):
            if provider.name == name:
                self.providers.pop(i)
                return True
        return False

    def update_provider(self, name: str, **updates: Any) -> LocalProviderConfig | None:
        """Update a provider's configuration.

        Args:
            name: Provider name to update
            **updates: Fields to update

        Returns:
            Updated config or None if not found

        """
        provider = self.get_provider(name)
        if not provider:
            return None

        # Create updated config
        data = provider.model_dump()
        data.update(updates)
        updated = LocalProviderConfig(**data)

        # Replace in list
        for i, p in enumerate(self.providers):
            if p.name == name:
                self.providers[i] = updated
                return updated
        return None


@dataclass
class LocalModelInfo(ModelInfo):
    """Model information with local-specific metadata.

    Extends the base ModelInfo with local-specific fields.
    """

    # Local-specific fields (added to inherited fields from ModelInfo)
    provider_name: str = ""
    is_local: bool = True
    capabilities_verified: bool = False


class ProviderStatus(BaseModel):
    """Runtime status of a provider connection."""

    name: str
    status: ProviderStatusEnum
    last_checked: datetime | None = None
    error_message: str | None = None
    available_models: list[str] = Field(default_factory=list)
    latency_ms: int | None = None


# --- Config file load/save functions ---


def load_providers_config(path: Path | None = None) -> ProvidersConfigFile:
    """Load providers configuration from file.

    Args:
        path: Config file path. Defaults to ~/.sandboxy/providers.json

    Returns:
        ProvidersConfigFile with loaded or default configuration

    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        logger.debug(f"Config file not found at {config_path}, using defaults")
        return ProvidersConfigFile()

    try:
        with open(config_path) as f:
            data = json.load(f)
        return ProvidersConfigFile.model_validate(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in config file: {e}")
        return ProvidersConfigFile()
    except Exception as e:
        logger.warning(f"Failed to load config: {e}")
        return ProvidersConfigFile()


def save_providers_config(config: ProvidersConfigFile, path: Path | None = None) -> None:
    """Save providers configuration to file.

    Args:
        config: Configuration to save
        path: Config file path. Defaults to ~/.sandboxy/providers.json

    """
    config_path = path or DEFAULT_CONFIG_PATH

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2, default=str)

    logger.debug(f"Saved providers config to {config_path}")


def get_enabled_providers() -> list[LocalProviderConfig]:
    """Get list of enabled local providers from config."""
    config = load_providers_config()
    return [p for p in config.providers if p.enabled]
