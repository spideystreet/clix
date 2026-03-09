---
name: clix
description: "Interact with Twitter/X from the terminal — read timelines, search, post, like, retweet, bookmark. Use when user asks to check Twitter, post tweets, monitor accounts, search X, or manage bookmarks."
---

# clix — Twitter/X CLI Skill

A CLI tool for Twitter/X using cookie-based authentication (no API keys needed).

## Setup

```bash
# Install (if not already)
cd /path/to/clix && uv sync

# Authenticate (one of these methods):
clix auth login                           # Extract cookies from browser
clix auth set --token TOKEN --ct0 CT0     # Manual cookie entry
export X_AUTH_TOKEN=xxx X_CT0=xxx      # Environment variables
```

## Commands Reference

### Reading

```bash
# Timeline
clix feed                                # For-you timeline
clix feed --type following               # Following timeline
clix feed --count 50                     # More tweets
clix feed --filter top --top 5           # Top 5 by engagement

# Search
clix search "query"                      # Search (Top results)
clix search "query" --type Latest        # Latest results
clix search "from:user topic"           # Search from specific user

# Tweets
clix tweet TWEET_ID                      # View single tweet
clix tweet TWEET_ID --thread             # View full thread

# Users
clix user handle                         # User profile
clix user tweets handle                  # User's tweets
clix user likes handle                   # User's likes
clix user followers handle               # User's followers
clix user following handle               # Who user follows

# Bookmarks
clix bookmarks                           # View your bookmarks
```

### Writing

```bash
clix post "Hello world"                  # Post a tweet
clix post "reply text" --reply-to ID     # Reply to tweet
clix post "quote" --quote URL            # Quote tweet
clix delete TWEET_ID --force             # Delete (--force skips confirm)
clix like TWEET_ID                       # Like a tweet
clix unlike TWEET_ID                     # Unlike
clix retweet TWEET_ID                    # Retweet
clix unretweet TWEET_ID                  # Undo retweet
clix bookmark TWEET_ID                   # Bookmark
clix unbookmark TWEET_ID                 # Remove bookmark
```

### Account Management

```bash
clix auth status                         # Check auth status
clix auth login                          # Extract browser cookies
clix auth login --browser chrome         # Specific browser
clix auth set --token T --ct0 C          # Manual credentials
clix auth accounts                       # List stored accounts
clix auth switch ACCOUNT_NAME            # Switch default account
```

## JSON Output (Agent Mode)

**All commands support `--json` for structured output.** Output is auto-JSON when stdout is not a TTY (piped).

```bash
clix feed --json                         # JSON array of tweets
clix search "query" --json               # JSON search results
clix user handle --json                  # JSON user profile
clix auth status --json                  # JSON auth check
```

### JSON Tweet Schema

```json
{
  "id": "1234567890",
  "text": "Tweet content",
  "author_handle": "username",
  "author_name": "Display Name",
  "author_verified": true,
  "created_at": "2024-01-01T00:00:00Z",
  "engagement": {
    "likes": 100,
    "retweets": 50,
    "replies": 10,
    "views": 5000,
    "bookmarks": 5,
    "quotes": 2
  },
  "media": [{"type": "photo", "url": "..."}],
  "reply_to_id": null,
  "tweet_url": "https://x.com/username/status/1234567890"
}
```

## Best Practices for Agents

1. **Always use `--json`** for parseable output
2. **Use `--force`** on `delete` to skip interactive confirmation
3. **Respect rate limits** — add delays between bulk operations
4. **Use `--count`** to limit results (default: 20, max: 100)
5. **Use `--pages`** for pagination (feed/search only)
6. **Check auth first** with `clix auth status --json` before operations
7. **Use `--account`** for multi-account workflows

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Authentication error |
| 3 | Rate limit exceeded |

## Rate Limiting

- Read operations have ~1.5s built-in delay between requests
- Write operations have 1.5-4s random delay
- Exponential backoff on 429 responses
- For bulk operations, add your own delays between calls

## MCP Server

clix is also available as an MCP server with 14 tools for any MCP-compatible client.

```bash
clix mcp    # Start stdio MCP server
```

Configure in your MCP client:

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

## Proxy Support

```bash
export X_PROXY=socks5://host:port     # SOCKS5 proxy
export X_PROXY=http://host:port       # HTTP proxy
```
