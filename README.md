<p align="center">
  <img src="https://github.com/user-attachments/assets/e7c0c8af-ae61-4a85-8aef-32a8367f505b" alt="clix" width="120">
</p>

<h3 align="center"><b>X from terminal. No API keys. No bullshit.</b></h3>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT"></a>
  <a href="https://pypi.org/project/clix0/"><img src="https://img.shields.io/pypi/v/clix0?style=flat-square&label=PyPI&color=green&cacheSeconds=3600" alt="PyPI"></a>
</p>

---

## Why?

Twitter killed free API access. clix uses **cookie-based auth** — just log in with your browser, and you're in.
Works for humans (rich terminal output) and AI agents (structured JSON). Zero API keys, zero OAuth dance.

## Quick Start

```bash
# install
uv pip install clix0

# authenticate (extracts cookies from your browser)
clix auth login
```

## Commands

### Content

| Command | Description |
|---|---|
| `clix feed [--type for-you\|following] [--count N]` | Timeline |
| `clix search <query> [--type top\|latest\|photos\|videos]` | Search tweets |
| `clix trending` | Trending topics |
| `clix tweet <id> [--export FILE]` | View tweet + thread (export articles as Markdown) |
| `clix tweets <id1> <id2> ...` | Batch fetch tweets |
| `clix user <handle>` | Profile + recent tweets |
| `clix users <handle1> <handle2> ...` | Batch fetch users |
| `clix bookmarks` | List bookmarks |

### Actions

| Command | Description |
|---|---|
| `clix post <text> [--reply-to ID] [--image FILE]` | Post a tweet (up to 4 images) |
| `clix delete <id>` | Delete a tweet |
| `clix like <id>` / `clix unlike <id>` | Like / unlike |
| `clix retweet <id>` / `clix unretweet <id>` | Retweet / undo |
| `clix bookmark <id>` / `clix unbookmark <id>` | Bookmark / remove |
| `clix follow <handle>` / `clix unfollow <handle>` | Follow / unfollow |
| `clix block <handle>` / `clix unblock <handle>` | Block / unblock |
| `clix mute <handle>` / `clix unmute <handle>` | Mute / unmute |
| `clix download <tweet-id> [--output-dir DIR]` | Download media |

### Scheduled Tweets

| Command | Description |
|---|---|
| `clix schedule <text> --at <time>` | Schedule a tweet |
| `clix scheduled` | List scheduled tweets |
| `clix unschedule <id>` | Cancel scheduled tweet |

### Lists

| Command | Description |
|---|---|
| `clix lists` | View your lists |
| `clix lists view <id>` | Tweets from a list |
| `clix lists create <name> [--private]` | Create a list |
| `clix lists delete <id>` | Delete a list |
| `clix lists members <id>` | View members |
| `clix lists add-member <id> <handle>` | Add member |
| `clix lists remove-member <id> <handle>` | Remove member |

### Direct Messages

| Command | Description |
|---|---|
| `clix dm inbox` | View conversations |
| `clix dm send <handle> <text>` | Send a DM |

### System

| Command | Description |
|---|---|
| `clix auth status\|login\|set\|accounts\|switch\|import` | Authentication |
| `clix config` | Manage config |
| `clix doctor` | Run diagnostics |

## Output Modes

Every command supports `--json` for structured output. Pipe detection is automatic — non-TTY gets JSON by default.

```bash
# structured JSON
clix feed --json | jq '.tweets[0].text'

# token-optimized for AI agents
clix feed --compact

# YAML
clix feed --yaml

# full text (no truncation)
clix feed --full-text
```

## MCP Server

clix ships as an [MCP](https://modelcontextprotocol.io) server — any MCP-compatible client can use it.

```json
{
  "mcpServers": {
    "clix": {
      "command": "uvx",
      "args": ["clix0", "mcp"]
    }
  }
}
```

Or with explicit auth:

```json
{
  "mcpServers": {
    "clix": {
      "command": "uvx",
      "args": ["clix0", "mcp"],
      "env": {
        "X_AUTH_TOKEN": "your-token",
        "X_CT0": "your-ct0"
      }
    }
  }
}
```

**38 tools** covering all commands: feed, search, trending, tweets, users, bookmarks, lists, DMs, post, delete, like, unlike, retweet, unretweet, bookmark, unbookmark, follow, unfollow, block, unblock, mute, unmute, schedule, download, and more.

## Proxy Support

```bash
# via environment variable
CLIX_PROXY=socks5://127.0.0.1:1080 clix feed

# via config
clix config set network.proxy socks5://127.0.0.1:1080
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Disclaimer

> This tool is for **educational and personal use only**. It is not affiliated with, endorsed by, or associated with X Corp (formerly Twitter). Use at your own risk. The authors are not responsible for any consequences resulting from the use of this software. By using this tool, you agree to comply with X/Twitter's Terms of Service.

## License

[MIT](LICENSE)
