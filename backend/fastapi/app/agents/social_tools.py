"""
Social Media Integration Tools

Real implementations for posting to:
- Twitter/X
- LinkedIn
- Facebook

Using official APIs with proper authentication and error handling.
"""

import logging
import os
import time
from typing import Any

import httpx
from backend.fastapi.app.agents.base import BaseTool, ToolResult, ToolType

logger = logging.getLogger(__name__)

class TwitterPostTool(BaseTool):
    """Post tweets to Twitter/X"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Post a tweet to Twitter
        
        Params:
        - text: string (tweet content, max 280 chars)
        - reply_to: string (optional, tweet ID to reply to)
        - media_ids: list[str] (optional, media IDs to attach)
        """
        start = time.time()
        
        try:
            text = input_params.get("text", "")
            reply_to = input_params.get("reply_to")
            media_ids = input_params.get("media_ids", [])
            
            if not text:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="text is required",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            if len(text) > 280:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error=f"Tweet too long: {len(text)} chars (max 280)",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            bearer_token = self.credentials.get("TWITTER_BEARER_TOKEN")
            
            if not bearer_token:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Twitter Bearer Token",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Create tweet
                payload = {"text": text}
                
                if reply_to:
                    payload["reply"] = {"in_reply_to_tweet_id": reply_to}
                
                if media_ids:
                    payload["media"] = {"media_ids": media_ids}
                
                response = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers={
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                tweet_id = data["data"]["id"]
                logger.info(f"Posted tweet: {tweet_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "tweet_id": tweet_id,
                        "text": text[:100],
                        "url": f"https://twitter.com/i/web/status/{tweet_id}",
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Twitter API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Twitter API error: {str(e)}",
                execution_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

class LinkedInPostTool(BaseTool):
    """Post to LinkedIn"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Post content to LinkedIn
        
        Params:
        - text: string (post content)
        - title: string (optional, for article/document posts)
        - link_url: string (optional, URL to share)
        - image_url: string (optional, image to attach)
        - post_type: string (optional, "TEXT_ONLY" or "ARTICLE", default: "TEXT_ONLY")
        """
        start = time.time()
        
        try:
            text = input_params.get("text", "")
            post_type = input_params.get("post_type", "TEXT_ONLY")
            
            if not text:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="text is required",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            access_token = self.credentials.get("LINKEDIN_ACCESS_TOKEN")
            
            if not access_token:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing LinkedIn Access Token",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Get user ID first
                me_response = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=30
                )
                me_response.raise_for_status()
                user_id = me_response.json()["id"]
                
                # Create post
                payload: dict[str, Any] = {
                    "author": f"urn:li:person:{user_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.UGCPost": {
                            "shareMediaCategory": "NONE" if post_type == "TEXT_ONLY" else "ARTICLE",
                            "shareCommentary": {
                                "text": text
                            }
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }
                
                if input_params.get("link_url"):
                    payload["specificContent"]["com.linkedin.ugc.UGCPost"]["shareMediaCategory"] = "ARTICLE"
                    payload["specificContent"]["com.linkedin.ugc.UGCPost"]["media"] = [
                        {
                            "status": "READY",
                            "description": {
                                "text": input_params.get("title", text[:100])
                            },
                            "media": input_params.get("link_url"),
                            "title": {
                                "text": input_params.get("title", "Share")
                            }
                        }
                    ]
                
                response = await client.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "LinkedIn-Version": "202401",
                    },
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                post_id = data.get("id", "")
                logger.info(f"Posted to LinkedIn: {post_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "post_id": post_id,
                        "text": text[:100],
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"LinkedIn API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"LinkedIn API error: {str(e)}",
                execution_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

class FacebookPostTool(BaseTool):
    """Post to Facebook"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Post to Facebook Page or Timeline
        
        Params:
        - text: string (post content)
        - link: string (optional, URL to share)
        - picture: string (optional, image URL)
        - page_id: string (optional, page ID to post to)
        """
        start = time.time()
        
        try:
            text = input_params.get("text", "")
            link = input_params.get("link")
            picture = input_params.get("picture")
            page_id = input_params.get("page_id")
            
            if not text:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="text is required",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            access_token = self.credentials.get("FACEBOOK_ACCESS_TOKEN")
            
            if not access_token:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Facebook Access Token",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            # Use page_id or "me" for personal feed
            target = page_id or "me"
            
            async with httpx.AsyncClient() as client:
                # Create post
                payload = {"message": text}
                
                if link:
                    payload["link"] = link
                
                if picture:
                    payload["picture"] = picture
                
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{target}/feed",
                    params={"access_token": access_token},
                    data=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                post_id = data.get("id", "")
                logger.info(f"Posted to Facebook: {post_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "post_id": post_id,
                        "text": text[:100],
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Facebook API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Facebook API error: {str(e)}",
                execution_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

# Register social tools
def register_social_tools(tool_registry):
    """Register all social media tools"""
    credentials = {
        "TWITTER_BEARER_TOKEN": os.getenv("TWITTER_BEARER_TOKEN", ""),
        "LINKEDIN_ACCESS_TOKEN": os.getenv("LINKEDIN_ACCESS_TOKEN", ""),
        "FACEBOOK_ACCESS_TOKEN": os.getenv("FACEBOOK_ACCESS_TOKEN", ""),
    }
    
    tool_registry.register(
        ToolType.TWITTER_POST,
        TwitterPostTool(ToolType.TWITTER_POST, credentials)
    )
    
    tool_registry.register(
        ToolType.LINKEDIN_POST,
        LinkedInPostTool(ToolType.LINKEDIN_POST, credentials)
    )
    
    tool_registry.register(
        ToolType.FACEBOOK_POST,
        FacebookPostTool(ToolType.FACEBOOK_POST, credentials)
    )
    
    logger.info("Social media tools registered")
