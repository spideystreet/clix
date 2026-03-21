"""MCP server for clix — Twitter/X CLI tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from clix.core.api import (
    add_list_member as _add_list_member,
)
from clix.core.api import (
    block_user as _block_user,
)
from clix.core.api import (
    bookmark_tweet as _bookmark_tweet,
)
from clix.core.api import (
    create_list as _create_list,
)
from clix.core.api import (
    create_scheduled_tweet as _create_scheduled_tweet,
)
from clix.core.api import (
    create_tweet as _create_tweet,
)
from clix.core.api import (
    delete_list as _delete_list,
)
from clix.core.api import (
    delete_scheduled_tweet as _delete_scheduled_tweet,
)
from clix.core.api import (
    delete_tweet as _delete_tweet,
)
from clix.core.api import (
    download_tweet_media as _download_tweet_media,
)
from clix.core.api import (
    follow_user as _follow_user,
)
from clix.core.api import (
    get_article as _get_article,
)
from clix.core.api import (
    get_bookmark_folder_timeline as _get_bookmark_folder_timeline,
)
from clix.core.api import (
    get_bookmark_folders as _get_bookmark_folders,
)
from clix.core.api import (
    get_bookmarks as _get_bookmarks,
)
from clix.core.api import (
    get_dm_inbox as _get_dm_inbox,
)
from clix.core.api import (
    get_followers as _get_followers,
)
from clix.core.api import (
    get_following as _get_following,
)
from clix.core.api import (
    get_home_timeline,
    get_list_tweets,
    get_tweet_detail,
    get_user_by_handle,
    get_user_lists,
    search_tweets,
)
from clix.core.api import get_job_detail as _get_job_detail
from clix.core.api import (
    get_list_members as _get_list_members,
)
from clix.core.api import (
    get_scheduled_tweets as _get_scheduled_tweets,
)
from clix.core.api import (
    get_trending as _get_trending,
)
from clix.core.api import (
    get_tweets_by_ids as _get_tweets_by_ids,
)
from clix.core.api import (
    get_user_likes as _get_user_likes,
)
from clix.core.api import (
    get_user_tweets as _get_user_tweets,
)
from clix.core.api import (
    like_tweet as _like_tweet,
)
from clix.core.api import (
    mute_user as _mute_user,
)
from clix.core.api import (
    pin_list as _pin_list,
)
from clix.core.api import (
    remove_list_member as _remove_list_member,
)
from clix.core.api import (
    retweet as _retweet,
)
from clix.core.api import search_jobs as _search_jobs
from clix.core.api import (
    send_dm as _send_dm,
)
from clix.core.api import (
    unblock_user as _unblock_user,
)
from clix.core.api import (
    unbookmark_tweet as _unbookmark_tweet,
)
from clix.core.api import (
    unfollow_user as _unfollow_user,
)
from clix.core.api import (
    unlike_tweet as _unlike_tweet,
)
from clix.core.api import (
    unmute_user as _unmute_user,
)
from clix.core.api import (
    unpin_list as _unpin_list,
)
from clix.core.api import (
    unretweet as _unretweet,
)
from clix.core.api import (
    upload_media as _upload_media,
)
from clix.core.auth import AuthError, get_credentials
from clix.core.client import RateLimitError, StaleEndpointError, XClient

mcp = FastMCP(
    "clix", instructions="Twitter/X CLI tool — read and write tweets, search, manage bookmarks."
)


def _error_response(error: Exception) -> str:
    """Format an error as a structured JSON string with retry guidance."""
    response: dict[str, object] = {
        "error": str(error),
        "type": type(error).__name__,
    }
    if hasattr(error, "status_code") and error.status_code:
        response["status_code"] = error.status_code
    if hasattr(error, "response_data") and error.response_data:
        response["response_data"] = error.response_data
    # Retry guidance for agentic consumers
    if isinstance(error, RateLimitError):
        response["retry"] = True
        response["retry_after_seconds"] = 60
    elif isinstance(error, StaleEndpointError):
        response["retry"] = True
        response["retry_after_seconds"] = 5
    elif isinstance(error, AuthError):
        response["retry"] = False
    return json.dumps(response, default=str)


def _serialize(obj: object) -> str:
    """Serialize a pydantic model or dict to JSON."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), default=str)
    return json.dumps(obj, default=str)


