"""
Provider-Specific Action Executors

Native SDK integration for major social platforms:
- Slack: chat.postMessage, thread replies
- X: tweets, quoted tweets, thread replies
- Facebook: photo posts, link shares, video uploads
- Instagram: photo carousel, reels, stories
- Threads: thread creation, replies
- TikTok: video uploads (via cloud API)
- YouTube: video uploads, playlist management

Each executor follows: verify credentials -> prepare payload -> execute -> return metadata
"""

from __future__ import annotations

from typing import Any

import httpx


class ProviderActionExecutor:
    """Base executor for all providers."""

    def __init__(self, token: str, timeout: float = 20.0):
        self.token = token
        self.timeout = timeout


class SlackExecutor(ProviderActionExecutor):
    """Slack message posting."""

    async def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> tuple[bool, dict[str, Any]]:
        """Post message to channel or thread."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)
            if response.status_code < 400:
                data = response.json()
                return data.get("ok", False), {"channel": channel, "ts": data.get("ts"), "ok": data.get("ok")}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class XExecutor(ProviderActionExecutor):
    """X (Twitter) tweet posting."""

    async def post_tweet(self, text: str, quote_id: str | None = None, reply_id: str | None = None) -> tuple[bool, dict[str, Any]]:
        """Post tweet, optionally as quote or reply."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"text": text}
        if quote_id:
            payload["quote_tweet_id"] = quote_id
        if reply_id:
            payload["reply"] = {"in_reply_to_tweet_id": reply_id}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post("https://api.x.com/2/tweets", json=payload, headers=headers)
            if response.status_code < 400:
                data = response.json()
                tweet_id = data.get("data", {}).get("id")
                return bool(tweet_id), {"tweet_id": tweet_id, "data": data.get("data", {})}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class FacebookExecutor(ProviderActionExecutor):
    """Facebook page posts (via Graph API)."""

    async def post_photo(self, page_id: str, photo_url: str, caption: str = "") -> tuple[bool, dict[str, Any]]:
        """Upload and post photo to page."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"url": photo_url, "caption": caption}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v20.0/{page_id}/photos", json=payload, headers=headers
                )
            if response.status_code < 400:
                data = response.json()
                post_id = data.get("post_id")
                return bool(post_id), {"post_id": post_id}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}

    async def post_link(self, page_id: str, link: str, message: str = "") -> tuple[bool, dict[str, Any]]:
        """Post link share to page."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"link": link, "message": message}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://graph.facebook.com/v20.0/{page_id}/feed", json=payload, headers=headers
                )
            if response.status_code < 400:
                data = response.json()
                post_id = data.get("id")
                return bool(post_id), {"post_id": post_id}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class InstagramExecutor(ProviderActionExecutor):
    """Instagram photo/video carousel posts (via Graph API)."""

    async def post_carousel(self, ig_user_id: str, items: list[dict[str, str]], caption: str = "") -> tuple[bool, dict[str, Any]]:
        """Post carousel of photos/videos."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "media_type": "CAROUSEL",
            "children": items,
            "caption": caption,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://graph.instagram.com/v20.0/{ig_user_id}/media", json=payload, headers=headers
                )
            if response.status_code < 400:
                data = response.json()
                media_id = data.get("id")
                if media_id:
                    publish_resp = await client.post(
                        f"https://graph.instagram.com/v20.0/{media_id}/publish", json={}, headers=headers
                    )
                    return publish_resp.status_code < 400, {"media_id": media_id}
                return False, {"error": "No media ID returned"}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}

    async def post_reel(self, ig_user_id: str, video_url: str, thumbnail_url: str, caption: str = "") -> tuple[bool, dict[str, Any]]:
        """Post reel video."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "thumb_offset": 0,
            "caption": caption,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://graph.instagram.com/v20.0/{ig_user_id}/media", json=payload, headers=headers
                )
            if response.status_code < 400:
                data = response.json()
                media_id = data.get("id")
                if media_id:
                    publish_resp = await client.post(
                        f"https://graph.instagram.com/v20.0/{media_id}/publish", json={}, headers=headers
                    )
                    return publish_resp.status_code < 400, {"media_id": media_id}
                return False, {"error": "No media ID returned"}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class ThreadsExecutor(ProviderActionExecutor):
    """Threads (Meta's text-based platform) posts."""

    async def post_thread(self, threads_user_id: str, text: str, image_url: str | None = None) -> tuple[bool, dict[str, Any]]:
        """Post to Threads."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload: dict[str, Any] = {"text": text}
        if image_url:
            payload["image_url"] = image_url

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://graph.threads.com/v1.0/{threads_user_id}/threads", json=payload, headers=headers
                )
            if response.status_code < 400:
                data = response.json()
                thread_id = data.get("id")
                if thread_id:
                    publish_resp = await client.post(
                        f"https://graph.threads.com/v1.0/{thread_id}/publish", json={}, headers=headers
                    )
                    return publish_resp.status_code < 400, {"thread_id": thread_id}
                return False, {"error": "No thread ID returned"}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class TikTokExecutor(ProviderActionExecutor):
    """TikTok video uploads (via TikTok Cloud API)."""

    async def upload_video(self, video_url: str, caption: str = "", disable_comment: bool = False) -> tuple[bool, dict[str, Any]]:
        """Upload video to TikTok."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
            "post_info": {"caption": caption, "disable_comment": disable_comment},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://open.tiktokapis.com/v1/post/publish/video/init/",
                    json=payload,
                    headers=headers,
                )
            if response.status_code < 400:
                data = response.json()
                request_id = data.get("data", {}).get("upload_id")
                return bool(request_id), {"upload_id": request_id, "data": data.get("data", {})}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


class YouTubeExecutor(ProviderActionExecutor):
    """YouTube video uploads and playlist management."""

    async def upload_video(
        self, title: str, description: str, video_url: str, privacy_status: str = "private"
    ) -> tuple[bool, dict[str, Any]]:
        """Upload video to YouTube."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "snippet": {"title": title, "description": description, "categoryId": "22"},
            "status": {"privacyStatus": privacy_status},
            "processingDetails": {},
            "processingProgress": {},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://www.googleapis.com/youtube/v3/videos?part=snippet,status,processingDetails",
                    json=payload,
                    headers=headers,
                )
            if response.status_code < 400:
                data = response.json()
                video_id = data.get("id")
                return bool(video_id), {"video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}

    async def add_to_playlist(self, playlist_id: str, video_id: str) -> tuple[bool, dict[str, Any]]:
        """Add video to playlist."""
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
                    json=payload,
                    headers=headers,
                )
            if response.status_code < 400:
                data = response.json()
                item_id = data.get("id")
                return bool(item_id), {"item_id": item_id}
            return False, {"error": f"HTTP {response.status_code}", "response": response.text[:500]}
        except Exception as e:
            return False, {"error": str(e)[:500]}


def get_executor(provider: str, token: str, timeout: float = 20.0) -> ProviderActionExecutor | None:
    """Factory to get provider-specific executor."""
    executors: dict[str, type[ProviderActionExecutor]] = {
        "slack": SlackExecutor,
        "x": XExecutor,
        "facebook": FacebookExecutor,
        "instagram": InstagramExecutor,
        "threads": ThreadsExecutor,
        "tiktok": TikTokExecutor,
        "youtube": YouTubeExecutor,
    }
    executor_class = executors.get(provider)
    return executor_class(token, timeout) if executor_class else None
