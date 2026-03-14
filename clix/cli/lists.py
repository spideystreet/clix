"""Lists CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.display.formatter import format_lists, format_tweet_list

lists_app = typer.Typer(no_args_is_help=False, invoke_without_command=True)


@lists_app.callback(invoke_without_command=True)
def lists_cmd(
    ctx: typer.Context,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """View your lists."""
    if ctx.invoked_subcommand is not None:
        return

    from clix.core.api import get_user_lists

    with get_client(account) as client:
        user_lists = get_user_lists(client)

    if is_json_mode(json_output):
        output_json(user_lists)
    else:
        format_lists(user_lists)


@lists_app.command("view")
def list_view(
    list_id: Annotated[str, typer.Argument(help="List ID")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """View tweets from a list."""
    from clix.core.api import get_list_tweets

    with get_client(account) as client:
        response = get_list_tweets(client, list_id, count)

    if is_json_mode(json_output):
        output_json([t.to_json_dict() for t in response.tweets])
    else:
        format_tweet_list(response.tweets)
