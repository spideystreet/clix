"""Search CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.display.formatter import format_tweet_list

search_app = typer.Typer(no_args_is_help=False, invoke_without_command=True)


@search_app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query")],
    search_type: Annotated[
        str, typer.Option("--type", "-t", help="Type: Top, Latest, Photos, Videos")
    ] = "Top",
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    pages: Annotated[int, typer.Option("--pages", "-p", help="Number of pages")] = 1,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Search for tweets."""
    if ctx.invoked_subcommand is not None:
        return

    from clix.core.api import search_tweets

    all_tweets = []
    cursor = None

    with get_client(account) as client:
        for _ in range(pages):
            response = search_tweets(client, query, search_type, count, cursor)
            all_tweets.extend(response.tweets)
            cursor = response.cursor_bottom
            if not response.has_more:
                break

    if is_json_mode(json_output):
        output_json([t.to_json_dict() for t in all_tweets])
    else:
        format_tweet_list(all_tweets)
