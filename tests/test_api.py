"""Tests for API response parsing logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clix.core.api import (
    _ext_from_url,
    _extract_tweets_from_timeline,
    _extract_users_from_timeline,
    _find_instructions,
    _parse_scheduled_tweets,
    _parse_trends,
    _parse_tweet_entry,
    _parse_tweet_volume,
    _parse_user_lists,
    _validate_media_file,
    get_bookmarks,
    get_trending,
)
from clix.core.client import APIError

# =============================================================================
# Shared fixtures — minimal API result shapes
# =============================================================================


def _make_user_result(
    rest_id: str = "123",
    screen_name: str = "testuser",
    name: str = "Test User",
) -> dict:
    """Build a minimal GraphQL user result that User.from_api_result can parse."""
    return {
        "rest_id": rest_id,
        "__typename": "User",
        "core": {
            "name": name,
            "screen_name": screen_name,
        },
        "legacy": {
            "name": name,
            "screen_name": screen_name,
            "description": "",
            "followers_count": 0,
            "friends_count": 0,
            "statuses_count": 0,
            "favourites_count": 0,
            "listed_count": 0,
            "media_count": 0,
            "pinned_tweet_ids_str": [],
        },
    }


def _make_tweet_result(
    rest_id: str = "100",
    full_text: str = "hello",
    screen_name: str = "author",
) -> dict:
    """Build a minimal GraphQL tweet result that Tweet.from_api_result can parse."""
    return {
        "__typename": "Tweet",
        "rest_id": rest_id,
        "core": {
            "user_results": {"result": _make_user_result(rest_id="900", screen_name=screen_name)}
        },
        "legacy": {
            "full_text": full_text,
            "created_at": "Thu Mar 13 12:00:00 +0000 2026",
            "favorite_count": 0,
            "retweet_count": 0,
            "reply_count": 0,
            "bookmark_count": 0,
            "quote_count": 0,
            "entities": {},
        },
    }


# =============================================================================
# _find_instructions
# =============================================================================


class TestFindInstructions:
    """Verify path traversal for all known API response shapes."""

    def test_home_timeline_path(self) -> None:
        """HomeTimeline response path."""
        data = {"data": {"home": {"home_timeline_urt": {"instructions": [{"type": "ok"}]}}}}
        assert _find_instructions(data) == [{"type": "ok"}]

    def test_search_timeline_path(self) -> None:
        """SearchTimeline response path."""
        data = {
            "data": {
                "search_by_raw_query": {
                    "search_timeline": {"timeline": {"instructions": [{"type": "search"}]}}
                }
            }
        }
        assert _find_instructions(data) == [{"type": "search"}]

    def test_user_timeline_v2_path(self) -> None:
        """User tweets (timeline_v2) response path."""
        data = {
            "data": {
                "user": {
                    "result": {"timeline_v2": {"timeline": {"instructions": [{"type": "user"}]}}}
                }
            }
        }
        assert _find_instructions(data) == [{"type": "user"}]

    def test_user_timeline_path(self) -> None:
        """User followers/following (timeline) response path."""
        data = {
            "data": {
                "user": {
                    "result": {"timeline": {"timeline": {"instructions": [{"type": "follow"}]}}}
                }
            }
        }
        assert _find_instructions(data) == [{"type": "follow"}]

    def test_bookmark_timeline_v2_path(self) -> None:
        """BookmarkTimeline v2 response path."""
        data = {"data": {"bookmark_timeline_v2": {"timeline": {"instructions": [{"type": "bm"}]}}}}
        assert _find_instructions(data) == [{"type": "bm"}]

    def test_bookmark_timeline_path(self) -> None:
        """BookmarkTimeline response path."""
        data = {"data": {"bookmark_timeline": {"timeline": {"instructions": [{"type": "bm2"}]}}}}
        assert _find_instructions(data) == [{"type": "bm2"}]

    def test_bookmark_collection_path(self) -> None:
        """Bookmark collection (folder) response path."""
        data = {
            "data": {
                "bookmark_collection_timeline": {"timeline": {"instructions": [{"type": "bc"}]}}
            }
        }
        assert _find_instructions(data) == [{"type": "bc"}]

    def test_bookmark_search_path(self) -> None:
        """BookmarkSearchTimeline response path."""
        data = {
            "data": {
                "search_by_raw_query": {
                    "bookmarks_search_timeline": {"timeline": {"instructions": [{"type": "bs"}]}}
                }
            }
        }
        assert _find_instructions(data) == [{"type": "bs"}]

    def test_list_tweets_path(self) -> None:
        """List tweets timeline response path."""
        data = {
            "data": {"list": {"tweets_timeline": {"timeline": {"instructions": [{"type": "lt"}]}}}}
        }
        assert _find_instructions(data) == [{"type": "lt"}]

    def test_list_members_path(self) -> None:
        """List members timeline response path."""
        data = {
            "data": {"list": {"members_timeline": {"timeline": {"instructions": [{"type": "lm"}]}}}}
        }
        assert _find_instructions(data) == [{"type": "lm"}]

    def test_threaded_conversation_path(self) -> None:
        """TweetDetail threaded conversation response path."""
        data = {
            "data": {
                "threaded_conversation_with_injections_v2": {"instructions": [{"type": "thread"}]}
            }
        }
        assert _find_instructions(data) == [{"type": "thread"}]

    def test_single_tweet_result_returns_empty(self) -> None:
        """tweetResult path hits a dict (not list) — should return empty."""
        data = {"data": {"tweetResult": {"result": {"rest_id": "1"}}}}
        assert _find_instructions(data) == []

    def test_empty_data_returns_empty(self) -> None:
        """No matching path should return empty list."""
        assert _find_instructions({}) == []
        assert _find_instructions({"data": {}}) == []
        assert _find_instructions({"data": {"unknown": {}}}) == []

    def test_non_dict_intermediate_returns_empty(self) -> None:
        """Non-dict intermediate value should not raise."""
        data = {"data": {"home": "not_a_dict"}}
        assert _find_instructions(data) == []


# =============================================================================
# _parse_tweet_entry
# =============================================================================


class TestParseTweetEntry:
    """Verify single tweet parsing from itemContent."""

    def test_parses_valid_tweet(self) -> None:
        """Standard TimelineTweet entry is parsed into a Tweet."""
        item_content = {
            "itemType": "TimelineTweet",
            "tweet_results": {"result": _make_tweet_result(rest_id="42", full_text="hi")},
        }
        tweet = _parse_tweet_entry(item_content)
        assert tweet is not None
        assert tweet.id == "42"
        assert tweet.text == "hi"

    def test_ignores_non_tweet_item_type(self) -> None:
        """Non-TimelineTweet items (e.g. TimelinePrompt) are skipped."""
        assert _parse_tweet_entry({"itemType": "TimelineUser"}) is None
        assert _parse_tweet_entry({"itemType": "TimelinePrompt"}) is None
        assert _parse_tweet_entry({}) is None

    def test_tombstone_returns_none(self) -> None:
        """TweetTombstone (deleted/withheld tweets) are skipped."""
        item_content = {
            "itemType": "TimelineTweet",
            "tweet_results": {"result": {"__typename": "TweetTombstone"}},
        }
        assert _parse_tweet_entry(item_content) is None

    def test_visibility_wrapper_unwrapped(self) -> None:
        """TweetWithVisibilityResults wrapper is unwrapped to the inner tweet."""
        inner = _make_tweet_result(rest_id="77", full_text="visible")
        item_content = {
            "itemType": "TimelineTweet",
            "tweet_results": {
                "result": {
                    "__typename": "TweetWithVisibilityResults",
                    "tweet": inner,
                }
            },
        }
        tweet = _parse_tweet_entry(item_content)
        assert tweet is not None
        assert tweet.id == "77"

    def test_empty_tweet_results(self) -> None:
        """Empty tweet_results should not crash."""
        item_content = {"itemType": "TimelineTweet", "tweet_results": {}}
        # result is {}, no __typename, from_api_result returns None
        result = _parse_tweet_entry(item_content)
        assert result is None


# =============================================================================
# _extract_users_from_timeline
# =============================================================================


class TestExtractUsersFromTimeline:
    """Verify user extraction from followers/following timeline responses."""

    def _make_response(self, entries: list) -> dict:
        """Build a user timeline API response (followers/following shape)."""
        return {
            "data": {
                "user": {
                    "result": {
                        "timeline": {
                            "timeline": {
                                "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                            }
                        }
                    }
                }
            }
        }

    def test_parses_users(self) -> None:
        """User entries are extracted from itemContent.user_results."""
        entries = [
            {
                "entryId": "user-1",
                "content": {
                    "itemContent": {"user_results": {"result": _make_user_result("1", "alice")}},
                },
            },
            {
                "entryId": "user-2",
                "content": {
                    "itemContent": {"user_results": {"result": _make_user_result("2", "bob")}},
                },
            },
        ]
        users, cursor = _extract_users_from_timeline(self._make_response(entries))
        assert len(users) == 2
        assert users[0].handle == "alice"
        assert users[1].handle == "bob"
        assert cursor is None

    def test_extracts_bottom_cursor(self) -> None:
        """Bottom cursor is extracted for pagination."""
        entries = [
            {"entryId": "cursor-bottom-abc", "content": {"value": "next_page"}},
        ]
        users, cursor = _extract_users_from_timeline(self._make_response(entries))
        assert users == []
        assert cursor == "next_page"

    def test_skips_empty_user_results(self) -> None:
        """Entries with empty user_results are silently skipped."""
        entries = [
            {
                "entryId": "user-bad",
                "content": {"itemContent": {"user_results": {"result": {}}}},
            },
        ]
        users, cursor = _extract_users_from_timeline(self._make_response(entries))
        assert users == []

    def test_empty_response(self) -> None:
        """Empty/malformed response returns no users and no cursor."""
        users, cursor = _extract_users_from_timeline({})
        assert users == []
        assert cursor is None

    def test_mixed_users_and_cursor(self) -> None:
        """Users and cursor are extracted from the same response."""
        entries = [
            {
                "entryId": "user-10",
                "content": {
                    "itemContent": {"user_results": {"result": _make_user_result("10", "charlie")}},
                },
            },
            {"entryId": "cursor-bottom-xyz", "content": {"value": "page2"}},
        ]
        users, cursor = _extract_users_from_timeline(self._make_response(entries))
        assert len(users) == 1
        assert users[0].handle == "charlie"
        assert cursor == "page2"


# =============================================================================
# _parse_scheduled_tweets
# =============================================================================


class TestParseScheduledTweets:
    """Verify parsing of FetchScheduledTweets GraphQL response."""

    def test_parses_scheduled_tweets(self) -> None:
        """Scheduled tweets are extracted with all fields."""
        data = {
            "data": {
                "viewer": {
                    "scheduled_tweet_list": [
                        {
                            "rest_id": "sched-1",
                            "scheduling_info": {
                                "execute_at": 1700000000,
                                "state": "Scheduled",
                            },
                            "tweet_create_request": {
                                "status": "Hello scheduled",
                                "media_ids": ["m1"],
                            },
                        },
                        {
                            "rest_id": "sched-2",
                            "scheduling_info": {
                                "execute_at": 1700001000,
                                "state": "Scheduled",
                            },
                            "tweet_create_request": {
                                "status": "Another one",
                            },
                        },
                    ]
                }
            }
        }
        result = _parse_scheduled_tweets(data)
        assert len(result) == 2
        assert result[0] == {
            "id": "sched-1",
            "text": "Hello scheduled",
            "execute_at": 1700000000,
            "state": "Scheduled",
            "media_ids": ["m1"],
        }
        assert result[1]["id"] == "sched-2"
        assert result[1]["media_ids"] == []

    def test_empty_scheduled_list(self) -> None:
        """No scheduled tweets returns empty list."""
        data = {"data": {"viewer": {"scheduled_tweet_list": []}}}
        assert _parse_scheduled_tweets(data) == []

    def test_missing_viewer(self) -> None:
        """Missing viewer key returns empty list."""
        assert _parse_scheduled_tweets({}) == []
        assert _parse_scheduled_tweets({"data": {}}) == []

    def test_fallback_to_id_field(self) -> None:
        """Falls back to 'id' when 'rest_id' is missing."""
        data = {
            "data": {
                "viewer": {
                    "scheduled_tweet_list": [
                        {
                            "id": 999,
                            "scheduling_info": {"state": "Scheduled"},
                            "tweet_create_request": {"status": "test"},
                        }
                    ]
                }
            }
        }
        result = _parse_scheduled_tweets(data)
        assert result[0]["id"] == "999"


# =============================================================================
# _validate_media_file
# =============================================================================


class TestValidateMediaFile:
    """Verify media file validation logic."""

    def test_valid_jpeg(self, tmp_path: Path) -> None:
        """Valid JPEG file passes validation."""
        f = tmp_path / "test.jpg"
        f.write_bytes(b"\xff\xd8\xff" + b"x" * 100)
        size, mime = _validate_media_file(str(f))
        assert size == 103
        assert mime == "image/jpeg"

    def test_valid_png(self, tmp_path: Path) -> None:
        """Valid PNG file passes validation."""
        f = tmp_path / "test.png"
        f.write_bytes(b"\x89PNG" + b"x" * 100)
        size, mime = _validate_media_file(str(f))
        assert mime == "image/png"

    def test_file_not_found(self) -> None:
        """Non-existent file raises APIError."""
        with pytest.raises(APIError, match="File not found"):
            _validate_media_file("/nonexistent/file.jpg")

    def test_not_a_file(self, tmp_path: Path) -> None:
        """Directory raises APIError."""
        with pytest.raises(APIError, match="Not a file"):
            _validate_media_file(str(tmp_path))

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file raises APIError."""
        f = tmp_path / "empty.jpg"
        f.write_bytes(b"")
        with pytest.raises(APIError, match="File is empty"):
            _validate_media_file(str(f))

    def test_file_too_large(self, tmp_path: Path) -> None:
        """File exceeding 5MB raises APIError."""
        f = tmp_path / "big.jpg"
        f.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
        with pytest.raises(APIError, match="File too large"):
            _validate_media_file(str(f))

    def test_unsupported_format(self, tmp_path: Path) -> None:
        """Non-image file raises APIError."""
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        with pytest.raises(APIError, match="Unsupported image format"):
            _validate_media_file(str(f))


