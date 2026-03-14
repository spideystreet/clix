"""Twitter/X API operations — read and write."""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from clix.core.client import APIError, XClient
from clix.models.dm import DMConversation
from clix.models.tweet import TimelineResponse, Tweet
from clix.models.user import User

# Media upload constants
UPLOAD_URL = "https://upload.twitter.com/i/media/upload.json"
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGES = 4


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
        ["data", "list", "members_timeline", "timeline", "instructions"],
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


def get_article(client: XClient, tweet_id: str) -> dict[str, Any] | None:
    """Fetch article data for an article tweet.

    Uses TweetResultByRestId with article-specific features and field toggles.
    Returns the article_results dict if present, or None for non-article tweets.
    """
    variables = {
        "tweetId": tweet_id,
        "withCommunity": False,
        "includePromotedContent": False,
        "withVoice": False,
    }

    # Merge operation features with article-specific overrides
    from clix.core.endpoints import get_op_features

    features = get_op_features("TweetResultByRestId")
    features.update(
        {
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "articles_preview_enabled": True,
        }
    )

    field_toggles = {
        "withArticleRichContentState": True,
        "withArticlePlainText": True,
    }

    data = client.graphql_get(
        "TweetResultByRestId",
        variables,
        features=features,
        field_toggles=field_toggles,
    )

    result = data.get("data", {}).get("tweetResult", {}).get("result", {})
    if not result:
        return None

    # Handle TweetWithVisibilityResults wrapper
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet", result)

    article_results = result.get("article_results")
    if not article_results:
        return None

    # Include tweet metadata alongside article data
    return {
        "tweet_result": result,
        "article_results": article_results,
    }


def get_tweets_by_ids(client: XClient, tweet_ids: list[str]) -> list[Tweet]:
    """Batch fetch tweets by IDs."""
    variables: dict[str, Any] = {
        "tweetIds": tweet_ids,
        "includePromotedContent": False,
        "withBirdwatchNotes": False,
        "withVoice": True,
        "withCommunity": True,
        "withQuickPromoteEligibilityTweetFields": False,
    }
    data = client.graphql_get("TweetResultsByRestIds", variables)

    results = data.get("data", {}).get("tweetResult", [])
    tweets: list[Tweet] = []
    for r in results:
        result = r.get("result", {})
        if result.get("__typename") == "TweetTombstone":
            continue
        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", result)
        tweet = Tweet.from_api_result(result)
        if tweet:
            tweets.append(tweet)
    return tweets


def get_users_by_ids(client: XClient, user_ids: list[str]) -> list[User]:
    """Batch fetch users by IDs."""
    variables: dict[str, Any] = {"userIds": user_ids}
    data = client.graphql_get("UsersByRestIds", variables)

    results = data.get("data", {}).get("users", [])
    users: list[User] = []
    for r in results:
        result = r.get("result", {})
        if result.get("__typename") == "UserUnavailable":
            continue
        user = User.from_api_result(result)
        if user:
            users.append(user)
    return users


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


def get_user_lists(client: XClient) -> list[dict[str, Any]]:
    """Fetch the authenticated user's lists."""
    variables: dict[str, Any] = {"count": 100}

    data = client.graphql_get("ListsManagementPageTimeline", variables)

    lists: list[dict[str, Any]] = []
    instructions = (
        data.get("data", {})
        .get("viewer", {})
        .get("list_management_timeline", {})
        .get("timeline", {})
        .get("instructions", [])
    )

    for instruction in instructions:
        for entry in instruction.get("entries", []):
            content = entry.get("content", {})
            item_content = content.get("itemContent", {})
            list_result = item_content.get("list", {})

            if not list_result:
                continue

            list_info: dict[str, Any] = {
                "id": list_result.get("id_str", ""),
                "name": list_result.get("name", ""),
                "description": list_result.get("description", ""),
                "member_count": list_result.get("member_count", 0),
                "subscriber_count": list_result.get("subscriber_count", 0),
                "mode": list_result.get("mode", ""),
            }
            if list_info["id"]:
                lists.append(list_info)

    return lists


