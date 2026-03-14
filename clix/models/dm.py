"""Pydantic models for direct messages."""

from __future__ import annotations

from pydantic import BaseModel


class DMConversation(BaseModel):
    """A DM conversation summary."""

    id: str
    type: str = "one_to_one"
    participants: list[dict] = []
    last_message: str = ""
    last_message_time: str = ""
    unread: bool = False


class DMMessage(BaseModel):
    """A single DM message."""

    id: str
    sender_id: str
    sender_name: str = ""
    text: str
    created_at: str
    conversation_id: str = ""
