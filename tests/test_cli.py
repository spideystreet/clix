"""Tests for CLI commands."""

from typer.testing import CliRunner

from clix.cli.app import app

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
