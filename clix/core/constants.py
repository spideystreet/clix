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

# GraphQL operation IDs (these change periodically, may need updating)
GRAPHQL_ENDPOINTS = {
    # Read operations
    "HomeTimeline": "HCosKfLNW1AcOo3la3mMgg/HomeTimeline",
    "HomeLatestTimeline": "DiTkXJgAKXpkg5wTKMm-aA/HomeLatestTimeline",
    "SearchTimeline": "MJnbGWAp_51cbyb-hMB1IQ/SearchTimeline",
    "TweetDetail": "nBS-WpgA6ZG0CyNHD517JQ/TweetDetail",
    "UserByScreenName": "qW5u-DAen42o05gujSY8nw/UserByScreenName",
    "UserTweets": "CdG2Vuc1v6F5JyEngGpxVw/UserTweets",
    "UserTweetsAndReplies": "UtLStR_BnEOEtJ9rGgakRA/UserTweetsAndReplies",
    "Likes": "eSSNbhECHHWWALkkQq-YTA/Likes",
    "Followers": "pd8Tt2P9VuLQ8rPJCIb7Xg/Followers",
    "Following": "iSicc7LrzWGBgDPL0tM_TQ/Following",
    "Bookmarks": "uKP9v_I31k0_VSBmlpq2Xg/Bookmarks",
    "ListLatestTweetsTimeline": "BbGLL1ZfMQ2jogw0UCiNkg/ListLatestTweetsTimeline",
    # Write operations
    "CreateTweet": "oB-5XsHNAbjvARJEc8CZFw/CreateTweet",
    "DeleteTweet": "VaenaVgh5q5ih7kvyVjgtg/DeleteTweet",
    "FavoriteTweet": "lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
    "UnfavoriteTweet": "ZYKSe-w7KEslx3JhSIk5LA/UnfavoriteTweet",
    "CreateRetweet": "ojPdsZsimiJrUGLR1sjUtA/CreateRetweet",
    "DeleteRetweet": "iQtK4dl5hBmXewYZuEOKVw/DeleteRetweet",
    "CreateBookmark": "aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark",
    "DeleteBookmark": "Wlmlj2-xISYCxxdo9QzK2Q/DeleteBookmark",
}

# Default features for GraphQL requests
DEFAULT_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

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
