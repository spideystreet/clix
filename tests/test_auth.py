"""Tests for authentication."""

import os
from unittest.mock import patch

import pytest

from clix.core.auth import (
    AuthCredentials,
    AuthError,
    ChromeProfile,
    discover_chrome_profiles,
    extract_cookies_from_browser,
    get_auth_from_env,
    get_credentials,
    load_stored_auth,
    save_auth,
)


class TestAuthCredentials:
    def test_valid_credentials(self):
        creds = AuthCredentials(auth_token="abc123", ct0="xyz789")
        assert creds.is_valid is True

    def test_invalid_credentials(self):
        creds = AuthCredentials(auth_token="", ct0="")
        assert creds.is_valid is False

    def test_partial_credentials(self):
        creds = AuthCredentials(auth_token="abc", ct0="")
        assert creds.is_valid is False


class TestEnvAuth:
    def test_x_env_vars(self):
        with patch.dict(os.environ, {"X_AUTH_TOKEN": "token1", "X_CT0": "csrf1"}):
            creds = get_auth_from_env()
            assert creds is not None
            assert creds.auth_token == "token1"
            assert creds.ct0 == "csrf1"

    def test_twitter_env_vars(self):
        with patch.dict(os.environ, {"TWITTER_AUTH_TOKEN": "t2", "TWITTER_CT0": "c2"}, clear=False):
            # Remove X_ vars if present
            env = dict(os.environ)
            env.pop("X_AUTH_TOKEN", None)
            env.pop("X_CT0", None)
            with patch.dict(os.environ, env, clear=True):
                with patch.dict(os.environ, {"TWITTER_AUTH_TOKEN": "t2", "TWITTER_CT0": "c2"}):
                    creds = get_auth_from_env()
                    assert creds is not None

    def test_no_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            creds = get_auth_from_env()
            assert creds is None


