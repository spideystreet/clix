"""User data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class User(BaseModel):
    """A Twitter/X user."""

    id: str
    name: str
    handle: str
    bio: str = ""
    location: str = ""
    website: str = ""
    verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    listed_count: int = 0
    created_at: datetime | None = None
    profile_image_url: str = ""
    profile_banner_url: str = ""
    pinned_tweet_id: str | None = None

    @property
    def profile_url(self) -> str:
        """Full URL to the user's profile."""
        return f"https://x.com/{self.handle}"

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return self.model_dump(mode="json")

    @classmethod
    def from_api_result(cls, result: dict[str, Any]) -> User | None:
        """Parse a user from Twitter API GraphQL result."""
        try:
            legacy = result.get("legacy", {})
            rest_id = result.get("rest_id", "")

            if not rest_id:
                return None

            created_at = None
            raw_date = legacy.get("created_at")
            if raw_date:
                try:
                    created_at = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %z %Y")
                except (ValueError, TypeError):
                    pass

            # Extract website from entities
            website = ""
            urls = legacy.get("entities", {}).get("url", {}).get("urls", [])
            if urls:
                website = urls[0].get("expanded_url", urls[0].get("url", ""))

            pinned = legacy.get("pinned_tweet_ids_str", [])

            return cls(
                id=rest_id,
                name=legacy.get("name", ""),
                handle=legacy.get("screen_name", ""),
                bio=legacy.get("description", ""),
                location=legacy.get("location", ""),
                website=website,
                verified=result.get("is_blue_verified", False),
                followers_count=legacy.get("followers_count", 0),
                following_count=legacy.get("friends_count", 0),
                tweet_count=legacy.get("statuses_count", 0),
                listed_count=legacy.get("listed_count", 0),
                created_at=created_at,
                profile_image_url=legacy.get("profile_image_url_https", "").replace(
                    "_normal", "_400x400"
                ),
                profile_banner_url=legacy.get("profile_banner_url", ""),
                pinned_tweet_id=pinned[0] if pinned else None,
            )
        except (KeyError, TypeError, IndexError):
            return None
