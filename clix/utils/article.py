"""Convert Twitter Article Draft.js content to Markdown."""

from __future__ import annotations

import re
from typing import Any

_IMAGE_URL_PATTERN = re.compile(
    r"https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)"
    r"|https?://pbs\.twimg\.com/[^\s]+"
)


def _normalize_entity_map(entity_map: dict | list) -> dict[str, dict]:
    """Normalize entityMap from list or dict format to a uniform dict."""
    if isinstance(entity_map, list):
        return {str(item["key"]): item["value"] for item in entity_map if "key" in item}
    return {str(k): v for k, v in entity_map.items()}


def _find_image_url(data: dict[str, Any]) -> str:
    """Recursively search for an image URL in entity data."""
    for key in ("original_img_url", "mediaUrlHttps", "url", "src"):
        val = data.get(key)
        if isinstance(val, str) and _IMAGE_URL_PATTERN.search(val):
            return val
    for val in data.values():
        if isinstance(val, dict):
            found = _find_image_url(val)
            if found:
                return found
    return ""


def _find_caption(data: dict[str, Any]) -> str:
    """Extract alt text or caption from entity data."""
    for key in ("caption", "alt", "altText", "title"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _render_atomic_block(
    block: dict[str, Any],
    entity_map: dict[str, dict],
    media_url_map: dict[str, str],
) -> str:
    """Render an atomic block as markdown (image or embedded markdown)."""
    for entity_range in block.get("entityRanges", []):
        entity_key = str(entity_range.get("key", ""))
        entity = entity_map.get(entity_key, {})
        entity_type = entity.get("type", "")
        entity_data = entity.get("data", {})

        if entity_type == "MARKDOWN":
            return entity_data.get("markdown", entity_data.get("text", ""))

        if entity_type == "IMAGE" or entity_type == "PHOTO":
            url = _find_image_url(entity_data)
            if not url:
                # Try media ID lookup
                media_id = entity_data.get("mediaId", entity_data.get("media_id", ""))
                url = media_url_map.get(str(media_id), "")
            if url:
                caption = _find_caption(entity_data)
                return f"![{caption}]({url})"
    return ""


def _build_media_url_map(article_data: dict[str, Any]) -> dict[str, str]:
    """Build a media_id → URL lookup from article media entities."""
    result = article_data.get("result", article_data)
    url_map: dict[str, str] = {}

    # From cover_media
    cover = result.get("cover_media", {}).get("media_info", {})
    media_id = cover.get("media_id", "")
    url = cover.get("original_img_url", "")
    if media_id and url:
        url_map[str(media_id)] = url

    # From media_entities
    for entity in result.get("media_entities", []):
        mid = entity.get("media_id", "")
        murl = entity.get("original_img_url", entity.get("mediaUrlHttps", ""))
        if mid and murl:
            url_map[str(mid)] = murl

    return url_map


def article_to_markdown(article_data: dict[str, Any]) -> str:
    """Convert a Twitter Article's Draft.js content_state to Markdown.

    Handles block types: headers, blockquote, lists, code blocks, atomic
    (images/embedded markdown), and unstyled.
    """
    result = article_data.get("result", article_data)
    content_state = (
        result.get("content", {}).get("content_state", {})
        if "content" in result
        else result.get("content_state", {})
    )
    blocks = content_state.get("blocks", [])
    entity_map = _normalize_entity_map(content_state.get("entityMap", {}))
    media_url_map = _build_media_url_map(article_data)

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
            rendered = _render_atomic_block(block, entity_map, media_url_map)
            if rendered:
                lines.append(rendered)
            ordered_counter = 0
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
