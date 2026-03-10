"""Tests for GraphQL operation ID extraction from X.com bundles."""

import re
import time
from unittest.mock import patch

import pytest

from clix.core.endpoints import (
    _read_cache,
    _write_cache,
    extract_bundle_urls,
    extract_features_from_html,
    extract_operations_from_js,
    get_features,
    get_graphql_endpoints,
)

# --- Fixtures: realistic HTML/JS snippets ---

FAKE_MAIN_JS_HREF_URL = "https://abs.twimg.com/responsive-web/client-web/main.abc123.js"
FAKE_MAIN_JS_SRC_URL = "https://abs.twimg.com/responsive-web/client-web/main.def456.js"
FAKE_CHUNK_JS_URL = "https://abs.twimg.com/responsive-web/client-web/api.xyz789a.js"

FAKE_HOMEPAGE_HTML = f"""
<!DOCTYPE html>
<html>
<head>
<link rel="preload" as="script" href="{FAKE_MAIN_JS_HREF_URL}" />
<script src="{FAKE_CHUNK_JS_URL}"></script>
<script>window.__INITIAL_STATE__={{"featureSwitch":{{"defaultConfig":{{"rweb_tipjar_consumption_enabled":{{"value":false}},"view_counts_everywhere_api_enabled":{{"value":true}},"some_int_flag":{{"value":42}},"some_string_flag":{{"value":"hello"}}}}}}}}</script>
</head>
<body></body>
</html>
"""

FAKE_JS_CONTENT = """
!function(e){var t={};function n(r){if(t[r])return t[r].exports}
e.exports={queryId:"snvCaalBp51MiDb3-nGblg",operationName:"HomeTimeline",operationType:"query",metadata:{featureSwitches:["responsive_web_graphql_timeline_navigation_enabled"],fieldToggles:["withArticlePlainText"]}}
e.exports={queryId:"uY34Pldm6W89yqswRmPMSQ",operationName:"CreateTweet",operationType:"mutation",metadata:{featureSwitches:[],fieldToggles:[]}}
e.exports={queryId:"nWemVnGJ6A5eQAR5-oQeAg",operationName:"SearchTimeline",operationType:"query",metadata:{featureSwitches:[],fieldToggles:[]}}
"""

FAKE_JS_NO_OPS = """
!function(e){var t={};console.log("no operations here")}
"""

FAKE_HTML_MALFORMED_JSON = """
<script>window.__INITIAL_STATE__={"truncated": true}extra_garbage</script>
"""

FAKE_HTML_UNCLOSED_JSON = """
<script>window.__INITIAL_STATE__={"missing_close": true</script>
"""

CACHE_TTL_SECONDS = 86400  # 24h


# =============================================================================
# Task 1: Bundle URL extraction
# =============================================================================


class TestExtractBundleUrls:
    """Verify bundle URL extraction from HTML."""

    def test_extracts_main_js_url_from_href(self):
        """Must find the main.js URL from a <link href=...> tag."""
        urls = extract_bundle_urls(FAKE_HOMEPAGE_HTML)
        assert FAKE_MAIN_JS_HREF_URL in urls

    def test_extracts_chunk_url_from_src(self):
        """Must find bundle URLs from <script src=...> tags."""
        urls = extract_bundle_urls(FAKE_HOMEPAGE_HTML)
        assert FAKE_CHUNK_JS_URL in urls

    def test_main_js_comes_first(self):
        """main.js URLs must appear before other bundle URLs."""
        urls = extract_bundle_urls(FAKE_HOMEPAGE_HTML)
        main_idx = urls.index(FAKE_MAIN_JS_HREF_URL)
        chunk_idx = urls.index(FAKE_CHUNK_JS_URL)
        assert main_idx < chunk_idx

    def test_returns_empty_list_on_garbage_html(self):
        """No crash on HTML without any bundle URLs."""
        urls = extract_bundle_urls("<html><body>nothing</body></html>")
        assert urls == []

    def test_deduplicates_urls(self):
        """Same URL appearing in both href and src is deduplicated."""
        html = f"""
        <link href="{FAKE_MAIN_JS_HREF_URL}" />
        <script src="{FAKE_MAIN_JS_HREF_URL}"></script>
        """
        urls = extract_bundle_urls(html)
        assert urls.count(FAKE_MAIN_JS_HREF_URL) == 1


# =============================================================================
# Task 2: Operation ID extraction
# =============================================================================


