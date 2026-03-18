"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner

from clix.cli.app import app
from clix.cli.helpers import normalize_tweet_id

runner = CliRunner()


class TestCLI:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Twitter/X CLI" in result.stdout

    def test_config(self):
        result = runner.invoke(app, ["config", "--json"])
        assert result.exit_code == 0
        assert "default_count" in result.stdout

    def test_auth_status_no_auth(self):
        result = runner.invoke(app, ["auth", "status", "--json"])
        # Should fail with auth error (no credentials available)
        assert result.exit_code in (0, 2)

    def test_auth_accounts_empty(self):
        result = runner.invoke(app, ["auth", "accounts", "--json"])
        assert result.exit_code == 0

    def test_feed_help(self):
        result = runner.invoke(app, ["feed", "--help"])
        assert result.exit_code == 0
        assert "timeline" in result.stdout.lower()

    def test_search_help(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "query" in result.stdout.lower()

    def test_user_help(self):
        result = runner.invoke(app, ["user", "--help"])
        assert result.exit_code == 0

    def test_post_help(self):
        result = runner.invoke(app, ["post", "--help"])
        assert result.exit_code == 0
        assert "tweet" in result.stdout.lower()


class TestNormalizeTweetId:
    def test_bare_id(self):
        assert normalize_tweet_id("123456789") == "123456789"

    def test_x_url(self):
        assert normalize_tweet_id("https://x.com/elonmusk/status/123456789") == "123456789"

    def test_twitter_url(self):
        assert normalize_tweet_id("https://twitter.com/user/status/999888777") == "999888777"

    def test_url_with_query_params(self):
        assert normalize_tweet_id("https://x.com/user/status/123456789?s=20&t=abc") == "123456789"

    def test_bare_id_with_whitespace(self):
        assert normalize_tweet_id("  123456789  ") == "123456789"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="required"):
            normalize_tweet_id("")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid tweet URL"):
            normalize_tweet_id("https://x.com/user/likes")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="Invalid tweet ID"):
            normalize_tweet_id("not-a-number")
