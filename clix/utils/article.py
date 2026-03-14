"""Convert Twitter Article Draft.js content to Markdown."""

from __future__ import annotations

from typing import Any


def article_to_markdown(article_data: dict[str, Any]) -> str:
    """Convert a Twitter Article's Draft.js content_state to Markdown.

    Handles block types: headers, blockquote, lists, code blocks, and unstyled.
    Atomic blocks (media embeds) are skipped.
    """
    result = article_data.get("result", article_data)
    content_state = (
        result.get("content", {}).get("content_state", {})
        if "content" in result
        else result.get("content_state", {})
    )
    blocks = content_state.get("blocks", [])

    if not blocks:
        return ""

    lines: list[str] = []
    ordered_counter = 0

    for block in blocks:
        block_type = block.get("type", "unstyled")
        text = block.get("text", "")
        text = _apply_inline_styles(text, block.get("inlineStyleRanges", []))

        if block_type == "header-one":
            lines.append(f"# {text}")
            ordered_counter = 0
        elif block_type == "header-two":
            lines.append(f"## {text}")
            ordered_counter = 0
        elif block_type == "header-three":
            lines.append(f"### {text}")
            ordered_counter = 0
        elif block_type == "blockquote":
            lines.append(f"> {text}")
            ordered_counter = 0
        elif block_type == "unordered-list-item":
            lines.append(f"- {text}")
            ordered_counter = 0
        elif block_type == "ordered-list-item":
            ordered_counter += 1
            lines.append(f"{ordered_counter}. {text}")
        elif block_type == "code-block":
            lines.append(f"```\n{text}\n```")
            ordered_counter = 0
        elif block_type == "atomic":
            # Skip media/embed blocks
            ordered_counter = 0
            continue
        else:
            # unstyled or unknown — plain paragraph
            lines.append(text)
            ordered_counter = 0

    return "\n\n".join(lines)


def _apply_inline_styles(text: str, style_ranges: list[dict[str, Any]]) -> str:
    """Apply bold/italic inline styles to text.

    Processes ranges from right to left to preserve offsets.
    """
    if not style_ranges or not text:
        return text

    # Sort by offset descending so insertions don't shift earlier offsets
    sorted_ranges = sorted(style_ranges, key=lambda r: r.get("offset", 0), reverse=True)

    for style_range in sorted_ranges:
        offset = style_range.get("offset", 0)
        length = style_range.get("length", 0)
        style = style_range.get("style", "")

        if offset + length > len(text):
            continue

        segment = text[offset : offset + length]
        if style == "BOLD":
            segment = f"**{segment}**"
        elif style == "ITALIC":
            segment = f"*{segment}*"
        elif style == "CODE":
            segment = f"`{segment}`"

        text = text[:offset] + segment + text[offset + length :]

    return text


def extract_article_metadata(article_data: dict[str, Any]) -> dict[str, Any]:
    """Extract title, author, and other metadata from article data.

    Returns a dict with title, cover_image_url, and lifecycle_state.
    """
    result = article_data.get("result", article_data)
    title = result.get("title", "")
    cover_image = result.get("cover_media", {}).get("media_info", {}).get("original_img_url", "")
    lifecycle_state = result.get("lifecycle_state", "")

    return {
        "title": title,
        "cover_image_url": cover_image,
        "lifecycle_state": lifecycle_state,
    }
