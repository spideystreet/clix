"""Tweet engagement scoring and filtering."""

from __future__ import annotations

import math

from clix.core.config import FilterConfig
from clix.models.tweet import Tweet


def score_tweet(tweet: Tweet, config: FilterConfig | None = None) -> float:
    """Calculate engagement score for a tweet."""
    if config is None:
        config = FilterConfig()

    e = tweet.engagement
    views_log = math.log10(e.views + 1) if e.views > 0 else 0

    return (
        config.likes_weight * e.likes
        + config.retweets_weight * e.retweets
        + config.replies_weight * e.replies
        + config.bookmarks_weight * e.bookmarks
        + config.views_log_weight * views_log
    )


def filter_tweets(
    tweets: list[Tweet],
    mode: str = "all",
    threshold: float = 0.0,
    top_n: int = 10,
    config: FilterConfig | None = None,
) -> list[Tweet]:
    """Filter and sort tweets by engagement score.

    Modes:
        all: Sort by score, no filtering
        score: Keep tweets above threshold
        top: Keep top N tweets
    """
    scored = [(tweet, score_tweet(tweet, config)) for tweet in tweets]
    scored.sort(key=lambda x: x[1], reverse=True)

    if mode == "score":
        scored = [(t, s) for t, s in scored if s >= threshold]
    elif mode == "top":
        scored = scored[:top_n]

    return [t for t, _ in scored]
