"""Tests for API response parsing logic."""

from unittest.mock import MagicMock, patch

from clix.core.api import _extract_tweets_from_timeline, get_bookmarks


class TestCursorExtraction:
    """Verify cursor parsing from timeline responses."""

    def _make_timeline_response(self, entries: list) -> dict:
        """Build a minimal timeline-shaped API response."""
        return {
            "data": {
                "search_by_raw_query": {
                    "search_timeline": {
                        "timeline": {
                            "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                        }
                    }
                }
            }
        }

    def test_cursor_top_extracted(self):
        """cursor-top entry should populate cursor_top."""
        entries = [
            {"entryId": "cursor-top-123", "content": {"value": "abc"}},
        ]
        result = _extract_tweets_from_timeline(self._make_timeline_response(entries))
        assert result.cursor_top == "abc"

    def test_cursor_bottom_extracted(self):
        """cursor-bottom entry should populate cursor_bottom."""
        entries = [
            {"entryId": "cursor-bottom-456", "content": {"value": "def"}},
        ]
        result = _extract_tweets_from_timeline(self._make_timeline_response(entries))
        assert result.cursor_bottom == "def"
        assert result.has_more is True

    def test_both_cursors_extracted(self):
        """Both cursors should be extracted independently."""
        entries = [
            {"entryId": "cursor-top-1", "content": {"value": "top_val"}},
            {"entryId": "cursor-bottom-2", "content": {"value": "bottom_val"}},
        ]
        result = _extract_tweets_from_timeline(self._make_timeline_response(entries))
        assert result.cursor_top == "top_val"
        assert result.cursor_bottom == "bottom_val"

    def test_no_cursors(self):
        """Empty entries should produce no cursors."""
        result = _extract_tweets_from_timeline(self._make_timeline_response([]))
        assert result.cursor_top is None
        assert result.cursor_bottom is None
        assert result.has_more is False


class TestGetBookmarks:
    """Verify get_bookmarks sends the correct GraphQL variables."""

    @patch("clix.core.api.XClient", autospec=True)
    def test_includes_raw_query_variable(self, mock_client_cls: MagicMock) -> None:
        """BookmarkSearchTimeline requires rawQuery to avoid HTTP 422."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=10)

        args, _ = client.graphql_get.call_args
        operation, variables = args
        assert operation == "BookmarkSearchTimeline"
        assert "rawQuery" in variables
        assert variables["rawQuery"] != ""

    @patch("clix.core.api.XClient", autospec=True)
    def test_passes_cursor_when_provided(self, mock_client_cls: MagicMock) -> None:
        """Cursor should be forwarded for pagination."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=20, cursor="abc123")

        _, variables = client.graphql_get.call_args[0]
        assert variables["cursor"] == "abc123"

    @patch("clix.core.api.XClient", autospec=True)
    def test_omits_cursor_when_not_provided(self, mock_client_cls: MagicMock) -> None:
        """Cursor key should be absent when no cursor is passed."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=10)

        _, variables = client.graphql_get.call_args[0]
        assert "cursor" not in variables

    @patch("clix.core.api.XClient", autospec=True)
    def test_count_forwarded_to_variables(self, mock_client_cls: MagicMock) -> None:
        """Count parameter should be forwarded in the GraphQL variables."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=50)

        _, variables = client.graphql_get.call_args[0]
        assert variables["count"] == 50

    @patch("clix.core.api.XClient", autospec=True)
    def test_promoted_content_disabled(self, mock_client_cls: MagicMock) -> None:
        """Promoted content should always be excluded from bookmarks."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=20)

        _, variables = client.graphql_get.call_args[0]
        assert variables["includePromotedContent"] is False

    @patch("clix.core.api.XClient", autospec=True)
    def test_empty_response_returns_no_tweets(self, mock_client_cls: MagicMock) -> None:
        """Empty instructions should return an empty TimelineResponse."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        result = get_bookmarks(client, count=20)

        assert result.tweets == []
        assert result.has_more is False

    @patch("clix.core.api.XClient", autospec=True)
    def test_default_count_is_twenty(self, mock_client_cls: MagicMock) -> None:
        """Default count should be 20 when not specified."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client)

        _, variables = client.graphql_get.call_args[0]
        assert variables["count"] == 20


class TestGetBookmarksCLI:
    """Verify the bookmarks CLI command output and error handling."""

    def test_bookmarks_help(self) -> None:
        """Bookmarks command should display help text."""
        from typer.testing import CliRunner

        from clix.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["bookmarks", "--help"])
        assert result.exit_code == 0
        assert "bookmarks" in result.stdout.lower()

    @patch("clix.cli.app.get_client")
    @patch("clix.core.api.get_bookmarks")
    def test_json_output_empty_bookmarks(
        self, mock_get_bookmarks: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """JSON output with no bookmarks should return an empty list."""
        from typer.testing import CliRunner

        from clix.cli.app import app
        from clix.models.tweet import TimelineResponse

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get_client.return_value = mock_client
        mock_get_bookmarks.return_value = TimelineResponse(tweets=[], has_more=False)

        runner = CliRunner()
        result = runner.invoke(app, ["bookmarks", "--json"])

        assert result.exit_code == 0
        assert result.stdout.strip() == "[]"

    @patch("clix.cli.app.get_client")
    @patch("clix.core.api.get_bookmarks")
    def test_json_output_with_tweets(
        self, mock_get_bookmarks: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """JSON output with bookmarks should return a JSON array of tweet dicts."""
        import json

        from typer.testing import CliRunner

        from clix.cli.app import app
        from clix.models.tweet import TimelineResponse, Tweet

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get_client.return_value = mock_client

        tweet = Tweet(
            id="123",
            text="bookmarked tweet",
            author_id="456",
            author_name="Test User",
            author_handle="testuser",
        )
        mock_get_bookmarks.return_value = TimelineResponse(tweets=[tweet], has_more=False)

        runner = CliRunner()
        result = runner.invoke(app, ["bookmarks", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "123"

    @patch("clix.cli.app.get_client")
    def test_auth_error_exits_with_code_2(self, mock_get_client: MagicMock) -> None:
        """Auth failure should exit with code 2."""
        from typer.testing import CliRunner

        from clix.cli.app import app

        mock_get_client.side_effect = SystemExit(2)

        runner = CliRunner()
        result = runner.invoke(app, ["bookmarks", "--json"])

        assert result.exit_code == 2
