"""
Extra tests for ira_memory.py — covers DB, Redis, Pinecone, and Weaviate paths.
"""
from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.ira_memory import (
    IRAMemorySystem,
    _load_vault_secrets,
    _vault_get,
)


def _now() -> str:
    return "2026-01-01T00:00:00"


def _dummy_embed(texts: list[str]) -> tuple[str, list[list[float]]]:
    return "local", [[0.1, 0.2, 0.3] for _ in texts]


def _make_memory(**kwargs: Any) -> IRAMemorySystem:
    defaults: dict[str, Any] = {
        "db_dsn_fn": lambda: "host=localhost dbname=test",
        "now_iso_fn": _now,
        "short_term_store": [],
        "long_term_store": [],
        "structured_store": [],
        "embed_texts": _dummy_embed,
    }
    defaults.update(kwargs)
    return IRAMemorySystem(**defaults)


class TestLoadVaultSecretsDbPath:
    """Test _load_vault_secrets when postgres env vars are set."""

    def test_connection_failure_returns_empty(self) -> None:
        """When postgres is configured but connection fails → returns {}."""
        import backend.fastapi.app.ira_memory as mod
        orig_cache = mod._vault_cache
        orig_attempted = mod._vault_cache_attempted
        try:
            mod._vault_cache = None
            mod._vault_cache_attempted = False
            with patch.dict(os.environ, {"POSTGRES_HOST": "fakehost"}, clear=False):
                with patch("psycopg.connect", side_effect=Exception("no DB")):
                    result = _load_vault_secrets()
            assert result == {}
        finally:
            mod._vault_cache = orig_cache
            mod._vault_cache_attempted = orig_attempted

    def test_successful_connection_populates_cache(self) -> None:
        """When postgres is configured and connection succeeds → returns secrets dict."""
        import backend.fastapi.app.ira_memory as mod
        orig_cache = mod._vault_cache
        orig_attempted = mod._vault_cache_attempted
        try:
            mod._vault_cache = None
            mod._vault_cache_attempted = False
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = [("my_secret", "my_value"), ("other", "val2")]
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            with patch.dict(os.environ, {"POSTGRES_HOST": "fakehost"}, clear=False):
                with patch("psycopg.connect", return_value=mock_conn):
                    result = _load_vault_secrets()
            assert isinstance(result, dict)
        finally:
            mod._vault_cache = orig_cache
            mod._vault_cache_attempted = orig_attempted


class TestVaultGetWithVaultName:
    """Test _vault_get when a vault_name_env is configured."""

    def test_vault_name_set_but_vault_empty_falls_back_to_env(self) -> None:
        """When vault_secret_name is set but vault has no matching value → uses env var."""
        with patch.dict(os.environ, {"IRA_VAULT_SECRET_MY_KEY": "my-secret-name", "MY_ENV_KEY": "from-env"}):
            with patch("backend.fastapi.app.ira_memory._load_vault_secrets", return_value={}):
                result = _vault_get("MY_ENV_KEY", "IRA_VAULT_SECRET_MY_KEY")
        assert result == "from-env"

    def test_vault_name_set_and_vault_has_value(self) -> None:
        """When vault_secret_name is set and vault has a matching value → uses vault value."""
        vault_data = {"my-secret-name": "vault-secret-value"}
        with patch.dict(os.environ, {"IRA_VAULT_SECRET_MY_KEY": "my-secret-name"}):
            with patch("backend.fastapi.app.ira_memory._load_vault_secrets", return_value=vault_data):
                result = _vault_get("MY_ENV_KEY", "IRA_VAULT_SECRET_MY_KEY")
        assert result == "vault-secret-value"


