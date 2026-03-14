"""MCP server for clix — Twitter/X CLI tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from clix.core.api import (
    bookmark_tweet as _bookmark_tweet,
)
from clix.core.api import (
    create_tweet as _create_tweet,
)
from clix.core.api import (
    delete_tweet as _delete_tweet,
)
from clix.core.api import (
    follow_user as _follow_user,
)
from clix.core.api import (
    get_bookmarks as _get_bookmarks,
)
from clix.core.api import (
    get_home_timeline,
    get_tweet_detail,
    get_user_by_handle,
    search_tweets,
)
from clix.core.api import (
    like_tweet as _like_tweet,
)
from clix.core.api import (
    retweet as _retweet,
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
    unretweet as _unretweet,
)
from clix.core.auth import AuthError, get_credentials
from clix.core.client import XClient

mcp = FastMCP(
    "clix", instructions="Twitter/X CLI tool — read and write tweets, search, manage bookmarks."
)


def _error_response(error: Exception) -> str:
    """Format an error as a JSON string."""
    return json.dumps(
        {
            "error": str(error),
            "type": type(error).__name__,
        }
    )


def _serialize(obj: object) -> str:
    """Serialize a pydantic model or dict to JSON."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), default=str)
    return json.dumps(obj, default=str)


# =============================================================================
# Read Tools
# =============================================================================


@mcp.tool()
def get_feed(type: str = "for-you", count: int = 20) -> str:
    """Fetch the home timeline.

    Args:
        type: Timeline type — "for-you" or "following".
        count: Number of tweets to fetch (max 100).
    """
    try:
        with XClient() as client:
            response = get_home_timeline(client, timeline_type=type, count=count)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def search(query: str, type: str = "Top", count: int = 20) -> str:
    """Search for tweets.

    Args:
        query: Search query string.
        type: Search type — "Top", "Latest", "Photos", or "Videos".
        count: Number of results to return (max 100).
    """
    try:
        with XClient() as client:
            response = search_tweets(client, query=query, search_type=type, count=count)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


@mcp.tool()
def get_tweet(id: str, thread: bool = False) -> str:
    """Fetch a tweet by ID, optionally with its conversation thread.

    Args:
        id: The tweet ID.
        thread: If True, return the full conversation thread.
    """
    try:
        with XClient() as client:
            tweets = get_tweet_detail(client, tweet_id=id)
            if not tweets:
                return json.dumps({"error": "Tweet not found", "type": "NotFoundError"})
            if thread:
                return json.dumps([t.model_dump(mode="json") for t in tweets], default=str)
            # Return just the focal tweet (first one)
            return _serialize(tweets[0])
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
def list_bookmarks(count: int = 20) -> str:
    """Fetch bookmarked tweets.

    Args:
        count: Number of bookmarks to fetch (max 100).
    """
    try:
        with XClient() as client:
            response = _get_bookmarks(client, count=count)
            return _serialize(response)
    except Exception as e:
        return _error_response(e)


# =============================================================================
# Write Tools
# =============================================================================


@mcp.tool()
def post_tweet(text: str, reply_to: str | None = None, quote: str | None = None) -> str:
    """Post a new tweet.

    Args:
        text: The tweet text content.
        reply_to: Tweet ID to reply to (optional).
        quote: URL of tweet to quote (optional).
    """
    try:
        with XClient() as client:
            result = _create_tweet(client, text=text, reply_to_id=reply_to, quote_tweet_url=quote)
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
