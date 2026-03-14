"""Main CLI application."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console

from clix.cli.helpers import get_client, is_json_mode, output_json
from clix.core.auth import (
    AuthCredentials,
    AuthError,
    extract_cookies_from_browser,
    get_credentials,
    import_cookies_from_file,
    list_accounts,
    save_auth,
    set_default_account,
)
from clix.core.constants import EXIT_AUTH_ERROR, EXIT_ERROR
from clix.display.formatter import print_error, print_success, print_warning

app = typer.Typer(
    name="clix",
    help="Twitter/X CLI — browse, search, and post from your terminal.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


# =============================================================================
# Auth commands
# =============================================================================

auth_app = typer.Typer(help="Manage authentication")
app.add_typer(auth_app, name="auth")


@auth_app.command("status")
def auth_status(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Check authentication status."""
    try:
        creds = get_credentials(account)
        info = {
            "authenticated": True,
            "auth_token": creds.auth_token[:8] + "..." if creds.auth_token else None,
            "ct0": creds.ct0[:8] + "..." if creds.ct0 else None,
            "account": creds.account_name,
        }
        if is_json_mode(json_output):
            output_json(info)
        else:
            print_success(f"Authenticated (token: {info['auth_token']})")
            if creds.account_name:
                console.print(f"  Account: [cyan]{creds.account_name}[/cyan]")
    except AuthError:
        if is_json_mode(json_output):
            output_json({"authenticated": False})
        else:
            print_error("Not authenticated")
        raise typer.Exit(EXIT_AUTH_ERROR)


@auth_app.command("login")
def auth_login(
    browser: Annotated[
        str | None, typer.Option(help="Browser: chrome, firefox, edge, brave")
    ] = None,
    account: Annotated[str, typer.Option(help="Account name")] = "default",
):
    """Extract cookies from browser and save."""
    console.print(f"Extracting cookies from {browser or 'available browsers'}...")
    creds = extract_cookies_from_browser(browser)

    if creds and creds.is_valid:
        save_auth(creds, account)
        print_success(f"Authenticated! Saved as account '{account}'")
    else:
        print_error(
            "Could not extract cookies. Make sure you're logged into X/Twitter in your browser."
        )
        raise typer.Exit(EXIT_AUTH_ERROR)


@auth_app.command("import")
def auth_import(
    file: Annotated[str, typer.Argument(help="Path to Cookie Editor JSON export")],
    account: Annotated[str, typer.Option(help="Account name")] = "default",
):
    """Import cookies from a Cookie Editor JSON export file."""
    creds = import_cookies_from_file(file)

    if creds and creds.is_valid:
        save_auth(creds, account)
        print_success(f"Imported cookies! Saved as account '{account}'")
    else:
        print_error(
            "Could not find auth_token/ct0 in the file. "
            "Make sure you exported cookies from x.com with Cookie Editor."
        )
        raise typer.Exit(EXIT_AUTH_ERROR)


@auth_app.command("set")
def auth_set(
    auth_token: Annotated[
        str, typer.Option("--token", help="auth_token cookie value", prompt=True)
    ],
    ct0: Annotated[str, typer.Option("--ct0", help="ct0 cookie value", prompt=True)],
    account: Annotated[str, typer.Option(help="Account name")] = "default",
):
    """Manually set authentication credentials."""
    creds = AuthCredentials(auth_token=auth_token, ct0=ct0, account_name=account)
    save_auth(creds, account)
    print_success(f"Credentials saved as account '{account}'")


@auth_app.command("accounts")
def auth_accounts(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
):
    """List stored accounts."""
    accounts = list_accounts()
    if is_json_mode(json_output):
        output_json({"accounts": accounts})
    else:
        if not accounts:
            print_warning("No accounts stored")
        else:
            for acc in accounts:
                console.print(f"  [cyan]{acc}[/cyan]")


@auth_app.command("switch")
def auth_switch(
    account: Annotated[str, typer.Argument(help="Account name to switch to")],
):
    """Switch default account."""
    if set_default_account(account):
        print_success(f"Switched to account '{account}'")
    else:
        print_error(f"Account '{account}' not found")
        raise typer.Exit(EXIT_ERROR)


# =============================================================================
# Config command
# =============================================================================


@app.command("config")
def config_cmd(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
):
    """Show current configuration."""
    from clix.core.config import Config

    cfg = Config.load()
    if is_json_mode(json_output):
        output_json(cfg.model_dump())
    else:
        console.print(cfg.model_dump())


# =============================================================================
# Bookmarks command
# =============================================================================


