"""Main CLI application."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console

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
from clix.core.auth import (
    AuthCredentials,
    AuthError,
    discover_chrome_profiles,
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


@app.callback()
def main(
    ctx: typer.Context,
    full_text: Annotated[
        bool, typer.Option("--full-text", help="Show full tweet text without truncation")
    ] = False,
    compact: Annotated[
        bool, typer.Option("--compact", "-c", help="Compact JSON output for AI agents")
    ] = False,
) -> None:
    """Twitter/X CLI — browse, search, and post from your terminal."""
    ctx.ensure_object(dict)
    ctx.obj["full_text"] = full_text
    ctx.obj["compact"] = compact


# =============================================================================
# Auth commands
# =============================================================================

auth_app = typer.Typer(help="Manage authentication")
app.add_typer(auth_app, name="auth")


@auth_app.command("status")
def auth_status(
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Check authentication status."""
    validate_output_flags(json_output, yaml_output)
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
        elif is_yaml_mode(yaml_output):
            output_yaml(info)
        else:
            print_success(f"Authenticated (token: {info['auth_token']})")
            if creds.account_name:
                console.print(f"  Account: [cyan]{creds.account_name}[/cyan]")
    except AuthError:
        if is_json_mode(json_output):
            output_json({"authenticated": False})
        elif is_yaml_mode(yaml_output):
            output_yaml({"authenticated": False})
        else:
            print_error("Not authenticated")
        raise typer.Exit(EXIT_AUTH_ERROR)


@auth_app.command("login")
def auth_login(
    browser: Annotated[
        str | None, typer.Option(help="Browser: chrome, firefox, edge, brave")
    ] = None,
    account: Annotated[str, typer.Option(help="Account name")] = "default",
    profile: Annotated[
        str | None, typer.Option(help="Chrome profile name (e.g. 'Profile 3')")
    ] = None,
    list_profiles: Annotated[
        bool, typer.Option("--list-profiles", help="Show available browser profiles")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
):
    """Extract cookies from browser and save."""
    if list_profiles:
        profiles = discover_chrome_profiles()
        if is_json_mode(json_output):
            output_json([p.model_dump() for p in profiles])
        elif not profiles:
            print_warning("No Chrome/Chromium profiles found")
        else:
            from rich.table import Table

            table = Table(title="Browser Profiles")
            table.add_column("Browser", style="cyan")
            table.add_column("Profile", style="green")
            table.add_column("Cookie DB", style="dim")
            for p in profiles:
                table.add_row(p.browser, p.profile, p.path)
            console.print(table)
        return

    source = browser or "available browsers"
    if profile:
        source = f"{source} (profile: {profile})"
    console.print(f"Extracting cookies from {source}...")
    creds = extract_cookies_from_browser(browser, profile=profile)

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
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
):
    """List stored accounts."""
    validate_output_flags(json_output, yaml_output)
    accounts = list_accounts()
    if is_json_mode(json_output):
        output_json({"accounts": accounts})
    elif is_yaml_mode(yaml_output):
        output_yaml({"accounts": accounts})
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
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
):
    """Show current configuration."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.config import Config

    cfg = Config.load()
    if is_json_mode(json_output):
        output_json(cfg.model_dump())
    elif is_yaml_mode(yaml_output):
        output_yaml(cfg)
    else:
        console.print(cfg.model_dump())


# =============================================================================
# Bookmarks command
# =============================================================================


@app.command("bookmarks")
def bookmarks_cmd(
    ctx: typer.Context,
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets")] = 20,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View your bookmarks."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import get_bookmarks
    from clix.display.formatter import format_tweet_list

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        response = get_bookmarks(client, count)

    if compact:
        output_compact(response.tweets)
    elif is_json_mode(json_output):
        output_json([t.to_json_dict() for t in response.tweets])
    elif is_yaml_mode(yaml_output):
        output_yaml([t.to_json_dict() for t in response.tweets])
    else:
        full_text = ctx.obj.get("full_text", False) if ctx.obj else False
        format_tweet_list(response.tweets, full_text=full_text)


# =============================================================================
# Quick action shortcuts (top-level)
# =============================================================================


@app.command("post")
def post(
    ctx: typer.Context,
    text: Annotated[str, typer.Argument(help="Tweet text")],
    reply_to: Annotated[str | None, typer.Option("--reply-to", help="Tweet ID to reply to")] = None,
    quote: Annotated[str | None, typer.Option("--quote", help="Tweet URL to quote")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Post a new tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import create_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = create_tweet(client, text, reply_to_id=reply_to, quote_tweet_url=quote)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success("Tweet posted!")


@app.command("like")
def like(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Like a tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import like_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = like_tweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Liked tweet {tweet_id}")


@app.command("unlike")
def unlike(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Unlike a tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import unlike_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = unlike_tweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Unliked tweet {tweet_id}")


@app.command("retweet")
def rt(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Retweet a tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import retweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = retweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Retweeted {tweet_id}")


@app.command("unretweet")
def unrt(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Undo a retweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import unretweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = unretweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Unretweeted {tweet_id}")


@app.command("bookmark")
def bm(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Bookmark a tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import bookmark_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = bookmark_tweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Bookmarked tweet {tweet_id}")


@app.command("unbookmark")
def unbm(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """Remove a bookmark."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import unbookmark_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    with get_client(account) as client:
        result = unbookmark_tweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
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
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID to delete")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
):
    """Delete a tweet."""
    validate_output_flags(json_output, yaml_output)
    from clix.core.api import delete_tweet

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    if not force and sys.stdout.isatty():
        confirm = typer.confirm(f"Delete tweet {tweet_id}?")
        if not confirm:
            raise typer.Abort()

    with get_client(account) as client:
        result = delete_tweet(client, tweet_id)

    if compact or is_json_mode(json_output):
        output_json(result)
    elif is_yaml_mode(yaml_output):
        output_yaml(result)
    else:
        print_success(f"Deleted tweet {tweet_id}")


