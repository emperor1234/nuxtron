# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Knowledge Base (HubSpot Service Hub §6.2)
NEW: Help center articles, categories, search, view tracking, customer portal.
AI article suggestions from tickets; feedback ratings per article.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

ARTICLE_NOT_FOUND = 'Knowledge base article not found.'
CATEGORY_NOT_FOUND = 'Knowledge base category not found.'
ARTICLE_STATUSES = {'draft', 'published', 'archived'}


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    parent_category_id: int | None = None
    icon: str = Field(default='', max_length=100)
    sort_order: int = Field(default=0, ge=0)


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=100000)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default='draft', max_length=20)
    seo_title: str = Field(default='', max_length=300)
    seo_description: str = Field(default='', max_length=500)
    featured: bool = False


class ArticleUpdateRequest(BaseModel):
    title: str = Field(default='', max_length=300)
    body: str = Field(default='', max_length=100000)
    category_id: int | None = None
    tags: list[str] | None = None
    status: str = Field(default='', max_length=20)
    seo_title: str = Field(default='', max_length=300)
    seo_description: str = Field(default='', max_length=500)
    featured: bool | None = None


class ArticleFeedbackRequest(BaseModel):
    helpful: bool
    comment: str = Field(default='', max_length=1000)


def create_knowledge_base_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    kb_categories_memory: list[dict[str, Any]],
    kb_articles_memory: list[dict[str, Any]],
    kb_feedback_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Knowledge base router — HubSpot Service Hub §6.2."""
    router = APIRouter()
    _lock = threading.Lock()

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'knowledge-base-router',
            })

    # ── Categories ────────────────────────────────────────────────────────────

    @router.post('/kb/categories', summary='Create KB category')
    def create_category(payload: CategoryCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a knowledge base category."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:create-category', 60, 60)
        with _lock:
            cat = {
                'id': len(kb_categories_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'parent_category_id': payload.parent_category_id,
                'icon': payload.icon,
                'sort_order': payload.sort_order,
                'article_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
            }
            kb_categories_memory.append(cat)
        _append_audit(auth.tenant_id, 'kb_category_created', cat['id'])
        return {'status': 'ok', 'category': cat}

    @router.get('/kb/categories', summary='List KB categories')
    def list_categories(auth: AuthDep) -> dict[str, Any]:
        """NEW: List all knowledge base categories."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:list-categories', 120, 60)
        with _lock:
            cats = [c.copy() for c in kb_categories_memory if c.get('tenant_id') == auth.tenant_id]
        cats.sort(key=lambda x: (int(x.get('sort_order', 0)), str(x.get('name', ''))))
        return {'status': 'ok', 'categories': cats, 'total': len(cats)}

    # ── Articles ──────────────────────────────────────────────────────────────

    @router.post('/kb/articles', summary='Create KB article')
    def create_article(payload: ArticleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a knowledge base article."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:create-article', 60, 60)
        status = payload.status.strip().lower()
        if status not in ARTICLE_STATUSES:
            status = 'draft'
        with _lock:
            article = {
                'id': len(kb_articles_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'body': payload.body,
                'category_id': payload.category_id,
                'tags': payload.tags,
                'status': status,
                'seo_title': payload.seo_title or payload.title,
                'seo_description': payload.seo_description,
                'featured': payload.featured,
                'view_count': 0,
                'helpful_count': 0,
                'not_helpful_count': 0,
                'published_at': datetime.now(UTC).isoformat() if status == 'published' else None,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            kb_articles_memory.append(article)
            # Update category article count
            if payload.category_id:
                for cat in kb_categories_memory:
                    if cat.get('id') == payload.category_id and cat.get('tenant_id') == auth.tenant_id:
                        cat['article_count'] = cat.get('article_count', 0) + 1
                        break
        _append_audit(auth.tenant_id, 'kb_article_created', article['id'])
        return {'status': 'ok', 'article': article}

    @router.get('/kb/articles', summary='List KB articles')
    def list_articles(
        auth: AuthDep,
        category_id: Annotated[int | None, Query(ge=1)] = None,
        status: Annotated[str | None, Query(max_length=20)] = None,
        featured: Annotated[bool | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List KB articles with optional filters."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:list-articles', 120, 60)
        with _lock:
            items = [a.copy() for a in kb_articles_memory if a.get('tenant_id') == auth.tenant_id]
        if category_id is not None:
            items = [a for a in items if a.get('category_id') == category_id]
        if status:
            items = [a for a in items if a.get('status') == status]
        if featured is not None:
            items = [a for a in items if bool(a.get('featured')) == featured]
        items.sort(key=lambda x: int(x.get('view_count', 0)), reverse=True)
        return {'status': 'ok', 'articles': items[offset:offset + limit], 'total': len(items)}

    @router.get('/kb/articles/{article_id}', responses={404: {'description': ARTICLE_NOT_FOUND}})
    def get_article(article_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single article (increments view count)."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:get-article', 300, 60)
        with _lock:
            article = next((a for a in kb_articles_memory
                            if a.get('id') == article_id and a.get('tenant_id') == auth.tenant_id), None)
            if article is None:
                raise HTTPException(status_code=404, detail=ARTICLE_NOT_FOUND)
            article['view_count'] = article.get('view_count', 0) + 1
        return {'status': 'ok', 'article': article.copy()}

    @router.patch('/kb/articles/{article_id}', responses={404: {'description': ARTICLE_NOT_FOUND}})
    def update_article(article_id: int, payload: ArticleUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Update an existing KB article."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:update-article', 60, 60)
        with _lock:
            article = next((a for a in kb_articles_memory
                            if a.get('id') == article_id and a.get('tenant_id') == auth.tenant_id), None)
            if article is None:
                raise HTTPException(status_code=404, detail=ARTICLE_NOT_FOUND)
            if payload.title:
                article['title'] = payload.title
            if payload.body:
                article['body'] = payload.body
            if payload.category_id is not None:
                article['category_id'] = payload.category_id
            if payload.tags is not None:
                article['tags'] = payload.tags
            if payload.status and payload.status in ARTICLE_STATUSES:
                if payload.status == 'published' and article.get('status') != 'published':
                    article['published_at'] = datetime.now(UTC).isoformat()
                article['status'] = payload.status
            if payload.seo_title:
                article['seo_title'] = payload.seo_title
            if payload.seo_description:
                article['seo_description'] = payload.seo_description
            if payload.featured is not None:
                article['featured'] = payload.featured
            article['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'kb_article_updated', article_id)
        return {'status': 'ok', 'article': article.copy()}

    @router.delete('/kb/articles/{article_id}', responses={404: {'description': ARTICLE_NOT_FOUND}})
    def delete_article(article_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Delete a KB article."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:delete-article', 30, 60)
        with _lock:
            idx = next((i for i, a in enumerate(kb_articles_memory)
                        if a.get('id') == article_id and a.get('tenant_id') == auth.tenant_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail=ARTICLE_NOT_FOUND)
            removed = kb_articles_memory.pop(idx)
        _append_audit(auth.tenant_id, 'kb_article_deleted', article_id)
        return {'status': 'ok', 'deleted': True, 'article': removed}

    @router.post('/kb/articles/{article_id}/feedback', responses={404: {'description': ARTICLE_NOT_FOUND}})
    def submit_feedback(article_id: int, payload: ArticleFeedbackRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Submit helpful/not-helpful feedback on an article."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:feedback', 30, 60)
        with _lock:
            article = next((a for a in kb_articles_memory
                            if a.get('id') == article_id and a.get('tenant_id') == auth.tenant_id), None)
            if article is None:
                raise HTTPException(status_code=404, detail=ARTICLE_NOT_FOUND)
            fb = {
                'id': len(kb_feedback_memory) + 1,
                'tenant_id': auth.tenant_id,
                'article_id': article_id,
                'helpful': payload.helpful,
                'comment': payload.comment,
                'created_at': datetime.now(UTC).isoformat(),
            }
            kb_feedback_memory.append(fb)
            if payload.helpful:
                article['helpful_count'] = article.get('helpful_count', 0) + 1
            else:
                article['not_helpful_count'] = article.get('not_helpful_count', 0) + 1
        return {'status': 'ok', 'feedback': fb}

    @router.get('/kb/search', summary='Search KB articles')
    def search_articles(
        auth: AuthDep,
        q: Annotated[str, Query(min_length=1, max_length=200)],
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> dict[str, Any]:
        """NEW: Full-text search across KB articles (body + title + tags)."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:search', 120, 60)
        q_lower = q.lower()
        with _lock:
            published = [a.copy() for a in kb_articles_memory
                         if a.get('tenant_id') == auth.tenant_id and a.get('status') == 'published']
        results = [
            a for a in published
            if q_lower in str(a.get('title', '')).lower()
            or q_lower in str(a.get('body', '')).lower()
            or any(q_lower in str(tag).lower() for tag in a.get('tags', []))
        ]
        return {'status': 'ok', 'results': results[:limit], 'total': len(results), 'query': q}

    @router.get('/kb/analytics/summary', summary='KB analytics')
    def kb_analytics(auth: AuthDep) -> dict[str, Any]:
        """NEW: Knowledge base analytics — top articles, helpfulness rate."""
        enforce_rate_limit(f'{auth.tenant_id}:kb:analytics', 60, 60)
        with _lock:
            articles = [a for a in kb_articles_memory if a.get('tenant_id') == auth.tenant_id]
        published = [a for a in articles if a.get('status') == 'published']
        total_views = sum(int(a.get('view_count', 0)) for a in published)
        total_helpful = sum(int(a.get('helpful_count', 0)) for a in published)
        total_not_helpful = sum(int(a.get('not_helpful_count', 0)) for a in published)
        total_feedback = total_helpful + total_not_helpful
        top_articles = sorted(published, key=lambda x: int(x.get('view_count', 0)), reverse=True)[:10]
        return {
            'status': 'ok',
            'total_articles': len(articles),
            'published_articles': len(published),
            'total_views': total_views,
            'helpfulness_rate': round(total_helpful / total_feedback * 100, 1) if total_feedback else None,
            'top_articles': [{'id': a['id'], 'title': a['title'], 'views': a['view_count']} for a in top_articles],
        }

    return router
