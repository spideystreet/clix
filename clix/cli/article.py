"""Article CLI command — fetch and display X Articles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from clix.cli.helpers import (
    get_client,
    is_json_mode,
    output_json,
    validate_output_flags,
)
from clix.display.formatter import console, format_article


def _extract_tweet_id_from_url(url_or_id: str) -> str:
    """Extract tweet ID from a URL or return as-is if already an ID.

    Supports:
      - Plain tweet ID: 2033949937936085378
      - Tweet URL: https://x.com/user/status/2033949937936085378
      - Article URL: https://x.com/i/article/2033772621536591872
      - t.co short links (resolved via the tweet's entities)
    """
    # Already a numeric ID
    if url_or_id.isdigit():
        return url_or_id

    # Match tweet status URL
    m = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url_or_id)
    if m:
        return m.group(1)

    # Match article URL — extract the article ID but note: we need the
    # *tweet* ID for the API. We'll handle this in the command.
    m = re.search(r"(?:twitter\.com|x\.com)/i/article/(\d+)", url_or_id)
    if m:
        return f"article:{m.group(1)}"

    return url_or_id


def register_article(app: typer.Typer) -> None:
    """Register the article command on the main app."""

    @app.command("article")
    def article(
        tweet_id: Annotated[str, typer.Argument(help="Tweet ID, tweet URL, or article URL")],
        export: Annotated[
            Path | None,
            typer.Option("--export", "-o", help="Export article as Markdown file"),
        ] = None,
        json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
        yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
        account: Annotated[str | None, typer.Option(help="Account name")] = None,
    ) -> None:
        """Fetch and display an X Article.

        Accepts a tweet ID, tweet URL, or article URL.
        Use --export to save as Markdown.
        """
        validate_output_flags(json_output, yaml_output)

        from clix.core.api import get_article
        from clix.display.formatter import print_error, print_success
        from clix.utils.article import article_to_markdown, extract_article_metadata

        resolved_id = _extract_tweet_id_from_url(tweet_id)

        # If user passed an article URL, we need to find the parent tweet
        if resolved_id.startswith("article:"):
            article_id = resolved_id.split(":", 1)[1]
            # Try searching for the tweet that links to this article
            from clix.core.api import search_tweets

            with get_client(account) as client:
                search_result = search_tweets(
                    client,
                    f"url:x.com/i/article/{article_id}",
                    search_type="Latest",
                )
                tweets = search_result.tweets if search_result else []
                if not tweets:
                    print_error(
                        f"Could not find the tweet for article {article_id}. "
                        "Try passing the tweet URL instead."
                    )
                    raise typer.Exit(1)
                resolved_id = tweets[0].id
                # Now fetch the article from this tweet
                article_data = get_article(client, resolved_id)
                focal = tweets[0]
        else:
            with get_client(account) as client:
                article_data = get_article(client, resolved_id)

                if not article_data:
                    print_error(f"No article found for tweet {resolved_id}")
                    raise typer.Exit(1)

                # Get tweet details for metadata
                from clix.core.api import get_tweet_detail

                tweet_list = get_tweet_detail(client, resolved_id)
                focal = next((t for t in tweet_list if t.id == resolved_id), tweet_list[0]) if tweet_list else None

        if not article_data:
            print_error(f"No article found for tweet {resolved_id}")
            raise typer.Exit(1)

        article_results = article_data.get("article_results", {})
        metadata = extract_article_metadata(article_results)
        content_md = article_to_markdown(article_results)
        title = metadata.get("title", "")

        if is_json_mode(json_output):
            output = {
                "article": {
                    "title": title,
                    "cover_image_url": metadata.get("cover_image_url", ""),
                    "markdown": content_md,
                },
            }
            if focal:
                output["tweet"] = focal.to_json_dict()
            output_json(output)
        else:
            author = focal.author_handle if focal else "unknown"
            engagement = focal.engagement if focal else {}
            console.print(
                format_article(
                    title=title,
                    author=author,
                    content_md=content_md,
                    engagement=engagement,
                )
            )

        if export:
            export_path = Path(export)
            header = f"# {title}\n\n" if title else ""
            author_handle = focal.author_handle if focal else "unknown"
            author_line = f"*By @{author_handle}*\n\n"
            full_md = header + author_line + content_md
            export_path.write_text(full_md, encoding="utf-8")
            print_success(f"Article exported to {export_path}")
