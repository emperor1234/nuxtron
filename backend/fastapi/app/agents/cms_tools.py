"""
CMS Integration Tools for Agents

Real implementations for:
- Contentful (Headless CMS)
- Sanity (Headless CMS)
- WordPress (Traditional CMS)
- Framer (No-code builder)
"""

import logging
import os
import time
from typing import Any

import httpx
from backend.fastapi.app.agents.base import BaseTool, ToolResult, ToolType

logger = logging.getLogger(__name__)

class ContentfulCreateTool(BaseTool):
    """Create entries in Contentful CMS"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Create a new entry in Contentful
        
        Params:
        - content_type_id: string (e.g., "blogPost", "article")
        - title: string
        - body: string
        - tags: list[string] (optional)
        - metadata: dict (optional)
        """
        start = time.time()
        
        try:
            content_type_id = input_params.get("content_type_id", "article")
            title = input_params.get("title", "Untitled")
            body = input_params.get("body", "")
            tags = input_params.get("tags", [])
            
            space_id = self.credentials.get("CONTENTFUL_SPACE_ID")
            access_token = self.credentials.get("CONTENTFUL_PERSONAL_TOKEN")
            environment = self.credentials.get("CONTENTFUL_ENVIRONMENT", "master")
            
            if not (space_id and access_token):
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Contentful credentials",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Create entry
                response = await client.post(
                    f"https://api.contentful.com/spaces/{space_id}/environments/{environment}/entries",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/vnd.contentful.management.v1+json",
                        "X-Contentful-Content-Type": content_type_id,
                    },
                    json={
                        "fields": {
                            "title": {"en-US": title},
                            "body": {"en-US": body},
                            "tags": {"en-US": tags},
                        }
                    },
                    timeout=30
                )
                response.raise_for_status()
                entry = response.json()
                
                entry_id = entry["sys"]["id"]
                logger.info(f"Created Contentful entry: {entry_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "entry_id": entry_id,
                        "title": title,
                        "status": "created_draft",
                        "content_type": content_type_id,
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Contentful API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Contentful API error: {str(e)}",
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

class ContentfulPublishTool(BaseTool):
    """Publish entries in Contentful"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Publish an entry in Contentful
        
        Params:
        - entry_id: string
        - version: int (current version of entry)
        """
        start = time.time()
        
        try:
            entry_id = input_params.get("entry_id")
            version = input_params.get("version", 1)
            
            if not entry_id:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="entry_id is required",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            space_id = self.credentials.get("CONTENTFUL_SPACE_ID")
            access_token = self.credentials.get("CONTENTFUL_PERSONAL_TOKEN")
            environment = self.credentials.get("CONTENTFUL_ENVIRONMENT", "master")
            
            if not (space_id and access_token):
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Contentful credentials",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Publish entry
                response = await client.put(
                    f"https://api.contentful.com/spaces/{space_id}/environments/{environment}/entries/{entry_id}/published",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-Contentful-Version": str(version),
                        "Content-Type": "application/vnd.contentful.management.v1+json",
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                logger.info(f"Published Contentful entry: {entry_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "entry_id": entry_id,
                        "status": "published",
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Contentful publish error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Contentful publish error: {str(e)}",
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

class SanityMutateTool(BaseTool):
    """Mutate documents in Sanity CMS"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Create or update a document in Sanity
        
        Params:
        - _type: string (document type, e.g., "article")
        - title: string
        - body: string (or rich text object)
        - publish: bool (whether to publish immediately)
        """
        start = time.time()
        
        try:
            doc_type = input_params.get("_type", "article")
            title = input_params.get("title", "Untitled")
            body = input_params.get("body", "")
            publish = input_params.get("publish", False)
            
            project_id = self.credentials.get("SANITY_PROJECT_ID")
            api_token = self.credentials.get("SANITY_API_TOKEN")
            dataset = self.credentials.get("SANITY_DATASET", "production")
            
            if not (project_id and api_token):
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Sanity credentials",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Create/mutate document
                mutations = [
                    {
                        "create": {
                            "_type": doc_type,
                            "title": title,
                            "body": body,
                        }
                    }
                ]
                
                response = await client.post(
                    f"https://{project_id}.api.sanity.io/v1/data/mutate/{dataset}",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"mutations": mutations},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                doc_id = data["results"][0]["id"]
                logger.info(f"Created Sanity document: {doc_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "document_id": doc_id,
                        "title": title,
                        "status": "draft" if not publish else "published",
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Sanity API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Sanity API error: {str(e)}",
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

class WordPressTool(BaseTool):
    """Create/publish posts in WordPress"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Create or publish a post in WordPress
        
        Params:
        - title: string
        - content: string (HTML)
        - excerpt: string (optional)
        - status: string ("draft" or "publish", default: "draft")
        - categories: list[int] (optional, category IDs)
        - tags: list[str] (optional, tag names)
        """
        start = time.time()
        
        try:
            title = input_params.get("title", "Untitled")
            content = input_params.get("content", "")
            status = input_params.get("status", "draft")
            excerpt = input_params.get("excerpt", "")
            
            site_url = self.credentials.get("WORDPRESS_SITE_URL")
            api_token = self.credentials.get("WORDPRESS_REST_API_TOKEN")
            
            if not (site_url and api_token):
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing WordPress credentials",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Create post
                response = await client.post(
                    f"{site_url}/wp-json/wp/v2/posts",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "title": title,
                        "content": content,
                        "excerpt": excerpt,
                        "status": status,
                    },
                    timeout=30
                )
                response.raise_for_status()
                post = response.json()
                
                post_id = post["id"]
                logger.info(f"Created WordPress post: {post_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "post_id": post_id,
                        "title": title,
                        "status": status,
                        "post_url": post.get("link", ""),
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"WordPress API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"WordPress API error: {str(e)}",
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

class FramerUpdateTool(BaseTool):
    """Update Framer site content"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """
        Update Framer site content via API
        
        Params:
        - page_id: string
        - title: string (optional)
        - content: dict (page content object)
        """
        start = time.time()
        
        try:
            page_id = input_params.get("page_id")
            title = input_params.get("title", "")
            content = input_params.get("content", {})
            
            if not page_id:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="page_id is required",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            api_token = self.credentials.get("FRAMER_API_TOKEN")
            
            if not api_token:
                return ToolResult(
                    tool=self.tool_type,
                    success=False,
                    error="Missing Framer API token",
                    execution_time_ms=int((time.time() - start) * 1000)
                )
            
            async with httpx.AsyncClient() as client:
                # Update page
                response = await client.put(
                    f"https://api.framer.com/v1/pages/{page_id}",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "title": title,
                        "content": content,
                    },
                    timeout=30
                )
                response.raise_for_status()
                response.json()
                
                logger.info(f"Updated Framer page: {page_id}")
                
                return ToolResult(
                    tool=self.tool_type,
                    success=True,
                    data={
                        "page_id": page_id,
                        "title": title,
                        "status": "updated",
                    },
                    execution_time_ms=int((time.time() - start) * 1000)
                )
        
        except httpx.HTTPError as e:
            logger.error(f"Framer API error: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=f"Framer API error: {str(e)}",
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

# Register CMS tools
def register_cms_tools(tool_registry):
    """Register all CMS tools"""
    credentials = {
        "CONTENTFUL_SPACE_ID": os.getenv("CONTENTFUL_SPACE_ID", ""),
        "CONTENTFUL_PERSONAL_TOKEN": os.getenv("CONTENTFUL_PERSONAL_TOKEN", ""),
        "SANITY_PROJECT_ID": os.getenv("SANITY_PROJECT_ID", ""),
        "SANITY_API_TOKEN": os.getenv("SANITY_API_TOKEN", ""),
        "WORDPRESS_SITE_URL": os.getenv("WORDPRESS_SITE_URL", ""),
        "WORDPRESS_REST_API_TOKEN": os.getenv("WORDPRESS_REST_API_TOKEN", ""),
        "FRAMER_API_TOKEN": os.getenv("FRAMER_API_TOKEN", ""),
    }
    
    tool_registry.register(
        ToolType.CONTENTFUL_CREATE,
        ContentfulCreateTool(ToolType.CONTENTFUL_CREATE, credentials)
    )
    
    tool_registry.register(
        ToolType.CONTENTFUL_PUBLISH,
        ContentfulPublishTool(ToolType.CONTENTFUL_PUBLISH, credentials)
    )
    
    tool_registry.register(
        ToolType.SANITY_MUTATE,
        SanityMutateTool(ToolType.SANITY_MUTATE, credentials)
    )
    
    tool_registry.register(
        ToolType.WORDPRESS_POST,
        WordPressTool(ToolType.WORDPRESS_POST, credentials)
    )
    
    tool_registry.register(
        ToolType.FRAMER_UPDATE,
        FramerUpdateTool(ToolType.FRAMER_UPDATE, credentials)
    )
    
    logger.info("CMS tools registered")
