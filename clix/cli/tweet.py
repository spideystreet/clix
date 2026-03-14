"""Tweet detail CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import (
    get_client,
    is_compact_mode,
    is_json_mode,
    is_yaml_mode,
    output_compact,
    output_json,
    output_yaml,
    validate_output_flags,
)
from clix.display.formatter import console, format_thread, format_tweet

tweet_app = typer.Typer(no_args_is_help=False, invoke_without_command=True)


@tweet_app.callback(invoke_without_command=True)
def tweet(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    thread: Annotated[bool, typer.Option("--thread", help="Show full thread")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a tweet and its thread."""
    if ctx.invoked_subcommand is not None:
        return

    validate_output_flags(json_output, yaml_output)

    from clix.core.api import get_tweet_detail

    with get_client(account) as client:
        tweets = get_tweet_detail(client, tweet_id)

    if not tweets:
        from clix.display.formatter import print_error

        print_error(f"Tweet {tweet_id} not found")
        raise typer.Exit(1)

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    if compact:
        output_compact(tweets)
    elif is_json_mode(json_output):
        output_json([t.to_json_dict() for t in tweets])
    elif is_yaml_mode(yaml_output):
        output_yaml([t.to_json_dict() for t in tweets])
    elif thread:
        format_thread(tweets, focal_id=tweet_id)
    else:
        # Show just the focal tweet
        focal = next((t for t in tweets if t.id == tweet_id), tweets[0])
        full_text = ctx.obj.get("full_text", False) if ctx.obj else False
        console.print(format_tweet(focal, full_text=full_text))
