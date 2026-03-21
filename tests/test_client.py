"""Tests for XClient credential refresh logic."""

from unittest.mock import MagicMock, PropertyMock, patch

from clix.core.auth import AuthCredentials
from clix.core.client import XClient


def _make_creds(token: str = "tok", ct0: str = "csrf") -> AuthCredentials:
    return AuthCredentials(auth_token=token, ct0=ct0)


class TestTryRefreshCredentials:
    def test_refresh_succeeds_on_valid_browser_cookies(self):
        """Refresh replaces credentials when browser extraction succeeds."""
        old_creds = _make_creds("old_tok", "old_ct0")
        new_creds = _make_creds("new_tok", "new_ct0")

        client = XClient(credentials=old_creds)
        client._session = MagicMock()

        with (
            patch(
                "clix.core.client.extract_cookies_from_browser",
                return_value=new_creds,
            ),
            patch("clix.core.client.save_auth") as mock_save,
        ):
            result = client._try_refresh_credentials()

        assert result is True
        assert client._credentials.auth_token == "new_tok"
        assert client._session is None  # session reset
        mock_save.assert_called_once_with(new_creds, "default")

    def test_refresh_fails_when_browser_returns_nothing(self):
        """Refresh returns False when browser extraction finds no cookies."""
        client = XClient(credentials=_make_creds())

        with patch(
            "clix.core.client.extract_cookies_from_browser",
            return_value=None,
        ):
            result = client._try_refresh_credentials()

        assert result is False

    def test_refresh_only_attempted_once(self):
        """Refresh should not be retried after the first attempt."""
        client = XClient(credentials=_make_creds())

        with patch(
            "clix.core.client.extract_cookies_from_browser",
            return_value=None,
        ) as mock_extract:
            client._try_refresh_credentials()
            result = client._try_refresh_credentials()

        assert result is False
        assert mock_extract.call_count == 1

    def test_refresh_handles_extraction_exception(self):
        """Refresh returns False when browser extraction throws."""
        client = XClient(credentials=_make_creds())

        with patch(
            "clix.core.client.extract_cookies_from_browser",
            side_effect=RuntimeError("keyring locked"),
        ):
            result = client._try_refresh_credentials()

        assert result is False

    def test_refresh_uses_account_name(self):
        """Refresh saves with the correct account name."""
        new_creds = _make_creds("new_tok", "new_ct0")
        client = XClient(credentials=_make_creds(), account="work")
        client._session = MagicMock()

        with (
            patch(
                "clix.core.client.extract_cookies_from_browser",
                return_value=new_creds,
            ),
            patch("clix.core.client.save_auth") as mock_save,
        ):
            client._try_refresh_credentials()

        mock_save.assert_called_once_with(new_creds, "work")


class TestRequestAuthRefresh:
    def _make_client_with_mock_session(self, creds, responses):
        """Create a client where session property always returns the same mock."""
        client = XClient(credentials=creds)
        client._transaction_init_attempted = True

        mock_session = MagicMock()
        mock_session.request.side_effect = responses

        # Patch session property so it survives session reset
        patcher = patch.object(
            type(client), "session", new_callable=PropertyMock, return_value=mock_session
        )
        patcher.start()
        return client, mock_session, patcher

    def test_401_triggers_refresh_and_retries(self):
        """A 401 response should trigger cookie refresh and retry the request."""
        new_creds = _make_creds("new", "new")

        mock_401 = MagicMock(status_code=401)
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = {"data": "ok"}

        client, mock_session, patcher = self._make_client_with_mock_session(
            _make_creds("old", "old"), [mock_401, mock_200]
        )

        try:
            with (
                patch("clix.core.client.extract_cookies_from_browser", return_value=new_creds),
                patch("clix.core.client.save_auth"),
            ):
                result = client._request("GET", "https://api.x.com/test")

            assert result == {"data": "ok"}
            assert mock_session.request.call_count == 2
        finally:
            patcher.stop()

    def test_401_without_refresh_raises_auth_error(self):
        """A 401 with no browser cookies available should raise AuthError."""
        mock_401 = MagicMock(status_code=401)

        client, _, patcher = self._make_client_with_mock_session(_make_creds(), [mock_401])

        try:
            with patch("clix.core.client.extract_cookies_from_browser", return_value=None):
                try:
                    client._request("GET", "https://api.x.com/test")
                    assert False, "Should have raised AuthError"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        finally:
            patcher.stop()

    def test_403_triggers_refresh_and_retries(self):
        """A 403 response should also trigger cookie refresh (expired ct0 returns 403)."""
        new_creds = _make_creds("new", "new")

        mock_403 = MagicMock(status_code=403)
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = {"data": "ok"}

        client, mock_session, patcher = self._make_client_with_mock_session(
            _make_creds("old", "old"), [mock_403, mock_200]
        )

        try:
            with (
                patch("clix.core.client.extract_cookies_from_browser", return_value=new_creds),
                patch("clix.core.client.save_auth"),
            ):
                result = client._request("GET", "https://api.x.com/test")

            assert result == {"data": "ok"}
            assert mock_session.request.call_count == 2
        finally:
            patcher.stop()

    def test_403_without_refresh_raises_api_error(self):
        """A 403 with no browser cookies should raise APIError."""
        mock_403 = MagicMock(status_code=403)

        client, _, patcher = self._make_client_with_mock_session(_make_creds(), [mock_403])

        try:
            with patch("clix.core.client.extract_cookies_from_browser", return_value=None):
                try:
                    client._request("GET", "https://api.x.com/test")
                    assert False, "Should have raised APIError"
                except Exception as e:
                    assert "Forbidden" in str(e)
        finally:
            patcher.stop()


class TestApplicationLevelErrors:
    """HTTP 200 responses with errors in body must raise APIError."""

    def _make_client_with_mock_session(self, responses):
        """Create a client with a mocked session returning given responses."""
        creds = _make_creds()
        client = XClient(credentials=creds)
        client._transaction_init_attempted = True

        mock_session = MagicMock()
        mock_session.request.side_effect = responses

        patcher = patch.object(
            type(client), "session", new_callable=PropertyMock, return_value=mock_session
        )
        patcher.start()
        return client, mock_session, patcher

    def test_200_with_errors_and_no_data_raises_api_error(self):
        """X returns HTTP 200 with {"errors": [...]} and no data — must raise."""
        import pytest

        from clix.core.client import APIError

        error_body = {
            "errors": [{"code": 104, "message": "You aren't allowed to add members to this list"}]
        }
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = error_body

        client, _, patcher = self._make_client_with_mock_session([mock_200])
        try:
            with pytest.raises(APIError, match="code 104"):
                client._request("POST", "https://api.x.com/graphql/test")
        finally:
            patcher.stop()

    def test_200_with_errors_and_data_returns_normally(self):
        """Some X responses include both errors (warnings) and data — don't raise."""
        response_body = {
            "data": {"create_tweet": {"tweet_results": {"result": {"id": "123"}}}},
            "errors": [{"message": "Some non-fatal warning"}],
        }
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = response_body

        client, _, patcher = self._make_client_with_mock_session([mock_200])
        try:
            result = client._request("POST", "https://api.x.com/graphql/test")
            assert result == response_body
        finally:
            patcher.stop()

    def test_200_without_errors_returns_normally(self):
        """Normal successful response — no errors key."""
        response_body = {"data": {"user": {"id": "123"}}}
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = response_body

        client, _, patcher = self._make_client_with_mock_session([mock_200])
        try:
            result = client._request("POST", "https://api.x.com/graphql/test")
            assert result == response_body
        finally:
            patcher.stop()
