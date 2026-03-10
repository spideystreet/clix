# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-11

### Added
- Runtime extraction of GraphQL operation IDs from X.com JS bundles (`clix/core/endpoints.py`)
- Per-operation feature switch extraction — only sends the features each query needs
- Disk + memory cache for extracted endpoints (`~/.config/clix/graphql_ops.json`, 24h TTL)
- Auto-retry on HTTP 404 with cache invalidation (stale operation IDs)
- Full browser-like headers (Client Hints, Sec-Fetch-*) for Cloudflare bypass
- Runtime Chrome impersonation target detection (`best_chrome_target()`)
- Integration tests against live X.com

### Changed
- GraphQL endpoints are no longer hardcoded — resolved dynamically at runtime
- Feature flags are no longer hardcoded — extracted from `__INITIAL_STATE__` and scoped per-operation
- `Bookmarks` operation renamed to `BookmarkSearchTimeline` (X.com API change)

### Fixed
- HTTP 404 on GraphQL endpoints due to stale hardcoded operation IDs (closes #9)
- HTTP 503 from Cloudflare due to missing browser-like headers

## [0.1.0] - 2026-03-09

### Added
- Initial release
- CLI commands: feed, search, tweet, user, post, delete, like/unlike, retweet/unretweet, bookmark/unbookmark, bookmarks, auth, config
- MCP server with 14 tools (stdio transport)
- Cookie-based authentication (browser extraction, env vars, manual)
- Rich terminal output + `--json` flag for piped/scripted usage
- TLS fingerprinting via curl_cffi
