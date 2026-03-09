"""Tests for authentication."""

import os
from unittest.mock import patch

import pytest

from clix.core.auth import (
    AuthCredentials,
    AuthError,
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
