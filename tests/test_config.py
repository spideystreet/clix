"""Tests for configuration."""

from clix.core.config import Config, DisplayConfig, RequestConfig


class TestConfig:
    def test_default_config(self):
        cfg = Config()
        assert cfg.default_count == 20
        assert cfg.display.theme == "default"
        assert cfg.request.delay == 1.5
        assert cfg.filter.likes_weight == 1.0

    def test_custom_config(self):
        cfg = Config(
            default_count=50,
            display=DisplayConfig(theme="dark", max_width=120),
            request=RequestConfig(proxy="socks5://localhost:1080"),
        )
        assert cfg.default_count == 50
        assert cfg.display.theme == "dark"
        assert cfg.request.proxy == "socks5://localhost:1080"

    def test_config_validation(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Config(default_count=0)  # must be >= 1

        with pytest.raises(ValidationError):
            Config(default_count=200)  # must be <= 100
