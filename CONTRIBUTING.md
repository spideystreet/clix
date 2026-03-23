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

## Pull Requests

1. **Branch from `main`** — never commit directly to `main`.
2. **Use conventional commits** for your commit messages:
   ```
   feat(cli): add timeline filtering
   fix(auth): handle expired cookies
   ```
3. **One logical change per PR** — keep diffs focused and reviewable.
4. Make sure all checks pass before requesting review:
   ```bash
   ruff format --check .
   ruff check .
   pytest
   ```
5. Open your PR against the `main` branch.

## Reporting Issues

Open an issue with a clear description, steps to reproduce, and expected vs actual behavior.
