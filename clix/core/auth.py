"""Cookie-based authentication for Twitter/X."""

from __future__ import annotations

import glob as globmod
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from clix.core.constants import AUTH_FILE_NAME, CONFIG_DIR_NAME


class AuthCredentials(BaseModel):
    """Stored authentication credentials."""

    auth_token: str
    ct0: str
    cookies: dict[str, str] = {}
    account_name: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if credentials look valid (non-empty)."""
        return bool(self.auth_token and self.ct0)


class AuthError(Exception):
    """Raised when authentication fails."""


def get_auth_file() -> Path:
    """Get path to auth credentials file."""
    return Path.home() / ".config" / CONFIG_DIR_NAME / AUTH_FILE_NAME


def load_stored_auth(account: str | None = None) -> AuthCredentials | None:
    """Load credentials from stored auth file."""
    auth_file = get_auth_file()
    if not auth_file.exists():
        return None

    try:
        data = json.loads(auth_file.read_text())
        if account:
            account_data = data.get("accounts", {}).get(account)
            if account_data:
                return AuthCredentials.model_validate(account_data)
            return None

        # Use default account
        default = data.get("default")
        if default and "accounts" in data:
            account_data = data["accounts"].get(default)
            if account_data:
                return AuthCredentials.model_validate(account_data)

        # Try legacy single-account format
        if "auth_token" in data:
            return AuthCredentials.model_validate(data)

        return None
    except (json.JSONDecodeError, Exception):
        return None


def save_auth(creds: AuthCredentials, account: str | None = None) -> None:
    """Save credentials to auth file."""
    auth_file = get_auth_file()
    auth_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing data
    data: dict[str, Any] = {}
    if auth_file.exists():
        try:
            data = json.loads(auth_file.read_text())
        except json.JSONDecodeError:
            pass

    account_name = account or creds.account_name or "default"

    if "accounts" not in data:
        data["accounts"] = {}

    creds_dict = creds.model_dump()
    creds_dict["account_name"] = account_name
    data["accounts"][account_name] = creds_dict

    if "default" not in data:
        data["default"] = account_name

    auth_file.write_text(json.dumps(data, indent=2))
    # Set restrictive permissions
    auth_file.chmod(0o600)


def import_cookies_from_file(file_path: str) -> AuthCredentials | None:
    """Import cookies from a Cookie Editor JSON export file.

    Supports Cookie Editor format: list of {name, value, domain, ...}
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text())

        # Cookie Editor exports a list of cookie objects
        if isinstance(raw, list):
            cookies = {}
            for cookie in raw:
                name = cookie.get("name", "")
                value = cookie.get("value", "")
                domain = cookie.get("domain", "")
                # Only keep twitter/x cookies
                if (
                    ".x.com" in domain
                    or ".twitter.com" in domain
                    or domain
                    in (
                        "x.com",
                        "twitter.com",
                    )
                ):
                    cookies[name] = value

            auth_token = cookies.get("auth_token", "")
            ct0 = cookies.get("ct0", "")

            if auth_token and ct0:
                return AuthCredentials(
                    auth_token=auth_token,
                    ct0=ct0,
                    cookies=cookies,
                )
        return None
    except (json.JSONDecodeError, Exception):
        return None


def list_accounts() -> list[str]:
    """List all stored account names."""
    auth_file = get_auth_file()
    if not auth_file.exists():
        return []

    try:
        data = json.loads(auth_file.read_text())
        return list(data.get("accounts", {}).keys())
    except (json.JSONDecodeError, Exception):
        return []


def set_default_account(account: str) -> bool:
    """Set the default account."""
    auth_file = get_auth_file()
    if not auth_file.exists():
        return False

    try:
        data = json.loads(auth_file.read_text())
        if account in data.get("accounts", {}):
            data["default"] = account
            auth_file.write_text(json.dumps(data, indent=2))
            return True
    except (json.JSONDecodeError, Exception):
        pass
    return False


def get_auth_from_env() -> AuthCredentials | None:
    """Get credentials from environment variables."""
    auth_token = os.environ.get("X_AUTH_TOKEN") or os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("X_CT0") or os.environ.get("TWITTER_CT0")

    if auth_token and ct0:
        return AuthCredentials(auth_token=auth_token, ct0=ct0)
    return None