# =============================================================================
# Media Upload
# =============================================================================


def _validate_media_file(file_path: str) -> tuple[int, str]:
    """Validate a media file for upload.

    Returns the file size and MIME type.
    Raises APIError if validation fails.
    """
    path = Path(file_path)

    if not path.exists():
        raise APIError(f"File not found: {file_path}")
    if not path.is_file():
        raise APIError(f"Not a file: {file_path}")

    file_size = path.stat().st_size
    if file_size > MAX_IMAGE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise APIError(f"File too large: {size_mb:.1f}MB (max {MAX_IMAGE_SIZE // (1024 * 1024)}MB)")
    if file_size == 0:
        raise APIError(f"File is empty: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise APIError(
            f"Unsupported image format: {mime_type or 'unknown'}. "
            f"Supported: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    return file_size, mime_type


def upload_media(client: XClient, file_path: str) -> str:
    """Upload an image to Twitter/X and return the media_id_string.

    Uses the chunked upload protocol (INIT → APPEND → FINALIZE).
    Endpoint: upload.twitter.com (REST, not GraphQL).
    """
    file_size, mime_type = _validate_media_file(file_path)

    # Step 1: INIT
    media_category = "tweet_gif" if mime_type == "image/gif" else "tweet_image"
    init_data = urlencode(
        {
            "command": "INIT",
            "total_bytes": file_size,
            "media_type": mime_type,
            "media_category": media_category,
        }
    )
    init_response = client.rest_post(UPLOAD_URL, data=init_data)
    media_id = init_response.get("media_id_string")
    if not media_id:
        raise APIError(f"Upload INIT failed — no media_id in response: {init_response}")

    # Step 2: APPEND
    with open(file_path, "rb") as f:
        media_data = base64.b64encode(f.read()).decode("ascii")

    append_data = urlencode(
        {
            "command": "APPEND",
            "media_id": media_id,
            "segment_index": 0,
            "media_data": media_data,
        }
    )
    client.rest_post(UPLOAD_URL, data=append_data, timeout=60)

    # Step 3: FINALIZE
    finalize_data = urlencode(
        {
            "command": "FINALIZE",
            "media_id": media_id,
        }
    )
    client.rest_post(UPLOAD_URL, data=finalize_data)

    return media_id


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


def create_scheduled_tweet(
    client: XClient,
    text: str,
    execute_at: int,
    media_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Schedule a tweet for future posting.

    Uses hardcoded GraphQL query IDs since scheduled tweet operations
    are not present in the extracted JS bundles.

    Args:
        client: Authenticated XClient instance.
        text: Tweet text content.
        execute_at: Unix timestamp (seconds) for when the tweet should be posted.
        media_ids: Optional list of media IDs to attach.
    """
    variables: dict[str, Any] = {
        "post_tweet_request": {
            "auto_populate_reply_metadata": False,
            "status": text,
            "exclude_reply_user_ids": [],
            "media_ids": media_ids or [],
        },
        "execute_at": execute_at,
    }
    return client.graphql_post_raw("LCVzRQGxOaGnOnYH01NQXg", "CreateScheduledTweet", variables)


def get_scheduled_tweets(client: XClient) -> list[dict[str, Any]]:
    """List all scheduled tweets."""
    data = client.graphql_post_raw(
        "ITtjAzvlZni2wWXwf295Qg", "FetchScheduledTweets", {"ascending": True}
    )
    return _parse_scheduled_tweets(data)


def delete_scheduled_tweet(client: XClient, scheduled_tweet_id: str) -> dict[str, Any]:
    """Cancel a scheduled tweet."""
    variables: dict[str, Any] = {"scheduled_tweet_id": scheduled_tweet_id}
    return client.graphql_post_raw("CTOVqej0JBXAZSwkp1US0g", "DeleteScheduledTweet", variables)


def _parse_scheduled_tweets(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse scheduled tweets from the FetchScheduledTweets GraphQL response."""
    tweets: list[dict[str, Any]] = []

    # GraphQL response: data.viewer.scheduled_tweet_list is a list directly
    scheduled_list = data.get("data", {}).get("viewer", {}).get("scheduled_tweet_list", [])

    for entry in scheduled_list:
        scheduling_info = entry.get("scheduling_info", {})
        tweet_info = entry.get("tweet_create_request", {})

        tweets.append(
            {
                "id": entry.get("rest_id", str(entry.get("id", ""))),
                "text": tweet_info.get("status", ""),
                "execute_at": scheduling_info.get("execute_at"),
                "state": scheduling_info.get("state", ""),
                "media_ids": tweet_info.get("media_ids", []),
            }
        )

    return tweets


def bookmark_tweet(client: XClient, tweet_id: str) -> dict[str, Any]:
    """Bookmark a tweet."""
    return client.graphql_post("CreateBookmark", {"tweet_id": tweet_id})


# =============================================================================
# List Operations
# =============================================================================


def create_list(
    client: XClient,
    name: str,
    description: str = "",
    is_private: bool = False,
) -> dict[str, Any]:
    """Create a new list."""
    variables: dict[str, Any] = {
        "isPrivate": is_private,
        "name": name,
        "description": description,
    }
    return client.graphql_post("CreateList", variables)


def delete_list(client: XClient, list_id: str) -> dict[str, Any]:
    """Delete a list."""
    return client.graphql_post("DeleteList", {"listId": list_id})


def add_list_member(client: XClient, list_id: str, user_id: str) -> dict[str, Any]:
    """Add a member to a list."""
    return client.graphql_post("ListAddMember", {"listId": list_id, "userId": user_id})


def remove_list_member(client: XClient, list_id: str, user_id: str) -> dict[str, Any]:
    """Remove a member from a list."""
    return client.graphql_post("ListRemoveMember", {"listId": list_id, "userId": user_id})


def get_list_members(
    client: XClient,
    list_id: str,
    count: int = 20,
    cursor: str | None = None,
) -> tuple[list[User], str | None]:
    """Fetch members of a list."""
    variables: dict[str, Any] = {"listId": list_id, "count": count}
    if cursor:
        variables["cursor"] = cursor

    data = client.graphql_get("ListMembers", variables)
    return _extract_users_from_timeline(data)


def pin_list(client: XClient, list_id: str) -> dict[str, Any]:
    """Pin a list."""
    return client.graphql_post("ListPinOne", {"listId": list_id})


def unpin_list(client: XClient, list_id: str) -> dict[str, Any]:
    """Unpin a list."""
    return client.graphql_post("ListUnpinOne", {"listId": list_id})


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


def block_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Block a user by their user ID."""
    return client.rest_post(
        "https://x.com/i/api/1.1/blocks/create.json",
        data={"user_id": user_id},
    )


def unblock_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Unblock a user by their user ID."""
    return client.rest_post(
        "https://x.com/i/api/1.1/blocks/destroy.json",
        data={"user_id": user_id},
    )


# =============================================================================
# Media Operations
# =============================================================================


def _ext_from_url(url: str) -> str:
    """Extract file extension from a media URL."""
    from urllib.parse import urlparse

    path = urlparse(url).path
    if "." in path:
        return path.rsplit(".", 1)[1][:4]
    return "jpg"


def download_tweet_media(client: XClient, tweet_id: str, output_dir: str = ".") -> list[str]:
    """Download all media from a tweet.

    Fetches the tweet, then downloads each media attachment (photos, videos,
    GIFs) to the specified output directory.

    Returns list of saved file paths.
    """
    from pathlib import Path

    tweets = get_tweet_detail(client, tweet_id)

    # Find the focal tweet
    focal = None
    for t in tweets:
        if t.id == tweet_id:
            focal = t
            break

    if focal is None:
        return []

    if not focal.media:
        return []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    for i, media in enumerate(focal.media):
        url = media.url
        if not url:
            continue

        # For photos, request original quality
        if media.type == "photo" and "?" not in url:
            url = f"{url}?format=jpg&name=orig"

        ext = _ext_from_url(media.url)
        filename = f"{tweet_id}_{i}.{ext}"
        filepath = output_path / filename

        response = client.session.get(url)
        filepath.write_bytes(response.content)
        downloaded.append(str(filepath))

    return downloaded


def get_trending(client: XClient) -> list[dict[str, Any]]:
    """Get trending topics from the Explore tab."""
    url = "https://x.com/i/api/2/guide.json"
    params = {
        "include_page_configuration": "false",
        "initial_tab_id": "trending",
        "count": "20",
    }
    data = client.rest_get(url, params=params)
    return _parse_trends(data)


def _parse_trends(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract trending topics from guide.json response.

    The response nests trend entries inside timeline instructions/modules.
    Each trend item contains metadata like name, tweet volume, and context.
    """
    trends: list[dict[str, Any]] = []

    timeline = data.get("timeline", {})
    instructions = timeline.get("instructions", [])

    for instruction in instructions:
        entries = instruction.get("entries", [])
        for entry in entries:
            content = entry.get("content", {})

            # Trends may be inside a TimelineTimelineModule (grouped)
            items = content.get("items", [])
            if items:
                for item in items:
                    trend = _extract_trend(item)
                    if trend:
                        trends.append(trend)

            # Or directly in entry content
            trend = _extract_trend_from_content(content)
            if trend:
                trends.append(trend)

    return trends


def _extract_trend(item: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a single trend from a module item."""
    item_content = item.get("item", {}).get("content", {})
    return _extract_trend_from_content(item_content)


def _extract_trend_from_content(content: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a single trend from content dict."""
    trend_metadata = content.get("trend", {})
    if not trend_metadata:
        return None

    name = trend_metadata.get("name")
    if not name:
        return None

    # Tweet volume (may be absent)
    tweet_count: int | None = None
    description = trend_metadata.get("trendMetadata", {})
    if description:
        meta_description = description.get("metaDescription")
        tweet_count = _parse_tweet_volume(meta_description)

    # Context / category
    context = ""
    trend_context = content.get("trendContext", {}) or content.get("socialContext", {})
    if trend_context:
        context = trend_context.get("text", "")

    # URL
    url = trend_metadata.get("url", {})
    trend_url = ""
    if isinstance(url, dict):
        trend_url = url.get("url", "")
    elif isinstance(url, str):
        trend_url = url

    return {
        "name": name,
        "tweet_count": tweet_count,
        "context": context,
        "url": trend_url,
    }


def _parse_tweet_volume(text: str | None) -> int | None:
    """Parse tweet volume from text like '1,234 posts' or '12.5K posts'."""
    if not text:
        return None

    match = re.search(r"([\d,.]+)\s*([KkMm])?\s*(posts|tweets)?", text)
    if not match:
        return None

    num_str = match.group(1).replace(",", "")
    multiplier_str = match.group(2)

    try:
        value = float(num_str)
    except ValueError:
        return None

    if multiplier_str:
        if multiplier_str.upper() == "K":
            value *= 1_000
        elif multiplier_str.upper() == "M":
            value *= 1_000_000

    return int(value)


# =============================================================================
# Direct Messages
# =============================================================================


def _parse_dm_inbox(data: dict[str, Any]) -> list[DMConversation]:
    """Parse DM inbox response into conversation summaries."""
    state = data.get("inbox_initial_state", {})
    conversations_raw = state.get("conversations", {})
    entries = state.get("entries", [])
    users = state.get("users", {})

    # Index latest message per conversation from entries
    latest_messages: dict[str, dict[str, Any]] = {}
    for entry in entries:
        msg = entry.get("message", {})
        msg_data = msg.get("message_data", {})
        conv_id = msg.get("conversation_id", entry.get("conversation_id", ""))
        if conv_id and conv_id not in latest_messages:
            latest_messages[conv_id] = {
                "text": msg_data.get("text", ""),
                "time": msg_data.get("time", msg.get("time", "")),
                "sender_id": msg_data.get("sender_id", msg.get("sender_id", "")),
            }

    conversations: list[DMConversation] = []
    for conv_id, conv in conversations_raw.items():
        conv_type = conv.get("type", "ONE_TO_ONE")
        is_group = conv_type.upper() == "GROUP_DM"

        # Build participant list
        participant_ids = [p.get("user_id", "") for p in conv.get("participants", [])]
        participants = []
        for uid in participant_ids:
            user_info = users.get(uid, {})
            participants.append(
                {
                    "id": uid,
                    "name": user_info.get("name", ""),
                    "handle": user_info.get("screen_name", ""),
                }
            )

        # Get last message info
        last_msg = latest_messages.get(conv_id, {})

        conversations.append(
            DMConversation(
                id=conv_id,
                type="group" if is_group else "one_to_one",
                participants=participants,
                last_message=last_msg.get("text", ""),
                last_message_time=last_msg.get("time", ""),
                unread=conv.get("read_only", False) is False
                and conv.get("notifications_disabled", False) is False
                and int(conv.get("last_read_event_id", "0")) < int(conv.get("sort_event_id", "0")),
            )
        )

    return conversations


def get_dm_inbox(client: XClient) -> list[DMConversation]:
    """Get DM inbox conversations."""
    from clix.core.constants import API_BASE

    url = f"{API_BASE}/1.1/dm/inbox_initial_state.json"
    params = {
        "nsfw_filtering_enabled": "false",
        "filter_low_quality": "false",
        "include_quality": "all",
        "include_profile_interstitial_type": "1",
        "include_blocking": "1",
        "include_blocked_by": "1",
        "dm_secret_conversations_enabled": "false",
        "krs_registration_enabled": "true",
        "cards_platform": "Web-12",
        "include_cards": "1",
        "include_ext_alt_text": "true",
        "include_quote_count": "true",
        "include_reply_count": "1",
        "tweet_mode": "extended",
        "include_ext_collab_control": "true",
        "include_ext_is_blue_verified": "1",
        "include_ext_has_nft_avatar": "1",
        "include_ext_vibe_tag": "1",
        "include_ext_sensitive_media_warning": "true",
        "include_ext_media_color": "true",
        "include_ext_media_availability": "true",
        "include_ext_has_birdwatch_notes": "1",
    }

    data = client._request("GET", url, params=params)
    return _parse_dm_inbox(data)


def send_dm(client: XClient, user_id: str, text: str) -> dict[str, Any]:
    """Send a DM to a user."""
    import uuid

    variables = {
        "message": {"text": {"text": text}},
        "requestId": str(uuid.uuid4()),
        "target": {"participant_ids": [user_id]},
    }
    return client.graphql_post("useSendMessageMutation", variables)


def delete_dm(client: XClient, conversation_id: str, message_id: str) -> dict[str, Any]:
    """Delete a DM message."""
    variables = {
        "conversation_id": conversation_id,
        "message_id": message_id,
    }
    return client.graphql_post("DMMessageDeleteMutation", variables)


def mute_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Mute a user."""
    return client.rest_post(
        "https://x.com/i/api/1.1/mutes/users/create.json",
        {"user_id": user_id},
    )


def unmute_user(client: XClient, user_id: str) -> dict[str, Any]:
    """Unmute a user."""
    return client.rest_post(
        "https://x.com/i/api/1.1/mutes/users/destroy.json",
        {"user_id": user_id},
    )