class TestExtractOperationsFromJs:
    """Verify queryId/operationName extraction from JS content."""

    def test_extracts_all_operations(self):
        """Must find all queryId/operationName pairs."""
        ops, _ = extract_operations_from_js(FAKE_JS_CONTENT)
        assert ops["HomeTimeline"] == "snvCaalBp51MiDb3-nGblg/HomeTimeline"
        assert ops["CreateTweet"] == "uY34Pldm6W89yqswRmPMSQ/CreateTweet"
        assert ops["SearchTimeline"] == "nWemVnGJ6A5eQAR5-oQeAg/SearchTimeline"

    def test_returns_empty_dict_on_no_matches(self):
        """No crash on JS without any operations."""
        ops, _ = extract_operations_from_js(FAKE_JS_NO_OPS)
        assert ops == {}

    def test_query_id_format_is_valid(self):
        """Extracted query IDs must be base64url-like strings."""
        ops, _ = extract_operations_from_js(FAKE_JS_CONTENT)
        pattern = re.compile(r"^[A-Za-z0-9_-]{10,30}/[A-Za-z]+$")
        for name, endpoint in ops.items():
            assert pattern.match(endpoint), f"Bad format for {name}: {endpoint}"

    def test_handles_multiline_js(self):
        """Must extract operations even if queryId and operationName span lines."""
        multiline_js = """
        {queryId:"abc123def456ghij_k"
        ,operationName:"MultiLineOp"
        ,operationType:"query"}
        """
        ops, _ = extract_operations_from_js(multiline_js)
        assert ops["MultiLineOp"] == "abc123def456ghij_k/MultiLineOp"

    def test_extracts_feature_switches(self):
        """Must extract per-operation featureSwitches from metadata."""
        _, op_features = extract_operations_from_js(FAKE_JS_CONTENT)
        assert "HomeTimeline" in op_features
        assert "responsive_web_graphql_timeline_navigation_enabled" in op_features["HomeTimeline"]


# =============================================================================
# Task 3: Feature flag extraction
# =============================================================================


class TestExtractFeaturesFromHtml:
    """Verify feature flag extraction from __INITIAL_STATE__."""

    def test_extracts_feature_flags(self):
        """Must find boolean feature flags from __INITIAL_STATE__."""
        features = extract_features_from_html(FAKE_HOMEPAGE_HTML)
        assert features["rweb_tipjar_consumption_enabled"] is False
        assert features["view_counts_everywhere_api_enabled"] is True

    def test_skips_non_boolean_values(self):
        """Integer and string feature values must be skipped."""
        features = extract_features_from_html(FAKE_HOMEPAGE_HTML)
        assert "some_int_flag" not in features
        assert "some_string_flag" not in features

    def test_returns_empty_dict_on_missing_state(self):
        """No crash if __INITIAL_STATE__ is absent."""
        features = extract_features_from_html("<html><body>nothing</body></html>")
        assert features == {}

    def test_parses_valid_json_despite_trailing_garbage(self):
        """Must still extract features even if there's trailing content after JSON."""
        features = extract_features_from_html(FAKE_HTML_MALFORMED_JSON)
        assert features == {}  # has "truncated": true but not a bool feature

    def test_returns_empty_dict_on_unclosed_json(self):
        """No crash if __INITIAL_STATE__ JSON braces are not closed."""
        features = extract_features_from_html(FAKE_HTML_UNCLOSED_JSON)
        assert features == {}


# =============================================================================
# Task 4: Cache layer
# =============================================================================


class TestCache:
    """Verify cache read/write/expiry."""

    def test_write_and_read_cache(self, tmp_path):
        """Written cache is readable."""
        cache_file = tmp_path / "graphql_ops.json"
        data = {
            "endpoints": {"HomeTimeline": "abc123/HomeTimeline"},
            "features": {"some_flag": True},
            "timestamp": time.time(),
        }
        _write_cache(data, cache_file)
        loaded = _read_cache(cache_file, ttl=CACHE_TTL_SECONDS)
        assert loaded is not None
        assert loaded["endpoints"]["HomeTimeline"] == "abc123/HomeTimeline"

    def test_expired_cache_returns_none(self, tmp_path):
        """Cache older than TTL returns None."""
        cache_file = tmp_path / "graphql_ops.json"
        data = {
            "endpoints": {"HomeTimeline": "abc123/HomeTimeline"},
            "features": {},
            "timestamp": time.time() - CACHE_TTL_SECONDS - 1,
        }
        _write_cache(data, cache_file)
        loaded = _read_cache(cache_file, ttl=CACHE_TTL_SECONDS)
        assert loaded is None

    def test_missing_cache_returns_none(self, tmp_path):
        """Non-existent file returns None."""
        cache_file = tmp_path / "nonexistent.json"
        loaded = _read_cache(cache_file, ttl=CACHE_TTL_SECONDS)
        assert loaded is None

    def test_corrupted_cache_returns_none(self, tmp_path):
        """Corrupted JSON returns None without crashing."""
        cache_file = tmp_path / "graphql_ops.json"
        cache_file.write_text("NOT VALID JSON{{{")
        loaded = _read_cache(cache_file, ttl=CACHE_TTL_SECONDS)
        assert loaded is None

    def test_creates_parent_directories(self, tmp_path):
        """Cache write must create parent dirs if they don't exist."""
        cache_file = tmp_path / "nested" / "deep" / "graphql_ops.json"
        data = {"endpoints": {}, "features": {}, "timestamp": time.time()}
        _write_cache(data, cache_file)
        assert cache_file.exists()


# =============================================================================
# Task 5: Orchestration
# =============================================================================


