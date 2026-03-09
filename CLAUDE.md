# clix — Twitter/X CLI + MCP Server

## Project Overview
A CLI and MCP server for Twitter/X using cookie-based authentication (no API keys).
Three interfaces: rich terminal output (humans), `--json` flag (piped/scripted), MCP server (AI agents).

## Tech Stack
- **Python 3.11+** with `uv` for package management
- **typer** for CLI framework
- **rich** for terminal formatting
- **curl_cffi** for HTTP with TLS fingerprinting
- **pydantic** for data models
- **browser_cookie3** for cookie extraction
- **mcp** (FastMCP) for MCP server (stdio transport)
- **ruff** for linting
- **pytest** for testing

## Project Structure
```
clix/
├── __init__.py        # version
├── __main__.py        # python -m clix
├── cli/               # typer commands
│   ├── app.py         # main app + global options + mcp command
│   ├── helpers.py     # shared CLI utilities
│   ├── feed.py        # feed commands
│   ├── tweet.py       # tweet commands
│   ├── user.py        # user commands
│   └── search.py      # search commands
├── mcp/               # MCP server
│   ├── __init__.py
│   └── server.py      # FastMCP server with 14 tools
├── core/              # business logic (no CLI deps)
│   ├── api.py         # API methods (read + write)
│   ├── auth.py        # cookie extraction & credential management
│   ├── client.py      # HTTP client (curl_cffi + TLS fingerprinting)
│   ├── config.py      # TOML config management
│   └── constants.py   # endpoints, headers, defaults
├── models/            # pydantic models
│   ├── tweet.py       # Tweet, TweetEngagement, TweetMedia, TimelineResponse
│   └── user.py        # User model
├── display/           # rich formatting (humans only)
│   └── formatter.py   # tweet/user/thread formatting
└── utils/
    ├── filter.py      # engagement scoring
    └── rate_limit.py  # rate limiting with jitter
```

## Commands
- `clix feed [--type for-you|following] [--count N]` — timeline
- `clix search <query> [--type top|latest|photos|videos]` — search
- `clix tweet <id>` — view tweet + thread
- `clix user <handle>` — user profile + recent tweets
- `clix post <text> [--reply-to ID] [--quote URL]` — post tweet
- `clix delete <id> [--force]` — delete tweet
- `clix like/unlike <id>` — like operations
- `clix retweet/unretweet <id>` — retweet operations
- `clix bookmark/unbookmark <id>` — bookmark operations
- `clix bookmarks` — list bookmarks
- `clix auth status|login|set|accounts|switch|import` — authentication
- `clix config` — manage config
- `clix mcp` — start MCP server (stdio transport)

## MCP Server
`clix mcp` launches a stdio MCP server with 14 tools:
- **Read:** `get_feed`, `search`, `get_tweet`, `get_user`, `list_bookmarks`
- **Write:** `post_tweet`, `delete_tweet`, `like`, `unlike`, `retweet`, `unretweet`, `bookmark`, `unbookmark`
- **Info:** `auth_status`

Server code in `clix/mcp/server.py` — imports directly from `clix.core.api` and `clix.core.auth` (zero duplication).

## Conventions
- All CLI commands support `--json` flag for structured JSON output
- Non-TTY detection: auto-switch to JSON when piped
- Exit codes: 0 success, 1 general error, 2 auth error, 3 rate limit
- MCP tools return JSON strings, errors as `{"error": ..., "type": ...}`
- `core/` has no CLI or MCP deps — pure business logic, testable independently
- `mcp/` imports from `core/` only — no CLI deps
- Atomic commits with conventional commit messages
- Never commit secrets (.env, cookies, tokens)
- Run `ruff check` and `ruff format --check` before commits
- Tests in `tests/` mirroring `clix/` structure

## Auth Priority
1. Environment variables: `X_AUTH_TOKEN`, `X_CT0`
2. Stored credentials: `~/.config/clix/auth.json`
3. Browser cookie extraction (Chrome, Firefox, Edge, Brave)

Used by both CLI (`get_client()` in helpers.py) and MCP (`XClient()` in server.py) — same priority chain.
