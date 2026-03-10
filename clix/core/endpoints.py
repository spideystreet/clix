"""Runtime extraction of GraphQL operation IDs from X.com JS bundles."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from curl_cffi import requests as curl_requests

from clix.core.constants import (
    BASE_URL,
    CONFIG_DIR_NAME,
    SEC_CH_UA_ARCH,
    SEC_CH_UA_BITNESS,
    SEC_CH_UA_MOBILE,
    SEC_CH_UA_MODEL,
    SEC_CH_UA_PLATFORM_VERSION,
    best_chrome_target,
    get_accept_language,
    get_sec_ch_ua,
    get_sec_ch_ua_full_version_list,
    get_sec_ch_ua_platform,
    get_user_agent,
    sync_chrome_version,
)

logger = logging.getLogger(__name__)

# --- Bundle URL patterns ---

_BUNDLE_HREF_PATTERN = re.compile(
    r'href="(https://abs\.twimg\.com/responsive-web/client-web/[^"]+\.js)"'
)
_BUNDLE_SRC_PATTERN = re.compile(
    r'src="(https://abs\.twimg\.com/responsive-web/client-web/[^"]+\.js)"'
)

# Chunk mapping pattern: e+"."+{"api":"abc123","chunk":"def456"}[e]+"a.js"
_CHUNK_MAP_PATTERN = re.compile(r'"\+(\{[^}]+\})\[e\]\+"a\.js"')
_BUNDLE_CDN_BASE = "https://abs.twimg.com/responsive-web/client-web"

# --- Operation extraction pattern ---

_OPERATION_PATTERN = re.compile(
    r'queryId:\s*"([A-Za-z0-9_-]+)"'
    r".*?"
    r'operationName:\s*"([A-Za-z]+)"',
    re.DOTALL,
)

# --- Feature flag extraction ---

_INITIAL_STATE_MARKER = "window.__INITIAL_STATE__="

# --- Cache constants ---

CACHE_FILE_NAME = "graphql_ops.json"
CACHE_TTL_SECONDS = 86400  # 24 hours

# --- Fetch constants ---

_HOMEPAGE_URL = "https://x.com/elonmusk"

# Module-level cache to avoid re-reading disk on every call within a session
_memory_cache: dict[str, Any] | None = None


def extract_bundle_urls(html: str) -> list[str]:
    """Extract JS bundle URLs from X.com homepage HTML.

    Looks for <link> and <script> tags pointing to abs.twimg.com bundles,
    plus chunk URLs from inline JS chunk mappings.
    Returns a deduplicated list of URLs, main.js first.
    """
    urls = _BUNDLE_HREF_PATTERN.findall(html)
    urls.extend(_BUNDLE_SRC_PATTERN.findall(html))

    # Extract chunk URLs from inline JS: e+"."+{"api":"hash","endpoints":"hash"}[e]+"a.js"
    for match in _CHUNK_MAP_PATTERN.findall(html):
        try:
            chunk_map = json.loads(match)
            for name, hash_val in chunk_map.items():
                chunk_url = f"{_BUNDLE_CDN_BASE}/{name}.{hash_val}a.js"
                urls.append(chunk_url)
            logger.debug("Found %d chunk URLs from inline JS mapping", len(chunk_map))
        except (json.JSONDecodeError, TypeError):
            logger.debug("Failed to parse chunk mapping: %s", match[:100])

    # Deduplicate preserving order, main.js first
    seen: set[str] = set()
    main_urls: list[str] = []
    other_urls: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        if "/main." in url:
            main_urls.append(url)
        else:
            other_urls.append(url)

    result = main_urls + other_urls
    if not result:
        logger.warning(
            "No JS bundle URLs found in X.com HTML — "
            "page structure may have changed, or the request was blocked"
        )
    else:
        logger.debug("Found %d bundle URLs (main.js: %s)", len(result), bool(main_urls))
    return result


def extract_operations_from_js(
    js_content: str,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Extract GraphQL operations and their feature switches from JS bundle.

    Parses patterns like:
      queryId:"abc123",operationName:"HomeTimeline",...
      metadata:{featureSwitches:["feat_a","feat_b"]}

    Returns:
      - ops: dict mapping operation name to 'queryId/operationName'
      - op_features: dict mapping operation name to list of required feature keys
    """
    ops: dict[str, str] = {}
    op_features: dict[str, list[str]] = {}

    # Split by queryId boundaries to avoid greedy cross-operation matching
    blocks = re.split(r"(?=queryId:\s*\")", js_content)

    for block in blocks:
        m = re.search(
            r'queryId:\s*"([A-Za-z0-9_-]+)"'
            r".*?"
            r'operationName:\s*"([A-Za-z]+)"',
            block[:500],
            re.DOTALL,
        )
        if not m:
            continue

        query_id, op_name = m.groups()
        endpoint = f"{query_id}/{op_name}"

        if op_name in ops and ops[op_name] != endpoint:
            logger.warning(
                "Duplicate operation '%s' with different query IDs: "
                "'%s' vs '%s' — keeping the last one",
                op_name,
                ops[op_name],
                endpoint,
            )
        ops[op_name] = endpoint

        # Extract featureSwitches from metadata (within same block, limited scope)
        fs_match = re.search(r"featureSwitches:\s*(\[[^\]]*\])", block[:3000])
        if fs_match:
            try:
                op_features[op_name] = json.loads(fs_match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

    if not ops:
        logger.debug(
            "No GraphQL operations in JS bundle (%d bytes) — likely a vendor/framework bundle",
            len(js_content),
        )
    else:
        logger.debug(
            "Extracted %d GraphQL operations (%d with feature switches) from JS",
            len(ops),
            len(op_features),
        )

    return ops, op_features


def _extract_json_object(text: str, start: int) -> str | None:
    """Extract a complete JSON object from text starting at the given '{' position.

    Uses brace-counting to handle nested objects correctly.
    """
    if start >= len(text) or text[start] != "{":
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def extract_features_from_html(html: str) -> dict[str, bool]:
    """Extract feature flags from window.__INITIAL_STATE__ in HTML.

    Parses the featureSwitch.features object and extracts boolean values.
    Returns a flat dict of {feature_name: bool_value}.
    """
    idx = html.find(_INITIAL_STATE_MARKER)
    if idx == -1:
        logger.warning(
            "No window.__INITIAL_STATE__ found in HTML — "
            "X.com may have changed how feature flags are embedded"
        )
        return {}

    json_start = idx + len(_INITIAL_STATE_MARKER)
    raw_json = _extract_json_object(html, json_start)
    if not raw_json:
        logger.error(
            "Found __INITIAL_STATE__ marker but could not extract JSON object — "
            "brace matching failed, the HTML structure may have changed"
        )
        return {}

    try:
        state = json.loads(raw_json)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse __INITIAL_STATE__ JSON (%d chars): %s — "
            "the JSON structure may be malformed or truncated",
            len(raw_json),
            e,
        )
        return {}

    # Try both known paths: defaultConfig (current) and features (legacy)
    fs = state.get("featureSwitch", {})
    features_obj = fs.get("defaultConfig", {}) or fs.get("features", {})

    features: dict[str, bool] = {}
    for key, val in features_obj.items():
        v = val.get("value") if isinstance(val, dict) else val
        if isinstance(v, bool):
            features[key] = v

    if not features:
        logger.warning(
            "Parsed __INITIAL_STATE__ but found 0 boolean feature flags — "
            "the nested structure featureSwitch.features may have changed"
        )
    else:
        logger.debug("Extracted %d feature flags from __INITIAL_STATE__", len(features))

    return features


