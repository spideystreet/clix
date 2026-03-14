"""Tests for MCP server tool registration and serialization."""

from clix.mcp.server import _serialize, mcp


def _tool_names() -> set[str]:
    """Return the set of registered MCP tool names."""
    return set(mcp._tool_manager._tools.keys())


class TestMcpToolRegistration:
    """Verify all MCP tools are registered."""

    def test_all_tools_registered(self):
        """All 38 MCP tools should be registered."""
        expected = {
            "get_feed",
            "search",
            "get_tweet",
            "get_user",
            "list_bookmarks",
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
        }
        assert _tool_names() == expected

    def test_tool_count(self):
        """Exactly 38 tools should be registered."""
        assert len(_tool_names()) == 38

    def test_read_tools_present(self):
        """Read tools should be registered."""
        read_tools = {
            "get_feed",
            "search",
            "get_tweet",
            "get_user",
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
