import json
import os
from collections.abc import Callable
from datetime import datetime
from importlib import import_module
from typing import Any, cast

import httpx
import psycopg

# ---------------------------------------------------------------------------
# Supabase Vault resolver
# ---------------------------------------------------------------------------
# When SUPABASE_DB_URL or POSTGRES_HOST is configured, the memory system can
# look up sensitive credentials from Supabase's built-in encrypted secret
# store (vault.decrypted_secrets) instead of relying on plain env vars.
#
# To store a secret in Supabase Vault:
#   SELECT vault.create_secret('redis-password-value', 'IRA_REDIS_PASSWORD');
#
# Then set the corresponding IRA_VAULT_SECRET_* env var to that secret name:
#   IRA_VAULT_SECRET_REDIS_PASSWORD=IRA_REDIS_PASSWORD
#
# The resolver is called lazily and caches results per process lifetime so
# there is no extra DB round-trip on each request.
# ---------------------------------------------------------------------------

_vault_cache: dict[str, str] | None = None
_vault_cache_attempted = False


def _db_dsn_from_env() -> str:
    """Build a psycopg DSN from individual env vars (mirrors IRA router logic)."""
    direct = os.getenv('SUPABASE_DB_URL', '').strip()
    if direct:
        return direct
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nuxtron')
    user = os.getenv('POSTGRES_USER', 'nuxtron')
    password = os.getenv('POSTGRES_PASSWORD', '')
    return f'host={host} port={port} dbname={db_name} user={user} password={password} connect_timeout=2'


def _load_vault_secrets() -> dict[str, str]:
    """Fetch all decrypted secrets from vault.decrypted_secrets. Returns {} on failure."""
    global _vault_cache, _vault_cache_attempted  # noqa: PLW0603
    if _vault_cache_attempted:
        return _vault_cache or {}
    _vault_cache_attempted = True

    postgres_ready = bool(os.getenv('SUPABASE_DB_URL', '').strip() or os.getenv('POSTGRES_HOST', '').strip())
    if not postgres_ready:
        _vault_cache = {}
        return {}

    try:
        with psycopg.connect(_db_dsn_from_env()) as conn, conn.cursor() as cur:
            cur.execute("SELECT name, decrypted_secret FROM vault.decrypted_secrets")
            rows = cur.fetchall()
        _vault_cache = {str(name): str(secret) for name, secret in rows if name and secret}
    except Exception:
        _vault_cache = {}

    return _vault_cache


def _vault_get(env_key: str, vault_name_env: str, fallback: str = '') -> str:
    """
    Resolve a credential in priority order:
      1. Supabase Vault secret (named by IRA_VAULT_SECRET_<suffix>)
      2. Direct env var (env_key)
      3. fallback
    """
    vault_secret_name = os.getenv(vault_name_env, '').strip()
    if vault_secret_name:
        secrets = _load_vault_secrets()
        vault_value = secrets.get(vault_secret_name, '').strip()
        if vault_value:
            return vault_value
    return os.getenv(env_key, fallback).strip()


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return max(-1.0, min(1.0, round(sum(a * b for a, b in zip(left, right, strict=False)), 6)))


