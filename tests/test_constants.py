"""Tests for GraphQL constants integrity."""

import re

from clix.core.constants import GRAPHQL_ENDPOINTS


class TestGraphQLEndpoints:
    """Verify GraphQL endpoint definitions are well-formed."""

    def test_all_endpoints_have_valid_format(self):
        """Each endpoint value must be '<query_id>/<operation_name>'."""
        pattern = re.compile(r"^[A-Za-z0-9_-]+/[A-Za-z]+$")
        for name, endpoint in GRAPHQL_ENDPOINTS.items():
            assert pattern.match(endpoint), f"Endpoint '{name}' has invalid format: '{endpoint}'"

    def test_endpoint_name_matches_key(self):
        """The operation name in the value must match the dict key."""
        for name, endpoint in GRAPHQL_ENDPOINTS.items():
            op_name = endpoint.split("/", 1)[1]
            assert op_name == name, f"Key '{name}' does not match operation name '{op_name}'"

    def test_no_duplicate_query_ids(self):
        """Each query ID should be unique."""
        query_ids = [v.split("/")[0] for v in GRAPHQL_ENDPOINTS.values()]
        assert len(query_ids) == len(set(query_ids)), "Duplicate query IDs found"

    def test_search_timeline_present(self):
        """SearchTimeline endpoint must exist (regression for issue #9)."""
        assert "SearchTimeline" in GRAPHQL_ENDPOINTS
