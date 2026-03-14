"""Twitter/X API operations — read and write."""

from __future__ import annotations

from typing import Any

from clix.core.client import XClient
from clix.models.tweet import TimelineResponse, Tweet
from clix.models.user import User


def _extract_tweets_from_timeline(data: dict[str, Any]) -> TimelineResponse:
    """Extract tweets and cursors from a timeline-style API response."""
    tweets: list[Tweet] = []
    cursor_top: str | None = None
    cursor_bottom: str | None = None

    # Navigate to timeline instructions
    instructions = _find_instructions(data)

    for instruction in instructions:
        inst_type = instruction.get("type", "")

        entries = []
        if inst_type == "TimelineAddEntries":
            entries = instruction.get("entries", [])
        elif inst_type == "TimelineAddToModule":
            entries = instruction.get("moduleItems", [])

        for entry in entries:
            entry_id = entry.get("entryId", "")
            content = entry.get("content", {})

            if entry_id.startswith("cursor-top"):
                cursor_top = content.get("value") or _extract_cursor(content)
            elif entry_id.startswith("cursor-bottom"):
                cursor_bottom = content.get("value") or _extract_cursor(content)
            elif "itemContent" in content:
                tweet = _parse_tweet_entry(content["itemContent"])
                if tweet:
                    tweets.append(tweet)
            elif content.get("entryType") == "TimelineTimelineModule":
                for item in content.get("items", []):
                    item_content = item.get("item", {}).get("itemContent", {})
                    tweet = _parse_tweet_entry(item_content)
                    if tweet:
                        tweets.append(tweet)

    return TimelineResponse(
        tweets=tweets,
        cursor_top=cursor_top,
        cursor_bottom=cursor_bottom,
        has_more=cursor_bottom is not None,
    )


def _find_instructions(data: dict[str, Any]) -> list[dict]:
    """Find the instructions list in API response, handling various nesting."""
    # Try common paths
    for path in [
        ["data", "home", "home_timeline_urt", "instructions"],
        ["data", "search_by_raw_query", "search_timeline", "timeline", "instructions"],
        ["data", "user", "result", "timeline_v2", "timeline", "instructions"],
        ["data", "user", "result", "timeline", "timeline", "instructions"],
        ["data", "bookmark_timeline_v2", "timeline", "instructions"],
        ["data", "bookmark_timeline", "timeline", "instructions"],
        ["data", "search_by_raw_query", "bookmarks_search_timeline", "timeline", "instructions"],
        ["data", "list", "tweets_timeline", "timeline", "instructions"],
        ["data", "threaded_conversation_with_injections_v2", "instructions"],
        ["data", "tweetResult", "result"],
    ]:
        result = data
        for key in path:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                result = None
                break
        if result is not None:
            if isinstance(result, list):
                return result
            # Single tweet result
            return []

    return []


def _extract_cursor(content: dict[str, Any]) -> str | None:
    """Extract cursor value from content."""
    cursor_type = content.get("cursorType")
    if cursor_type:
        return content.get("value")
    # Try nested
    item = content.get("itemContent", {})
    return item.get("value")


def _parse_tweet_entry(item_content: dict[str, Any]) -> Tweet | None:
    """Parse a tweet from a timeline entry's itemContent."""
    if item_content.get("itemType") != "TimelineTweet":
        return None

    tweet_results = item_content.get("tweet_results", {})
    result = tweet_results.get("result", {})

    # Handle tombstone tweets
    if result.get("__typename") == "TweetTombstone":
        return None

    # Handle TweetWithVisibilityResults wrapper
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet", result)

    return Tweet.from_api_result(result)


# =============================================================================
# Read Operations
# =============================================================================


def get_home_timeline(
    client: XClient,
    timeline_type: str = "for-you",
    count: int = 20,
    cursor: str | None = None,
) -> TimelineResponse:
    """Fetch home timeline."""
    operation = "HomeLatestTimeline" if timeline_type == "following" else "HomeTimeline"

    variables: dict[str, Any] = {
        "count": count,
        "includePromotedContent": False,
        "latestControlAvailable": True,
    }

    if timeline_type == "following":
        variables["requestContext"] = "launch"

    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get(operation, variables)
    return _extract_tweets_from_timeline(data)


def get_tweet_detail(client: XClient, tweet_id: str) -> list[Tweet]:
    """Fetch a tweet and its conversation thread."""
    variables = {
        "focalTweetId": tweet_id,
        "with_rux_injections": False,
        "includePromotedContent": False,
        "withCommunity": True,
        "withQuickPromoteEligibilityTweetFields": False,
        "withBirdwatchNotes": True,
        "withVoice": True,
        "withV2Timeline": True,
    }

    data = client.graphql_get("TweetDetail", variables)

    # Parse threaded conversation
    tweets: list[Tweet] = []
    instructions = (
        data.get("data", {})
        .get("threaded_conversation_with_injections_v2", {})
        .get("instructions", [])
    )

    for instruction in instructions:
        for entry in instruction.get("entries", []):
            content = entry.get("content", {})

            if "itemContent" in content:
                tweet = _parse_tweet_entry(content["itemContent"])
                if tweet:
                    tweets.append(tweet)
            elif content.get("entryType") == "TimelineTimelineModule":
                for item in content.get("items", []):
                    item_content = item.get("item", {}).get("itemContent", {})
                    tweet = _parse_tweet_entry(item_content)
                    if tweet:
                        tweets.append(tweet)

    return tweets