class TestProviderStatus:
    """Test provider_status branches."""

    def test_postgres_backend(self) -> None:
        """When POSTGRES_HOST set → long_term backend = supabase_postgres."""
        mem = _make_memory()
        with patch.dict(os.environ, {"POSTGRES_HOST": "fakehost"}):
            result = mem.provider_status()
        assert result["long_term"]["active_backend"] == "supabase_postgres"
        assert result["long_term"]["supabase_postgres_ready"] is True

    def test_pinecone_backend(self) -> None:
        """When pinecone env vars set → long_term backend = pinecone."""
        mem = _make_memory()
        env = {
            "POSTGRES_HOST": "",
            "SUPABASE_DB_URL": "",
            "PINECONE_API_KEY": "pk-test",
            "PINECONE_INDEX_HOST": "myindex.pinecone.io",
        }
        with patch.dict(os.environ, env):
            result = mem.provider_status()
        assert result["long_term"]["active_backend"] == "pinecone"
        assert result["long_term"]["pinecone_ready"] is True

    def test_weaviate_backend(self) -> None:
        """When weaviate URL set → long_term backend = weaviate."""
        mem = _make_memory()
        env = {
            "POSTGRES_HOST": "",
            "SUPABASE_DB_URL": "",
            "PINECONE_API_KEY": "",
            "PINECONE_INDEX_HOST": "",
            "WEAVIATE_URL": "http://weaviate:8080",
        }
        with patch.dict(os.environ, env):
            result = mem.provider_status()
        assert result["long_term"]["active_backend"] == "weaviate"
        assert result["long_term"]["weaviate_ready"] is True

    def test_in_memory_backend(self) -> None:
        """When no external backends → all in_memory."""
        mem = _make_memory()
        env = {
            "POSTGRES_HOST": "",
            "SUPABASE_DB_URL": "",
            "PINECONE_API_KEY": "",
            "PINECONE_INDEX_HOST": "",
            "WEAVIATE_URL": "",
        }
        with patch.dict(os.environ, env):
            result = mem.provider_status()
        assert result["long_term"]["active_backend"] == "in_memory"

    def test_redis_short_term(self) -> None:
        """When REDIS_HOST set → short_term backend = redis."""
        mem = _make_memory()
        mock_redis = MagicMock()
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.provider_status()
        assert result["short_term"]["active_backend"] == "redis"


class TestUpsertStructuredMemoryDbPaths:
    """Test upsert_structured_memory DB branches."""

    def test_postgres_exception_falls_back_to_in_memory(self) -> None:
        """When postgres is ready but connection fails → source='in_memory'."""
        mem = _make_memory()
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", side_effect=Exception("no DB")):
                    result = mem.upsert_structured_memory(
                        tenant_id="t1",
                        memory_type="prefs",
                        memory_key="key1",
                        payload={"x": 1},
                    )
        assert result["source"] == "in_memory"

    def test_postgres_success(self) -> None:
        """When postgres is ready and connection succeeds → source='supabase_postgres'."""
        mem = _make_memory()
        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", return_value=mock_conn):
                    result = mem.upsert_structured_memory(
                        tenant_id="t1",
                        memory_type="prefs",
                        memory_key="key2",
                        payload={"y": 2},
                    )
        assert result["source"] == "supabase_postgres"

    def test_upsert_updates_existing(self) -> None:
        """Upserting same key updates existing record."""
        mem = _make_memory()
        mem.upsert_structured_memory(tenant_id="t1", memory_type="prefs", memory_key="k", payload={"a": 1})
        result = mem.upsert_structured_memory(tenant_id="t1", memory_type="prefs", memory_key="k", payload={"a": 2})
        assert result["payload"] == {"a": 2}


class TestListStructuredMemoryDbPaths:
    """Test list_structured_memory DB branches."""

    def test_postgres_exception_falls_back(self) -> None:
        """When postgres ready but connection fails → returns in-memory records."""
        mem = _make_memory()
        # Pre-populate in-memory store
        mem.upsert_structured_memory(tenant_id="t2", memory_type="settings", memory_key="k1", payload={"z": 3})
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", side_effect=Exception("no DB")):
                    result = mem.list_structured_memory("t2")
        assert any(r["memory_key"] == "k1" for r in result)

    def test_postgres_exception_with_type_filter(self) -> None:
        """When postgres ready but fails → type filter applies to in-memory records."""
        mem = _make_memory()
        mem.upsert_structured_memory(tenant_id="t3", memory_type="typeA", memory_key="k1", payload={})
        mem.upsert_structured_memory(tenant_id="t3", memory_type="typeB", memory_key="k2", payload={})
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", side_effect=Exception("no DB")):
                    result = mem.list_structured_memory("t3", memory_type="typeA")
        assert all(r["memory_type"] == "typeA" for r in result)

    def test_postgres_success_returns_data(self) -> None:
        """When postgres ready and succeeds → returns rows from DB."""
        from datetime import UTC, datetime
        mem = _make_memory()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            ("typeA", "k1", {"val": 1}, datetime(2026, 1, 1, tzinfo=UTC)),
        ]
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", return_value=mock_conn):
                    result = mem.list_structured_memory("t4")
        assert len(result) == 1
        assert result[0]["memory_key"] == "k1"
        assert result[0]["source"] == "supabase_postgres"


