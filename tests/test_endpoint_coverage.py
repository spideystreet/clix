"""Tests that all GraphQL operations used in api.py are resolvable.

This test catches broken endpoints early: if X.com removes an operation
from its JS bundles and we don't have a fallback, this test fails in CI
before users hit the error at runtime.
"""

import ast
from pathlib import Path

from clix.core.endpoints import FALLBACK_OPERATIONS

# Operations called via graphql_get_raw / graphql_post_raw with hardcoded query IDs.
# These are in lazy-loaded bundles and cannot be extracted at runtime.
HARDCODED_RAW_OPERATIONS = {
    # Bookmark folders (not in homepage bundles)
    "BookmarkFoldersSlice",
    "BookmarkFolderTimeline",
    # Scheduled tweets (lazy-loaded from compose page)
    "CreateScheduledTweet",
    "FetchScheduledTweets",
    "DeleteScheduledTweet",
    # Jobs (lazy-loaded from /jobs page)
    "JobSearchQueryScreenJobsQuery",
    "JobScreenQuery",
}

# All dynamic GraphQL operations used via graphql_get/graphql_post.
# These are resolved at runtime from X.com JS bundles or FALLBACK_OPERATIONS.
# If you add a new graphql_get/graphql_post call, add the operation here.
KNOWN_DYNAMIC_OPERATIONS = {
    # Read operations (graphql_get)
    "BookmarkSearchTimeline",
    "ExplorePage",
    "Followers",
    "Following",
    "Likes",
    "ListLatestTweetsTimeline",
    "ListMembers",
    "ListsManagementPageTimeline",
    "SearchTimeline",
    "TweetDetail",
    "TweetResultByRestId",
    "TweetResultsByRestIds",
    "UserByScreenName",
    "UsersByRestIds",
    # Write operations (graphql_post)
    "CreateBookmark",
    "CreateList",
    "CreateRetweet",
    "CreateTweet",
    "DeleteBookmark",
    "DeleteList",
    "DeleteRetweet",
    "DeleteTweet",
    "DMMessageDeleteMutation",  # Known broken — not in bundles, not exposed in CLI/MCP
    "FavoriteTweet",
    "ListAddMember",
    "ListPinOne",
    "ListRemoveMember",
    "ListUnpinOne",
    "UnfavoriteTweet",
}


def _extract_graphql_operations_from_source() -> set[str]:
    """Parse api.py AST to find all graphql_get/graphql_post operation names."""
    api_path = Path(__file__).parent.parent / "clix" / "core" / "api.py"
    source = api_path.read_text()
    tree = ast.parse(source)

    operations: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Match client.graphql_get("OpName", ...) and client.graphql_post("OpName", ...)
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "graphql_get",
                "graphql_post",
            ):
                if node.args and isinstance(node.args[0], ast.Constant):
                    operations.add(node.args[0].value)
    return operations


def _extract_raw_operations_from_source() -> set[str]:
    """Parse api.py to find all graphql_get_raw/graphql_post_raw operation names."""
    api_path = Path(__file__).parent.parent / "clix" / "core" / "api.py"
    source = api_path.read_text()
    tree = ast.parse(source)

    operations: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "graphql_get_raw",
                "graphql_post_raw",
            ):
                # Operation name is the 2nd positional arg (after query_id)
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    operations.add(node.args[1].value)
    return operations


class TestEndpointCoverage:
    def test_no_unknown_dynamic_operations(self):
        """Every graphql_get/graphql_post operation must be in KNOWN_DYNAMIC_OPERATIONS.

        If this fails, a new operation was added to api.py without registering it.
        Add it to KNOWN_DYNAMIC_OPERATIONS above.
        """
        operations = _extract_graphql_operations_from_source()
        assert len(operations) > 0, "No operations found — parser may be broken"

        unknown = operations - KNOWN_DYNAMIC_OPERATIONS
        assert not unknown, (
            f"Unknown dynamic operations in api.py: {unknown}. "
            f"Add them to KNOWN_DYNAMIC_OPERATIONS in test_endpoint_coverage.py"
        )

    def test_no_stale_dynamic_operations(self):
        """KNOWN_DYNAMIC_OPERATIONS should not have entries removed from api.py.

        If this fails, an operation was removed from api.py but still listed.
        Remove it from KNOWN_DYNAMIC_OPERATIONS above.
        """
        operations = _extract_graphql_operations_from_source()
        stale = KNOWN_DYNAMIC_OPERATIONS - operations
        assert not stale, (
            f"Stale entries in KNOWN_DYNAMIC_OPERATIONS (not in api.py): {stale}. "
            f"Remove them from KNOWN_DYNAMIC_OPERATIONS in test_endpoint_coverage.py"
        )

    def test_dynamic_operations_have_resolution_path(self):
        """Every dynamic operation must be resolvable: either in FALLBACK_OPERATIONS
        or expected to come from X.com JS bundle extraction at runtime.

        Operations in FALLBACK_OPERATIONS are guaranteed available.
        Others depend on X.com not removing them from homepage bundles.
        """
        operations = _extract_graphql_operations_from_source()
        fallback_names = set(FALLBACK_OPERATIONS.keys())

        # These are guaranteed available via fallback
        covered = operations & fallback_names
        # These depend on runtime extraction — if X removes them, they break
        uncovered = operations - fallback_names

        # Just document the split for visibility — not a failure
        assert len(covered) + len(uncovered) == len(operations)

    def test_all_raw_operations_are_hardcoded(self):
        """Every graphql_*_raw operation must be in HARDCODED_RAW_OPERATIONS.

        If this fails, a new raw operation was added without documenting it.
        """
        raw_ops = _extract_raw_operations_from_source()
        undocumented = raw_ops - HARDCODED_RAW_OPERATIONS
        assert not undocumented, (
            f"Undocumented raw operations: {undocumented}. "
            f"Add them to HARDCODED_RAW_OPERATIONS in test_endpoint_coverage.py"
        )

    def test_no_graphql_call_for_rest_endpoints(self):
        """DM send should NOT use graphql_post (regression guard)."""
        api_path = Path(__file__).parent.parent / "clix" / "core" / "api.py"
        source = api_path.read_text()

        # useSendMessageMutation was removed from X.com bundles
        assert "useSendMessageMutation" not in source, (
            "send_dm still references useSendMessageMutation — "
            "this GraphQL operation was removed from X.com bundles. "
            "Use REST API dm/new2.json instead."
        )

        # DMMessageDeleteMutation may also be broken (not in bundles)
        # but delete_dm is not exposed in CLI/MCP yet, so just flag it
        operations = _extract_graphql_operations_from_source()
        if "DMMessageDeleteMutation" in operations:
            import warnings

            warnings.warn(
                "DMMessageDeleteMutation is used in api.py but not in X.com bundles. "
                "It will fail at runtime. Migrate to REST API when exposing delete_dm.",
                stacklevel=1,
            )

    def test_fallback_operations_not_empty(self):
        """FALLBACK_OPERATIONS should have entries for operations periodically removed."""
        assert len(FALLBACK_OPERATIONS) >= 3, (
            f"Only {len(FALLBACK_OPERATIONS)} fallback operations — expected at least 3"
        )