@app.command("bookmarks")
def bookmarks_cmd(
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View your bookmarks."""
    from clix.core.api import get_bookmarks
    from clix.display.formatter import format_tweet_list

    with get_client(account) as client:
        response = get_bookmarks(client, count)

    if is_json_mode(json_output):
        output_json([t.to_json_dict() for t in response.tweets])
    else:
        format_tweet_list(response.tweets)


# =============================================================================
# Quick action shortcuts (top-level)
# =============================================================================


@app.command("post")
def post(
    text: Annotated[str, typer.Argument(help="Tweet text")],
    reply_to: Annotated[str | None, typer.Option("--reply-to", help="Tweet ID to reply to")] = None,
    quote: Annotated[str | None, typer.Option("--quote", help="Tweet URL to quote")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Post a new tweet."""
    from clix.core.api import create_tweet

    with get_client(account) as client:
        result = create_tweet(client, text, reply_to_id=reply_to, quote_tweet_url=quote)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success("Tweet posted!")


@app.command("like")
def like(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Like a tweet."""
    from clix.core.api import like_tweet

    with get_client(account) as client:
        result = like_tweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Liked tweet {tweet_id}")


@app.command("unlike")
def unlike(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Unlike a tweet."""
    from clix.core.api import unlike_tweet

    with get_client(account) as client:
        result = unlike_tweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Unliked tweet {tweet_id}")


@app.command("retweet")
def rt(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Retweet a tweet."""
    from clix.core.api import retweet

    with get_client(account) as client:
        result = retweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Retweeted {tweet_id}")


@app.command("unretweet")
def unrt(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Undo a retweet."""
    from clix.core.api import unretweet

    with get_client(account) as client:
        result = unretweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Unretweeted {tweet_id}")


@app.command("bookmark")
def bm(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Bookmark a tweet."""
    from clix.core.api import bookmark_tweet

    with get_client(account) as client:
        result = bookmark_tweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Bookmarked tweet {tweet_id}")


@app.command("unbookmark")
def unbm(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Remove a bookmark."""
    from clix.core.api import unbookmark_tweet

    with get_client(account) as client:
        result = unbookmark_tweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Unbookmarked tweet {tweet_id}")


@app.command("follow")
def follow_cmd(
    handle: Annotated[str, typer.Argument(help="User handle (without @)")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Follow a user by handle."""
    from clix.core.api import follow_user, get_user_by_handle

    with get_client(account) as client:
        user = get_user_by_handle(client, handle.lstrip("@"))
        if user is None:
            if is_json_mode(json_output):
                output_json({"error": f"User @{handle} not found"})
            else:
                print_error(f"User @{handle} not found")
            raise typer.Exit(EXIT_ERROR)

        result = follow_user(client, user.id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Followed @{handle}")


@app.command("unfollow")
def unfollow_cmd(
    handle: Annotated[str, typer.Argument(help="User handle (without @)")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Unfollow a user by handle."""
    from clix.core.api import get_user_by_handle, unfollow_user

    with get_client(account) as client:
        user = get_user_by_handle(client, handle.lstrip("@"))
        if user is None:
            if is_json_mode(json_output):
                output_json({"error": f"User @{handle} not found"})
            else:
                print_error(f"User @{handle} not found")
            raise typer.Exit(EXIT_ERROR)

        result = unfollow_user(client, user.id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Unfollowed @{handle}")


@app.command("delete")
def delete(
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID to delete")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
):
    """Delete a tweet."""
    from clix.core.api import delete_tweet

    if not force and sys.stdout.isatty():
        confirm = typer.confirm(f"Delete tweet {tweet_id}?")
        if not confirm:
            raise typer.Abort()

    with get_client(account) as client:
        result = delete_tweet(client, tweet_id)

    if is_json_mode(json_output):
        output_json(result)
    else:
        print_success(f"Deleted tweet {tweet_id}")


# =============================================================================
# MCP server command
# =============================================================================


@app.command("mcp", help="Start the MCP server (stdio transport).")
def mcp_server() -> None:
    """Launch the clix MCP server for use with any MCP-compatible client."""
    from clix.mcp.server import mcp

    mcp.run(transport="stdio")


# =============================================================================
# Register sub-command groups (must be after app definition, import at bottom
# to avoid circular imports)
# =============================================================================


def _register_subcommands() -> None:
    """Register subcommand groups."""
    from clix.cli.feed import feed_app
    from clix.cli.search import search_app
    from clix.cli.tweet import tweet_app
    from clix.cli.user import user_app

    app.add_typer(feed_app, name="feed", help="View your timeline")
    app.add_typer(tweet_app, name="tweet", help="View or manage tweets")
    app.add_typer(search_app, name="search", help="Search tweets")
    app.add_typer(user_app, name="user", help="View user profiles")


_register_subcommands()


if __name__ == "__main__":
    app()
