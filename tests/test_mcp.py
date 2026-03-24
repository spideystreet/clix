"""Tests for MCP server tool registration and serialization."""

import json

from clix.core.auth import AuthError
from clix.core.client import APIError, RateLimitError, StaleEndpointError
from clix.mcp.server import _error_response, _serialize, mcp


def _tool_names() -> set[str]:
    """Return the set of registered MCP tool names."""
    return set(mcp._tool_manager._tools.keys())


class TestMcpToolRegistration:
    """Verify all MCP tools are registered."""

    def test_all_tools_registered(self):
        """All 44 MCP tools should be registered."""
        expected = {
            "get_feed",
            "search",
            "get_tweet",
            "get_user",
            "get_user_tweets",
            "get_user_likes",
            "get_followers",
            "get_following",
            "list_bookmarks",
            "get_bookmark_folders",
            "get_bookmark_folder_timeline",
            "get_lists",
            "get_list_timeline",
            "get_trending",
            "get_tweets_batch",
            "get_users_batch",
            "post_tweet",
            "delete_tweet",
            "like",
            "unlike",
            "retweet",
            "unretweet",
            "bookmark",
            "unbookmark",
            "follow",
            "unfollow",
            "block",
            "unblock",
            "download_media",
            "mute",
            "unmute",
            "schedule_tweet",
            "list_scheduled_tweets",
            "cancel_scheduled_tweet",
            "auth_status",
            "create_list",
            "delete_list",
            "add_list_member",
            "remove_list_member",
            "get_list_members",
            "pin_list",
            "unpin_list",
            "dm_inbox",
            "dm_send",
            "dm_delete",
            "search_jobs",
            "get_job",
        }
        assert _tool_names() == expected

    def test_tool_count(self):
        """Exactly 47 tools should be registered."""
        assert len(_tool_names()) == 47

    def test_read_tools_present(self):
        """Read tools should be registered."""
        read_tools = {
            "get_feed",
            "search",
            "get_tweet",
            "get_user",
            "get_user_tweets",
            "get_user_likes",
            "get_followers",
            "get_following",
            "list_bookmarks",
            "get_lists",
            "get_list_timeline",
            "get_trending",
        }
        assert read_tools.issubset(_tool_names())

    def test_write_tools_present(self):
        """Write tools should be registered."""
        write_tools = {
            "post_tweet",
            "delete_tweet",
            "like",
            "unlike",
            "retweet",
            "unretweet",
            "bookmark",
            "unbookmark",
            "follow",
            "unfollow",
            "block",
            "unblock",
            "create_list",
            "delete_list",
            "add_list_member",
            "remove_list_member",
            "pin_list",
            "unpin_list",
            "mute",
            "unmute",
        }
        assert write_tools.issubset(_tool_names())

    def test_list_tools_present(self):
        """List tools should be registered."""
        list_tools = {
            "create_list",
            "delete_list",
            "add_list_member",
            "remove_list_member",
            "get_list_members",
            "pin_list",
            "unpin_list",
        }
        assert list_tools.issubset(_tool_names())

    def test_auth_status_tool_present(self):
        """auth_status tool should be registered."""
        assert "auth_status" in _tool_names()


class TestSerialize:
    """Test the _serialize helper."""

    def test_serialize_dict(self):
        """Serializing a dict produces valid JSON with expected keys."""
        result = _serialize({"key": "value"})
        assert '"key": "value"' in result

    def test_serialize_list(self):
        """Serializing a list of dicts includes all entries."""
        result = _serialize([{"a": 1}, {"b": 2}])
        assert '"a": 1' in result
        assert '"b": 2' in result

    def test_serialize_empty_list(self):
        """Serializing an empty list returns '[]'."""
        result = _serialize([])
        assert result == "[]"

    def test_serialize_empty_dict(self):
        """Serializing an empty dict returns '{}'."""
        result = _serialize({})
        assert result == "{}"

    def test_serialize_nested(self):
        """Serializing nested dicts preserves inner structure."""
        result = _serialize({"outer": {"inner": "val"}})
        assert '"inner": "val"' in result

    def test_serialize_returns_string(self):
        """_serialize always returns a string."""
        assert isinstance(_serialize({"a": 1}), str)
        assert isinstance(_serialize([1, 2, 3]), str)
        assert isinstance(_serialize("hello"), str)


class TestErrorResponse:
    """Test the structured _error_response helper."""

    def test_basic_error(self):
        """A plain Exception produces error and type fields."""
        result = json.loads(_error_response(ValueError("bad input")))
        assert result["error"] == "bad input"
        assert result["type"] == "ValueError"

    def test_api_error_includes_status_code(self):
        """APIError includes status_code and response_data when set."""
        err = APIError("fail", status_code=422, response_data={"detail": "missing field"})
        result = json.loads(_error_response(err))
        assert result["status_code"] == 422
        assert result["response_data"] == {"detail": "missing field"}

    def test_rate_limit_error_retry_guidance(self):
        """RateLimitError includes retry=True with 60s backoff."""
        err = RateLimitError("rate limited", status_code=429)
        result = json.loads(_error_response(err))
        assert result["retry"] is True
        assert result["retry_after_seconds"] == 60

    def test_stale_endpoint_error_retry_guidance(self):
        """StaleEndpointError includes retry=True with 5s backoff."""
        err = StaleEndpointError("stale", status_code=404)
        result = json.loads(_error_response(err))
        assert result["retry"] is True
        assert result["retry_after_seconds"] == 5

    def test_auth_error_no_retry(self):
        """AuthError includes retry=False."""
        err = AuthError("expired cookies")
        result = json.loads(_error_response(err))
        assert result["retry"] is False
