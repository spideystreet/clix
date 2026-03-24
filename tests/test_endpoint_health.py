"""Live endpoint health checks — verifies X.com still serves expected operations.

These tests hit X.com to extract current GraphQL operations from JS bundles
and compare against what clix expects. Marked as integration tests (skipped
in normal CI, run daily by endpoint-health workflow).

If a test fails, X.com has removed or renamed an operation.
Action: add to FALLBACK_OPERATIONS or migrate to REST API.
"""

import pytest

from clix.core.endpoints import (
    FALLBACK_OPERATIONS,
    _fetch_and_extract,
)

# Duplicated from test_endpoint_coverage.py to avoid cross-test imports.
# Keep in sync — test_endpoint_coverage.py is the source of truth.
HARDCODED_RAW_OPERATIONS = {
    "BookmarkFoldersSlice",
    "BookmarkFolderTimeline",
    "CreateScheduledTweet",
    "FetchScheduledTweets",
    "DeleteScheduledTweet",
    "JobSearchQueryScreenJobsQuery",
    "JobScreenQuery",
}

KNOWN_DYNAMIC_OPERATIONS = {
    "BookmarkSearchTimeline",
    "CreateBookmark",
    "CreateList",
    "CreateRetweet",
    "CreateTweet",
    "DeleteBookmark",
    "DeleteList",
    "DeleteRetweet",
    "DeleteTweet",
    "ExplorePage",
    "FavoriteTweet",
    "Followers",
    "Following",
    "Likes",
    "ListAddMember",
    "ListLatestTweetsTimeline",
    "ListMembers",
    "ListRemoveMember",
    "ListsManagementPageTimeline",
    "PinTimeline",
    "SearchTimeline",
    "TweetDetail",
    "TweetResultByRestId",
    "TweetResultsByRestIds",
    "UnfavoriteTweet",
    "UnpinTimeline",
    "UserByScreenName",
    "UsersByRestIds",
}

# Operations known to be broken but not exposed in CLI/MCP.
# Exempt from live health checks — will be fixed when exposed.
KNOWN_BROKEN_OPERATIONS: set[str] = set()


@pytest.fixture(scope="module")
def live_operations() -> dict[str, str]:
    """Fetch current operations from X.com (cached per test module)."""
    endpoints, _features, _op_features = _fetch_and_extract()
    return endpoints


@pytest.mark.integration
class TestEndpointHealth:
    def test_dynamic_operations_available(self, live_operations: dict[str, str]):
        """All dynamic operations should be extractable from X.com bundles.

        Operations in FALLBACK_OPERATIONS are exempt — they have hardcoded IDs.
        Operations in HARDCODED_RAW_OPERATIONS are exempt — they use _raw methods.
        """
        fallback_names = set(FALLBACK_OPERATIONS.keys())
        exempt = fallback_names | HARDCODED_RAW_OPERATIONS

        # Operations that MUST be in live bundles (no fallback)
        must_resolve = KNOWN_DYNAMIC_OPERATIONS - exempt - KNOWN_BROKEN_OPERATIONS
        live_names = set(live_operations.keys())

        missing = must_resolve - live_names
        assert not missing, (
            f"Operations missing from X.com bundles: {missing}. "
            f"X.com may have removed them. "
            f"Add to FALLBACK_OPERATIONS in endpoints.py with a hardcoded query ID, "
            f"or migrate to REST API."
        )

    def test_fallback_operations_still_in_bundles(self, live_operations: dict[str, str]):
        """Check if fallback operations have returned to bundles.

        If they reappear, we can remove them from FALLBACK_OPERATIONS
        and let the dynamic resolver handle them again.
        """
        live_names = set(live_operations.keys())
        returned = set(FALLBACK_OPERATIONS.keys()) & live_names

        if returned:
            # Not a failure — just informational
            pytest.skip(
                f"Fallback operations now in bundles (can remove from FALLBACK_OPERATIONS): "
                f"{returned}"
            )

    def test_extracted_operation_count(self, live_operations: dict[str, str]):
        """X.com should serve a reasonable number of operations.

        If this drops significantly, the extraction logic may be broken
        or X.com changed their bundle format.
        """
        count = len(live_operations)
        assert count >= 100, (
            f"Only {count} operations extracted from X.com (expected 100+). "
            f"Bundle extraction may be broken or X.com changed their format."
        )

    def test_known_stable_operations_present(self, live_operations: dict[str, str]):
        """Core operations that have never been removed should still be present.

        These are the most stable operations — if they disappear,
        something is fundamentally wrong with extraction.
        """
        core_ops = {
            "HomeTimeline",
            "TweetDetail",
            "UserByScreenName",
            "CreateTweet",
            "FavoriteTweet",
        }
        live_names = set(live_operations.keys())
        missing = core_ops - live_names
        assert not missing, (
            f"Core operations missing: {missing}. "
            f"This likely means bundle extraction is broken, not that X removed them."
        )
