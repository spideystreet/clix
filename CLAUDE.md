# clix — Twitter/X CLI Tool

## Project Overview
A command-line interface for Twitter/X that uses cookie-based authentication (no API keys).
Designed for both humans (rich terminal output) and AI agents (structured JSON output + SKILL.md).

## Tech Stack
- **Python 3.11+** with `uv` for package management
- **typer** for CLI framework
- **rich** for terminal formatting
- **curl_cffi** for HTTP with TLS fingerprinting
- **pydantic** for data models
- **browser_cookie3** for cookie extraction
- **ruff** for linting
- **pytest** for testing

## Project Structure
```
clix/
├── __init__.py        # version
├── __main__.py        # python -m clix
├── cli/               # typer commands
│   ├── app.py         # main app + global options
│   ├── feed.py        # feed commands
│   ├── tweet.py       # tweet commands
│   ├── user.py        # user commands
│   └── search.py      # search commands
├── core/              # business logic (no CLI deps)
│   ├── api.py         # API methods
│   ├── auth.py        # cookie extraction & management
│   ├── client.py      # HTTP client (curl_cffi)
│   ├── config.py      # TOML config management
│   └── constants.py   # endpoints, headers, defaults
├── models/            # pydantic models
│   ├── tweet.py       # Tweet model
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
- `clix post <text> [--reply-to ID]` — post tweet
- `clix delete <id>` — delete tweet
- `clix like/unlike <id>` — like operations
- `clix retweet/unretweet <id>` — retweet operations
- `clix bookmark/unbookmark <id>` — bookmark operations
- `clix bookmarks` — list bookmarks
- `clix auth` — authenticate / check auth status
- `clix config` — manage config

## Conventions
- All commands support `--json` flag for structured JSON output
- Non-TTY detection: auto-switch to JSON when piped
- Exit codes: 0 success, 1 general error, 2 auth error, 3 rate limit
- Atomic commits with descriptive messages
- Never commit secrets (.env, cookies, tokens)
- Use `ruff` for formatting and linting before commits
- Tests in `tests/` mirroring `clix/` structure

## Git Config
- User: spideystreet <dhicham.pro@gmail.com>
- Branch strategy: dev branch, merge to main when stable
- Atomic commits, no sensitive data

## Auth Priority
1. Environment variables: `X_AUTH_TOKEN`, `X_CT0`
2. Stored credentials: `~/.config/clix/auth.json` (encrypted)
3. Browser cookie extraction (Chrome, Firefox, Edge, Brave)
