"""TOML-based configuration management."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from clix.core.constants import (
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_COUNT,
    DEFAULT_DELAY_SECONDS,
)


def get_config_dir() -> Path:
    """Get the config directory, creating it if needed."""
    config_dir = Path.home() / ".config" / CONFIG_DIR_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / CONFIG_FILE_NAME


class DisplayConfig(BaseModel):
    """Display settings."""

    theme: str = "default"
    show_engagement: bool = True
    show_timestamps: bool = True
    max_width: int = 100


class RequestConfig(BaseModel):
    """Request settings."""

    delay: float = DEFAULT_DELAY_SECONDS
    proxy: str | None = None
    timeout: int = 30
    max_retries: int = 3


class NetworkConfig(BaseModel):
    """Network settings (proxy, etc.)."""

    proxy: str = ""


class FilterConfig(BaseModel):
    """Filter settings for tweet scoring."""

    likes_weight: float = 1.0
    retweets_weight: float = 1.5
    replies_weight: float = 0.5
    bookmarks_weight: float = 2.0
    views_log_weight: float = 0.3


class Config(BaseModel):
    """Root configuration."""

    default_count: int = Field(default=DEFAULT_COUNT, ge=1, le=100)
    default_account: str | None = None
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    request: RequestConfig = Field(default_factory=RequestConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)

    @classmethod
    def load(cls) -> Config:
        """Load config from TOML file, with defaults for missing values."""
        config_path = get_config_path()
        if not config_path.exists():
            return cls()

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        return cls.model_validate(data)

    def save(self) -> None:
        """Save config to TOML file."""
        config_path = get_config_path()
        lines = _dict_to_toml(self.model_dump())
        config_path.write_text(lines)


def _dict_to_toml(data: dict[str, Any], prefix: str = "") -> str:
    """Simple dict to TOML string converter."""
    lines: list[str] = []
    tables: list[tuple[str, dict]] = []

    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        elif isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif value is None:
            continue
        else:
            lines.append(f"{key} = {value}")

    for key, table in tables:
        section = f"{prefix}.{key}" if prefix else key
        lines.append(f"\n[{section}]")
        lines.append(_dict_to_toml(table, section))

    return "\n".join(lines) + "\n"
