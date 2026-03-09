"""Cookie-based authentication for Twitter/X."""

from __future__ import annotations

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


def extract_cookies_from_browser(browser: str | None = None) -> AuthCredentials | None:
    """Extract Twitter cookies from browser.

    Tries browsers in order: Chrome, Firefox, Edge, Brave.
    """
    try:
        import browser_cookie3
    except ImportError:
        return None

    browsers = []
    if browser:
        browsers = [browser.lower()]
    else:
        browsers = _get_available_browsers()

    cookie_fns = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "brave": browser_cookie3.brave,
        "opera": browser_cookie3.opera,
    }

    for browser_name in browsers:
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
