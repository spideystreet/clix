# Contributing to clix

Thanks for your interest in contributing! This guide will help you get started.

## Getting Started

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-username>/clix.git
   cd clix
   ```

2. Install dependencies with [uv](https://docs.astral.sh/uv/):

   ```bash
   uv sync
   ```

   Requires **Python 3.11+**.

## Development

### Formatting and linting

We use [ruff](https://docs.astral.sh/ruff/) for both formatting and linting:

```bash
ruff format .
ruff check .
```

Fix auto-fixable lint issues:

```bash
ruff check --fix .
```

### Running tests

```bash
pytest
```

### Code style

- Type hints on all function signatures.
- Docstrings on all public functions.
- Keep `core/` free of CLI dependencies (pure business logic).
- Use pydantic models for data structures.
- Never hardcode secrets or tokens.

### CLI commands checklist

When adding or modifying a CLI command, make sure it:

- Accepts `ctx: typer.Context` to access global flags (`--compact`, `--full-text`)
- Supports all output modes: `--json`, `--yaml`, `--compact`
- Uses helpers from `cli/helpers.py`: `get_client()`, `output_json()`, `output_yaml()`, `output_compact()`
- Reuses existing helpers instead of duplicating logic (e.g. `_handle_article()` in `tweet.py`)

## Pull Requests

1. **Create a feature branch** from `main` (e.g. `fix/my-fix`, `feat/my-feature`) — never PR from your `main` to ours.
2. **Use conventional commits** for your commit messages:
   ```
   feat(cli): add timeline filtering
   fix(auth): handle expired cookies
   ```
3. **One logical change per PR** — keep diffs focused and reviewable.
4. **Run all checks locally** before pushing:
   ```bash
   ruff format .
   ruff check .
   pytest
   ```
   CI runs the same checks — if they fail, the PR won't be merged.
5. Open your PR against the `main` branch.

## Reporting Issues

Open an issue with a clear description, steps to reproduce, and expected vs actual behavior.
