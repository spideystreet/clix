"""Shared CLI helpers — avoids circular imports between app.py and subcommands."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import typer
from rich.console import Console

from clix.core.auth import AuthError
from clix.core.config import Config
from clix.core.constants import EXIT_AUTH_ERROR

console = Console()


def is_json_mode(json_flag: bool) -> bool:
    """Determine if output should be JSON (explicit flag or non-TTY)."""
    return json_flag or not sys.stdout.isatty()


def get_output_mode(json_flag: bool = False, compact_flag: bool = False) -> str:
    """Return output mode: 'rich', 'json', or 'compact'."""
    if compact_flag:
        return "compact"
    if json_flag or not sys.stdout.isatty():
        return "json"
    return "rich"


def is_compact_mode(ctx: typer.Context) -> bool:
    """Check if compact mode is enabled via the global --compact flag."""
    return bool((ctx.obj or {}).get("compact", False))


def validate_output_flags(json_flag: bool, yaml_flag: bool) -> None:
    """Raise an error if both --json and --yaml are passed."""
    if json_flag and yaml_flag:
        raise typer.BadParameter("--json and --yaml are mutually exclusive")


def output_json(data: object) -> None:
    """Print JSON output."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")  # type: ignore[union-attr]
    elif isinstance(data, list):
        data = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in data
        ]
    print(json.dumps(data, indent=2, default=str))


def _compact_tweet(tweet: Any) -> dict[str, Any]:
    """Produce a minimal dict for a single tweet."""
    created = ""
    if tweet.created_at:
        created = tweet.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": tweet.id,
        "author": f"@{tweet.author_handle}",
        "text": tweet.text[:140],
        "likes": tweet.engagement.likes,
        "rts": tweet.engagement.retweets,
        "time": created,
    }


def _compact_user(user: Any) -> dict[str, Any]:
    """Produce a minimal dict for a single user."""
    return {
        "handle": f"@{user.handle}",
        "name": user.name,
        "followers": user.followers_count,
        "bio": user.bio[:120] if user.bio else "",
    }


def output_compact(data: list[Any] | Any, *, kind: str = "tweets") -> None:
    """Minimal JSON output optimized for LLM token efficiency.

    Args:
        data: A list of tweets/users or a single user/tweet object.
        kind: 'tweets', 'users', or 'user' to select the compact format.
    """
    if kind == "user":
        print(json.dumps(_compact_user(data), separators=(",", ":")))
        return

    if kind == "users":
        items = [_compact_user(u) for u in data]
    else:
        items = [_compact_tweet(t) for t in data]

    print(json.dumps(items, separators=(",", ":")))


def is_yaml_mode(yaml_flag: bool) -> bool:
    """Determine if output should be YAML (explicit flag)."""
    return yaml_flag


def output_yaml(data: list | dict | object) -> None:
    """Output data as YAML."""
    import yaml

    if isinstance(data, list):
        serialized = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in data
        ]
    elif hasattr(data, "model_dump"):
        serialized = data.model_dump(mode="json")  # type: ignore[union-attr]
    else:
        serialized = data
    print(
        yaml.safe_dump(serialized, allow_unicode=True, sort_keys=False, default_flow_style=False),
        end="",
    )


def get_client(account: str | None = None, proxy: str | None = None):
    """Create an XClient with error handling.

    Proxy resolution order: explicit arg > CLIX_PROXY env > config file > XClient defaults.
    """
    from clix.core.client import XClient

    resolved_proxy = proxy or os.environ.get("CLIX_PROXY") or Config.load().network.proxy

    try:
        return XClient(account=account, proxy=resolved_proxy or None)
    except AuthError as e:
        from clix.display.formatter import print_error

        print_error(str(e))
        raise typer.Exit(EXIT_AUTH_ERROR)