# =============================================================================
# Doctor command
# =============================================================================


@app.command("doctor")
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    account: Annotated[str | None, typer.Option("--account", "-a", help="Account to check")] = None,
) -> None:
    """Run diagnostics to check clix health."""
    import platform
    import time

    import curl_cffi

    from clix import __version__
    from clix.core.auth import get_auth_file, get_auth_from_env, load_stored_auth
    from clix.core.constants import best_chrome_target
    from clix.core.endpoints import CACHE_TTL_SECONDS, _get_cache_path

    checks: list[dict[str, str]] = []

    def _pass(name: str, detail: str) -> None:
        checks.append({"name": name, "status": "pass", "detail": detail})

    def _fail(name: str, detail: str) -> None:
        checks.append({"name": name, "status": "fail", "detail": detail})

    def _warn(name: str, detail: str) -> None:
        checks.append({"name": name, "status": "warn", "detail": detail})

    # 1. System info
    try:
        py_version = platform.python_version()
        plat = platform.platform()
        _pass("Python", f"{py_version} ({plat})")
        _pass("clix", f"v{__version__}")
    except Exception as e:
        _fail("System info", str(e))

    # 2. Dependencies
    try:
        cffi_version = curl_cffi.__version__
        target = best_chrome_target()
        _pass("curl_cffi", f"{cffi_version} (target: {target})")
    except Exception as e:
        _fail("curl_cffi", str(e))

    # 3. Auth status
    try:
        env_creds = get_auth_from_env()
        if env_creds and env_creds.is_valid:
            _pass("Auth (env)", "X_AUTH_TOKEN and X_CT0 set")
        else:
            _warn("Auth (env)", "X_AUTH_TOKEN / X_CT0 not set")
    except Exception as e:
        _fail("Auth (env)", str(e))

    try:
        auth_file = get_auth_file()
        if auth_file.exists():
            stored = load_stored_auth(account)
            if stored and stored.is_valid:
                label = stored.account_name or "default"
                _pass("Auth (stored)", f"credentials for @{label}")
            else:
                _warn("Auth (stored)", f"{auth_file} exists but no valid credentials")
        else:
            _warn("Auth (stored)", f"{auth_file} not found")
    except Exception as e:
        _fail("Auth (stored)", str(e))

    # 4. Cookie validation
    try:
        creds = None
        env_creds = get_auth_from_env()
        if env_creds and env_creds.is_valid:
            creds = env_creds
        else:
            creds = load_stored_auth(account)

        if creds and creds.is_valid:
            from clix.core.client import XClient

            with XClient(credentials=creds) as client:
                start_t = time.monotonic()
                resp = client.session.get(
                    "https://api.x.com/1.1/account/verify_credentials.json",
                    headers=client._get_headers(),
                    cookies=client._get_cookies(),
                    timeout=10,
                )
                elapsed = int((time.monotonic() - start_t) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    screen_name = data.get("screen_name", "unknown")
                    _pass("Cookie validation", f"@{screen_name} verified ({elapsed}ms)")
                elif resp.status_code == 401:
                    _fail("Cookie validation", "cookies expired or invalid (HTTP 401)")
                else:
                    _fail("Cookie validation", f"HTTP {resp.status_code} ({elapsed}ms)")
        else:
            _warn("Cookie validation", "no credentials available to validate")
    except Exception as e:
        _fail("Cookie validation", str(e))

    # 5. Endpoint cache
    try:
        cache_path = _get_cache_path()
        if cache_path.exists():
            import json as json_mod

            cache_data = json_mod.loads(cache_path.read_text())
            timestamp = cache_data.get("timestamp", 0)
            age_seconds = time.time() - timestamp
            num_ops = len(cache_data.get("endpoints", {}))
            stale = age_seconds > CACHE_TTL_SECONDS

            age_str = _format_age(age_seconds)
            if stale:
                _warn("Endpoint cache", f"{num_ops} operations cached ({age_str} old, stale)")
            else:
                _pass("Endpoint cache", f"{num_ops} operations cached ({age_str} old)")
        else:
            _warn("Endpoint cache", f"{cache_path} not found (will be created on first API call)")
    except Exception as e:
        _fail("Endpoint cache", str(e))

    # 6. API connectivity
    try:
        start_t = time.monotonic()
        from curl_cffi import requests as curl_requests

        resp = curl_requests.head("https://x.com", timeout=10)
        elapsed = int((time.monotonic() - start_t) * 1000)
        if resp.status_code < 400:
            _pass("API connectivity", f"x.com reachable ({elapsed}ms)")
        else:
            _fail("API connectivity", f"x.com returned HTTP {resp.status_code} ({elapsed}ms)")
    except Exception as e:
        _fail("API connectivity", f"x.com unreachable: {e}")

    # Output
    if is_json_mode(json_output):
        output_json({"checks": checks})
    else:
        for check in checks:
            status = check["status"]
            name = check["name"]
            detail = check["detail"]
            if status == "pass":
                console.print(f"  [green]\\[PASS][/green] {name}: {detail}")
            elif status == "fail":
                console.print(f"  [red]\\[FAIL][/red] {name}: {detail}")
            else:
                console.print(f"  [yellow]\\[WARN][/yellow] {name}: {detail}")


def _format_age(seconds: float) -> str:
    """Format seconds into a human-readable age string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    else:
        return f"{seconds / 86400:.1f}d"


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
    from clix.cli.lists import lists_app
    from clix.cli.search import search_app
    from clix.cli.tweet import tweet_app
    from clix.cli.user import user_app

    app.add_typer(feed_app, name="feed", help="View your timeline")
    app.add_typer(tweet_app, name="tweet", help="View or manage tweets")
    app.add_typer(search_app, name="search", help="Search tweets")
    app.add_typer(user_app, name="user", help="View user profiles")
    app.add_typer(lists_app, name="lists", help="View your lists")


_register_subcommands()


if __name__ == "__main__":
    app()