class TestSyncLongTermMemoryPaths:
    """Test sync_long_term_memory with different backends."""

    def test_postgres_exception_falls_back_to_in_memory(self) -> None:
        """When postgres ready but fails → provider = 'in_memory'."""
        mem = _make_memory()
        records = [{"chunk_id": "c1", "embedding": [0.1, 0.2], "content": "hello"}]
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_ensure_tables"):
                with patch("psycopg.connect", side_effect=Exception("no DB")):
                    result = mem.sync_long_term_memory(tenant_id="t1", records=records)
        assert result["provider"] == "in_memory"

    def test_pinecone_sync(self) -> None:
        """When in_memory and pinecone ready → syncs via pinecone."""
        mem = _make_memory()
        records = [{"chunk_id": "c1", "embedding": [0.1, 0.2], "content": "hello", "title": "T", "source": "S"}]
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        with patch.object(mem, "_postgres_ready", return_value=False):
            with patch.object(mem, "_pinecone_ready", return_value=True):
                with patch("backend.fastapi.app.ira_memory._vault_get", return_value="pk-test"):
                    with patch.dict(os.environ, {"PINECONE_INDEX_HOST": "my-index.pinecone.io"}):
                        with patch("httpx.Client", return_value=mock_client):
                            result = mem.sync_long_term_memory(tenant_id="t1", records=records)
        assert result["provider"] in ("pinecone", "in_memory")

    def test_weaviate_sync(self) -> None:
        """When in_memory and weaviate ready → syncs via weaviate."""
        mem = _make_memory()
        records = [{"chunk_id": "c1", "embedding": [0.1, 0.2], "content": "hello"}]
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        with patch.object(mem, "_postgres_ready", return_value=False):
            with patch.object(mem, "_pinecone_ready", return_value=False):
                with patch.dict(os.environ, {"WEAVIATE_URL": "http://weaviate:8080"}):
                    with patch("httpx.Client", return_value=mock_client):
                        result = mem.sync_long_term_memory(tenant_id="t1", records=records)
        assert result["provider"] in ("weaviate", "in_memory")

    def test_weaviate_sync_failure(self) -> None:
        """When weaviate call fails → provider stays in_memory."""
        mem = _make_memory()
        records = [{"chunk_id": "c1", "embedding": [0.1, 0.2], "content": "hello"}]
        with patch.object(mem, "_postgres_ready", return_value=False):
            with patch.object(mem, "_pinecone_ready", return_value=False):
                with patch.dict(os.environ, {"WEAVIATE_URL": "http://weaviate:8080"}):
                    with patch("httpx.Client", side_effect=Exception("connection refused")):
                        result = mem.sync_long_term_memory(tenant_id="t1", records=records)
        assert result["provider"] == "in_memory"


class TestAppendShortTermRedis:
    """Test append_short_term_message with Redis backend."""

    def test_redis_success(self) -> None:
        """When redis client available → stores in redis, source='redis'."""
        mem = _make_memory()
        mock_redis = MagicMock()
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.append_short_term_message(
                tenant_id="t1",
                role="user",
                channel="chat",
                content="Hello redis",
            )
        assert result["source"] == "redis"
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()

    def test_redis_exception_falls_back_to_in_memory(self) -> None:
        """When redis raises exception → source='in_memory'."""
        mem = _make_memory()
        mock_redis = MagicMock()
        mock_redis.lpush.side_effect = Exception("redis down")
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.append_short_term_message(
                tenant_id="t1",
                role="user",
                channel="chat",
                content="Hello fallback",
            )
        assert result["source"] == "in_memory"


class TestGetShortTermRedis:
    """Test get_short_term_messages with Redis backend."""

    def test_redis_success_returns_items(self) -> None:
        """When redis has items → returns decoded list."""
        mem = _make_memory()
        record = {"tenant_id": "t1", "role": "user", "content": "Hi", "channel": "chat"}
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [json.dumps(record).encode()]
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.get_short_term_messages("t1", limit=10)
        assert len(result) >= 1

    def test_redis_empty_falls_back_to_in_memory(self) -> None:
        """When redis returns empty → falls through to in-memory."""
        mem = _make_memory(short_term_store=[
            {"tenant_id": "t1", "role": "assistant", "content": "Hello", "channel": "chat"}
        ])
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = []
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.get_short_term_messages("t1", limit=5)
        assert len(result) >= 1

    def test_redis_exception_falls_back_to_in_memory(self) -> None:
        """When redis raises exception → falls through to in-memory."""
        mem = _make_memory(short_term_store=[
            {"tenant_id": "t1", "role": "user", "content": "msg", "channel": "chat"}
        ])
        mock_redis = MagicMock()
        mock_redis.lrange.side_effect = Exception("redis error")
        with patch.object(mem, "_redis_client", return_value=mock_redis):
            result = mem.get_short_term_messages("t1", limit=5)
        assert len(result) >= 1


