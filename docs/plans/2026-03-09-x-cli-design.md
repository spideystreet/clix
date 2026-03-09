# clix Design Document

## Goal
Build a Twitter/X CLI tool that works via cookie-based auth (no API keys).
Optimized for both human terminal use and AI agent integration.

## Design Choices
1. **typer** — modern CLI framework with autocompletion
2. **rich** — colored panels, tables, tree views for threads
3. **TOML config** — Pythonic standard
4. **pydantic models** — typed, validated data structures
5. **SKILL.md** — first-class AI agent support
6. **Multi-account** — switch between accounts
7. **Thread tree view** — visual thread hierarchy

## Architecture
- `core/` = pure business logic, no CLI deps, testable independently
- `cli/` = typer interface for humans
- `display/` = rich formatting (only used in human mode)
- `models/` = pydantic models for API responses
- SKILL.md = agent interface documentation

## Auth Flow
1. Check env vars (X_AUTH_TOKEN, X_CT0)
2. Check stored credentials (~/.config/clix/auth.json)
3. Extract from browser (Chrome > Firefox > Edge > Brave)
4. Store extracted cookies for reuse (encrypted with machine key)

## API Strategy
- Use Twitter GraphQL endpoints (same as web app)
- curl_cffi for TLS fingerprinting (appear as real browser)
- Rate limiting: configurable delays with jitter
- Proxy support via X_PROXY env var

## Output Modes
- **Human**: rich panels with colors, engagement stats, timestamps
- **JSON**: structured output for piping and agent consumption
- **Auto-detect**: JSON when stdout is not a TTY