class ChromeProfile(BaseModel):
    """A discovered Chrome/Chromium browser profile."""

    browser: str
    profile: str
    path: str


def _get_chrome_base_dirs() -> list[tuple[str, Path]]:
    """Return (browser_name, base_dir) tuples for Chrome-family browsers.

    Platform-aware: Linux, macOS, Windows.
    """
    system = platform.system()
    results: list[tuple[str, Path]] = []

    if system == "Linux":
        config = Path.home() / ".config"
        candidates = [
            ("chrome", config / "google-chrome"),
            ("chromium", config / "chromium"),
            ("edge", config / "microsoft-edge"),
            ("brave", config / "BraveSoftware" / "Brave-Browser"),
        ]
    elif system == "Darwin":
        support = Path.home() / "Library" / "Application Support"
        candidates = [
            ("chrome", support / "Google" / "Chrome"),
            ("edge", support / "Microsoft Edge"),
            ("brave", support / "BraveSoftware" / "Brave-Browser"),
        ]
    elif system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            ("chrome", local / "Google" / "Chrome" / "User Data"),
            ("edge", local / "Microsoft" / "Edge" / "User Data"),
            ("brave", local / "BraveSoftware" / "Brave-Browser" / "User Data"),
        ]
    else:
        candidates = []

    for name, base in candidates:
        if base.exists():
            results.append((name, base))

    return results


def _get_cookie_db_name() -> str:
    """Return the cookie database filename for the current platform."""
    system = platform.system()
    if system == "Windows":
        return "Cookies"
    # Linux and macOS both use "Cookies"
    return "Cookies"


def discover_chrome_profiles() -> list[ChromeProfile]:
    """Find all Chrome/Chromium profiles with cookie databases.

    Scans Default and Profile N directories in all Chrome-family browsers.
    """
    profiles: list[ChromeProfile] = []
    cookie_db = _get_cookie_db_name()

    for browser_name, base_dir in _get_chrome_base_dirs():
        # Check Default profile
        default_cookies = base_dir / "Default" / cookie_db
        if default_cookies.exists():
            profiles.append(
                ChromeProfile(
                    browser=browser_name,
                    profile="Default",
                    path=str(default_cookies),
                )
            )

        # Scan Profile N directories
        pattern = str(base_dir / "Profile *" / cookie_db)
        for cookie_path in sorted(globmod.glob(pattern)):
            profile_dir = Path(cookie_path).parent
            profiles.append(
                ChromeProfile(
                    browser=browser_name,
                    profile=profile_dir.name,
                    path=cookie_path,
                )
            )

    return profiles


def _browser_cookie3_fn_for(browser_name: str) -> Any | None:
    """Return the browser_cookie3 function for a browser name."""
    try:
        import browser_cookie3
    except ImportError:
        return None

    mapping = {
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chrome,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
    }
    return mapping.get(browser_name)


def _extract_from_cookie_file(fn: Any, cookie_file: str) -> AuthCredentials | None:
    """Extract Twitter/X credentials from a specific cookie file using browser_cookie3."""
    try:
        cookie_jar = fn(cookie_file=cookie_file, domain_name=".x.com")
        cookies = {c.name: c.value for c in cookie_jar}

        # Also try twitter.com domain
        try:
            cookie_jar_tw = fn(cookie_file=cookie_file, domain_name=".twitter.com")
            for c in cookie_jar_tw:
                if c.name not in cookies:
                    cookies[c.name] = c.value
        except Exception:
            pass

        auth_token = cookies.get("auth_token", "")
        ct0 = cookies.get("ct0", "")

        if auth_token and ct0:
            return AuthCredentials(
                auth_token=auth_token,
                ct0=ct0,
                cookies=cookies,
                account_name=None,
            )
    except Exception:
        pass
    return None