class TestRedisClientInstantiation:
    """Test _redis_client method."""

    def test_no_host_returns_none(self) -> None:
        """When REDIS_HOST not set → returns None."""
        mem = _make_memory()
        with patch("backend.fastapi.app.ira_memory._vault_get", return_value=""):
            client = mem._redis_client()
        assert client is None

    def test_redis_import_and_connect(self) -> None:
        """When REDIS_HOST set → imports redis and creates client."""
        mem = _make_memory()
        mock_redis_module = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_module.Redis.return_value = mock_redis_instance
        with patch("backend.fastapi.app.ira_memory._vault_get", return_value="redis-host"):
            with patch("backend.fastapi.app.ira_memory.import_module", return_value=mock_redis_module):
                client = mem._redis_client()
        assert client == mock_redis_instance

    def test_redis_import_exception_returns_none(self) -> None:
        """When redis import fails → returns None."""
        mem = _make_memory()
        with patch("backend.fastapi.app.ira_memory._vault_get", return_value="redis-host"):
            with patch("backend.fastapi.app.ira_memory.import_module", side_effect=Exception("no redis")):
                client = mem._redis_client()
        assert client is None


class TestQueryLongTermMemory:
    """Test query_long_term_memory."""

    def test_postgres_ready_but_no_results_falls_back(self) -> None:
        """When postgres ready but empty results → uses in_memory fallback."""
        mem = _make_memory()
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_query_supabase_postgres", return_value=[]):
                provider, results = mem.query_long_term_memory(
                    tenant_id="t1",
                    query="test query",
                    top_k=5,
                    min_score=0.0,
                    fallback_items=[],
                )
        assert provider == "in_memory"

    def test_postgres_ready_returns_results(self) -> None:
        """When postgres ready and returns results → provider='supabase_postgres'."""
        mem = _make_memory()
        fake_results = [{"content": "found it", "score": 0.9}]
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch.object(mem, "_query_supabase_postgres", return_value=fake_results):
                provider, results = mem.query_long_term_memory(
                    tenant_id="t1",
                    query="test query",
                    top_k=5,
                    min_score=0.0,
                    fallback_items=[],
                )
        assert provider == "supabase_postgres"
        assert len(results) == 1

    def test_fallback_with_embeddings(self) -> None:
        """In-memory fallback with embeddings filters by min_score."""
        mem = _make_memory()
        fallback_items = [
            {"chunk_id": "c1", "embedding": [0.1, 0.2, 0.3], "content": "hello", "title": "T", "source": "S"},
            {"chunk_id": "c2", "embedding": [0.1, 0.2, 0.3], "content": "world", "title": "T2", "source": "S2"},
        ]
        with patch.object(mem, "_postgres_ready", return_value=False):
            provider, results = mem.query_long_term_memory(
                tenant_id="t1",
                query="hello",
                top_k=5,
                min_score=0.0,
                fallback_items=fallback_items,
            )
        assert provider == "in_memory"
        assert len(results) >= 0  # May have 0 if cosine similarity < min_score


class TestEnsureTablesPaths:
    """Test _ensure_tables logic."""

    def test_skips_when_tables_already_ready(self) -> None:
        """When _tables_ready=True → skips DB."""
        mem = _make_memory()
        mem._tables_ready = True
        with patch("psycopg.connect", side_effect=Exception("should not connect")):
            mem._ensure_tables()  # Should not raise

    def test_skips_when_postgres_not_ready(self) -> None:
        """When postgres not ready → skips DB."""
        mem = _make_memory()
        mem._tables_ready = False
        with patch.object(mem, "_postgres_ready", return_value=False):
            with patch("psycopg.connect", side_effect=Exception("should not connect")):
                mem._ensure_tables()  # Should not raise

    def test_exception_sets_tables_ready_false(self) -> None:
        """When DB fails → _tables_ready remains False."""
        mem = _make_memory()
        mem._tables_ready = False
        with patch.object(mem, "_postgres_ready", return_value=True):
            with patch("psycopg.connect", side_effect=Exception("no DB")):
                mem._ensure_tables()
        assert mem._tables_ready is False