class IRAMemorySystem:
    def __init__(
        self,
        *,
        db_dsn_fn: Callable[[], str],
        now_iso_fn: Callable[[], str],
        short_term_store: list[dict[str, Any]],
        long_term_store: list[dict[str, Any]],
        structured_store: list[dict[str, Any]],
        embed_texts: Callable[[list[str]], tuple[str, list[list[float]]]],
    ) -> None:
        self._db_dsn_fn = db_dsn_fn
        self._now_iso_fn = now_iso_fn
        self._short_term_store = short_term_store
        self._long_term_store = long_term_store
        self._structured_store = structured_store
        self._embed_texts = embed_texts
        self._tables_ready = False

    def overview(self, tenant_id: str) -> dict[str, Any]:
        short_term = self.get_short_term_messages(tenant_id, limit=12)
        structured = self.list_structured_memory(tenant_id)
        long_term_documents = {
            str(item.get('document_id', '')).strip()
            for item in self._long_term_store
            if item.get('tenant_id') == tenant_id and str(item.get('document_id', '')).strip()
        }
        provider_status = self.provider_status()
        return {
            'providers': provider_status,
            'summary': {
                'short_term_messages': len(short_term),
                'long_term_documents': len(long_term_documents),
                'long_term_chunks': len([item for item in self._long_term_store if item.get('tenant_id') == tenant_id]),
                'structured_records': len(structured),
                'active_short_term_backend': provider_status['short_term']['active_backend'],
                'active_long_term_backend': provider_status['long_term']['active_backend'],
                'active_structured_backend': provider_status['structured']['active_backend'],
            },
            'recent_short_term': short_term,
            'structured_records': structured[-25:],
        }

    def provider_status(self) -> dict[str, Any]:
        redis_ready = self._redis_client() is not None
        postgres_ready = self._postgres_ready()
        pinecone_ready = bool(os.getenv('PINECONE_API_KEY', '').strip() and os.getenv('PINECONE_INDEX_HOST', '').strip())
        weaviate_ready = bool(os.getenv('WEAVIATE_URL', '').strip())

        if postgres_ready:
            long_term_backend = 'supabase_postgres'
        elif pinecone_ready:
            long_term_backend = 'pinecone'
        elif weaviate_ready:
            long_term_backend = 'weaviate'
        else:
            long_term_backend = 'in_memory'

        return {
            'short_term': {
                'active_backend': 'redis' if redis_ready else 'in_memory',
                'redis_configured': redis_ready,
            },
            'long_term': {
                'active_backend': long_term_backend,
                'supabase_postgres_ready': postgres_ready,
                'pinecone_ready': pinecone_ready,
                'weaviate_ready': weaviate_ready,
            },
            'structured': {
                'active_backend': 'supabase_postgres' if postgres_ready else 'in_memory',
                'supabase_postgres_ready': postgres_ready,
            },
        }

    def append_short_term_message(
        self,
        *,
        tenant_id: str,
        role: str,
        channel: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            'id': len(self._short_term_store) + 1,
            'tenant_id': tenant_id,
            'role': role,
            'channel': channel,
            'content': content,
            'context': context or {},
            'created_at': self._now_iso_fn(),
        }
        self._short_term_store.append(record)
        self._trim_short_term_store()

        client = self._redis_client()
        if client is not None:
            try:
                payload = json.dumps(record)
                key = self._redis_key(tenant_id)
                client.lpush(key, payload)
                client.ltrim(key, 0, self._short_term_limit() - 1)
                record['source'] = 'redis'
            except Exception:
                record['source'] = 'in_memory'
        else:
            record['source'] = 'in_memory'
        return record

    def get_short_term_messages(self, tenant_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        client = self._redis_client()
        if client is not None:
            try:
                rows = client.lrange(self._redis_key(tenant_id), 0, max(0, limit - 1))
                items: list[dict[str, Any]] = []
                for row in rows:
                    decoded = row.decode('utf-8') if isinstance(row, bytes) else str(row)
                    payload = json.loads(decoded)
                    if isinstance(payload, dict):
                        payload_map = cast(dict[str, Any], payload)
                        items.append({str(key): value for key, value in payload_map.items()})
                items.reverse()
                if items:
                    return items[-limit:]
            except Exception:
                pass

        items = [item for item in self._short_term_store if item.get('tenant_id') == tenant_id]
        return items[-limit:]

    def upsert_structured_memory(
        self,
        *,
        tenant_id: str,
        memory_type: str,
        memory_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now_iso = self._now_iso_fn()
        record: dict[str, Any] = {
            'tenant_id': tenant_id,
            'memory_type': memory_type,
            'memory_key': memory_key,
            'payload': payload,
            'updated_at': now_iso,
        }

        existing = next(
            (
                item for item in self._structured_store
                if item.get('tenant_id') == tenant_id and item.get('memory_type') == memory_type and item.get('memory_key') == memory_key
            ),
            None,
        )
        if existing is not None:
            existing.update(record)
            stored = existing
        else:
            stored: dict[str, Any] = {'id': len(self._structured_store) + 1, **record}
            self._structured_store.append(stored)

        if self._postgres_ready():
            self._ensure_tables()
            try:
                with psycopg.connect(self._db_dsn_fn()) as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ira_structured_memory (tenant_id, memory_type, memory_key, payload, updated_at)
                        VALUES (%s, %s, %s, %s::jsonb, NOW())
                        ON CONFLICT (tenant_id, memory_type, memory_key)
                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                        """,
                        (tenant_id, memory_type, memory_key, json.dumps(payload)),
                    )
                    conn.commit()
                stored['source'] = 'supabase_postgres'
            except Exception:
                stored['source'] = 'in_memory'
        else:
            stored['source'] = 'in_memory'
        return stored

    def list_structured_memory(self, tenant_id: str, *, memory_type: str | None = None) -> list[dict[str, Any]]:
        if self._postgres_ready():
            self._ensure_tables()
            try:
                query = """
                    SELECT memory_type, memory_key, payload, updated_at
                    FROM ira_structured_memory
                    WHERE tenant_id = %s
                """
                params: list[Any] = [tenant_id]
                if memory_type:
                    query += ' AND memory_type = %s'
                    params.append(memory_type)
                query += ' ORDER BY updated_at ASC'
                with psycopg.connect(self._db_dsn_fn()) as conn, conn.cursor() as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()
                return [
                    {
                        'tenant_id': tenant_id,
                        'memory_type': str(memory_type_value),
                        'memory_key': str(memory_key_value),
                        'payload': payload_value if isinstance(payload_value, dict) else {},
                        'updated_at': updated_at.isoformat() if isinstance(updated_at, datetime) else '',
                        'source': 'supabase_postgres',
                    }
                    for memory_type_value, memory_key_value, payload_value, updated_at in rows
                ]
            except Exception:
                pass

        return [
            item.copy()
            for item in self._structured_store
            if item.get('tenant_id') == tenant_id and (memory_type is None or item.get('memory_type') == memory_type)
        ]

    def sync_long_term_memory(self, *, tenant_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        synced_count = 0
        provider = 'in_memory'

        if self._postgres_ready():
            provider = 'supabase_postgres'
            self._ensure_tables()
            try:
                with psycopg.connect(self._db_dsn_fn()) as conn, conn.cursor() as cur:
                    for item in records:
                        cur.execute(
                            """
                            INSERT INTO ira_vector_memory (
                                tenant_id, memory_id, namespace, title, source, embedding_backend, embedding, content, metadata, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, NOW())
                            ON CONFLICT (tenant_id, memory_id)
                            DO UPDATE SET
                                namespace = EXCLUDED.namespace,
                                title = EXCLUDED.title,
                                source = EXCLUDED.source,
                                embedding_backend = EXCLUDED.embedding_backend,
                                embedding = EXCLUDED.embedding,
                                content = EXCLUDED.content,
                                metadata = EXCLUDED.metadata,
                                updated_at = NOW()
                            """,
                            (
                                tenant_id,
                                str(item.get('chunk_id', item.get('document_id', ''))),
                                str(item.get('namespace', 'ira_knowledge')),
                                str(item.get('title', '')),
                                str(item.get('source', '')),
                                str(item.get('embedding_backend', 'local_hash')),
                                json.dumps(item.get('embedding', [])),
                                str(item.get('content', '')),
                                json.dumps(item.get('metadata', {})),
                            ),
                        )
                        synced_count += 1
                    conn.commit()
            except Exception:
                provider = 'in_memory'

        if provider == 'in_memory' and self._pinecone_ready():
            synced_count = self._sync_pinecone(tenant_id=tenant_id, records=records)
            if synced_count:
                provider = 'pinecone'

        if provider == 'in_memory' and self._weaviate_ready():
            synced_count = self._sync_weaviate(tenant_id=tenant_id, records=records)
            if synced_count:
                provider = 'weaviate'

        return {'provider': provider, 'synced_count': synced_count}

    def query_long_term_memory(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int,
        min_score: float,
        fallback_items: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        if self._postgres_ready():
            results = self._query_supabase_postgres(tenant_id=tenant_id, query=query, top_k=top_k, min_score=min_score)
            if results:
                return 'supabase_postgres', results

        results = self._query_fallback(query=query, top_k=top_k, min_score=min_score, items=fallback_items)
        return 'in_memory', results

    def _query_fallback(self, *, query: str, top_k: int, min_score: float, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        _, query_vectors = self._embed_texts([query])
        query_vector = query_vectors[0] if query_vectors else []
        ranked: list[dict[str, Any]] = []
        for item in items:
            embedding = cast(list[float], item.get('embedding', [])) if isinstance(item.get('embedding'), list) else []
            score = _cosine_similarity(query_vector, embedding)
            if score < min_score:
                continue
            ranked.append({
                'document_id': item.get('document_id', ''),
                'chunk_id': item.get('chunk_id', ''),
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'content': item.get('content', ''),
                'score': round(score, 4),
                'provider': 'in_memory',
            })
        ranked.sort(key=lambda item: (-float(item.get('score', 0.0)), str(item.get('chunk_id', ''))))
        return ranked[:top_k]

    def _query_supabase_postgres(self, *, tenant_id: str, query: str, top_k: int, min_score: float) -> list[dict[str, Any]]:
        self._ensure_tables()
        _, query_vectors = self._embed_texts([query])
        query_vector = query_vectors[0] if query_vectors else []
        try:
            with psycopg.connect(self._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT memory_id, title, source, content, embedding, metadata
                    FROM ira_vector_memory
                    WHERE tenant_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """,
                    (tenant_id,),
                )
                rows = cur.fetchall()
        except Exception:
            return []

        ranked: list[dict[str, Any]] = []
        for memory_id, title, source, content, embedding, metadata in rows:
            vector = [float(entry) for entry in embedding] if isinstance(embedding, list) else []
            score = _cosine_similarity(query_vector, vector)
            if score < min_score:
                continue
            metadata_map = cast(dict[str, Any], metadata) if isinstance(metadata, dict) else {}
            ranked.append({
                'document_id': str(metadata_map.get('document_id', memory_id)),
                'chunk_id': str(memory_id),
                'title': str(title or ''),
                'source': str(source or ''),
                'content': str(content or ''),
                'score': round(score, 4),
                'provider': 'supabase_postgres',
            })
        ranked.sort(key=lambda item: (-float(item.get('score', 0.0)), str(item.get('chunk_id', ''))))
        return ranked[:top_k]

    def _redis_client(self) -> Any | None:
        # Prefer Supabase Vault secret; fall back to env var
        host = _vault_get('REDIS_HOST', 'IRA_VAULT_SECRET_REDIS_HOST')
        if not host:
            return None
        try:
            redis_module = import_module('redis')

            port = int(os.getenv('REDIS_PORT', '6379'))
            password = _vault_get('REDIS_PASSWORD', 'IRA_VAULT_SECRET_REDIS_PASSWORD') or None
            db_index = int(os.getenv('REDIS_DB', '0'))
            redis_class = redis_module.Redis
            return redis_class(host=host, port=port, password=password, db=db_index, socket_timeout=1.5)
        except Exception:
            return None

    def _redis_key(self, tenant_id: str) -> str:
        prefix = os.getenv('IRA_MEMORY_REDIS_PREFIX', 'ira:memory')
        return f'{prefix}:{tenant_id}:short_term'

    def _short_term_limit(self) -> int:
        return max(10, int(os.getenv('IRA_SHORT_TERM_MEMORY_LIMIT', '40')))

    def _trim_short_term_store(self) -> None:
        limit = self._short_term_limit()
        if len(self._short_term_store) > limit * 10:
            del self._short_term_store[:-limit * 10]

    def _postgres_ready(self) -> bool:
        return bool(os.getenv('SUPABASE_DB_URL', '').strip() or os.getenv('POSTGRES_HOST', '').strip())

    def _ensure_tables(self) -> None:
        if self._tables_ready or not self._postgres_ready():
            return
        try:
            with psycopg.connect(self._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ira_structured_memory (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        memory_key TEXT NOT NULL,
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (tenant_id, memory_type, memory_key)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ira_vector_memory (
                        id BIGSERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        memory_id TEXT NOT NULL,
                        namespace TEXT NOT NULL DEFAULT 'ira_knowledge',
                        title TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT '',
                        embedding_backend TEXT NOT NULL DEFAULT 'local_hash',
                        embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
                        content TEXT NOT NULL DEFAULT '',
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (tenant_id, memory_id)
                    )
                    """
                )
                conn.commit()
            self._tables_ready = True
        except Exception:
            self._tables_ready = False

    def _pinecone_ready(self) -> bool:
        return bool(
            _vault_get('PINECONE_API_KEY', 'IRA_VAULT_SECRET_PINECONE_API_KEY')
            and os.getenv('PINECONE_INDEX_HOST', '').strip()
        )

    def _sync_pinecone(self, *, tenant_id: str, records: list[dict[str, Any]]) -> int:
        api_key = _vault_get('PINECONE_API_KEY', 'IRA_VAULT_SECRET_PINECONE_API_KEY')
        index_host = os.getenv('PINECONE_INDEX_HOST', '').strip().rstrip('/')
        namespace = os.getenv('PINECONE_NAMESPACE', 'ira-memory').strip() or 'ira-memory'
        if not (api_key and index_host):
            return 0
        vectors: list[dict[str, Any]] = []
        for item in records:
            vectors.append({
                'id': f"{tenant_id}:{str(item.get('chunk_id', item.get('document_id', '')))}",
                'values': item.get('embedding', []),
                'metadata': {
                    'tenant_id': tenant_id,
                    'title': str(item.get('title', '')),
                    'source': str(item.get('source', '')),
                    'content': str(item.get('content', '')),
                    'document_id': str(item.get('document_id', '')),
                },
            })
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f'https://{index_host}/vectors/upsert',
                    headers={'Api-Key': api_key, 'Content-Type': 'application/json'},
                    json={'namespace': namespace, 'vectors': vectors},
                )
            return len(vectors) if response.is_success else 0
        except Exception:
            return 0

    def _weaviate_ready(self) -> bool:
        return bool(os.getenv('WEAVIATE_URL', '').strip())

    def _sync_weaviate(self, *, tenant_id: str, records: list[dict[str, Any]]) -> int:
        base_url = os.getenv('WEAVIATE_URL', '').strip().rstrip('/')
        api_key = _vault_get('WEAVIATE_API_KEY', 'IRA_VAULT_SECRET_WEAVIATE_API_KEY')
        class_name = os.getenv('WEAVIATE_CLASS_NAME', 'IraMemoryChunk').strip() or 'IraMemoryChunk'
        if not base_url:
            return 0
        objects: list[dict[str, Any]] = []
        for item in records:
            objects.append({
                'class': class_name,
                'id': f"{tenant_id}-{str(item.get('chunk_id', item.get('document_id', '')))}",
                'properties': {
                    'tenantId': tenant_id,
                    'documentId': str(item.get('document_id', '')),
                    'title': str(item.get('title', '')),
                    'source': str(item.get('source', '')),
                    'content': str(item.get('content', '')),
                },
                'vector': item.get('embedding', []),
            })
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f'{base_url}/v1/batch/objects', headers=headers, json={'objects': objects})
            return len(objects) if response.is_success else 0
        except Exception:
            return 0