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
- **xclienttransaction** for X-Client-Transaction-Id header
- **pyyaml** for YAML output
- **ruff** for linting
- **pytest** for testing

## Project Structure
```
clix/
├── __init__.py        # version
├── __main__.py        # python -m clix
├── cli/               # typer commands
│   ├── app.py         # main app + global options + action commands
│   ├── helpers.py     # shared CLI utilities (output modes, client)
│   ├── feed.py        # feed commands
│   ├── tweet.py       # tweet commands
│   ├── user.py        # user commands
│   ├── search.py      # search commands
│   ├── lists.py       # list commands (view + CRUD)
│   ├── dm.py          # direct message commands
│   └── jobs.py        # job search commands
├── mcp/               # MCP server
│   ├── __init__.py
│   └── server.py      # FastMCP server with 46 tools
├── core/              # business logic (no CLI deps)
│   ├── api.py         # API methods (read + write + DM + lists + media + jobs)
│   ├── auth.py        # cookie extraction & credential management
│   ├── client.py      # HTTP client (curl_cffi + TLS fingerprinting + transaction ID)
│   ├── config.py      # TOML config management
│   ├── constants.py   # endpoints, headers, defaults
│   └── endpoints.py   # runtime GraphQL operation ID extraction
├── models/            # pydantic models
│   ├── tweet.py       # Tweet, TweetEngagement, TweetMedia, TimelineResponse
│   ├── user.py        # User model
│   ├── dm.py          # DMConversation, DMMessage models
│   └── job.py         # Job, JobCompany, JobSearchResponse models
├── display/           # rich formatting (humans only)
│   └── formatter.py   # tweet/user/thread/list/trend/DM/article/job formatting
└── utils/
    ├── article.py     # Draft.js → Markdown converter (Twitter Articles)
    ├── filter.py      # engagement scoring
    └── rate_limit.py  # rate limiting with jitter
```

## Commands

### Content
- `clix feed [--type for-you|following] [--count N]` — timeline
- `clix search <query> [--type top|latest|photos|videos]` — search
- `clix trending` — trending topics
- `clix tweet <id> [--export FILE]` — view tweet (+ article export)
- `clix tweets <id1> [id2...]` — batch fetch tweets
- `clix user <handle>` — user profile
- `clix users <handle1> [handle2...]` — batch fetch users
- `clix bookmarks` — list bookmarks

### Actions
- `clix post <text> [--reply-to ID] [--quote URL] [--image FILE]` — post tweet (with images)
- `clix delete <id> [--force]` — delete tweet
- `clix like/unlike <id>` — like operations
- `clix retweet/unretweet <id>` — retweet operations
- `clix bookmark/unbookmark <id>` — bookmark operations
- `clix follow/unfollow <handle>` — follow operations
- `clix block/unblock <handle>` — block operations
- `clix mute/unmute <handle>` — mute operations
- `clix download <tweet-id> [--output-dir DIR]` — download media

### Jobs
- `clix jobs search <query> [--location LOC] [--location-type remote|onsite|hybrid]` — search job listings
- `clix jobs view <id>` — view job details

### Scheduled Tweets
- `clix schedule <text> --at <time>` — schedule tweet
- `clix scheduled` — list scheduled tweets
- `clix unschedule <id>` — cancel scheduled tweet

### Lists
- `clix lists` — show your lists
- `clix lists view <id> [--count N]` — tweets from a list
- `clix lists create <name> [--description TEXT] [--private]` — create list
- `clix lists delete <id> [--force]` — delete list
- `clix lists members <id>` — list members
- `clix lists add-member/remove-member <id> <handle>` — manage members
- `clix lists pin/unpin <id>` — pin/unpin lists

### Direct Messages
- `clix dm inbox` — view conversations
- `clix dm send <handle> <text>` — send DM

### System
- `clix auth status|login|set|accounts|switch|import` — authentication
- `clix config` — manage config
- `clix doctor` — run diagnostics
- `clix mcp` — start MCP server (stdio transport)

### Global Flags
- `--json` — structured JSON output
- `--yaml` — YAML output
- `--compact` / `-c` — token-optimized JSON for AI agents
- `--full-text` — disable text truncation
- `--account` / `-a` — use specific account

## MCP Server
`clix mcp` launches a stdio MCP server with 46 tools:
- **Read:** `get_feed`, `search`, `get_tweet`, `get_user`, `list_bookmarks`, `get_trending`, `get_lists`, `get_list_timeline`, `get_list_members`, `get_tweets_batch`, `get_users_batch`, `dm_inbox`, `list_scheduled_tweets`, `search_jobs`, `get_job`
- **Write:** `post_tweet`, `delete_tweet`, `like`, `unlike`, `retweet`, `unretweet`, `bookmark`, `unbookmark`, `follow`, `unfollow`, `block`, `unblock`, `mute`, `unmute`, `create_list`, `delete_list`, `add_list_member`, `remove_list_member`, `pin_list`, `unpin_list`, `dm_send`, `schedule_tweet`, `cancel_scheduled_tweet`, `download_media`
- **Info:** `auth_status`

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
3. Browser cookie extraction (Chrome multi-profile, Firefox, Edge, Brave)

Used by both CLI (`get_client()` in helpers.py) and MCP (`XClient()` in server.py) — same priority chain.