def extract_cookies_from_browser(
    browser: str | None = None,
    profile: str | None = None,
) -> AuthCredentials | None:
    """Extract Twitter cookies from browser.

    Supports multi-profile discovery for Chrome-family browsers.
    Falls back to default browser_cookie3 behavior for Firefox/Opera.

    Args:
        browser: Force a specific browser (chrome, firefox, edge, brave).
        profile: Force a specific Chrome profile name (e.g. "Profile 3").
                 Can also be set via CLIX_CHROME_PROFILE env var.
    """
    try:
        import browser_cookie3
    except ImportError:
        return None

    # Resolve profile from env var if not explicitly provided
    profile = profile or os.environ.get("CLIX_CHROME_PROFILE")

    # Try multi-profile extraction for Chrome-family browsers
    chrome_family = {"chrome", "chromium", "edge", "brave"}
    target_browsers = {browser.lower()} if browser else chrome_family

    # If a specific profile is requested, or auto-discover profiles
    discovered = discover_chrome_profiles()
    if discovered:
        # Filter by browser if specified
        candidates = [p for p in discovered if p.browser in target_browsers]

        if profile:
            # User requested a specific profile
            candidates = [p for p in candidates if p.profile == profile]

        for prof in candidates:
            fn = _browser_cookie3_fn_for(prof.browser)
            if not fn:
                continue
            creds = _extract_from_cookie_file(fn, prof.path)
            if creds:
                return creds

    # Fall back to default browser_cookie3 behavior (handles Firefox, Opera,
    # and cases where profile discovery found nothing)
    browsers_to_try: list[str] = []
    if browser:
        browsers_to_try = [browser.lower()]
    else:
        browsers_to_try = _get_available_browsers()

    cookie_fns = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
        "opera": browser_cookie3.opera,
    }

    for browser_name in browsers_to_try:
        # Skip Chrome-family browsers we already tried via profile discovery
        if discovered and browser_name in chrome_family:
            continue

        fn = cookie_fns.get(browser_name)
        if not fn:
            continue

        try:
            cookie_jar = fn(domain_name=".x.com")
            cookies = {c.name: c.value for c in cookie_jar}

            # Also try twitter.com domain
            try:
                cookie_jar_tw = fn(domain_name=".twitter.com")
                for c in cookie_jar_tw:
                    if c.name not in cookies:
                        cookies[c.name] = c.value
            except Exception:
                pass

            auth_token = cookies.get("auth_token", "")
            ct0 = cookies.get("ct0", "")

            if auth_token and ct0:
                return AuthCredentials(
                    auth_token=auth_token,
                    ct0=ct0,
                    cookies=cookies,
                    account_name=None,
                )
        except Exception:
            continue

    return None


def _get_available_browsers() -> list[str]:
    """Detect available browsers on the system."""
    system = platform.system()
    browsers = []

    if system == "Darwin":
        browser_paths = {
            "chrome": "/Applications/Google Chrome.app",
            "brave": "/Applications/Brave Browser.app",
            "firefox": "/Applications/Firefox.app",
            "edge": "/Applications/Microsoft Edge.app",
        }
        for name, path in browser_paths.items():
            if Path(path).exists():
                browsers.append(name)
    elif system == "Linux":
        for name in ["chrome", "firefox", "brave", "edge"]:
            cmd = ["which", f"google-{name}" if name == "chrome" else name]
            try:
                if subprocess.run(cmd, capture_output=True).returncode == 0:
                    browsers.append(name)
            except Exception:
                pass
    elif system == "Windows":
        browsers = ["chrome", "edge", "firefox", "brave"]

    return browsers or ["chrome", "firefox"]


def get_credentials(account: str | None = None) -> AuthCredentials:
    """Get credentials using priority: env vars > stored > browser extraction.

    Raises AuthError if no credentials found.
    """
    # 1. Environment variables
    creds = get_auth_from_env()
    if creds and creds.is_valid:
        return creds

    # 2. Stored credentials
    creds = load_stored_auth(account)
    if creds and creds.is_valid:
        return creds

    # 3. Browser extraction
    creds = extract_cookies_from_browser()
    if creds and creds.is_valid:
        # Auto-save extracted cookies
        save_auth(creds, account or "default")
        return creds

    raise AuthError(
        "No Twitter/X credentials found. Options:\n"
        "  1. Set X_AUTH_TOKEN and X_CT0 environment variables\n"
        "  2. Run 'clix auth login' to extract from browser\n"
        "  3. Run 'clix auth set' to manually enter credentials"
    )
