"""Tweet detail CLI commands."""

from __future__ import annotations

from pathlib import Path
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
from clix.display.formatter import console, format_article, format_thread, format_tweet

tweet_app = typer.Typer(no_args_is_help=False, invoke_without_command=True)


@tweet_app.callback(invoke_without_command=True)
def tweet(
    ctx: typer.Context,
    tweet_id: Annotated[str, typer.Argument(help="Tweet ID")],
    thread: Annotated[bool, typer.Option("--thread", help="Show full thread")] = False,
    export: Annotated[
        Path | None,
        typer.Option("--export", help="Export article as Markdown file"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
):
    """View a tweet and its thread."""
    if ctx.invoked_subcommand is not None:
        return

    validate_output_flags(json_output, yaml_output)

    from clix.core.api import get_article, get_tweet_detail

    with get_client(account) as client:
        tweets = get_tweet_detail(client, tweet_id)

        if not tweets:
            from clix.display.formatter import print_error

            print_error(f"Tweet {tweet_id} not found")
            raise typer.Exit(1)

        # Check if this tweet is an article
        article_data = get_article(client, tweet_id)

    focal = next((t for t in tweets if t.id == tweet_id), tweets[0])

    compact = is_compact_mode(ctx)
    if compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    if article_data:
        _handle_article(article_data, focal, export, is_json_mode(json_output))
    elif compact:
        output_compact(tweets)
    elif is_json_mode(json_output):
        output_json([t.to_json_dict() for t in tweets])
    elif is_yaml_mode(yaml_output):
        output_yaml([t.to_json_dict() for t in tweets])
    elif thread:
        format_thread(tweets, focal_id=tweet_id)
    else:
        full_text = ctx.obj.get("full_text", False) if ctx.obj else False
        console.print(format_tweet(focal, full_text=full_text))


def _handle_article(
    article_data: dict,
    focal_tweet: object,
    export: Path | None,
    json_mode: bool,
) -> None:
    """Handle display and export of an article tweet."""
    from clix.utils.article import article_to_markdown, extract_article_metadata

    article_results = article_data.get("article_results", {})
    metadata = extract_article_metadata(article_results)
    content_md = article_to_markdown(article_results)
    title = metadata.get("title", "")

    if json_mode:
        output_json(
            {
                "tweet": focal_tweet.to_json_dict(),  # type: ignore[union-attr]
                "article": {
                    "title": title,
                    "cover_image_url": metadata.get("cover_image_url", ""),
                    "markdown": content_md,
                },
            }
        )
    else:
        console.print(
            format_article(
                title=title,
                author=focal_tweet.author_handle,  # type: ignore[union-attr]
                content_md=content_md,
                engagement=focal_tweet.engagement,  # type: ignore[union-attr]
            )
        )

    if export:
        export_path = Path(export)
        # Build full markdown with frontmatter
        header = f"# {title}\n\n" if title else ""
        author_line = f"*By @{focal_tweet.author_handle}*\n\n"  # type: ignore[union-attr]
        full_md = header + author_line + content_md
        export_path.write_text(full_md, encoding="utf-8")
        from clix.display.formatter import print_success

        print_success(f"Article exported to {export_path}")
