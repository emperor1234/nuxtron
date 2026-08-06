# pyright: reportUnusedFunction=false
"""
Media Library — Hootsuite Blueprint §4.3
ADDED: Centralised asset repository with folder organisation, AI tagging,
and search/filter capabilities. Used by Create/Compose workflow for attaching
approved media to scheduled posts.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

ASSET_NOT_FOUND = 'Media asset not found.'
FOLDER_NOT_FOUND = 'Folder not found.'

ASSET_TYPES = {'image', 'video', 'gif', 'pdf', 'audio'}

# ── Request models ──────────────────────────────────────────────────────────────

class FolderCreateRequest(BaseModel):
    """ADDED: Create a folder in the media library (supports nested folders)."""
    name: str = Field(min_length=1, max_length=120)
    parent_folder_id: int | None = Field(default=None, description='Parent folder ID for nested organisation.')
    description: str | None = Field(default=None, max_length=300)


class AssetRegisterRequest(BaseModel):
    """
    ADDED: Register a media asset in the library.
    In production this would accompany a multipart upload; here we accept the URL/path
    from the storage layer (e.g. the existing /storage/presign workflow).
    """
    filename: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=2, max_length=20, description='image | video | gif | pdf | audio')
    url: str = Field(min_length=5, max_length=2048, description='Public or signed URL to the asset.')
    size_bytes: int | None = Field(default=None, ge=0)
    folder_id: int | None = Field(default=None, description='Folder to place this asset in.')
    # ADDED: manual tags supplement AI-auto-generated tags
    tags: list[str] = Field(default_factory=list, max_length=30, description='Manual tags for searchability.')
    alt_text: str | None = Field(default=None, max_length=500, description='Accessibility alt text for images.')


class AssetUpdateRequest(BaseModel):
    """ADDED: Update metadata on an existing asset (tags, folder, alt text)."""
    folder_id: int | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    alt_text: str | None = Field(default=None, max_length=500)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _ai_tag_asset(filename: str, asset_type: str) -> list[str]:
    """
    ADDED: Simple deterministic AI-tagging stub.
    In production, this calls a vision model (e.g. Azure Computer Vision).
    Returns plausible auto-tags based on filename and type for the selftest to validate.
    """
    tags: list[str] = [f'auto:{asset_type}']
    stem = filename.lower().rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ')
    for word in stem.split():
        if len(word) >= 3:
            tags.append(f'auto:{word}')
    return tags[:8]  # cap at 8 auto-tags


# ── Router factory ──────────────────────────────────────────────────────────────

def create_media_library_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    assets_memory: list[dict[str, Any]],
    folders_memory: list[dict[str, Any]],
    tags_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the media library router.
    Assets and folders are tenant-scoped; no duplication of existing storage/presign routes.
    """
    router = APIRouter()
    _lock = threading.Lock()

    # ── Scoped helpers ──────────────────────────────────────────────────────────

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'media-library-router',
            })

    def _get_asset(tenant_id: str, asset_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (a for a in assets_memory if a.get('tenant_id') == tenant_id and a.get('id') == asset_id),
                None,
            )

    def _get_folder(tenant_id: str, folder_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (f for f in folders_memory if f.get('tenant_id') == tenant_id and f.get('id') == folder_id),
                None,
            )

    # ── Folder routes ───────────────────────────────────────────────────────────

    @router.post('/media/folders', responses={404: {'description': FOLDER_NOT_FOUND}})
    def create_folder(payload: FolderCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Create a folder for organising media assets."""
        enforce_rate_limit(f'{auth.tenant_id}:media:folders:create', 60, 60)
        if payload.parent_folder_id is not None:
            parent = _get_folder(auth.tenant_id, payload.parent_folder_id)
            if parent is None:
                raise HTTPException(status_code=404, detail=FOLDER_NOT_FOUND)

        with _lock:
            folder: dict[str, Any] = {
                'id': len(folders_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'parent_folder_id': payload.parent_folder_id,
                'description': payload.description,
                'created_at': datetime.now(UTC).isoformat(),
            }
            folders_memory.append(folder)

        _audit(auth.tenant_id, 'media_folder_created', folder['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'folder': folder.copy()}

    @router.get('/media/folders')
    def list_folders(auth: AuthDep) -> dict[str, Any]:
        """ADDED: List all media library folders for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:media:folders:list', 180, 60)
        with _lock:
            items = [f.copy() for f in folders_memory if f.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'folders': items}

    # ── Asset routes ────────────────────────────────────────────────────────────

    @router.post('/media/assets', responses={404: {'description': FOLDER_NOT_FOUND}})
    def register_asset(payload: AssetRegisterRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Register a media asset in the library after upload via /storage/presign.
        Automatically generates AI tags (stub — deterministic for testability).
        """
        enforce_rate_limit(f'{auth.tenant_id}:media:assets:create', 120, 60)
        safe_type = payload.asset_type.strip().lower()
        if safe_type not in ASSET_TYPES:
            safe_type = 'image'

        if payload.folder_id is not None:
            folder = _get_folder(auth.tenant_id, payload.folder_id)
            if folder is None:
                raise HTTPException(status_code=404, detail=FOLDER_NOT_FOUND)

        # ADDED: AI auto-tagging — deterministic stub for production parity
        auto_tags = _ai_tag_asset(payload.filename, safe_type)
        manual_tags = [t.strip().lower() for t in payload.tags if t.strip()]
        all_tags = list(dict.fromkeys(auto_tags + manual_tags))  # deduplicated, insertion order

        with _lock:
            asset: dict[str, Any] = {
                'id': len(assets_memory) + 1,
                'tenant_id': auth.tenant_id,
                'filename': payload.filename,
                'asset_type': safe_type,
                'url': payload.url,
                'size_bytes': payload.size_bytes,
                'folder_id': payload.folder_id,
                # ADDED: combined auto + manual tags for searchability
                'auto_tags': auto_tags,
                'manual_tags': manual_tags,
                'tags': all_tags,
                'alt_text': payload.alt_text,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            assets_memory.append(asset)
            # ADDED: persist tag index for cross-asset tag analytics
            for tag in all_tags:
                tags_memory.append({
                    'tenant_id': auth.tenant_id,
                    'asset_id': asset['id'],
                    'tag': tag,
                    'created_at': asset['created_at'],
                })

        _audit(auth.tenant_id, 'media_asset_registered', asset['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'asset': asset.copy()}

    @router.get('/media/assets')
    def list_assets(
        auth: AuthDep,
        asset_type: Annotated[str | None, Query(max_length=20)] = None,
        folder_id: Annotated[int | None, Query(ge=1)] = None,
        tag: Annotated[str | None, Query(max_length=80)] = None,
        search: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """
        ADDED: List/search media assets for this tenant.
        Supports filter by type, folder, tag, and filename substring search.
        """
        enforce_rate_limit(f'{auth.tenant_id}:media:assets:list', 240, 60)
        type_filter = asset_type.strip().lower() if asset_type else None
        tag_filter = tag.strip().lower() if tag else None
        search_lower = search.strip().lower() if search else None

        with _lock:
            items = [
                a.copy()
                for a in assets_memory
                if a.get('tenant_id') == auth.tenant_id
                and (type_filter is None or a.get('asset_type') == type_filter)
                and (folder_id is None or a.get('folder_id') == folder_id)
                and (tag_filter is None or tag_filter in [str(t).lower() for t in a.get('tags', [])])
                and (search_lower is None or search_lower in str(a.get('filename', '')).lower())
            ]
        items.sort(key=lambda a: str(a.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'assets': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.get('/media/assets/{asset_id}', responses={404: {'description': ASSET_NOT_FOUND}})
    def get_asset(asset_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Retrieve full metadata for a single media asset."""
        enforce_rate_limit(f'{auth.tenant_id}:media:assets:get', 300, 60)
        asset = _get_asset(auth.tenant_id, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail=ASSET_NOT_FOUND)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'asset': asset.copy()}

    @router.patch(
        '/media/assets/{asset_id}',
        responses={404: {'description': ASSET_NOT_FOUND}},
    )
    def update_asset(asset_id: int, payload: AssetUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Update folder assignment, tags, or alt text for an existing asset."""
        enforce_rate_limit(f'{auth.tenant_id}:media:assets:update', 120, 60)
        if payload.folder_id is not None:
            folder = _get_folder(auth.tenant_id, payload.folder_id)
            if folder is None:
                raise HTTPException(status_code=404, detail=FOLDER_NOT_FOUND)

        with _lock:
            asset = next(
                (a for a in assets_memory if a.get('tenant_id') == auth.tenant_id and a.get('id') == asset_id),
                None,
            )
            if asset is None:
                raise HTTPException(status_code=404, detail=ASSET_NOT_FOUND)

            if payload.folder_id is not None:
                asset['folder_id'] = payload.folder_id
            if payload.tags is not None:
                manual_tags = [t.strip().lower() for t in payload.tags if t.strip()]
                asset['manual_tags'] = manual_tags
                asset['tags'] = list(dict.fromkeys(list(asset.get('auto_tags', [])) + manual_tags))
            if payload.alt_text is not None:
                asset['alt_text'] = payload.alt_text
            asset['updated_at'] = datetime.now(UTC).isoformat()
            updated = asset.copy()

        _audit(auth.tenant_id, 'media_asset_updated', asset_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'asset': updated}

    @router.delete('/media/assets/{asset_id}', responses={404: {'description': ASSET_NOT_FOUND}})
    def delete_asset(asset_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Remove a media asset from the library."""
        enforce_rate_limit(f'{auth.tenant_id}:media:assets:delete', 60, 60)
        with _lock:
            idx = next(
                (
                    i for i, a in enumerate(assets_memory)
                    if a.get('tenant_id') == auth.tenant_id and a.get('id') == asset_id
                ),
                None,
            )
            if idx is None:
                raise HTTPException(status_code=404, detail=ASSET_NOT_FOUND)
            removed = assets_memory.pop(idx)

        _audit(auth.tenant_id, 'media_asset_deleted', asset_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'deleted': True, 'asset': removed}

    @router.get('/media/stats')
    def library_stats(auth: AuthDep) -> dict[str, Any]:
        """ADDED: Summary statistics for the tenant's media library."""
        enforce_rate_limit(f'{auth.tenant_id}:media:stats', 120, 60)
        with _lock:
            items = [a for a in assets_memory if a.get('tenant_id') == auth.tenant_id]
            folder_count = sum(1 for f in folders_memory if f.get('tenant_id') == auth.tenant_id)

        by_type: dict[str, int] = {}
        total_size = 0
        for asset in items:
            atype = str(asset.get('asset_type', 'unknown'))
            by_type[atype] = by_type.get(atype, 0) + 1
            total_size += int(asset.get('size_bytes') or 0)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'total_assets': len(items),
            'total_folders': folder_count,
            'total_size_bytes': total_size,
            'by_type': by_type,
        }

    return router