# =============================================================================
# Read Tools
# =============================================================================


@mcp.tool()
def get_feed(type: str = "for-you", count: int = 20, cursor: str | None = None) -> str:
    """Fetch the home timeline.

    Args:
        type: Timeline type — "for-you" or "following".
        count: Number of tweets to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            response = get_home_timeline(client, timeline_type=type, count=count, cursor=cursor)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def search(query: str, type: str = "Top", count: int = 20, cursor: str | None = None) -> str:
    """Search for tweets.

    Args:
        query: Search query string.
        type: Search type — "Top", "Latest", "Photos", or "Videos".
        count: Number of results to return (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            response = search_tweets(
                client, query=query, search_type=type, count=count, cursor=cursor
            )
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_tweet(id: str, thread: bool = False) -> str:
    """Fetch a tweet by ID, optionally with its conversation thread.

    If the tweet is a Twitter Article, includes article_markdown in the response.

    Args:
        id: The tweet ID.
        thread: If True, return the full conversation thread.
    """
    try:
        with XClient() as client:
            tweets = get_tweet_detail(client, tweet_id=id)
            if not tweets:
                return json.dumps({"error": "Tweet not found", "type": "NotFoundError"})

            # Check if the focal tweet is an article
            article_md = None
            try:
                article_data = _get_article(client, tweet_id=id)
                if article_data:
                    from clix.utils.article import (
                        article_to_markdown,
                        extract_article_metadata,
                    )

                    article_results = article_data.get("article_results", {})
                    metadata = extract_article_metadata(article_results)
                    article_md = article_to_markdown(article_results)
            except Exception:
                # Article fetch is best-effort — don't fail the whole request
                pass

            if thread:
                result = [t.model_dump(mode="json") for t in tweets]
                if article_md:
                    result[0]["article_markdown"] = article_md
                    result[0]["article_title"] = metadata.get("title", "")
                return json.dumps(result, default=str)

            # Return just the focal tweet
            tweet_data = tweets[0].model_dump(mode="json")
            if article_md:
                tweet_data["article_markdown"] = article_md
                tweet_data["article_title"] = metadata.get("title", "")
            return json.dumps(tweet_data, default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_user(handle: str) -> str:
    """Fetch a user profile by handle.

    Args:
        handle: The user's screen name (without @).
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle)
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            return _serialize(user)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def list_bookmarks(count: int = 20, cursor: str | None = None) -> str:
    """Fetch bookmarked tweets.

    Args:
        count: Number of bookmarks to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            response = _get_bookmarks(client, count=count, cursor=cursor)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_bookmark_folders() -> str:
    """Fetch the authenticated user's bookmark folders."""
    try:
        with XClient() as client:
            folders = _get_bookmark_folders(client)
            return _serialize(folders)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_bookmark_folder_timeline(folder_id: str, count: int = 20, cursor: str | None = None) -> str:
    """Fetch tweets from a bookmark folder.

    Args:
        folder_id: The bookmark folder ID.
        count: Number of tweets to fetch.
        cursor: Pagination cursor.
    """
    try:
        with XClient() as client:
            response = _get_bookmark_folder_timeline(
                client, folder_id=folder_id, count=count, cursor=cursor
            )
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_lists() -> str:
    """Fetch the authenticated user's lists.

    Returns list metadata including id, name, member count, and description.
    """
    try:
        with XClient() as client:
            lists = get_user_lists(client)
            return json.dumps(lists, default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_list_timeline(list_id: str, count: int = 20, cursor: str | None = None) -> str:
    """Fetch tweets from a list.

    Args:
        list_id: The list ID.
        count: Number of tweets to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            response = get_list_tweets(client, list_id=list_id, count=count, cursor=cursor)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_trending() -> str:
    """Get currently trending topics on Twitter/X.

    Returns a list of trending topics with name, tweet count, context, and URL.
    """
    try:
        with XClient() as client:
            trends = _get_trending(client)
            return json.dumps(trends, default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_tweets_batch(tweet_ids: list[str]) -> str:
    """Batch fetch multiple tweets by their IDs.

    Args:
        tweet_ids: List of tweet IDs to fetch.
    """
    try:
        with XClient() as client:
            tweets = _get_tweets_by_ids(client, tweet_ids=tweet_ids)
            return json.dumps([t.model_dump(mode="json") for t in tweets], default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_users_batch(handles: list[str]) -> str:
    """Batch fetch multiple user profiles by handle.

    Args:
        handles: List of user handles (without @) to fetch.
    """
    try:
        users = []
        with XClient() as client:
            for handle in handles:
                handle = handle.lstrip("@")
                user = get_user_by_handle(client, handle=handle)
                if user:
                    users.append(user)
        return json.dumps([u.model_dump(mode="json") for u in users], default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_user_tweets(handle: str, count: int = 20, cursor: str | None = None) -> str:
    """Get tweets posted by a user. Returns tweets and pagination cursor.

    Args:
        handle: The user's screen name (without @).
        count: Number of tweets to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            response = _get_user_tweets(client, user_id=user.id, count=count, cursor=cursor)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_user_likes(handle: str, count: int = 20, cursor: str | None = None) -> str:
    """Get tweets liked by a user. Returns tweets and pagination cursor.

    Args:
        handle: The user's screen name (without @).
        count: Number of tweets to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            response = _get_user_likes(client, user_id=user.id, count=count, cursor=cursor)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_followers(handle: str, count: int = 20, cursor: str | None = None) -> str:
    """Get followers of a user. Returns users and pagination cursor.

    Args:
        handle: The user's screen name (without @).
        count: Number of followers to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            users, next_cursor = _get_followers(client, user_id=user.id, count=count, cursor=cursor)
            return json.dumps(
                {
                    "users": [u.model_dump(mode="json") for u in users],
                    "next_cursor": next_cursor,
                },
                default=str,
            )
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_following(handle: str, count: int = 20, cursor: str | None = None) -> str:
    """Get users followed by a user. Returns users and pagination cursor.

    Args:
        handle: The user's screen name (without @).
        count: Number of users to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            users, next_cursor = _get_following(client, user_id=user.id, count=count, cursor=cursor)
            return json.dumps(
                {
                    "users": [u.model_dump(mode="json") for u in users],
                    "next_cursor": next_cursor,
                },
                default=str,
            )
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Write Tools
# =============================================================================


@mcp.tool()
def post_tweet(
    text: str,
    reply_to: str | None = None,
    quote: str | None = None,
    media_paths: list[str] | None = None,
) -> str:
    """Post a new tweet, optionally with images (up to 4).

    Args:
        text: The tweet text content.
        reply_to: Tweet ID or URL to reply to (optional).
        quote: URL of tweet to quote (optional).
        media_paths: List of file paths to images to attach (optional, max 4).
    """
    try:
        # Normalize reply-to: accept full URLs or bare tweet IDs
        if reply_to:
            from clix.cli.helpers import normalize_tweet_id

            reply_to = normalize_tweet_id(reply_to)

        media_ids: list[str] | None = None
        with XClient() as client:
            if media_paths:
                media_ids = []
                for path in media_paths:
                    mid = _upload_media(client, file_path=path)
                    media_ids.append(mid)
            result = _create_tweet(
                client,
                text=text,
                reply_to_id=reply_to,
                quote_tweet_url=quote,
                media_ids=media_ids,
            )
            if media_ids:
                result = {**result, "media_ids": media_ids}
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def delete_tweet(id: str) -> str:
    """Delete a tweet by ID.

    Args:
        id: The tweet ID to delete.
    """
    try:
        with XClient() as client:
            result = _delete_tweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def like(id: str) -> str:
    """Like a tweet.

    Args:
        id: The tweet ID to like.
    """
    try:
        with XClient() as client:
            result = _like_tweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unlike(id: str) -> str:
    """Unlike a tweet.

    Args:
        id: The tweet ID to unlike.
    """
    try:
        with XClient() as client:
            result = _unlike_tweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def retweet(id: str) -> str:
    """Retweet a tweet.

    Args:
        id: The tweet ID to retweet.
    """
    try:
        with XClient() as client:
            result = _retweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unretweet(id: str) -> str:
    """Undo a retweet.

    Args:
        id: The tweet ID to unretweet.
    """
    try:
        with XClient() as client:
            result = _unretweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def bookmark(id: str) -> str:
    """Bookmark a tweet.

    Args:
        id: The tweet ID to bookmark.
    """
    try:
        with XClient() as client:
            result = _bookmark_tweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unbookmark(id: str) -> str:
    """Remove a bookmark from a tweet.

    Args:
        id: The tweet ID to unbookmark.
    """
    try:
        with XClient() as client:
            result = _unbookmark_tweet(client, tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def follow(handle: str) -> str:
    """Follow a user by handle.

    Args:
        handle: The user's screen name (without @).
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            result = _follow_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unfollow(handle: str) -> str:
    """Unfollow a user by handle.

    Args:
        handle: The user's screen name (without @).
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle.lstrip("@"))
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            result = _unfollow_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def block(handle: str) -> str:
    """Block a user by handle.

    Args:
        handle: The user's screen name (without @).
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle)
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            result = _block_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unblock(handle: str) -> str:
    """Unblock a user by handle.

    Args:
        handle: The user's screen name (without @).
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle)
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            result = _unblock_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Media Tools
# =============================================================================


@mcp.tool()
def download_media(tweet_id: str, output_dir: str = ".") -> str:
    """Download media files (photos, videos, GIFs) from a tweet.

    Args:
        tweet_id: The tweet ID to download media from.
        output_dir: Directory to save files to (default: current directory).
    """
    try:
        with XClient() as client:
            files = _download_tweet_media(client, tweet_id, output_dir=output_dir)
            return json.dumps({"tweet_id": tweet_id, "files": files, "count": len(files)})
    except Exception as e:
        return _error_response(e)


# =============================================================================
# List Tools
# =============================================================================


@mcp.tool()
def create_list(name: str, description: str = "", is_private: bool = False) -> str:
    """Create a new list.

    Args:
        name: Name for the new list.
        description: List description.
        is_private: Whether the list should be private.
    """
    try:
        with XClient() as client:
            result = _create_list(client, name, description=description, is_private=is_private)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def delete_list(list_id: str) -> str:
    """Delete a list.

    Args:
        list_id: The list ID to delete.
    """
    try:
        with XClient() as client:
            result = _delete_list(client, list_id=list_id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def add_list_member(list_id: str, user_id: str) -> str:
    """Add a member to a list.

    Args:
        list_id: The list ID.
        user_id: The user ID to add.
    """
    try:
        with XClient() as client:
            result = _add_list_member(client, list_id=list_id, user_id=user_id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def remove_list_member(list_id: str, user_id: str) -> str:
    """Remove a member from a list.

    Args:
        list_id: The list ID.
        user_id: The user ID to remove.
    """
    try:
        with XClient() as client:
            result = _remove_list_member(client, list_id=list_id, user_id=user_id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_list_members(list_id: str, count: int = 20, cursor: str | None = None) -> str:
    """Fetch members of a list.

    Args:
        list_id: The list ID.
        count: Number of members to fetch (max 100).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            users, next_cursor = _get_list_members(
                client, list_id=list_id, count=count, cursor=cursor
            )
            return json.dumps(
                {
                    "users": [u.model_dump(mode="json") for u in users],
                    "next_cursor": next_cursor,
                },
                default=str,
            )
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def pin_list(list_id: str) -> str:
    """Pin a list.

    Args:
        list_id: The list ID to pin.
    """
    try:
        with XClient() as client:
            result = _pin_list(client, list_id=list_id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unpin_list(list_id: str) -> str:
    """Unpin a list.

    Args:
        list_id: The list ID to unpin.
    """
    try:
        with XClient() as client:
            result = _unpin_list(client, list_id=list_id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# DM Tools
# =============================================================================


@mcp.tool()
def dm_inbox() -> str:
    """Fetch DM inbox conversations.

    Returns a list of conversations with participants, last message, and time.
    """
    try:
        with XClient() as client:
            conversations = _get_dm_inbox(client)
            return json.dumps([c.model_dump() for c in conversations], default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def dm_send(handle: str, text: str) -> str:
    """Send a direct message to a user.

    Args:
        handle: The user's screen name (without @).
        text: The message text to send.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle=handle)
            if user is None:
                return json.dumps({"error": "User not found", "type": "NotFoundError"})
            result = _send_dm(client, user_id=user.id, text=text)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def mute(handle: str) -> str:
    """Mute a user.

    Args:
        handle: The username (screen name) to mute.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle)
            if not user:
                return json.dumps({"error": f"User @{handle} not found", "type": "not_found"})
            result = _mute_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def unmute(handle: str) -> str:
    """Unmute a user.

    Args:
        handle: The username (screen name) to unmute.
    """
    try:
        with XClient() as client:
            user = get_user_by_handle(client, handle)
            if not user:
                return json.dumps({"error": f"User @{handle} not found", "type": "not_found"})
            result = _unmute_user(client, user_id=user.id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Scheduled Tweets Tools
# =============================================================================


@mcp.tool()
def schedule_tweet(text: str, execute_at: int) -> str:
    """Schedule a tweet for future posting.

    Args:
        text: The tweet text content.
        execute_at: Unix timestamp (seconds) for when the tweet should be posted.
    """
    try:
        with XClient() as client:
            result = _create_scheduled_tweet(client, text=text, execute_at=execute_at)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def list_scheduled_tweets() -> str:
    """List all scheduled tweets."""
    try:
        with XClient() as client:
            tweets = _get_scheduled_tweets(client)
            return json.dumps(tweets, default=str)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def cancel_scheduled_tweet(id: str) -> str:
    """Cancel a scheduled tweet.

    Args:
        id: The scheduled tweet ID to cancel.
    """
    try:
        with XClient() as client:
            result = _delete_scheduled_tweet(client, scheduled_tweet_id=id)
            return _serialize(result)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Job Tools
# =============================================================================


@mcp.tool()
def search_jobs(
    keyword: str = "",
    location: str = "",
    location_type: list[str] | None = None,
    employment_type: list[str] | None = None,
    seniority_level: list[str] | None = None,
    company: str = "",
    industry: str = "",
    count: int = 25,
    cursor: str | None = None,
) -> str:
    """Search for job listings on X/Twitter.

    Args:
        keyword: Search keyword (e.g. "data engineer", "product manager").
        location: Location filter (e.g. "Paris", "New York").
        location_type: Location type filters (e.g. ["remote", "onsite", "hybrid"]).
        employment_type: Employment type filters (e.g. ["full_time", "contract"]).
        seniority_level: Seniority level filters (e.g. ["entry_level", "mid_level", "senior"]).
        company: Company name filter.
        industry: Industry filter.
        count: Number of results per page (max 25).
        cursor: Pagination cursor from a previous response.
    """
    try:
        with XClient() as client:
            response = _search_jobs(
                client,
                keyword=keyword,
                location=location,
                location_type=location_type,
                employment_type=employment_type,
                seniority_level=seniority_level,
                company=company,
                industry=industry,
                count=count,
                cursor=cursor,
            )
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_job(job_id: str) -> str:
    """Get detailed information about a specific job listing.

    Args:
        job_id: The job listing ID.
    """
    try:
        with XClient() as client:
            job = _get_job_detail(client, job_id=job_id)
            if not job:
                return json.dumps({"error": "Job not found", "type": "NotFoundError"})
            return _serialize(job)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Info Tools
# =============================================================================


@mcp.tool()
def auth_status() -> str:
    """Check authentication status and return credential info."""
    try:
        creds = get_credentials()
        return json.dumps(
            {
                "authenticated": True,
                "valid": creds.is_valid,
                "account": creds.account_name,
                "has_cookies": bool(creds.cookies),
            }
        )
    except AuthError as e:
        return json.dumps(
            {
                "authenticated": False,
                "valid": False,
                "error": str(e),
            }
        )
    except Exception as e:
        return _error_response(e)
