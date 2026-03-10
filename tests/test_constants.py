"""Tests for constants module."""

from clix.core.constants import (
    BASE_URL,
    BEARER_TOKEN,
    DEFAULT_FIELD_TOGGLES,
    GRAPHQL_BASE,
)


class TestConstants:
    """Verify remaining constants are well-defined."""

    def test_base_url_is_https(self):
        assert BASE_URL.startswith("https://")

    def test_graphql_base_includes_api(self):
        assert "graphql" in GRAPHQL_BASE

    def test_bearer_token_is_set(self):
        assert len(BEARER_TOKEN) > 50

    def test_field_toggles_has_article_key(self):
        assert "withArticlePlainText" in DEFAULT_FIELD_TOGGLES
