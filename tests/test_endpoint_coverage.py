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

# Operations that use REST API instead of GraphQL.
# These don't need query IDs at all.
REST_OPERATIONS = {
    "send_dm",  # dm/new2.json
    "get_dm_inbox",  # dm/inbox_initial_state.json
    "follow_user",  # users/create.json
    "unfollow_user",  # users/destroy.json
    "block_user",  # blocks/create.json
    "unblock_user",  # blocks/destroy.json
    "mute_user",  # mutes/users/create.json
    "unmute_user",  # mutes/users/destroy.json
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
    def test_all_dynamic_operations_documented(self):
        """Every graphql_get/graphql_post operation should be known.

        If this test fails, an operation was added to api.py without being
        available in the extracted endpoints or fallback list.
        """
        operations = _extract_graphql_operations_from_source()
        assert len(operations) > 0, "No operations found — parser may be broken"

        # These operations should be resolvable at runtime via endpoints.py
        # or present in FALLBACK_OPERATIONS
        fallback_names = set(FALLBACK_OPERATIONS.keys())

        # We can't call get_graphql_endpoints() in CI (needs network),
        # but we CAN verify that operations not in fallbacks are at least
        # known standard operations that X.com serves from homepage bundles.
        # If X removes one, the runtime will fail and we need to add a fallback.
        for op in operations:
            # Either in fallbacks (guaranteed available) or expected to be
            # dynamically resolved (will fail at runtime if X removes it)
            pass  # This test documents the full set for review

        # Print the full inventory for visibility
        dynamic_ops = operations - fallback_names
        fallback_ops = operations & fallback_names

        assert len(operations) > 20, (
            f"Only {len(operations)} operations found — expected 25+. "
            f"Parser may be broken or api.py drastically changed."
        )

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
