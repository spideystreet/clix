"""Tests for API response parsing logic."""

from unittest.mock import MagicMock, patch

from clix.core.api import (
    _extract_tweets_from_timeline,
    _parse_trends,
    _parse_tweet_volume,
    get_bookmarks,
    get_trending,
)


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


class TestParseTweetVolume:
    """Verify tweet volume parsing from trend metadata text."""

    def test_plain_number(self):
        """Plain number like '1234 posts' should parse correctly."""
        assert _parse_tweet_volume("1234 posts") == 1234

    def test_comma_separated(self):
        """Comma-separated number like '1,234 posts' should parse correctly."""
        assert _parse_tweet_volume("1,234 posts") == 1234

    def test_k_suffix(self):
        """K suffix like '12.5K posts' should multiply by 1000."""
        assert _parse_tweet_volume("12.5K posts") == 12500

    def test_m_suffix(self):
        """M suffix like '1.2M posts' should multiply by 1000000."""
        assert _parse_tweet_volume("1.2M posts") == 1200000

    def test_none_input(self):
        """None input should return None."""
        assert _parse_tweet_volume(None) is None

    def test_empty_string(self):
        """Empty string should return None."""
        assert _parse_tweet_volume("") is None

    def test_no_number(self):
        """Text without a number should return None."""
        assert _parse_tweet_volume("Trending") is None

    def test_tweets_instead_of_posts(self):
        """'tweets' suffix should work like 'posts'."""
        assert _parse_tweet_volume("5,000 tweets") == 5000


class TestParseTrends:
    """Verify trend parsing from guide.json-like responses."""

    def _make_guide_response(self, entries: list) -> dict:
        """Build a minimal guide.json-shaped response."""
        return {
            "timeline": {
                "instructions": [
                    {"entries": entries},
                ]
            }
        }

    def _make_trend_entry(
        self,
        name: str,
        meta_description: str | None = None,
        url: str = "",
        context_text: str = "",
    ) -> dict:
        """Build a single trend entry inside a module."""
        trend: dict = {"name": name}
        if meta_description:
            trend["trendMetadata"] = {"metaDescription": meta_description}
        if url:
            trend["url"] = {"url": url}

        content: dict = {"trend": trend}
        if context_text:
            content["trendContext"] = {"text": context_text}

        return {
            "content": {
                "items": [
                    {"item": {"content": content}},
                ],
            },
        }

    def test_single_trend_extracted(self):
        """A single trend entry should be extracted."""
        entry = self._make_trend_entry("Python", "10K posts")
        result = _parse_trends(self._make_guide_response([entry]))
        assert len(result) == 1
        assert result[0]["name"] == "Python"
        assert result[0]["tweet_count"] == 10000

    def test_multiple_trends(self):
        """Multiple trend entries should all be extracted."""
        entries = [
            self._make_trend_entry("Python"),
            self._make_trend_entry("Rust"),
        ]
        result = _parse_trends(self._make_guide_response(entries))
        assert len(result) == 2
        names = {t["name"] for t in result}
        assert names == {"Python", "Rust"}

    def test_trend_with_context(self):
        """Trend context text should be captured."""
        entry = self._make_trend_entry("Python", context_text="Technology")
        result = _parse_trends(self._make_guide_response([entry]))
        assert result[0]["context"] == "Technology"

    def test_trend_with_url(self):
        """Trend URL should be captured."""
        entry = self._make_trend_entry("Python", url="/search?q=Python")
        result = _parse_trends(self._make_guide_response([entry]))
        assert result[0]["url"] == "/search?q=Python"

    def test_empty_response(self):
        """Empty guide response should return empty list."""
        result = _parse_trends({"timeline": {"instructions": []}})
        assert result == []

    def test_missing_timeline(self):
        """Response without timeline key should return empty list."""
        result = _parse_trends({})
        assert result == []

    def test_trend_without_volume(self):
        """Trend without tweet volume should have tweet_count=None."""
        entry = self._make_trend_entry("Python")
        result = _parse_trends(self._make_guide_response([entry]))
        assert result[0]["tweet_count"] is None


class TestGetTrending:
    """Verify get_trending calls the REST API correctly."""

    def test_calls_rest_get(self):
        """get_trending should call client.rest_get with guide.json URL."""
        client = MagicMock()
        client.rest_get.return_value = {"timeline": {"instructions": []}}

        get_trending(client)

        client.rest_get.assert_called_once()
        url = client.rest_get.call_args[0][0]
        assert "guide.json" in url

    def test_passes_trending_tab(self):
        """get_trending should request the trending tab."""
        client = MagicMock()
        client.rest_get.return_value = {"timeline": {"instructions": []}}

        get_trending(client)

        params = client.rest_get.call_args[1].get("params") or client.rest_get.call_args[0][1]
        assert params["initial_tab_id"] == "trending"

    def test_returns_parsed_trends(self):
        """get_trending should return parsed trend list."""
        client = MagicMock()
        client.rest_get.return_value = {
            "timeline": {
                "instructions": [
                    {
                        "entries": [
                            {
                                "content": {
                                    "items": [
                                        {
                                            "item": {
                                                "content": {
                                                    "trend": {"name": "#TestTrend"},
                                                }
                                            }
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                ]
            }
        }

        result = get_trending(client)
        assert len(result) == 1
        assert result[0]["name"] == "#TestTrend"


class TestTrendingCLI:
    """Verify the trending CLI command output."""

    def test_trending_help(self) -> None:
        """Trending command should display help text."""
        from typer.testing import CliRunner

        from clix.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["trending", "--help"])
        assert result.exit_code == 0
        assert "trending" in result.stdout.lower()

    @patch("clix.cli.app.get_client")
    @patch("clix.core.api.get_trending")
    def test_json_output_empty_trends(
        self, mock_get_trending: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """JSON output with no trends should return an empty list."""
        import json

        from typer.testing import CliRunner

        from clix.cli.app import app

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get_client.return_value = mock_client
        mock_get_trending.return_value = []

        runner = CliRunner()
        result = runner.invoke(app, ["trending", "--json"])

        assert result.exit_code == 0
        assert json.loads(result.stdout.strip()) == []

    @patch("clix.cli.app.get_client")
    @patch("clix.core.api.get_trending")
    def test_json_output_with_trends(
        self, mock_get_trending: MagicMock, mock_get_client: MagicMock
    ) -> None:
        """JSON output with trends should return a JSON array of trend dicts."""
        import json

        from typer.testing import CliRunner

        from clix.cli.app import app

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_get_client.return_value = mock_client
        mock_get_trending.return_value = [
            {"name": "#Python", "tweet_count": 5000, "context": "Technology", "url": ""},
        ]

        runner = CliRunner()
        result = runner.invoke(app, ["trending", "--json"])

        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "#Python"


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
