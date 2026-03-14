"""Tests for Twitter Article parsing and conversion."""

from clix.utils.article import article_to_markdown, extract_article_metadata


class TestArticleToMarkdown:
    """Verify Draft.js block conversion to Markdown."""

    def test_header_one(self):
        """header-one blocks should produce h1 Markdown."""
        data = {"content_state": {"blocks": [{"type": "header-one", "text": "Title"}]}}
        assert article_to_markdown(data) == "# Title"

    def test_header_two(self):
        """header-two blocks should produce h2 Markdown."""
        data = {"content_state": {"blocks": [{"type": "header-two", "text": "Section"}]}}
        assert article_to_markdown(data) == "## Section"

    def test_header_three(self):
        """header-three blocks should produce h3 Markdown."""
        data = {"content_state": {"blocks": [{"type": "header-three", "text": "Sub"}]}}
        assert article_to_markdown(data) == "### Sub"

    def test_blockquote(self):
        """blockquote blocks should produce > prefixed lines."""
        data = {"content_state": {"blocks": [{"type": "blockquote", "text": "Quote here"}]}}
        assert article_to_markdown(data) == "> Quote here"

    def test_unordered_list(self):
        """unordered-list-item blocks should produce - prefixed lines."""
        data = {
            "content_state": {
                "blocks": [
                    {"type": "unordered-list-item", "text": "Item A"},
                    {"type": "unordered-list-item", "text": "Item B"},
                ]
            }
        }
        result = article_to_markdown(data)
        assert "- Item A" in result
        assert "- Item B" in result

    def test_ordered_list_numbering(self):
        """ordered-list-item blocks should have incrementing numbers."""
        data = {
            "content_state": {
                "blocks": [
                    {"type": "ordered-list-item", "text": "First"},
                    {"type": "ordered-list-item", "text": "Second"},
                    {"type": "ordered-list-item", "text": "Third"},
                ]
            }
        }
        result = article_to_markdown(data)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    def test_ordered_list_counter_resets(self):
        """Ordered list counter should reset after a non-list block."""
        data = {
            "content_state": {
                "blocks": [
                    {"type": "ordered-list-item", "text": "A"},
                    {"type": "unstyled", "text": "Break"},
                    {"type": "ordered-list-item", "text": "B"},
                ]
            }
        }
        result = article_to_markdown(data)
        lines = [line for line in result.split("\n\n") if line.strip()]
        assert lines[0] == "1. A"
        assert lines[2] == "1. B"

    def test_code_block(self):
        """code-block should produce fenced code."""
        data = {"content_state": {"blocks": [{"type": "code-block", "text": "x = 1"}]}}
        result = article_to_markdown(data)
        assert "```\nx = 1\n```" in result

    def test_atomic_blocks_skipped(self):
        """atomic blocks (media) should be omitted from output."""
        data = {
            "content_state": {
                "blocks": [
                    {"type": "unstyled", "text": "Before"},
                    {"type": "atomic", "text": " "},
                    {"type": "unstyled", "text": "After"},
                ]
            }
        }
        result = article_to_markdown(data)
        assert "Before" in result
        assert "After" in result
        assert result.count("\n\n") == 1  # two blocks with one separator

    def test_unstyled_plain_paragraph(self):
        """unstyled blocks should produce plain paragraphs."""
        data = {"content_state": {"blocks": [{"type": "unstyled", "text": "Hello world"}]}}
        assert article_to_markdown(data) == "Hello world"

    def test_empty_blocks(self):
        """Empty blocks list should return empty string."""
        assert article_to_markdown({"content_state": {"blocks": []}}) == ""
        assert article_to_markdown({}) == ""

    def test_nested_result_key(self):
        """Data wrapped in a 'result' key should be unwrapped."""
        data = {
            "result": {
                "content": {"content_state": {"blocks": [{"type": "unstyled", "text": "Nested"}]}}
            }
        }
        assert article_to_markdown(data) == "Nested"

    def test_inline_bold_style(self):
        """BOLD inline style should wrap text in ** markers."""
        data = {
            "content_state": {
                "blocks": [
                    {
                        "type": "unstyled",
                        "text": "Hello world",
                        "inlineStyleRanges": [{"offset": 6, "length": 5, "style": "BOLD"}],
                    }
                ]
            }
        }
        assert article_to_markdown(data) == "Hello **world**"

    def test_inline_italic_style(self):
        """ITALIC inline style should wrap text in * markers."""
        data = {
            "content_state": {
                "blocks": [
                    {
                        "type": "unstyled",
                        "text": "Hello world",
                        "inlineStyleRanges": [{"offset": 0, "length": 5, "style": "ITALIC"}],
                    }
                ]
            }
        }
        assert article_to_markdown(data) == "*Hello* world"

    def test_inline_code_style(self):
        """CODE inline style should wrap text in backtick markers."""
        data = {
            "content_state": {
                "blocks": [
                    {
                        "type": "unstyled",
                        "text": "Use print here",
                        "inlineStyleRanges": [{"offset": 4, "length": 5, "style": "CODE"}],
                    }
                ]
            }
        }
        assert article_to_markdown(data) == "Use `print` here"


class TestExtractArticleMetadata:
    """Verify article metadata extraction."""

    def test_extracts_title(self):
        """Title should be extracted from result."""
        data = {"result": {"title": "My Article"}}
        meta = extract_article_metadata(data)
        assert meta["title"] == "My Article"

    def test_missing_title_returns_empty(self):
        """Missing title should default to empty string."""
        meta = extract_article_metadata({})
        assert meta["title"] == ""

    def test_extracts_cover_image(self):
        """Cover image URL should be extracted from nested path."""
        data = {
            "result": {
                "title": "Test",
                "cover_media": {"media_info": {"original_img_url": "https://example.com/img.jpg"}},
            }
        }
        meta = extract_article_metadata(data)
        assert meta["cover_image_url"] == "https://example.com/img.jpg"

    def test_extracts_lifecycle_state(self):
        """lifecycle_state should be extracted."""
        data = {"result": {"lifecycle_state": "Published"}}
        meta = extract_article_metadata(data)
        assert meta["lifecycle_state"] == "Published"
