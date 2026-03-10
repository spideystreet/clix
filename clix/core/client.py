"""HTTP client for Twitter/X API with TLS fingerprinting."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from curl_cffi import requests as curl_requests

from clix.core.auth import AuthCredentials, AuthError, get_credentials
from clix.core.constants import (
    BASE_URL,
    BEARER_TOKEN,
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
        self._proxy = proxy or os.environ.get("X_PROXY") or os.environ.get("TWITTER_PROXY")
        self._session: curl_requests.Session | None = None

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

    def _get_headers(self) -> dict[str, str]:
        """Build browser-like request headers for API calls."""
        creds = self.credentials
        return {
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
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make an authenticated request with retry logic."""
        headers = self._get_headers()
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
    ) -> dict[str, Any]:
        """Make a GraphQL request with auto-retry on stale endpoint IDs."""
        resolved_features = features if features is not None else get_op_features(operation)

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
                        "fieldToggles": json.dumps(DEFAULT_FIELD_TOGGLES),
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
        raise APIError(f"Unreachable: _graphql_request retry loop for '{operation}'")

    def graphql_get(
        self,
        operation: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL GET request."""
        return self._graphql_request("GET", operation, variables, features)

    def graphql_post(
        self,
        operation: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL POST request (for write operations)."""
        return self._graphql_request("POST", operation, variables, features)

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> XClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
