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

## CLI Rules
- All commands must support `--json` flag
- Use `get_client()` from `cli/helpers.py` for XClient creation
- Use `is_json_mode()` / `output_json()` for output

## MCP Rules
- All tools return `str` (JSON serialized)
- Wrap tool bodies in try/except, return `_error_response()` on failure
- Use `XClient()` context manager directly (auto-resolves credentials)
- Alias conflicting imports from `core.api` with underscore prefix
