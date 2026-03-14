"""Tests for DM models and inbox parsing."""

from clix.core.api import _parse_dm_inbox
from clix.models.dm import DMConversation, DMMessage


class TestDMConversationModel:
    def test_create_conversation(self):
        conv = DMConversation(
            id="conv-123",
            type="one_to_one",
            participants=[{"id": "1", "name": "Alice", "handle": "alice"}],
            last_message="Hello!",
            last_message_time="1710000000000",
        )
        assert conv.id == "conv-123"
        assert conv.type == "one_to_one"
        assert len(conv.participants) == 1
        assert conv.last_message == "Hello!"
        assert conv.unread is False

    def test_conversation_defaults(self):
        conv = DMConversation(id="conv-456")
        assert conv.type == "one_to_one"
        assert conv.participants == []
        assert conv.last_message == ""
        assert conv.unread is False

    def test_group_conversation(self):
        conv = DMConversation(
            id="conv-789",
            type="group",
            participants=[
                {"id": "1", "name": "Alice", "handle": "alice"},
                {"id": "2", "name": "Bob", "handle": "bob"},
            ],
        )
        assert conv.type == "group"
        assert len(conv.participants) == 2


class TestDMMessageModel:
    def test_create_message(self):
        msg = DMMessage(
            id="msg-1",
            sender_id="123",
            sender_name="Alice",
            text="Hey there!",
            created_at="1710000000000",
            conversation_id="conv-1",
        )
        assert msg.id == "msg-1"
        assert msg.text == "Hey there!"
        assert msg.sender_name == "Alice"

    def test_message_defaults(self):
        msg = DMMessage(
            id="msg-2",
            sender_id="456",
            text="Hello",
            created_at="1710000000000",
        )
        assert msg.sender_name == ""
        assert msg.conversation_id == ""


class TestParseDmInbox:
    def test_empty_response(self):
        result = _parse_dm_inbox({})
        assert result == []

    def test_empty_inbox(self):
        data = {
            "inbox_initial_state": {
                "conversations": {},
                "entries": [],
                "users": {},
            }
        }
        result = _parse_dm_inbox(data)
        assert result == []

    def test_single_conversation(self):
        data = {
            "inbox_initial_state": {
                "conversations": {
                    "conv-1": {
                        "type": "ONE_TO_ONE",
                        "participants": [
                            {"user_id": "111"},
                            {"user_id": "222"},
                        ],
                        "last_read_event_id": "10",
                        "sort_event_id": "10",
                    }
                },
                "entries": [
                    {
                        "message": {
                            "conversation_id": "conv-1",
                            "message_data": {
                                "text": "Hello!",
                                "time": "1710000000000",
                                "sender_id": "111",
                            },
                        }
                    }
                ],
                "users": {
                    "111": {"name": "Alice", "screen_name": "alice"},
                    "222": {"name": "Bob", "screen_name": "bob"},
                },
            }
        }
        result = _parse_dm_inbox(data)
        assert len(result) == 1
        conv = result[0]
        assert conv.id == "conv-1"
        assert conv.type == "one_to_one"
        assert len(conv.participants) == 2
        assert conv.last_message == "Hello!"
        assert conv.participants[0]["handle"] == "alice"

    def test_group_conversation(self):
        data = {
            "inbox_initial_state": {
                "conversations": {
                    "conv-g": {
                        "type": "GROUP_DM",
                        "participants": [
                            {"user_id": "1"},
                            {"user_id": "2"},
                            {"user_id": "3"},
                        ],
                    }
                },
                "entries": [],
                "users": {},
            }
        }
        result = _parse_dm_inbox(data)
        assert len(result) == 1
        assert result[0].type == "group"
        assert len(result[0].participants) == 3

    def test_unread_detection(self):
        """Conversation is unread when sort_event_id > last_read_event_id."""
        data = {
            "inbox_initial_state": {
                "conversations": {
                    "conv-u": {
                        "type": "ONE_TO_ONE",
                        "participants": [],
                        "last_read_event_id": "5",
                        "sort_event_id": "10",
                    }
                },
                "entries": [],
                "users": {},
            }
        }
        result = _parse_dm_inbox(data)
        assert result[0].unread is True
