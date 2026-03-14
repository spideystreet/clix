"""List management CLI commands."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.display.formatter import (
    format_lists,
    format_tweet_list,
    format_user_list,
    print_error,
    print_success,
)

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


@lists_app.command("create")
def lists_create(
    name: Annotated[str, typer.Argument(help="Name for the new list")],
    description: Annotated[str, typer.Option("--description", "-d", help="List description")] = "",
    private: Annotated[bool, typer.Option("--private", help="Make the list private")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Create a new list."""
    from clix.core.api import create_list

    with get_client(account) as client:
        result = create_list(client, name, description=description, is_private=private)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"List '{name}' created!")


@lists_app.command("delete")
def lists_delete(
    list_id: Annotated[str, typer.Argument(help="List ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Delete a list."""
    from clix.core.api import delete_list

    if not force and sys.stdout.isatty():
        confirm = typer.confirm(f"Delete list {list_id}?")
        if not confirm:
            raise typer.Abort()

    with get_client(account) as client:
        result = delete_list(client, list_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"List {list_id} deleted!")


@lists_app.command("members")
def lists_members(
    list_id: Annotated[str, typer.Argument(help="List ID")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of members")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """View members of a list."""
    from clix.core.api import get_list_members

    with get_client(account) as client:
        users, _ = get_list_members(client, list_id, count)

    if is_json_mode(json_output):
        output_json([u.to_json_dict() for u in users])
    else:
        format_user_list(users)


@lists_app.command("add-member")
def lists_add_member(
    list_id: Annotated[str, typer.Argument(help="List ID")],
    handle: Annotated[str, typer.Argument(help="Twitter handle to add (without @)")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Add a member to a list."""
    from clix.core.api import add_list_member, get_user_by_handle

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        result = add_list_member(client, list_id, user.id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Added @{handle} to list {list_id}")


@lists_app.command("remove-member")
def lists_remove_member(
    list_id: Annotated[str, typer.Argument(help="List ID")],
    handle: Annotated[str, typer.Argument(help="Twitter handle to remove (without @)")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Remove a member from a list."""
    from clix.core.api import get_user_by_handle, remove_list_member

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if not user:
            print_error(f"User @{handle} not found")
            raise typer.Exit(1)

        result = remove_list_member(client, list_id, user.id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Removed @{handle} from list {list_id}")


@lists_app.command("pin")
def lists_pin(
    list_id: Annotated[str, typer.Argument(help="List ID to pin")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Pin a list."""
    from clix.core.api import pin_list

    with get_client(account) as client:
        result = pin_list(client, list_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Pinned list {list_id}")


@lists_app.command("unpin")
def lists_unpin(
    list_id: Annotated[str, typer.Argument(help="List ID to unpin")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Unpin a list."""
    from clix.core.api import unpin_list

    with get_client(account) as client:
        result = unpin_list(client, list_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Unpinned list {list_id}")
