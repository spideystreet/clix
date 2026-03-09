"""Tests for tweet filtering and scoring."""

from clix.core.config import FilterConfig
from clix.models.tweet import Tweet, TweetEngagement
from clix.utils.filter import filter_tweets, score_tweet


def _make_tweet(tweet_id: str, likes: int = 0, retweets: int = 0, views: int = 0) -> Tweet:
    return Tweet(
        id=tweet_id,
        text=f"Tweet {tweet_id}",
        author_id="1",
        author_name="Test",
        author_handle="test",
        engagement=TweetEngagement(likes=likes, retweets=retweets, views=views),
    )


class TestScoring:
    def test_score_zero_engagement(self):
        tweet = _make_tweet("1")
        assert score_tweet(tweet) == 0.0

    def test_score_with_likes(self):
        tweet = _make_tweet("1", likes=100)
        score = score_tweet(tweet)
        assert score > 0

    def test_score_custom_weights(self):
        tweet = _make_tweet("1", likes=100)
        config = FilterConfig(likes_weight=2.0)
        score = score_tweet(tweet, config)
        assert score == 200.0

    def test_score_views_log(self):
        tweet1 = _make_tweet("1", views=100)
        tweet2 = _make_tweet("2", views=1000000)
        # Log scaling means 1M views isn't 10000x more than 100 views
        s1 = score_tweet(tweet1)
        s2 = score_tweet(tweet2)
        assert s2 > s1
        assert s2 < s1 * 100  # not linear


class TestFiltering:
    def test_filter_all(self):
        tweets = [
            _make_tweet("1", likes=10),
            _make_tweet("2", likes=100),
            _make_tweet("3", likes=50),
        ]
        result = filter_tweets(tweets, mode="all")
        assert len(result) == 3
        assert result[0].id == "2"  # highest score first

    def test_filter_top_n(self):
        tweets = [_make_tweet(str(i), likes=i) for i in range(10)]
        result = filter_tweets(tweets, mode="top", top_n=3)
        assert len(result) == 3
        assert result[0].id == "9"

    def test_filter_score_threshold(self):
        tweets = [
            _make_tweet("1", likes=5),
            _make_tweet("2", likes=50),
            _make_tweet("3", likes=500),
        ]
        result = filter_tweets(tweets, mode="score", threshold=100.0)
        assert len(result) == 1
        assert result[0].id == "3"

    def test_filter_empty(self):
        result = filter_tweets([], mode="all")
        assert result == []
