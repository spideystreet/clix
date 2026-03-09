"""Tests for data models."""

from clix.models.tweet import TimelineResponse, Tweet, TweetEngagement, TweetMedia
from clix.models.user import User


class TestTweetModel:
    def test_create_tweet(self):
        tweet = Tweet(
            id="123",
            text="Hello world",
            author_id="456",
            author_name="Test User",
            author_handle="testuser",
        )
        assert tweet.id == "123"
        assert tweet.text == "Hello world"
        assert tweet.tweet_url == "https://x.com/testuser/status/123"

    def test_tweet_with_engagement(self):
        tweet = Tweet(
            id="123",
            text="Popular tweet",
            author_id="456",
            author_name="Test",
            author_handle="test",
            engagement=TweetEngagement(likes=100, retweets=50, views=10000),
        )
        assert tweet.engagement.likes == 100
        assert tweet.engagement.retweets == 50
        assert tweet.engagement.views == 10000

    def test_tweet_with_media(self):
        tweet = Tweet(
            id="123",
            text="Photo tweet",
            author_id="456",
            author_name="Test",
            author_handle="test",
            media=[
                TweetMedia(type="photo", url="https://example.com/photo.jpg"),
            ],
        )
        assert len(tweet.media) == 1
        assert tweet.media[0].type == "photo"

    def test_tweet_to_json(self):
        tweet = Tweet(
            id="123",
            text="Test",
            author_id="456",
            author_name="Test",
            author_handle="test",
        )
        data = tweet.to_json_dict()
        assert data["id"] == "123"
        assert "tweet_url" in data

    def test_tweet_from_api_result(self):
        api_data = {
            "rest_id": "999",
            "core": {
                "user_results": {
                    "result": {
                        "rest_id": "111",
                        "is_blue_verified": True,
                        "legacy": {
                            "name": "API User",
                            "screen_name": "apiuser",
                        },
                    }
                }
            },
            "legacy": {
                "full_text": "Tweet from API",
                "favorite_count": 42,
                "retweet_count": 10,
                "reply_count": 5,
                "quote_count": 2,
                "bookmark_count": 3,
                "created_at": "Mon Jan 01 12:00:00 +0000 2024",
                "lang": "en",
            },
            "views": {"count": "50000"},
        }

        tweet = Tweet.from_api_result(api_data)
        assert tweet is not None
        assert tweet.id == "999"
        assert tweet.text == "Tweet from API"
        assert tweet.author_handle == "apiuser"
        assert tweet.author_verified is True
        assert tweet.engagement.likes == 42
        assert tweet.engagement.views == 50000

    def test_tweet_from_api_result_retweet(self):
        api_data = {
            "rest_id": "rt_id",
            "core": {
                "user_results": {
                    "result": {
                        "rest_id": "retweeter_id",
                        "legacy": {
                            "name": "Retweeter",
                            "screen_name": "retweeter",
                        },
                    }
                }
            },
            "legacy": {
                "full_text": "RT @original: Original tweet",
                "retweeted_status_result": {
                    "result": {
                        "rest_id": "original_id",
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "orig_user_id",
                                    "legacy": {
                                        "name": "Original",
                                        "screen_name": "original",
                                    },
                                }
                            }
                        },
                        "legacy": {
                            "full_text": "Original tweet",
                            "favorite_count": 100,
                            "retweet_count": 50,
                        },
                    }
                },
            },
        }

        tweet = Tweet.from_api_result(api_data)
        assert tweet is not None
        assert tweet.is_retweet is True
        assert tweet.retweeted_by == "retweeter"
        assert tweet.author_handle == "original"

    def test_tweet_from_api_result_invalid(self):
        assert Tweet.from_api_result({}) is None
        assert Tweet.from_api_result({"rest_id": ""}) is None


class TestTimelineResponse:
    def test_empty_response(self):
        resp = TimelineResponse()
        assert resp.tweets == []
        assert resp.cursor_bottom is None
        assert resp.has_more is False

    def test_response_with_tweets(self):
        tweets = [
            Tweet(id="1", text="A", author_id="x", author_name="X", author_handle="x"),
            Tweet(id="2", text="B", author_id="y", author_name="Y", author_handle="y"),
        ]
        resp = TimelineResponse(tweets=tweets, cursor_bottom="abc", has_more=True)
        assert len(resp.tweets) == 2
        assert resp.has_more is True


class TestUserModel:
    def test_create_user(self):
        user = User(
            id="123",
            name="Test User",
            handle="testuser",
            bio="A test user",
            followers_count=1000,
            following_count=500,
        )
        assert user.id == "123"
        assert user.profile_url == "https://x.com/testuser"

    def test_user_from_api_result(self):
        api_data = {
            "rest_id": "789",
            "is_blue_verified": True,
            "legacy": {
                "name": "API User",
                "screen_name": "apiuser",
                "description": "Bio text",
                "location": "Earth",
                "followers_count": 5000,
                "friends_count": 200,
                "statuses_count": 10000,
                "listed_count": 50,
                "created_at": "Tue Jan 01 00:00:00 +0000 2020",
                "profile_image_url_https": "https://pbs.twimg.com/pic_normal.jpg",
                "profile_banner_url": "https://pbs.twimg.com/banner.jpg",
            },
        }

        user = User.from_api_result(api_data)
        assert user is not None
        assert user.id == "789"
        assert user.verified is True
        assert user.followers_count == 5000
        assert user.following_count == 200
        assert "_400x400" in user.profile_image_url

    def test_user_from_api_result_invalid(self):
        assert User.from_api_result({}) is None
        assert User.from_api_result({"rest_id": ""}) is None

    def test_user_to_json(self):
        user = User(id="1", name="T", handle="t")
        data = user.to_json_dict()
        assert data["id"] == "1"
        assert "profile_url" not in data  # computed property, not in model_dump