def search_tweets(
    client: XClient,
    query: str,
    search_type: str = "Top",
    count: int = 20,
    cursor: str | None = None,
) -> TimelineResponse:
    """Search for tweets."""
    variables: dict[str, Any] = {
        "rawQuery": query,
        "count": count,
        "querySource": "typed_query",
        "product": search_type,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("SearchTimeline", variables)
    return _extract_tweets_from_timeline(data)


def get_user_by_handle(client: XClient, handle: str) -> User | None:
    """Fetch user profile by screen name."""
    variables = {
        "screen_name": handle,
        "withSafetyModeUserFields": True,
    }

    data = client.graphql_get("UserByScreenName", variables)
    result = data.get("data", {}).get("user", {}).get("result", {})

    if not result or result.get("__typename") == "UserUnavailable":
        return None

    return User.from_api_result(result)


def get_user_tweets(
    client: XClient,
    user_id: str,
    count: int = 20,
    cursor: str | None = None,
    include_replies: bool = False,
) -> TimelineResponse:
    """Fetch tweets from a user."""
    operation = "UserTweetsAndReplies" if include_replies else "UserTweets"

    variables: dict[str, Any] = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": False,
        "withVoice": True,
        "withV2Timeline": True,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get(operation, variables)
    return _extract_tweets_from_timeline(data)


def get_user_likes(
    client: XClient,
    user_id: str,
    count: int = 20,
    cursor: str | None = None,
) -> TimelineResponse:
    """Fetch likes from a user."""
    variables: dict[str, Any] = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": False,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("Likes", variables)
    return _extract_tweets_from_timeline(data)


def get_followers(
    client: XClient,
    user_id: str,
    count: int = 20,
    cursor: str | None = None,
) -> tuple[list[User], str | None]:
    """Fetch followers of a user."""
    variables: dict[str, Any] = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": False,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("Followers", variables)
    return _extract_users_from_timeline(data)


def get_following(
    client: XClient,
    user_id: str,
    count: int = 20,
    cursor: str | None = None,
) -> tuple[list[User], str | None]:
    """Fetch users followed by a user."""
    variables: dict[str, Any] = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": False,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("Following", variables)
    return _extract_users_from_timeline(data)


def _extract_users_from_timeline(data: dict[str, Any]) -> tuple[list[User], str | None]:
    """Extract users from a timeline response (followers/following)."""
    users: list[User] = []
    next_cursor: str | None = None
    instructions = _find_instructions(data)

    for instruction in instructions:
        for entry in instruction.get("entries", []):
            entry_id = entry.get("entryId", "")
            content = entry.get("content", {})

            if entry_id.startswith("cursor-bottom"):
                next_cursor = content.get("value") or _extract_cursor(content)
            elif "itemContent" in content:
                user_results = content["itemContent"].get("user_results", {}).get("result", {})
                if user_results:
                    user = User.from_api_result(user_results)
                    if user:
                        users.append(user)

    return users, next_cursor


def get_bookmarks(
    client: XClient,
    count: int = 20,
    cursor: str | None = None,
) -> TimelineResponse:
    """Fetch bookmarked tweets."""
    variables: dict[str, Any] = {
        "count": count,
        "includePromotedContent": False,
        "rawQuery": "a OR e OR i OR o OR u OR t OR s OR n OR r OR l",
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("BookmarkSearchTimeline", variables)
    return _extract_tweets_from_timeline(data)


def get_list_tweets(
    client: XClient,
    list_id: str,
    count: int = 20,
    cursor: str | None = None,
) -> TimelineResponse:
    """Fetch tweets from a list."""
    variables: dict[str, Any] = {
        "listId": list_id,
        "count": count,
    }
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("ListLatestTweetsTimeline", variables)
    return _extract_tweets_from_timeline(data)


# =============================================================================
# Write Operations
# =============================================================================


def create_tweet(
    client: XClient,
    text: str,
    reply_to_id: str | None = None,
    quote_tweet_url: str | None = None,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new tweet."""
    variables: dict[str, Any] = {
        "tweet_text": text,
        "dark_request": False,
        "media": {
            "media_entities": [{"media_id": mid, "tagged_users": []} for mid in (media_ids or [])],
            "possibly_sensitive": False,
        },
        "semantic_annotation_ids": [],
    }

    if reply_to_id:
        variables["reply"] = {
            "in_reply_to_tweet_id": reply_to_id,
            "exclude_reply_user_ids": [],
        }

    if quote_tweet_url:
        variables["attachment_url"] = quote_tweet_url

    return client.graphql_post("CreateTweet", variables)


def delete_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Delete a tweet."""
    return client.graphql_post("DeleteTweet", {"tweet_id": tweet_id})


def like_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Like a tweet."""
    return client.graphql_post("FavoriteTweet", {"tweet_id": tweet_id})


def unlike_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Unlike a tweet."""
    return client.graphql_post("UnfavoriteTweet", {"tweet_id": tweet_id})


def retweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Retweet a tweet."""
    return client.graphql_post("CreateRetweet", {"tweet_id": tweet_id})


def unretweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Undo a retweet."""
    return client.graphql_post("DeleteRetweet", {"source_tweet_id": tweet_id})


def bookmark_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Bookmark a tweet."""
    return client.graphql_post("CreateBookmark", {"tweet_id": tweet_id})


def unbookmark_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Remove a bookmark."""
    return client.graphql_post("DeleteBookmark", {"tweet_id": tweet_id})


def follow_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Follow a user by ID."""
    return client.rest_post(
        "https://x.com/i/api/1.1/friendships/create.json",
        data={
            "user_id": user_id,
            "include_profile_interstitial_type": "1",
        },
    )


def unfollow_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Unfollow a user by ID."""
    return client.rest_post(
        "https://x.com/i/api/1.1/friendships/destroy.json",
        data={
            "user_id": user_id,
            "include_profile_interstitial_type": "1",
        },
    )