# --- Cache functions ---


def _get_cache_path() -> Path:
    """Get the path to the cached operations file."""
    return Path.home() / ".config" / CONFIG_DIR_NAME / CACHE_FILE_NAME


def _read_cache(path: Path, ttl: int = CACHE_TTL_SECONDS) -> dict[str, Any] | None:
    """Read cached operations if the file exists and is not expired."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        logger.debug("Cache miss: %s does not exist", path)
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Cache file %s is corrupted or unreadable: %s — will re-fetch from X.com",
            path,
            e,
        )
        return None

    timestamp = data.get("timestamp", 0)
    age = time.time() - timestamp
    if age > ttl:
        logger.info(
            "Cache expired: age=%.0fs, ttl=%ds — will re-fetch from X.com",
            age,
            ttl,
        )
        return None

    logger.debug("Cache hit: age=%.0fs, %d endpoints", age, len(data.get("endpoints", {})))
    return data


def _write_cache(data: dict[str, Any], path: Path | None = None) -> None:
    """Write operations data to cache file."""
    path = path or _get_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    logger.debug("Cache written to %s", path)


# --- Orchestration ---


def _build_fetch_headers() -> dict[str, str]:
    """Build browser-like headers for fetching X.com homepage and JS bundles."""
    return {
        "user-agent": get_user_agent(),
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": get_accept_language(),
        "sec-ch-ua": get_sec_ch_ua(),
        "sec-ch-ua-mobile": SEC_CH_UA_MOBILE,
        "sec-ch-ua-platform": get_sec_ch_ua_platform(),
        "sec-ch-ua-arch": SEC_CH_UA_ARCH,
        "sec-ch-ua-bitness": SEC_CH_UA_BITNESS,
        "sec-ch-ua-full-version-list": get_sec_ch_ua_full_version_list(),
        "sec-ch-ua-model": SEC_CH_UA_MODEL,
        "sec-ch-ua-platform-version": SEC_CH_UA_PLATFORM_VERSION,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "referer": f"{BASE_URL}/",
        "upgrade-insecure-requests": "1",
    }


def _fetch_and_extract() -> tuple[dict[str, str], dict[str, bool], dict[str, list[str]]]:
    """Fetch X.com homepage + JS bundles and extract operations + features.

    Respects X_PROXY / TWITTER_PROXY environment variables.
    Returns (endpoints, feature_values, op_features).
    Raises RuntimeError if extraction fails at any step.
    """
    target = best_chrome_target()
    sync_chrome_version(target)
    session = curl_requests.Session(impersonate=target)

    proxy = os.environ.get("X_PROXY") or os.environ.get("TWITTER_PROXY")
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    headers = _build_fetch_headers()

    # Step 1: Fetch homepage
    logger.info("Fetching X.com homepage to discover JS bundles...")
    try:
        response = session.get(_HOMEPAGE_URL, headers=headers, timeout=15)
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch X.com homepage: {e} — "
            f"check your network connection and proxy settings"
        ) from e

    if response.status_code != 200:
        raise RuntimeError(
            f"X.com returned HTTP {response.status_code} — "
            f"the site may be down, or the request was blocked (IP ban, captcha)"
        )

    html = response.text

    # Step 2: Extract bundle URLs
    bundle_urls = extract_bundle_urls(html)
    if not bundle_urls:
        raise RuntimeError(
            "No JS bundle URLs found in X.com HTML — "
            "X.com may have changed their page structure, "
            "or the response was a login/captcha wall"
        )

    # Step 3: Download bundles and extract operations + per-op features
    all_ops: dict[str, str] = {}
    all_op_features: dict[str, list[str]] = {}
    for url in bundle_urls:
        try:
            js_response = session.get(url, headers=headers, timeout=15)
        except Exception as e:
            logger.warning("Failed to download bundle %s: %s — skipping", url, e)
            continue

        if js_response.status_code != 200:
            logger.warning(
                "Bundle %s returned HTTP %d — skipping",
                url,
                js_response.status_code,
            )
            continue

        ops, op_feats = extract_operations_from_js(js_response.text)
        all_ops.update(ops)
        all_op_features.update(op_feats)

    if not all_ops:
        raise RuntimeError(
            f"Downloaded {len(bundle_urls)} JS bundles but extracted 0 operations — "
            f"the regex pattern may need updating (X.com changed bundle format)"
        )

    logger.info(
        "Extracted %d GraphQL operations from %d bundles",
        len(all_ops),
        len(bundle_urls),
    )

    # Step 4: Extract feature values from homepage HTML
    features = extract_features_from_html(html)
    if not features:
        logger.warning(
            "No feature flags extracted — requests may fail if X.com requires specific flags"
        )

    session.close()
    return all_ops, features, all_op_features


def _ensure_cache() -> dict[str, Any]:
    """Load cache from memory, disk, or fresh fetch. Returns cache dict."""
    global _memory_cache

    # Try in-memory cache first
    if _memory_cache:
        age = time.time() - _memory_cache.get("timestamp", 0)
        if age <= CACHE_TTL_SECONDS:
            return _memory_cache

    # Try disk cache
    cache_path = _get_cache_path()
    cached = _read_cache(cache_path)
    if cached and cached.get("endpoints"):
        _memory_cache = cached
        return cached

    # Fetch fresh
    ops, features, op_features = _fetch_and_extract()
    cache_data: dict[str, Any] = {
        "endpoints": ops,
        "features": features,
        "op_features": op_features,
        "timestamp": time.time(),
    }
    _write_cache(cache_data, cache_path)
    _memory_cache = cache_data
    return cache_data


def get_graphql_endpoints() -> dict[str, str]:
    """Get current GraphQL endpoints — from cache or by fetching X.com.

    Returns dict mapping operation name to 'queryId/operationName'.
    Raises RuntimeError if endpoints cannot be resolved.
    """
    return _ensure_cache()["endpoints"]


def get_features() -> dict[str, bool]:
    """Get all feature flag values — from cache or by fetching X.com.

    Returns the full dict of feature flags from __INITIAL_STATE__.
    Raises RuntimeError if resolution fails.
    """
    return _ensure_cache().get("features", {})


def get_op_features(operation: str) -> dict[str, bool]:
    """Get feature flags for a specific GraphQL operation.

    Returns only the features that the operation requires (per its
    featureSwitches metadata in the JS bundle), with values from
    __INITIAL_STATE__. Falls back to empty dict if operation has
    no known feature requirements.
    """
    cache = _ensure_cache()
    all_values = cache.get("features", {})
    op_keys = cache.get("op_features", {}).get(operation, [])

    if not op_keys:
        return {}

    return {key: all_values.get(key, False) for key in op_keys}


def invalidate_cache() -> None:
    """Force re-fetch on next call. Call this on HTTP 404 from a GraphQL endpoint."""
    global _memory_cache
    _memory_cache = None
    cache_path = _get_cache_path()
    try:
        cache_path.unlink()
        logger.info("Cache invalidated — will re-fetch from X.com on next API call")
    except FileNotFoundError:
        pass
