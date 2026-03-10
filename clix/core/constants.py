"""Twitter/X API constants: endpoints, headers, and defaults."""

from __future__ import annotations

import os
import re
import sys

# Base URLs
BASE_URL = "https://x.com"
API_BASE = "https://x.com/i/api"
GRAPHQL_BASE = f"{API_BASE}/graphql"

# Bearer token (public, embedded in Twitter web app)
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Default field toggles
DEFAULT_FIELD_TOGGLES = {
    "withArticlePlainText": False,
}

# Request defaults
DEFAULT_COUNT = 20
MAX_COUNT = 100
DEFAULT_DELAY_SECONDS = 1.5
WRITE_DELAY_RANGE = (1.5, 4.0)

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_AUTH_ERROR = 2
EXIT_RATE_LIMIT = 3

# Config
CONFIG_DIR_NAME = "clix"
CONFIG_FILE_NAME = "config.toml"
AUTH_FILE_NAME = "auth.json"


# --- Chrome impersonation & browser-like headers ---

# Mutable — set by sync_chrome_version() when session is created
_chrome_version = "133"


def best_chrome_target() -> str:
    """Detect the best available Chrome impersonation target at runtime.

    Queries curl_cffi's BrowserType enum for supported targets.
    """
    try:
        from curl_cffi.requests import BrowserType

        available = {e.value for e in BrowserType}
    except Exception:
        available = set()

    for target in ("chrome133", "chrome133a", "chrome136", "chrome131", "chrome130"):
        if target in available:
            return target

    chrome_targets = sorted(
        [v for v in available if v.startswith("chrome") and v.replace("chrome", "").isdigit()],
        key=lambda x: int(x.replace("chrome", "")),
        reverse=True,
    )
    return chrome_targets[0] if chrome_targets else "chrome131"


def sync_chrome_version(impersonate_target: str) -> None:
    """Sync User-Agent / sec-ch-ua headers with the actual impersonate target."""
    global _chrome_version
    match = re.search(r"(\d+)", impersonate_target)
    if match:
        _chrome_version = match.group(1)


def get_user_agent() -> str:
    """Build a User-Agent string matching the impersonated Chrome version."""
    if sys.platform == "darwin":
        platform = "Macintosh; Intel Mac OS X 10_15_7"
    elif sys.platform.startswith("win"):
        platform = "Windows NT 10.0; Win64; x64"
    else:
        platform = "X11; Linux x86_64"
    return (
        f"Mozilla/5.0 ({platform}) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{_chrome_version}.0.0.0 Safari/537.36"
    )


def get_sec_ch_ua() -> str:
    """Build sec-ch-ua header matching the impersonated Chrome version."""
    v = _chrome_version
    return f'"Chromium";v="{v}", "Not(A:Brand";v="99", "Google Chrome";v="{v}"'


def get_sec_ch_ua_full_version_list() -> str:
    """Build sec-ch-ua-full-version-list header."""
    v = _chrome_version
    return f'"Google Chrome";v="{v}.0.0.0", "Chromium";v="{v}.0.0.0", "Not.A/Brand";v="99.0.0.0"'


def get_sec_ch_ua_platform() -> str:
    """Build sec-ch-ua-platform header."""
    if sys.platform == "darwin":
        return '"macOS"'
    if sys.platform.startswith("win"):
        return '"Windows"'
    return '"Linux"'


def get_accept_language() -> str:
    """Build Accept-Language header from system locale."""
    raw = (
        os.environ.get("LC_ALL")
        or os.environ.get("LC_MESSAGES")
        or os.environ.get("LANG")
        or "en_US.UTF-8"
    )
    tag = raw.split(".", 1)[0].replace("_", "-") or "en-US"
    language = tag.split("-", 1)[0] or "en"
    return f"{tag},{language};q=0.9,en;q=0.8"


# Static Client Hints
SEC_CH_UA_MOBILE = "?0"
SEC_CH_UA_ARCH = '"arm"' if sys.platform == "darwin" else '"x86"'
SEC_CH_UA_BITNESS = '"64"'
SEC_CH_UA_MODEL = '""'
SEC_CH_UA_PLATFORM_VERSION = '"15.0.0"' if sys.platform == "darwin" else '"10.0.0"'
