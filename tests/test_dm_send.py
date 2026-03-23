"""Tests for DM send via REST API."""

from unittest.mock import MagicMock

from clix.core.api import send_dm


class TestSendDm:
    def test_calls_rest_post_with_json_body(self):
        """send_dm should use rest_post with JSON body, not graphql_post."""
        client = MagicMock()
        client.rest_post.return_value = {"entries": []}

        result = send_dm(client, "12345", "hello")

        client.rest_post.assert_called_once()
        call_kwargs = client.rest_post.call_args
        # Should use dm/new2.json endpoint
        assert "dm/new2.json" in call_kwargs.args[0]
        # Should pass JSON body, not form data
        assert call_kwargs.kwargs["json_body"] is not None
        assert call_kwargs.kwargs["json_body"]["text"] == "hello"
        assert call_kwargs.kwargs["json_body"]["recipient_ids"] == "12345"
        # Should pass query params
        assert call_kwargs.kwargs["params"] is not None
        assert call_kwargs.kwargs["params"]["include_groups"] == "true"

    def test_does_not_use_graphql(self):
        """send_dm must not call graphql_post (operation was removed from bundles)."""
        client = MagicMock()
        client.rest_post.return_value = {"entries": []}

        send_dm(client, "12345", "test")

        client.graphql_post.assert_not_called()

    def test_includes_request_id(self):
        """Each DM should have a unique request_id."""
        client = MagicMock()
        client.rest_post.return_value = {"entries": []}

        send_dm(client, "12345", "test")

        body = client.rest_post.call_args.kwargs["json_body"]
        assert "request_id" in body
        assert len(body["request_id"]) > 0
