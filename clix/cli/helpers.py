"""Shared CLI helpers — avoids circular imports between app.py and subcommands."""

from __future__ import annotations

import json
import os
import sys

import typer
from rich.console import Console

from clix.core.auth import AuthError
from clix.core.config import Config
from clix.core.constants import EXIT_AUTH_ERROR

console = Console()


def is_json_mode(json_flag: bool) -> bool:
    """Determine if output should be JSON (explicit flag or non-TTY)."""
    return json_flag or not sys.stdout.isatty()


def output_json(data: object) -> None:
    """Print JSON output."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")  # type: ignore[union-attr]
    elif isinstance(data, list):
        data = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in data
        ]
    print(json.dumps(data, indent=2, default=str))


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