class TestStoredAuth:
    def test_save_and_load(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        with patch("clix.core.auth.get_auth_file", return_value=auth_file):
            creds = AuthCredentials(auth_token="saved_token", ct0="saved_ct0")
            save_auth(creds, "test_account")

            loaded = load_stored_auth("test_account")
            assert loaded is not None
            assert loaded.auth_token == "saved_token"

    def test_load_nonexistent(self, tmp_path):
        auth_file = tmp_path / "nonexistent.json"
        with patch("clix.core.auth.get_auth_file", return_value=auth_file):
            assert load_stored_auth() is None

    def test_multi_account(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        with patch("clix.core.auth.get_auth_file", return_value=auth_file):
            creds1 = AuthCredentials(auth_token="t1", ct0="c1")
            creds2 = AuthCredentials(auth_token="t2", ct0="c2")
            save_auth(creds1, "account1")
            save_auth(creds2, "account2")

            loaded1 = load_stored_auth("account1")
            loaded2 = load_stored_auth("account2")
            assert loaded1 is not None
            assert loaded2 is not None
            assert loaded1.auth_token == "t1"
            assert loaded2.auth_token == "t2"


class TestDiscoverChromeProfiles:
    def test_discovers_default_profile(self, tmp_path):
        """Default profile is found when its Cookies file exists."""
        chrome_dir = tmp_path / "google-chrome" / "Default"
        chrome_dir.mkdir(parents=True)
        (chrome_dir / "Cookies").touch()

        with patch(
            "clix.core.auth._get_chrome_base_dirs",
            return_value=[("chrome", tmp_path / "google-chrome")],
        ):
            profiles = discover_chrome_profiles()
            assert len(profiles) == 1
            assert profiles[0].browser == "chrome"
            assert profiles[0].profile == "Default"
            assert profiles[0].path == str(chrome_dir / "Cookies")

    def test_discovers_multiple_profiles(self, tmp_path):
        """Multiple Profile N directories are discovered and sorted."""
        chrome_dir = tmp_path / "google-chrome"
        for name in ["Default", "Profile 1", "Profile 2"]:
            p = chrome_dir / name
            p.mkdir(parents=True)
            (p / "Cookies").touch()

        with patch(
            "clix.core.auth._get_chrome_base_dirs",
            return_value=[("chrome", chrome_dir)],
        ):
            profiles = discover_chrome_profiles()
            assert len(profiles) == 3
            names = [p.profile for p in profiles]
            assert names == ["Default", "Profile 1", "Profile 2"]

    def test_discovers_multiple_browsers(self, tmp_path):
        """Profiles from different browsers are all discovered."""
        chrome = tmp_path / "google-chrome" / "Default"
        chrome.mkdir(parents=True)
        (chrome / "Cookies").touch()

        edge = tmp_path / "microsoft-edge" / "Default"
        edge.mkdir(parents=True)
        (edge / "Cookies").touch()

        with patch(
            "clix.core.auth._get_chrome_base_dirs",
            return_value=[
                ("chrome", tmp_path / "google-chrome"),
                ("edge", tmp_path / "microsoft-edge"),
            ],
        ):
            profiles = discover_chrome_profiles()
            assert len(profiles) == 2
            browsers = {p.browser for p in profiles}
            assert browsers == {"chrome", "edge"}

    def test_empty_when_no_profiles(self, tmp_path):
        """Returns empty list when no cookie databases exist."""
        chrome_dir = tmp_path / "google-chrome"
        chrome_dir.mkdir(parents=True)

        with patch(
            "clix.core.auth._get_chrome_base_dirs",
            return_value=[("chrome", chrome_dir)],
        ):
            profiles = discover_chrome_profiles()
            assert profiles == []

    def test_skips_profiles_without_cookies(self, tmp_path):
        """Profile dirs without a Cookies file are ignored."""
        chrome_dir = tmp_path / "google-chrome"
        (chrome_dir / "Default").mkdir(parents=True)
        # No Cookies file in Default
        p1 = chrome_dir / "Profile 1"
        p1.mkdir(parents=True)
        (p1 / "Cookies").touch()

        with patch(
            "clix.core.auth._get_chrome_base_dirs",
            return_value=[("chrome", chrome_dir)],
        ):
            profiles = discover_chrome_profiles()
            assert len(profiles) == 1
            assert profiles[0].profile == "Profile 1"


class TestExtractCookiesMultiProfile:
    def test_profile_env_var_is_used(self, tmp_path):
        """CLIX_CHROME_PROFILE env var filters to the requested profile."""
        chrome_dir = tmp_path / "google-chrome"
        for name in ["Default", "Profile 1"]:
            p = chrome_dir / name
            p.mkdir(parents=True)
            (p / "Cookies").touch()

        expected_creds = AuthCredentials(auth_token="tok", ct0="csrf")

        with (
            patch(
                "clix.core.auth._get_chrome_base_dirs",
                return_value=[("chrome", chrome_dir)],
            ),
            patch(
                "clix.core.auth._extract_from_cookie_file",
                return_value=expected_creds,
            ) as mock_extract,
            patch.dict(os.environ, {"CLIX_CHROME_PROFILE": "Profile 1"}),
        ):
            creds = extract_cookies_from_browser()
            assert creds is not None
            assert creds.auth_token == "tok"
            # Should only have been called with Profile 1's cookie path
            # _extract_from_cookie_file(fn, cookie_file) — positional args
            cookie_file_arg = mock_extract.call_args[0][1]
            assert "Profile 1" in cookie_file_arg

    def test_explicit_profile_param_overrides_env(self, tmp_path):
        """Explicit profile parameter takes precedence over env var."""
        chrome_dir = tmp_path / "google-chrome"
        for name in ["Default", "Profile 1", "Profile 2"]:
            p = chrome_dir / name
            p.mkdir(parents=True)
            (p / "Cookies").touch()

        expected_creds = AuthCredentials(auth_token="tok", ct0="csrf")

        with (
            patch(
                "clix.core.auth._get_chrome_base_dirs",
                return_value=[("chrome", chrome_dir)],
            ),
            patch(
                "clix.core.auth._extract_from_cookie_file",
                return_value=expected_creds,
            ) as mock_extract,
            patch.dict(os.environ, {"CLIX_CHROME_PROFILE": "Profile 1"}),
        ):
            creds = extract_cookies_from_browser(profile="Profile 2")
            assert creds is not None
            cookie_file_arg = mock_extract.call_args[0][1]
            assert "Profile 2" in cookie_file_arg

    def test_first_valid_profile_wins(self, tmp_path):
        """When no profile specified, first profile with valid creds is used."""
        chrome_dir = tmp_path / "google-chrome"
        for name in ["Default", "Profile 1"]:
            p = chrome_dir / name
            p.mkdir(parents=True)
            (p / "Cookies").touch()

        valid_creds = AuthCredentials(auth_token="tok", ct0="csrf")

        def mock_extract(fn: object, cookie_file: str) -> AuthCredentials | None:
            if "Profile 1" in cookie_file:
                return valid_creds
            return None

        with (
            patch(
                "clix.core.auth._get_chrome_base_dirs",
                return_value=[("chrome", chrome_dir)],
            ),
            patch(
                "clix.core.auth._extract_from_cookie_file",
                side_effect=mock_extract,
            ),
            patch.dict(os.environ, {}, clear=True),
        ):
            creds = extract_cookies_from_browser()
            assert creds is not None
            assert creds.auth_token == "tok"


class TestChromeProfileModel:
    def test_serialization(self):
        """ChromeProfile model serializes correctly."""
        profile = ChromeProfile(browser="chrome", profile="Default", path="/path/to/Cookies")
        data = profile.model_dump()
        assert data == {
            "browser": "chrome",
            "profile": "Default",
            "path": "/path/to/Cookies",
        }


class TestGetCredentials:
    def test_raises_when_no_auth(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("clix.core.auth.get_auth_file", return_value=auth_file),
            patch("clix.core.auth.extract_cookies_from_browser", return_value=None),
        ):
            with pytest.raises(AuthError):
                get_credentials()
