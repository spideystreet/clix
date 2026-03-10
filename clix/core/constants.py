"""Twitter/X API constants: endpoints, headers, and defaults."""

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