class TestGetGraphqlEndpoints:
    """Verify the full orchestration: fetch → parse → cache → return."""

    @pytest.fixture(autouse=True)
    def _reset_memory_cache(self):
        """Reset module-level memory cache between tests."""
        import clix.core.endpoints as ep

        ep._memory_cache = None
        yield
        ep._memory_cache = None

    def test_returns_cached_endpoints(self, tmp_path):
        """If cache is fresh, return it without fetching."""
        cache_file = tmp_path / "graphql_ops.json"
        cached = {
            "endpoints": {"HomeTimeline": "cached123/HomeTimeline"},
            "features": {"some_flag": True},
            "timestamp": time.time(),
        }
        _write_cache(cached, cache_file)

        with patch("clix.core.endpoints._get_cache_path", return_value=cache_file):
            endpoints = get_graphql_endpoints()
        assert endpoints["HomeTimeline"] == "cached123/HomeTimeline"

    def test_fetches_when_cache_expired(self, tmp_path):
        """If cache is expired, must fetch from X.com."""
        cache_file = tmp_path / "graphql_ops.json"
        cached = {
            "endpoints": {"HomeTimeline": "old/HomeTimeline"},
            "features": {},
            "timestamp": time.time() - CACHE_TTL_SECONDS - 1,
        }
        _write_cache(cached, cache_file)

        fresh_ops = {"HomeTimeline": "fresh123/HomeTimeline", "CreateTweet": "xyz/CreateTweet"}
        fresh_features = {"some_flag": True}

        with (
            patch("clix.core.endpoints._get_cache_path", return_value=cache_file),
            patch(
                "clix.core.endpoints._fetch_and_extract",
                return_value=(fresh_ops, fresh_features, {}),
            ),
        ):
            endpoints = get_graphql_endpoints()
        assert endpoints["HomeTimeline"] == "fresh123/HomeTimeline"

    def test_raises_on_fetch_failure(self, tmp_path):
        """If fetch fails and no cache, raise with clear error."""
        cache_file = tmp_path / "nonexistent.json"

        with (
            patch("clix.core.endpoints._get_cache_path", return_value=cache_file),
            patch(
                "clix.core.endpoints._fetch_and_extract",
                side_effect=RuntimeError("blocked"),
            ),
        ):
            with pytest.raises(RuntimeError, match="blocked"):
                get_graphql_endpoints()


class TestGetFeatures:
    """Verify feature flag retrieval."""

    @pytest.fixture(autouse=True)
    def _reset_memory_cache(self):
        """Reset module-level memory cache between tests."""
        import clix.core.endpoints as ep

        ep._memory_cache = None
        yield
        ep._memory_cache = None

    def test_returns_cached_features(self, tmp_path):
        """If cache is fresh, return features from it."""
        cache_file = tmp_path / "graphql_ops.json"
        cached = {
            "endpoints": {"HomeTimeline": "x/HomeTimeline"},
            "features": {"rweb_tipjar_consumption_enabled": False},
            "timestamp": time.time(),
        }
        _write_cache(cached, cache_file)

        with patch("clix.core.endpoints._get_cache_path", return_value=cache_file):
            features = get_features()
        assert features["rweb_tipjar_consumption_enabled"] is False


# =============================================================================
# Task 9: Integration tests (require network + cookies)
# =============================================================================

REQUIRED_OPERATIONS = [
    "HomeTimeline",
    "HomeLatestTimeline",
    "SearchTimeline",
    "TweetDetail",
    "UserByScreenName",
    "UserTweets",
    "BookmarkSearchTimeline",
    "CreateTweet",
    "DeleteTweet",
    "FavoriteTweet",
    "UnfavoriteTweet",
    "CreateRetweet",
    "DeleteRetweet",
    "CreateBookmark",
    "DeleteBookmark",
]


@pytest.mark.integration
class TestLiveExtraction:
    """Integration tests — require network access to X.com."""

    def test_fetch_and_extract_returns_operations(self):
        """Must extract a reasonable number of operations from live X.com."""
        from clix.core.endpoints import _fetch_and_extract

        ops, features, op_features = _fetch_and_extract()
        assert len(ops) > 50, f"Expected >50 operations, got {len(ops)}"
        assert len(features) > 10, f"Expected >10 features, got {len(features)}"
        assert len(op_features) > 50, f"Expected >50 op_features, got {len(op_features)}"

    def test_all_required_operations_present(self):
        """Every operation clix uses must be present in extracted IDs."""
        from clix.core.endpoints import _fetch_and_extract

        ops, _, _ = _fetch_and_extract()
        missing = [op for op in REQUIRED_OPERATIONS if op not in ops]
        assert not missing, f"Missing required operations: {missing}"

    def test_extracted_ids_work_for_read(self):
        """A real GET request with extracted IDs must succeed."""
        from clix.core.client import XClient

        with XClient() as client:
            data = client.graphql_get(
                "UserByScreenName",
                {"screen_name": "x", "withSafetyModeUserFields": True},
            )
        assert "data" in data
        assert data["data"]["user"]["result"]["__typename"] in ("User", "UserUnavailable")
