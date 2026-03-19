"""Direct message CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.core.constants import EXIT_ERROR
from clix.display.formatter import format_dm_inbox, print_error

dm_app = typer.Typer(no_args_is_help=True)


@dm_app.command("inbox")
def inbox(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """View your DM inbox."""
    from clix.core.api import get_dm_inbox

    with get_client(account) as client:
        conversations = get_dm_inbox(client)

    if is_json_mode(json_output):
        output_json([c.model_dump() for c in conversations])
    else:
        format_dm_inbox(conversations)


@dm_app.command("send")
def send(
    handle: Annotated[str, typer.Argument(help="User handle to send DM to (without @)")],
    text: Annotated[str, typer.Argument(help="Message text")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Send a direct message to a user."""
    from clix.core.api import get_user_by_handle, send_dm
    from clix.display.formatter import print_success

    handle = handle.lstrip("@")

    with get_client(account) as client:
        user = get_user_by_handle(client, handle)
        if user is None:
            print_error(f"User @{handle} not found")
            raise typer.Exit(EXIT_ERROR)

        result = send_dm(client, user.id, text)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"DM sent to @{handle}")
