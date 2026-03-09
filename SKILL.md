---
name: x-cli
description: "Interact with Twitter/X from the terminal — read timelines, search, post, like, retweet, bookmark. Use when user asks to check Twitter, post tweets, monitor accounts, search X, or manage bookmarks."
---

# x-cli — Twitter/X CLI Skill

A CLI tool for Twitter/X using cookie-based authentication (no API keys needed).

## Setup

```bash
# Install (if not already)
cd /path/to/x-cli && uv sync

# Authenticate (one of these methods):
x auth login                           # Extract cookies from browser
x auth set --token TOKEN --ct0 CT0     # Manual cookie entry
export X_AUTH_TOKEN=xxx X_CT0=xxx      # Environment variables
```

## Commands Reference

### Reading

```bash
# Timeline
x feed                                # For-you timeline
x feed --type following               # Following timeline
x feed --count 50                     # More tweets
x feed --filter top --top 5           # Top 5 by engagement

# Search
x search "query"                      # Search (Top results)
x search "query" --type Latest        # Latest results
x search "from:user topic"           # Search from specific user

# Tweets
x tweet TWEET_ID                      # View single tweet
x tweet TWEET_ID --thread             # View full thread

# Users
x user handle                         # User profile
x user tweets handle                  # User's tweets
x user likes handle                   # User's likes
x user followers handle               # User's followers
x user following handle               # Who user follows

# Bookmarks
x bookmarks                           # View your bookmarks
```

### Writing

```bash
x post "Hello world"                  # Post a tweet
x post "reply text" --reply-to ID     # Reply to tweet
x post "quote" --quote URL            # Quote tweet
x delete TWEET_ID --force             # Delete (--force skips confirm)
x like TWEET_ID                       # Like a tweet
x unlike TWEET_ID                     # Unlike
x retweet TWEET_ID                    # Retweet
x unretweet TWEET_ID                  # Undo retweet
x bookmark TWEET_ID                   # Bookmark
x unbookmark TWEET_ID                 # Remove bookmark
```

### Account Management

```bash
x auth status                         # Check auth status
x auth login                          # Extract browser cookies
x auth login --browser chrome         # Specific browser
x auth set --token T --ct0 C          # Manual credentials
x auth accounts                       # List stored accounts
x auth switch ACCOUNT_NAME            # Switch default account
```

## JSON Output (Agent Mode)

**All commands support `--json` for structured output.** Output is auto-JSON when stdout is not a TTY (piped).

```bash
x feed --json                         # JSON array of tweets
x search "query" --json               # JSON search results
x user handle --json                  # JSON user profile
x auth status --json                  # JSON auth check
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
6. **Check auth first** with `x auth status --json` before operations
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

## Proxy Support

```bash
export X_PROXY=socks5://host:port     # SOCKS5 proxy
export X_PROXY=http://host:port       # HTTP proxy
```
