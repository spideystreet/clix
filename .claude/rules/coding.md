# Coding Rules

## General
- Write clean, typed Python (type hints on all function signatures)
- Use pydantic models for all data structures
- All public functions must have docstrings
- Use `ruff format` and `ruff check` before committing
- No hardcoded secrets or tokens in code
- Prefer composition over inheritance
- Handle errors explicitly with custom exceptions

## Architecture Boundaries
- `core/` — pure business logic, no CLI or MCP deps
- `cli/` — typer commands, depends on `core/` only
- `mcp/` — MCP server, depends on `core/` only
- `display/` — rich formatting, used by `cli/` only
- `models/` — pydantic models, used everywhere
- `utils/` — shared utilities (article parser, filter, rate limit)

## CLI Rules
- All commands must support `--json` flag
- Use `get_client()` from `cli/helpers.py` for XClient creation
- Use `is_json_mode()` / `output_json()` for standard output
- Use `is_compact_mode()` / `output_compact()` for `--compact` mode
- Use `is_yaml_mode()` / `output_yaml()` for `--yaml` mode
- Global flags (`--compact`, `--full-text`, `--yaml`) stored in `ctx.obj`
- Handle → user_id resolution via `get_user_by_handle()` for user action commands

## MCP Rules
- All tools return `str` (JSON serialized)
- Wrap tool bodies in try/except, return `_error_response()` on failure
- Use `XClient()` context manager directly (auto-resolves credentials)
- Alias conflicting imports from `core.api` with underscore prefix

## Client Methods
- `graphql_get(operation, variables)` — dynamic query ID from endpoint resolver
- `graphql_post(operation, variables)` — dynamic query ID from endpoint resolver
- `graphql_post_raw(query_id, operation, variables)` — hardcoded query ID (for ops not in JS bundles)
- `rest_post(url, data)` — form-encoded REST POST (follow, block, mute)
- `rest_get(url, params)` — authenticated REST GET (DM inbox)

## GraphQL API Gotchas
- **Always check required variables**: Twitter/X GraphQL endpoints may require variables even when they seem optional. Missing variables cause HTTP 422
- **Fallback query IDs**: Some operations (CreateRetweet, CreateBookmark, DeleteBookmark, scheduled tweet ops) are not in X.com JS bundles — use `FALLBACK_OPERATIONS` in `endpoints.py` or `graphql_post_raw()`
- **GET→POST migration**: X.com periodically migrates read endpoints from GET to POST. The client auto-retries as POST on 404 after cache refresh, so no caller changes needed
- **BookmarkSearchTimeline**: search-only — `rawQuery: ""` triggers `ERROR_EMPTY_QUERY`. Use broad catch-all OR query to fetch all bookmarks
- **Response paths change**: Always verify actual response structure and add new paths to `_find_instructions()` in `api.py`
- When adding new endpoints, verify the full variable schema — don't assume optional fields are truly optional
