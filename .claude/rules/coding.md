# Coding Rules

- Write clean, typed Python (type hints on all function signatures)
- Use pydantic models for all data structures
- Keep core/ free of CLI dependencies (pure business logic)
- All public functions must have docstrings
- Use `ruff` format before committing
- No hardcoded secrets or tokens in code
- Prefer composition over inheritance
- Handle errors explicitly with custom exceptions
- All CLI commands must support --json flag
