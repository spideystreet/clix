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
    # Read operations (IDs updated 2026-03-08 from X.com bundle)
    "HomeTimeline": "snvCaalBp51MiDb3-nGblg/HomeTimeline",
    "HomeLatestTimeline": "KLMY6cZZUfQrLubs5DHHtQ/HomeLatestTimeline",
    "SearchTimeline": "nWemVnGJ6A5eQAR5-oQeAg/SearchTimeline",
    "TweetDetail": "16nxv6mC_2VaBvBwY2V85g/TweetDetail",
    "UserByScreenName": "pLsOiyHJ1eFwPJlNmLp4Bg/UserByScreenName",
    "UserTweets": "ix7iRrsAvfXyGUQ06Z7krA/UserTweets",
    "UserTweetsAndReplies": "RCpRL9JyzOSO5qS6YDOg7w/UserTweetsAndReplies",
    "Likes": "LJ-3k8SBSgNZEYGd7RMIbA/Likes",
    "Followers": "ggGqWO5y_c4Iu58dyHnbzg/Followers",
    "Following": "NElglO5nnh78FWMvYQuwDw/Following",
    "Bookmarks": "c-7G4ohSLIuTcfa5Mn5qdw/Bookmarks",
    "ListLatestTweetsTimeline": "CMHuPAVadvYIqbIFURJFmw/ListLatestTweetsTimeline",
    # Write operations
    "CreateTweet": "uY34Pldm6W89yqswRmPMSQ/CreateTweet",
    "DeleteTweet": "nxpZCY2K-I6QoFHAHeojFQ/DeleteTweet",
    "FavoriteTweet": "lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
    "UnfavoriteTweet": "ZYKSe-w7KEslx3JhSIk5LA/UnfavoriteTweet",
    "CreateRetweet": "mbRO74GrOvSfRcJnlMapnQ/CreateRetweet",
    "DeleteRetweet": "ZyZigVsNiFO6v1dEks1eWg/DeleteRetweet",
    "CreateBookmark": "aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark",
    "DeleteBookmark": "Wlmlj2-xzyS1GN3a6cj-mQ/DeleteBookmark",
}

# Default features for GraphQL requests
DEFAULT_FEATURES = {
    # Updated 2026-03-08 from X.com bundle
    "rweb_tipjar_consumption_enabled": False,
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
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
    "rweb_video_screen_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "premium_content_api_read_enabled": False,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": False,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
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