# =============================================================================
# _ext_from_url
# =============================================================================


class TestExtFromUrl:
    """Verify file extension extraction from media URLs."""

    def test_jpg_url(self) -> None:
        assert _ext_from_url("https://pbs.twimg.com/media/abc.jpg") == "jpg"

    def test_png_url(self) -> None:
        assert _ext_from_url("https://pbs.twimg.com/media/abc.png") == "png"

    def test_mp4_url(self) -> None:
        assert _ext_from_url("https://video.twimg.com/abc.mp4") == "mp4"

    def test_url_with_query_params(self) -> None:
        """Extension is extracted before query string."""
        assert _ext_from_url("https://pbs.twimg.com/media/abc.jpg?format=jpg&name=large") == "jpg"

    def test_no_extension_defaults_to_jpg(self) -> None:
        """URLs without extension default to jpg."""
        assert _ext_from_url("https://pbs.twimg.com/media/abc") == "jpg"

    def test_long_extension_truncated(self) -> None:
        """Extension is truncated to 4 chars."""
        assert len(_ext_from_url("https://example.com/file.abcdef")) <= 4


# =============================================================================
# Existing tests (cursor, bookmarks, trends, user lists)
# =============================================================================


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


class TestParseUserLists:
    """Verify parsing of ListsManagementPageTimeline responses."""

    def _make_list_item(
        self,
        list_id: str,
        name: str,
        description: str = "",
        member_count: int = 0,
        subscriber_count: int = 0,
        mode: str = "Public",
    ) -> dict:
        """Build a single list item as returned by the API."""
        return {
            "entryId": f"owned-subscribed-list-module-item-{list_id}",
            "item": {
                "itemContent": {
                    "__typename": "TimelineTwitterList",
                    "list": {
                        "id_str": list_id,
                        "name": name,
                        "description": description,
                        "member_count": member_count,
                        "subscriber_count": subscriber_count,
                        "mode": mode,
                    },
                }
            },
        }

    def _make_response(self, owned_items: list, suggestion_items: list | None = None) -> dict:
        """Build a ListsManagementPageTimeline API response."""
        entries = []
        if suggestion_items:
            entries.append(
                {
                    "entryId": "list-to-follow-module-123",
                    "content": {
                        "__typename": "TimelineTimelineModule",
                        "items": suggestion_items,
                    },
                }
            )
        entries.append(
            {
                "entryId": "owned-subscribed-list-module-456",
                "content": {
                    "__typename": "TimelineTimelineModule",
                    "items": owned_items,
                },
            }
        )
        return {
            "data": {
                "viewer": {
                    "list_management_timeline": {
                        "timeline": {
                            "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                        }
                    }
                }
            }
        }

    def test_parses_owned_lists(self) -> None:
        """Owned lists are extracted from the TimelineTimelineModule items."""
        data = self._make_response(
            owned_items=[
                self._make_list_item("111", "My List", "A test list", 5, 2, "Private"),
                self._make_list_item("222", "Another", mode="Public"),
            ]
        )
        result = _parse_user_lists(data)
        assert len(result) == 2
        assert result[0] == {
            "id": "111",
            "name": "My List",
            "description": "A test list",
            "member_count": 5,
            "subscriber_count": 2,
            "mode": "Private",
        }
        assert result[1]["id"] == "222"

    def test_ignores_suggestion_lists(self) -> None:
        """Lists from the 'Discover new Lists' module are not included."""
        suggestion = {
            "entryId": "list-to-follow-item-999",
            "item": {
                "itemContent": {
                    "__typename": "TimelineTwitterList",
                    "list": {
                        "id_str": "999",
                        "name": "Suggested List",
                        "description": "",
                        "member_count": 100,
                        "subscriber_count": 50,
                        "mode": "Public",
                    },
                }
            },
        }
        data = self._make_response(owned_items=[], suggestion_items=[suggestion])
        result = _parse_user_lists(data)
        assert result == []

    def test_empty_owned_module(self) -> None:
        """Account with no lists returns empty list (MessagePrompt item)."""
        empty_prompt = {
            "entryId": "messageprompt-OwnedSubscribedListsEmptyPrompt",
            "item": {
                "itemContent": {
                    "__typename": "TimelineMessagePrompt",
                    "content": {
                        "bodyText": "You haven't created or followed any Lists.",
                    },
                }
            },
        }
        data = self._make_response(owned_items=[empty_prompt])
        result = _parse_user_lists(data)
        assert result == []

    def test_empty_response(self) -> None:
        """Completely empty or malformed response returns empty list."""
        assert _parse_user_lists({}) == []
        assert _parse_user_lists({"data": {}}) == []
        assert _parse_user_lists({"data": {"viewer": {}}}) == []

    def test_skips_items_without_id(self) -> None:
        """List items missing id_str are excluded."""
        bad_item = {
            "entryId": "owned-subscribed-list-module-item-bad",
            "item": {
                "itemContent": {
                    "__typename": "TimelineTwitterList",
                    "list": {"name": "No ID", "description": ""},
                }
            },
        }
        data = self._make_response(owned_items=[bad_item])
        result = _parse_user_lists(data)
        assert result == []
