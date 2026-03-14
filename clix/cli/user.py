"""User profile CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.display.formatter import (
    console,
    format_tweet_list,
    format_user,
    format_user_list,
    print_error,
)

user_app = typer.Typer(no_args_is_help=False, invoke_without_command=True)


@user_app.callback(invoke_without_command=True)
def user_profile(
    ctx: typer.Context,
    handle: Annotated[str, typer.Argument(help="Twitter handle (without @)")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a user's profile."""
    if ctx.invoked_subcommand is not None:
        return

    from clix.core.api import get_user_by_handle

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)

    if not user:
        print_error(f"User @{handle} not found")
        raise typer.Exit(1)

    if is_json_mode(json_output):
        output_json(user.to_json_dict())
    else:
        console.print(format_user(user))


@user_app.command("tweets")
def user_tweets(
    ctx: typer.Context,
    handle: Annotated[str, typer.Argument(help="Twitter handle")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    replies: Annotated[bool, typer.Option("--replies", help="Include replies")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a user's tweets."""
    from clix.core.api import get_user_by_handle, get_user_tweets

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        response = get_user_tweets(client, user.id, count, include_replies=replies)

    if is_json_mode(json_output):
        output_json([t.to_json_dict() for t in response.tweets])
    else:
        full_text = ctx.obj.get("full_text", False) if ctx.obj else False
        format_tweet_list(response.tweets, full_text=full_text)


@user_app.command("likes")
def user_likes(
    ctx: typer.Context,
    handle: Annotated[str, typer.Argument(help="Twitter handle")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a user's liked tweets."""
    from clix.core.api import get_user_by_handle, get_user_likes

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        response = get_user_likes(client, user.id, count)

    if is_json_mode(json_output):
        output_json([t.to_json_dict() for t in response.tweets])
    else:
        full_text = ctx.obj.get("full_text", False) if ctx.obj else False
        format_tweet_list(response.tweets, full_text=full_text)


@user_app.command("followers")
def user_followers(
    handle: Annotated[str, typer.Argument(help="Twitter handle")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of users")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a user's followers."""
    from clix.core.api import get_followers, get_user_by_handle

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        users, _ = get_followers(client, user.id, count)

    if is_json_mode(json_output):
        output_json([u.to_json_dict() for u in users])
    else:
        format_user_list(users)


@user_app.command("following")
def user_following(
    handle: Annotated[str, typer.Argument(help="Twitter handle")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of users")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View who a user follows."""
    from clix.core.api import get_following, get_user_by_handle

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        users, _ = get_following(client, user.id, count)

    if is_json_mode(json_output):
        output_json([u.to_json_dict() for u in users])
    else:
        format_user_list(users)
