import os

import pytest

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.core.supabase_client import get_supabase
from backend.fastapi.app.intelligence import engine, routes


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_fetch_news_uses_rapidapi_fallback(monkeypatch):
    monkeypatch.setattr(engine, "NEWSAPI_KEY", "")
    monkeypatch.setattr(engine, "RAPIDAPI_KEY", "rapid-key")
    monkeypatch.setattr(engine, "RAPIDAPI_NEWS_HOST", "real-time-news-data.p.rapidapi.com")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None, headers=None):
            assert "real-time-news-data.p.rapidapi.com" in url
            assert headers and headers.get("X-RapidAPI-Key") == "rapid-key"
            return _FakeResponse(
                200,
                {
                    "data": [
                        {
                            "title": "RapidAPI Market Update",
                            "source_name": "Rapid Wire",
                            "link": "https://example.com/news/1",
                            "published_datetime_utc": "2026-05-17T00:00:00Z",
                            "summary": "Signal from rapid fallback",
                        }
                    ]
                },
            )

    monkeypatch.setattr(engine.httpx, "AsyncClient", FakeAsyncClient)

    items = await engine.fetch_news("nuxtron", days_back=1)
    assert len(items) == 1
    assert items[0]["title"] == "RapidAPI Market Update"
    assert items[0]["source"] == "Rapid Wire"


@pytest.mark.asyncio
async def test_collect_youtube_public_normalizes_videos(monkeypatch):
    monkeypatch.setattr(engine, "YOUTUBE_API_KEY", "yt-key")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None, headers=None):
            if "youtube/v3/search" in url:
                if params and params.get("type") == "channel" and params.get("q"):
                    return _FakeResponse(
                        200,
                        {"items": [{"id": {"channelId": "UC123"}}]},
                    )
                return _FakeResponse(
                    200,
                    {
                        "items": [
                            {"id": {"videoId": "vid-1"}},
                            {"id": {"videoId": "vid-2"}},
                        ]
                    },
                )

            if "youtube/v3/videos" in url:
                return _FakeResponse(
                    200,
                    {
                        "items": [
                            {
                                "id": "vid-1",
                                "snippet": {
                                    "title": "Video One",
                                    "description": "Description one",
                                    "channelTitle": "Nuxtron Channel",
                                    "channelId": "UC123",
                                    "publishedAt": "2026-05-17T01:00:00Z",
                                },
                                "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "10"},
                                "contentDetails": {"duration": "PT5M"},
                            },
                            {
                                "id": "vid-2",
                                "snippet": {
                                    "title": "Video Two",
                                    "description": "Description two",
                                    "channelTitle": "Nuxtron Channel",
                                    "channelId": "UC123",
                                    "publishedAt": "2026-05-17T02:00:00Z",
                                },
                                "statistics": {"viewCount": "2000", "likeCount": "200", "commentCount": "20"},
                                "contentDetails": {"duration": "PT8M"},
                            },
                        ]
                    },
                )

            return _FakeResponse(404, {})

    monkeypatch.setattr(engine.httpx, "AsyncClient", FakeAsyncClient)

    posts = await engine.collect_youtube_public("nuxtron-channel", limit=2)
    assert len(posts) == 2
    assert posts[0]["platform"] == "youtube"
    assert posts[0]["platform_post_id"] == "vid-1"
    assert posts[0]["views"] == 1000
    assert posts[1]["likes"] == 200


@pytest.mark.asyncio
async def test_full_scan_background_includes_youtube_posts(monkeypatch):
    sb = get_supabase()

    target = (
        sb.table("intel_targets")
        .insert(
            {
                "org_id": "org-yt",
                "name": "YouTube Competitor",
                "twitter_handle": "",
                "reddit_username": "",
                "youtube_channel_id": "UCYOUTUBE",
                "facebook_page": "",
                "domain": "",
                "track_social": True,
                "track_news": False,
                "track_ads": False,
                "track_website": False,
            }
        )
        .execute()
        .data[0]
    )

    async def _twitter(_handle):
        return []

    async def _reddit(_username):
        return []

    async def _youtube(_channel_id):
        return [
            {
                "platform": "youtube",
                "platform_post_id": "yt-post-1",
                "post_url": "https://www.youtube.com/watch?v=yt-post-1",
                "author_handle": "YouTube Competitor",
                "content": "Video content",
                "content_type": "video",
                "likes": 50,
                "comments": 5,
                "shares": 0,
                "views": 500,
                "posted_at": "2026-05-17T03:00:00Z",
                "metadata": {"channel_id": "UCYOUTUBE"},
            }
        ]

    async def _website(_domain):
        return {}

    async def _news(_query):
        return []

    async def _ads(_page_name):
        return []

    async def _scores(posts):
        enriched = []
        for p in posts:
            enriched.append(
                {
                    **p,
                    "engagement_rate": 10.0,
                    "engagement_velocity": 5.0,
                    "virality_coefficient": 1.0,
                    "content_resonance_index": 15.0,
                    "estimated_organic_reach": 1000,
                    "trend_phase": "emerging",
                }
            )
        return enriched

    monkeypatch.setattr(routes, "collect_twitter_public", _twitter)
    monkeypatch.setattr(routes, "collect_reddit_public", _reddit)
    monkeypatch.setattr(routes, "collect_youtube_public", _youtube)
    monkeypatch.setattr(routes, "scrape_public_website", _website)
    monkeypatch.setattr(routes, "fetch_news", _news)
    monkeypatch.setattr(routes, "fetch_meta_ads", _ads)
    monkeypatch.setattr(routes, "calculate_scores", _scores)

    await routes._full_scan_background(target["id"], "org-yt")

    stored = (
        sb.table("intel_social_posts")
        .select("*")
        .eq("target_id", target["id"])
        .eq("platform", "youtube")
        .execute()
        .data
    )

    assert len(stored) >= 1
    assert stored[0]["platform_post_id"] == "yt-post-1"
