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
    def test_includes_search_query_variable(self, mock_client_cls: MagicMock) -> None:
        """BookmarkSearchTimeline requires search_query to avoid HTTP 422."""
        client = mock_client_cls.return_value
        client.graphql_get.return_value = {
            "data": {"bookmark_timeline_v2": {"timeline": {"instructions": []}}}
        }

        get_bookmarks(client, count=10)

        args, _ = client.graphql_get.call_args
        operation, variables = args
        assert operation == "BookmarkSearchTimeline"
        assert "search_query" in variables
        assert variables["search_query"] == ""

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
