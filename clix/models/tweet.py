"""Tweet data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class TweetMedia(BaseModel):
    """Media attachment on a tweet."""

    type: str  # photo, video, animated_gif
    url: str
    preview_url: str | None = None
    alt_text: str | None = None


class TweetEngagement(BaseModel):
    """Engagement metrics for a tweet."""

    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    bookmarks: int = 0
    views: int = 0


class Tweet(BaseModel):
    """A tweet/post."""

    id: str
    text: str
    author_id: str
    author_name: str
    author_handle: str
    author_verified: bool = False
    created_at: datetime | None = None
    engagement: TweetEngagement = Field(default_factory=TweetEngagement)
    media: list[TweetMedia] = Field(default_factory=list)
    quoted_tweet: Tweet | None = None
    reply_to_id: str | None = None
    reply_to_handle: str | None = None
    conversation_id: str | None = None
    language: str | None = None
    source: str | None = None
    is_retweet: bool = False
    retweeted_by: str | None = None
    url: str | None = None

    @computed_field
    @property
    def tweet_url(self) -> str:
        """Full URL to the tweet."""
        return f"https://x.com/{self.author_handle}/status/{self.id}"

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return self.model_dump(mode="json")

    @classmethod
    def from_api_result(cls, result: dict[str, Any]) -> Tweet | None:
        """Parse a tweet from Twitter API GraphQL result."""
        try:
            # Handle different result wrappers
            tweet_data = result
            if "tweet" in result:
                tweet_data = result["tweet"]

            core = tweet_data.get("core", {})
            user_results = core.get("user_results", {}).get("result", {})
            legacy_user = user_results.get("legacy", {})
            legacy = tweet_data.get("legacy", {})
            rest_id = tweet_data.get("rest_id", legacy.get("id_str", ""))

            if not rest_id:
                return None

            # Check for retweet
            retweeted_status = legacy.get("retweeted_status_result", {}).get("result")
            is_retweet = retweeted_status is not None

            if is_retweet and retweeted_status:
                # Parse the original tweet instead
                original = cls.from_api_result(retweeted_status)
                if original:
                    original.is_retweet = True
                    original.retweeted_by = legacy_user.get("screen_name")
                return original

            # Parse engagement
            engagement = TweetEngagement(
                likes=legacy.get("favorite_count", 0),
                retweets=legacy.get("retweet_count", 0),
                replies=legacy.get("reply_count", 0),
                quotes=legacy.get("quote_count", 0),
                bookmarks=legacy.get("bookmark_count", 0),
                views=int(tweet_data.get("views", {}).get("count", 0) or 0),
            )

            # Parse media
            media_list: list[TweetMedia] = []
            for m in legacy.get("extended_entities", {}).get("media", []):
                media_type = m.get("type", "photo")
                if media_type == "video" or media_type == "animated_gif":
                    variants = m.get("video_info", {}).get("variants", [])
                    mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
                    url = max(mp4s, key=lambda v: v.get("bitrate", 0))["url"] if mp4s else ""
                else:
                    url = m.get("media_url_https", "")

                media_list.append(
                    TweetMedia(
                        type=media_type,
                        url=url,
                        preview_url=m.get("media_url_https"),
                        alt_text=m.get("ext_alt_text"),
                    )
                )

            # Parse timestamp
            created_at = None
            raw_date = legacy.get("created_at")
            if raw_date:
                try:
                    created_at = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %z %Y")
                except (ValueError, TypeError):
                    pass

            # Get full text
            text = legacy.get("full_text", legacy.get("text", ""))

            # Parse quoted tweet
            quoted = None
            quoted_result = tweet_data.get("quoted_status_result", {}).get("result")
            if quoted_result:
                quoted = cls.from_api_result(quoted_result)

            return cls(
                id=rest_id,
                text=text,
                author_id=user_results.get("rest_id", ""),
                author_name=legacy_user.get("name", ""),
                author_handle=legacy_user.get("screen_name", ""),
                author_verified=user_results.get("is_blue_verified", False),
                created_at=created_at,
                engagement=engagement,
                media=media_list,
                quoted_tweet=quoted,
                reply_to_id=legacy.get("in_reply_to_status_id_str"),
                reply_to_handle=legacy.get("in_reply_to_screen_name"),
                conversation_id=legacy.get("conversation_id_str"),
                language=legacy.get("lang"),
                source=tweet_data.get("source"),
            )
        except (KeyError, TypeError, IndexError):
            return None


class TimelineResponse(BaseModel):
    """Response from a timeline/search API call."""

    tweets: list[Tweet] = Field(default_factory=list)
    cursor_top: str | None = None
    cursor_bottom: str | None = None
    has_more: bool = False
