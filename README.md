<p align="center">
  <img src="X.png" alt="clix" width="120">
</p>

<h3 align="center"><b>Twitter/X from your terminal. No API keys. No bullshit.</b></h3>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-PolyForm%20NC%201.0-blue?style=flat-square" alt="PolyForm NC 1.0"></a>
  <a href="https://pypi.org/project/clix0/"><img src="https://img.shields.io/pypi/v/clix0?style=flat-square&label=PyPI&color=green" alt="PyPI"></a>
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
clix auth
```

## Commands

| Command | Description |
|---|---|
| `clix feed [--type for-you\|following] [--count N]` | Timeline |
| `clix search <query> [--type top\|latest\|photos\|videos]` | Search tweets |
| `clix tweet <id>` | View tweet + thread |
| `clix user <handle>` | Profile + recent tweets |
| `clix post <text> [--reply-to ID]` | Post a tweet |
| `clix delete <id>` | Delete a tweet |
| `clix like <id>` / `clix unlike <id>` | Like / unlike |
| `clix retweet <id>` / `clix unretweet <id>` | Retweet / undo |
| `clix bookmark <id>` / `clix unbookmark <id>` | Bookmark / remove |
| `clix bookmarks` | List bookmarks |
| `clix auth` | Auth status / setup |
| `clix config` | Manage config |

## Agent Mode

Every command supports `--json` for structured output. Pipe detection is automatic — non-TTY gets JSON by default.

```bash
# explicit
clix feed --json | jq '.tweets[0].text'

# automatic when piped
clix search "LLM" | python process.py
```

See [`SKILL.md`](SKILL.md) for AI agent integration docs.

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

**14 tools:** `get_feed`, `search`, `get_tweet`, `get_user`, `list_bookmarks`, `post_tweet`, `delete_tweet`, `like`, `unlike`, `retweet`, `unretweet`, `bookmark`, `unbookmark`, `auth_status`

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Disclaimer

> This tool is for **educational and personal use only**. It is not affiliated with, endorsed by, or associated with X Corp (formerly Twitter). Use at your own risk. The authors are not responsible for any consequences resulting from the use of this software. By using this tool, you agree to comply with X/Twitter's Terms of Service.

## License

[PolyForm Noncommercial 1.0.0](LICENSE)
