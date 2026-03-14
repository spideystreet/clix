"""HTTP client for Twitter/X API with TLS fingerprinting."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
from pathlib import Path
from typing import Any

import bs4
from curl_cffi import requests as curl_requests
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, get_ondemand_file_url

from clix.core.auth import AuthCredentials, AuthError, get_credentials
from clix.core.constants import (
    BASE_URL,
    BEARER_TOKEN,
    CONFIG_DIR_NAME,
    DEFAULT_FIELD_TOGGLES,
    GRAPHQL_BASE,
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
from clix.core.endpoints import get_graphql_endpoints, get_op_features, invalidate_cache
from clix.utils.rate_limit import backoff_delay, delay, write_delay

logger = logging.getLogger(__name__)

# Transaction cache settings
_TRANSACTION_CACHE_FILE = "transaction_cache.json"
_TRANSACTION_CACHE_TTL = 3600  # 1 hour


def _transaction_cache_path() -> Path:
    """Return path to the transaction data disk cache."""
    return Path.home() / ".config" / CONFIG_DIR_NAME / _TRANSACTION_CACHE_FILE


def _load_transaction_cache() -> dict[str, Any] | None:
    """Load cached homepage + ondemand JS from disk if still fresh."""
    path = _transaction_cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > _TRANSACTION_CACHE_TTL:
            logger.debug("Transaction cache expired (age=%ds)", time.time() - cached_at)
            return None
        if "home_html" not in data or "ondemand_text" not in data:
            return None
        return data
    except Exception:
        logger.debug("Failed to read transaction cache", exc_info=True)
        return None


def _save_transaction_cache(home_html: str, ondemand_text: str) -> None:
    """Persist homepage + ondemand JS to disk cache."""
    path = _transaction_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "home_html": home_html,
                    "ondemand_text": ondemand_text,
                    "cached_at": time.time(),
                }
            )
        )
    except Exception:
        logger.debug("Failed to write transaction cache", exc_info=True)


class APIError(Exception):
    """Raised when an API call fails."""

    def __init__(self, message: str, status_code: int = 0, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class RateLimitError(APIError):
    """Raised when rate limited."""


class StaleEndpointError(APIError):
    """Raised when a GraphQL endpoint returns 404 (stale operation ID)."""


class XClient:
    """HTTP client for Twitter/X GraphQL API."""

    def __init__(
        self,
        credentials: AuthCredentials | None = None,
        account: str | None = None,
        proxy: str | None = None,
    ):
        self._credentials = credentials
        self._account = account
        self._proxy = (
            proxy
            or os.environ.get("CLIX_PROXY")
            or os.environ.get("X_PROXY")
            or os.environ.get("TWITTER_PROXY")
            or ""
        )
        self._session: curl_requests.Session | None = None
        self._client_transaction: ClientTransaction | None = None
        self._transaction_init_attempted: bool = False

    @property
    def credentials(self) -> AuthCredentials:
        """Lazy-load credentials."""
        if self._credentials is None:
            self._credentials = get_credentials(self._account)
        return self._credentials

    @property
    def session(self) -> curl_requests.Session:
        """Get or create HTTP session with Chrome impersonation."""
        if self._session is None:
            target = best_chrome_target()
            sync_chrome_version(target)
            logger.debug("curl_cffi impersonating %s", target)
            self._session = curl_requests.Session(impersonate=target)

            if self._proxy:
                self._session.proxies = {
                    "http": self._proxy,
                    "https": self._proxy,
                }
        return self._session

    def _init_transaction(self) -> None:
        """Initialize X-Client-Transaction-Id generator (lazy, cached to disk).

        Fetches X.com homepage and ondemand JS to build the transaction signer.
        Results are cached to disk with a 1-hour TTL. On any failure the header
        is silently skipped for this client lifetime.
        """
        if self._transaction_init_attempted:
            return
        self._transaction_init_attempted = True

        try:
            # Try disk cache first
            cached = _load_transaction_cache()
            if cached:
                home_soup = bs4.BeautifulSoup(cached["home_html"], "html.parser")
                self._client_transaction = ClientTransaction(
                    home_page_response=home_soup,
                    ondemand_file_response=cached["ondemand_text"],
                )
                logger.debug("Loaded transaction signer from disk cache")
                return

            # Cache miss — fetch live data
            logger.debug("Transaction cache miss, fetching homepage + ondemand JS")
            headers = generate_headers()
            home_resp = self.session.get(f"{BASE_URL}/", headers=headers, timeout=15)
            home_html = home_resp.text
            home_soup = bs4.BeautifulSoup(home_html, "html.parser")

            ondemand_url = get_ondemand_file_url(home_soup)
            if not ondemand_url:
                logger.warning("Could not extract ondemand JS URL from homepage")
                return

            ondemand_resp = self.session.get(ondemand_url, headers=headers, timeout=15)
            ondemand_text = ondemand_resp.text

            self._client_transaction = ClientTransaction(
                home_page_response=home_soup,
                ondemand_file_response=ondemand_text,
            )

            # Persist to disk cache
            _save_transaction_cache(home_html, ondemand_text)
            logger.debug("Transaction signer initialized and cached")

        except Exception:
            logger.debug(
                "Failed to initialize transaction signer — "
                "X-Client-Transaction-Id header will be skipped",
                exc_info=True,
            )

    def _get_headers(self, method: str = "GET", url: str = "") -> dict[str, str]:
        """Build browser-like request headers for API calls."""
        creds = self.credentials
        headers = {
            "authorization": f"Bearer {BEARER_TOKEN}",
            "x-csrf-token": creds.ct0,
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "content-type": "application/json",
            "referer": f"{BASE_URL}/home",
            "origin": BASE_URL,
            # Browser identity headers
            "user-agent": get_user_agent(),
            "accept": "*/*",
            "accept-language": get_accept_language(),
            # Client Hints — required by Cloudflare to pass bot detection
            "sec-ch-ua": get_sec_ch_ua(),
            "sec-ch-ua-mobile": SEC_CH_UA_MOBILE,
            "sec-ch-ua-platform": get_sec_ch_ua_platform(),
            "sec-ch-ua-arch": SEC_CH_UA_ARCH,
            "sec-ch-ua-bitness": SEC_CH_UA_BITNESS,
            "sec-ch-ua-full-version-list": get_sec_ch_ua_full_version_list(),
            "sec-ch-ua-model": SEC_CH_UA_MODEL,
            "sec-ch-ua-platform-version": SEC_CH_UA_PLATFORM_VERSION,
            # Fetch metadata — browsers always send these on XHR/fetch
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

        # Transaction ID — generated per-request from method + path
        if self._client_transaction and url:
            try:
                path = urllib.parse.urlparse(url).path
                tid = self._client_transaction.generate_transaction_id(method=method, path=path)
                headers["x-client-transaction-id"] = tid
            except Exception:
                logger.debug(
                    "Failed to generate transaction ID for %s %s",
                    method,
                    url,
                    exc_info=True,
                )

        return headers

    def _get_cookies(self) -> dict[str, str]:
        """Build cookie dict."""
        creds = self.credentials
        cookies = dict(creds.cookies) if creds.cookies else {}
        cookies["auth_token"] = creds.auth_token
        cookies["ct0"] = creds.ct0
        return cookies

    def _request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
        data: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make an authenticated request with retry logic."""
        # Lazy-init transaction signer on first API call
        self._init_transaction()

        headers = self._get_headers(method=method, url=url)
        headers = self._get_headers()
        if data is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"
        cookies = self._get_cookies()

        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    params=params,
                    json=json_data,
                    data=data,
                    timeout=30,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise AuthError("Authentication failed. Cookies may be expired.")
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        backoff_delay(attempt)
                        continue
                    raise RateLimitError(
                        "Rate limited by Twitter/X",
                        status_code=429,
                    )
                elif response.status_code == 403:
                    raise APIError(
                        "Forbidden — account may be suspended or action not allowed",
                        status_code=403,
                    )
                elif response.status_code == 404:
                    raise StaleEndpointError(
                        "GraphQL endpoint not found (HTTP 404) — operation IDs may be stale",
                        status_code=404,
                    )
                elif response.status_code == 422:
                    body = response.text[:1000]
                    logger.error(
                        "HTTP 422 from %s — response body: %s",
                        url,
                        body,
                    )
                    raise APIError(
                        f"API error: HTTP 422 (Unprocessable Entity) — "
                        f"required variables may be missing or invalid. "
                        f"Response: {body}",
                        status_code=422,
                        response_data=body,
                    )
                else:
                    raise APIError(
                        f"API error: HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.text[:500],
                    )

            except (AuthError, RateLimitError, StaleEndpointError, APIError):
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    backoff_delay(attempt)
                    continue

        raise APIError(f"Request failed after {max_retries} retries: {last_error}")

    def _graphql_request(
        self,
        method: str,
        operation: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
        field_toggles: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL request with auto-retry on stale endpoint IDs."""
        resolved_features = features if features is not None else get_op_features(operation)
        resolved_toggles = field_toggles if field_toggles is not None else DEFAULT_FIELD_TOGGLES

        for attempt in range(2):
            endpoints = get_graphql_endpoints()
            endpoint = endpoints.get(operation)
            if not endpoint:
                raise APIError(
                    f"Unknown GraphQL operation '{operation}' — "
                    f"not found in {len(endpoints)} extracted operations. "
                    f"Available: {', '.join(sorted(endpoints.keys()))}"
                )
            url = f"{GRAPHQL_BASE}/{endpoint}"

            if method == "GET":
                kwargs: dict[str, Any] = {
                    "params": {
                        "variables": json.dumps(variables),
                        "features": json.dumps(resolved_features),
                        "fieldToggles": json.dumps(resolved_toggles),
                    }
                }
            else:
                kwargs = {
                    "json_data": {
                        "variables": variables,
                        "features": resolved_features,
                        "queryId": endpoint.split("/")[0],
                    }
                }

            try:
                result = self._request(method, url, **kwargs)
                delay() if method == "GET" else write_delay()
                return result
            except StaleEndpointError:
                if attempt == 0:
                    logger.warning(
                        "HTTP 404 for '%s' — operation IDs may be stale, "
                        "invalidating cache and retrying with fresh IDs",
                        operation,
                    )
                    invalidate_cache()
                    if features is None:
                        resolved_features = get_op_features(operation)
                    continue
                raise APIError(
                    f"GraphQL endpoint '{operation}' not found (HTTP 404) "
                    f"even after cache refresh — X.com may have removed this operation",
                    status_code=404,
                )
            except APIError as e:
                if e.status_code == 422 and attempt == 0:
                    logger.warning(
                        "HTTP 422 for '%s' — variables or query ID may be stale, "
                        "invalidating cache and retrying with fresh IDs. "
                        "Response: %s",
                        operation,
                        e.response_data,
                    )
                    invalidate_cache()
                    if features is None:
                        resolved_features = get_op_features(operation)
                    continue
                raise
        raise APIError(f"Unreachable: _graphql_request retry loop for '{operation}'")

    def rest_get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated REST API GET request (non-GraphQL)."""
        return self._request("GET", url, params=params)

    def graphql_post_raw(
        self,
        query_id: str,
        operation_name: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a GraphQL POST request with a hardcoded query ID.

        Used for operations not present in the JS bundles (e.g., scheduled tweets).

        Args:
            query_id: The static query ID for this operation.
            operation_name: The GraphQL operation name.
            variables: Variables to pass to the operation.
        """
        url = f"{GRAPHQL_BASE}/{query_id}/{operation_name}"
        json_data = {
            "variables": variables,
            "queryId": query_id,
        }
        result = self._request("POST", url, json_data=json_data)
        write_delay()
        return result

    def graphql_get(
        self,
        operation: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
        field_toggles: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL GET request."""
        return self._graphql_request("GET", operation, variables, features, field_toggles)

    def graphql_post(
        self,
        operation: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
        field_toggles: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL POST request (for write operations)."""
        return self._graphql_request("POST", operation, variables, features, field_toggles)

    def rest_post(
        self,
        url: str,
        data: str | dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated REST POST request (form-encoded, not GraphQL).

        Used for endpoints like the media upload API on upload.twitter.com.
        """
        headers = self._get_headers()
        # REST endpoints use form-encoded bodies, not JSON
        headers.pop("content-type", None)
        if data is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"
        # Cross-origin uploads (e.g. upload.twitter.com from x.com)
        if "upload.twitter.com" in url:
            headers["sec-fetch-site"] = "same-site"
        cookies = self._get_cookies()

        response = self.session.request(
            method="POST",
            url=url,
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=timeout,
        )

        if response.status_code in (200, 201, 202, 204):
            if response.text:
                return response.json()
            return {}
        elif response.status_code == 401:
            raise AuthError("Authentication failed. Cookies may be expired.")
        elif response.status_code == 429:
            raise RateLimitError("Rate limited by Twitter/X", status_code=429)
        elif response.status_code == 403:
            raise APIError(
                "Forbidden — account may be suspended or action not allowed",
                status_code=403,
            )
        else:
            raise APIError(
                f"REST API error: HTTP {response.status_code} — {response.text[:500]}",
                status_code=response.status_code,
                response_data=response.text[:500],
            )

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> XClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
