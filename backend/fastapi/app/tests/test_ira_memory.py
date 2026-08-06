"""Tests for ira_memory.py — IRAMemorySystem and module-level helpers."""
from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

from backend.fastapi.app.ira_memory import (
    IRAMemorySystem,
    _cosine_similarity,
    _db_dsn_from_env,
    _load_vault_secrets,
    _vault_get,
)

# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _now() -> str:
    return "2026-01-01T00:00:00"


def _dummy_embed(texts: list[str]) -> tuple[str, list[list[float]]]:
    return "local", [[0.1, 0.2, 0.3] for _ in texts]


def _make_memory(**kwargs) -> IRAMemorySystem:
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


# --------------------------------------------------------------------------- #
#  Module-level helpers
# --------------------------------------------------------------------------- #

class TestDbDsnFromEnv:
    def test_direct_url_takes_priority(self):
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgres://direct"}):
            assert _db_dsn_from_env() == "postgres://direct"

    def test_builds_from_parts_when_no_direct_url(self):
        env = {
            "SUPABASE_DB_URL": "",
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypw",
        }
        with patch.dict(os.environ, env):
            dsn = _db_dsn_from_env()
        assert "myhost" in dsn
        assert "5433" in dsn
        assert "mydb" in dsn


class TestLoadVaultSecrets:
    def test_returns_empty_when_no_postgres(self):
        """No env vars → returns {} without attempting DB connection."""
        import backend.fastapi.app.ira_memory as mod
        orig_cache = mod._vault_cache
        orig_attempted = mod._vault_cache_attempted
        try:
            mod._vault_cache = None
            mod._vault_cache_attempted = False
            env = {"SUPABASE_DB_URL": "", "POSTGRES_HOST": ""}
            with patch.dict(os.environ, env, clear=False):
                # Forcibly clear the offending vars
                os.environ.pop("SUPABASE_DB_URL", None)
                os.environ.pop("POSTGRES_HOST", None)
                result = _load_vault_secrets()
            assert result == {}
        finally:
            mod._vault_cache = orig_cache
            mod._vault_cache_attempted = orig_attempted

    def test_returns_cached_on_second_call(self):
        import backend.fastapi.app.ira_memory as mod
        orig_cache = mod._vault_cache
        orig_attempted = mod._vault_cache_attempted
        try:
            mod._vault_cache = {"key": "val"}
            mod._vault_cache_attempted = True
            result = _load_vault_secrets()
            assert result == {"key": "val"}
        finally:
            mod._vault_cache = orig_cache
            mod._vault_cache_attempted = orig_attempted


class TestVaultGet:
    def test_returns_env_var_when_no_vault_name(self):
        with patch.dict(os.environ, {"MY_KEY": "myvalue"}):
            assert _vault_get("MY_KEY", "IRA_VAULT_SECRET_MY_KEY") == "myvalue"

    def test_returns_fallback_when_nothing_set(self):
        os.environ.pop("MISSING_KEY_XYZ", None)
        result = _vault_get("MISSING_KEY_XYZ", "IRA_VAULT_SECRET_MISSING", fallback="default")
        assert result == "default"


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == 1.0

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_empty_vectors_returns_zero(self):
        assert _cosine_similarity([], []) == 0.0

    def test_mismatched_lengths_returns_zero(self):
        assert _cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_clamped_to_minus_one(self):
        # Opposite direction: [-1, 0] · [1, 0] = -1
        result = _cosine_similarity([-1.0, 0.0], [1.0, 0.0])
        assert result == -1.0


# --------------------------------------------------------------------------- #
#  IRAMemorySystem - provider_status
# --------------------------------------------------------------------------- #

class TestProviderStatus:
    def test_in_memory_when_nothing_configured(self):
        m = _make_memory()
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "", "POSTGRES_HOST": ""}, clear=False):
            os.environ.pop("SUPABASE_DB_URL", None)
            os.environ.pop("POSTGRES_HOST", None)
            os.environ.pop("PINECONE_API_KEY", None)
            os.environ.pop("WEAVIATE_URL", None)
            status = m.provider_status()
        assert status["short_term"]["active_backend"] == "in_memory"
        assert status["long_term"]["active_backend"] == "in_memory"

    def test_pinecone_long_term_backend(self):
        m = _make_memory()
        env = {
            "SUPABASE_DB_URL": "",
            "POSTGRES_HOST": "",
            "PINECONE_API_KEY": "pk-xxx",
            "PINECONE_INDEX_HOST": "index.pinecone.io",
            "WEAVIATE_URL": "",
        }
        with patch.dict(os.environ, env):
            status = m.provider_status()
        assert status["long_term"]["active_backend"] == "pinecone"

    def test_weaviate_long_term_backend(self):
        m = _make_memory()
        env = {
            "SUPABASE_DB_URL": "",
            "POSTGRES_HOST": "",
            "PINECONE_API_KEY": "",
            "PINECONE_INDEX_HOST": "",
            "WEAVIATE_URL": "http://weaviate:8080",
        }
        with patch.dict(os.environ, env):
            status = m.provider_status()
        assert status["long_term"]["active_backend"] == "weaviate"


# --------------------------------------------------------------------------- #
#  Short-term memory
# --------------------------------------------------------------------------- #

class TestShortTermMemory:
    def test_append_and_get(self):
        store: list[dict] = []
        m = _make_memory(short_term_store=store)
        with patch.dict(os.environ, {"REDIS_HOST": ""}, clear=False):
            os.environ.pop("REDIS_HOST", None)
            record = m.append_short_term_message(
                tenant_id="t1", role="user", channel="chat", content="hello"
            )
        assert record["content"] == "hello"
        assert record["source"] == "in_memory"
        assert record in store

    def test_get_limits_results(self):
        store = []
        m = _make_memory(short_term_store=store)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REDIS_HOST", None)
            for i in range(10):
                m.append_short_term_message(tenant_id="t1", role="user", channel="chat", content=f"msg{i}")
            results = m.get_short_term_messages("t1", limit=3)
        assert len(results) == 3

    def test_filters_by_tenant(self):
        store = []
        m = _make_memory(short_term_store=store)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REDIS_HOST", None)
            m.append_short_term_message(tenant_id="t1", role="user", channel="chat", content="for t1")
            m.append_short_term_message(tenant_id="t2", role="user", channel="chat", content="for t2")
            results = m.get_short_term_messages("t1")
        assert all(r["tenant_id"] == "t1" for r in results)

    def test_append_with_redis(self):
        store = []
        m = _make_memory(short_term_store=store)
        mock_redis = MagicMock()
        with patch.object(m, "_redis_client", return_value=mock_redis):
            record = m.append_short_term_message(
                tenant_id="t1", role="bot", channel="chat", content="hi"
            )
        assert record["source"] == "redis"
        mock_redis.lpush.assert_called_once()

    def test_append_with_redis_exception_falls_back(self):
        store = []
        m = _make_memory(short_term_store=store)
        mock_redis = MagicMock()
        mock_redis.lpush.side_effect = Exception("redis down")
        with patch.object(m, "_redis_client", return_value=mock_redis):
            record = m.append_short_term_message(
                tenant_id="t1", role="user", channel="chat", content="msg"
            )
        assert record["source"] == "in_memory"

    def test_get_from_redis(self):
        m = _make_memory()
        payload = json.dumps({"tenant_id": "t1", "content": "hello", "source": "redis"})
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [payload.encode()]
        with patch.object(m, "_redis_client", return_value=mock_redis):
            results = m.get_short_term_messages("t1", limit=5)
        assert len(results) == 1
        assert results[0]["content"] == "hello"

    def test_get_from_redis_exception_falls_back_to_store(self):
        store = [{"tenant_id": "t1", "content": "stored"}]
        m = _make_memory(short_term_store=store)
        mock_redis = MagicMock()
        mock_redis.lrange.side_effect = Exception("err")
        with patch.object(m, "_redis_client", return_value=mock_redis):
            results = m.get_short_term_messages("t1")
        assert results[0]["content"] == "stored"


# --------------------------------------------------------------------------- #
#  Structured memory
# --------------------------------------------------------------------------- #

class TestStructuredMemory:
    def _no_postgres_env(self):
        return patch.dict(os.environ, {"SUPABASE_DB_URL": "", "POSTGRES_HOST": ""}, clear=False)

    def test_upsert_creates_record(self):
        store = []
        m = _make_memory(structured_store=store)
        with self._no_postgres_env():
            os.environ.pop("POSTGRES_HOST", None)
            os.environ.pop("SUPABASE_DB_URL", None)
            record = m.upsert_structured_memory(
                tenant_id="t1", memory_type="preferences", memory_key="theme", payload={"color": "dark"}
            )
        assert record["source"] == "in_memory"
        assert record["payload"] == {"color": "dark"}
        assert len(store) == 1

    def test_upsert_updates_existing(self):
        existing = {"tenant_id": "t1", "memory_type": "preferences", "memory_key": "theme", "payload": {"color": "light"}}
        store = [existing]
        m = _make_memory(structured_store=store)
        with self._no_postgres_env():
            os.environ.pop("POSTGRES_HOST", None)
            os.environ.pop("SUPABASE_DB_URL", None)
            record = m.upsert_structured_memory(
                tenant_id="t1", memory_type="preferences", memory_key="theme", payload={"color": "dark"}
            )
        assert record["payload"] == {"color": "dark"}
        assert len(store) == 1  # still only one record

    def test_list_returns_tenant_records(self):
        store = [
            {"tenant_id": "t1", "memory_type": "prefs", "memory_key": "a", "payload": {}},
            {"tenant_id": "t2", "memory_type": "prefs", "memory_key": "b", "payload": {}},
        ]
        m = _make_memory(structured_store=store)
        with self._no_postgres_env():
            os.environ.pop("POSTGRES_HOST", None)
            os.environ.pop("SUPABASE_DB_URL", None)
            results = m.list_structured_memory("t1")
        assert all(r["tenant_id"] == "t1" for r in results)

    def test_list_filters_by_type(self):
        store = [
            {"tenant_id": "t1", "memory_type": "prefs", "memory_key": "a", "payload": {}},
            {"tenant_id": "t1", "memory_type": "facts", "memory_key": "b", "payload": {}},
        ]
        m = _make_memory(structured_store=store)
        with self._no_postgres_env():
            os.environ.pop("POSTGRES_HOST", None)
            os.environ.pop("SUPABASE_DB_URL", None)
            results = m.list_structured_memory("t1", memory_type="prefs")
        assert all(r["memory_type"] == "prefs" for r in results)


# --------------------------------------------------------------------------- #
#  Long-term memory
# --------------------------------------------------------------------------- #

class TestLongTermMemory:
    def _no_postgres_env(self):
        return patch.dict(os.environ, {}, clear=False)

    def test_sync_returns_in_memory_when_no_backend(self):
        m = _make_memory()
        with patch.object(m, "_postgres_ready", return_value=False), \
             patch.object(m, "_pinecone_ready", return_value=False), \
             patch.object(m, "_weaviate_ready", return_value=False):
            result = m.sync_long_term_memory(tenant_id="t1", records=[
                {"chunk_id": "c1", "title": "T", "content": "C", "embedding": [0.1, 0.2]}
            ])
        assert result["provider"] == "in_memory"
        assert result["synced_count"] == 0

    def test_query_falls_back_to_in_memory(self):
        items = [
            {"chunk_id": "c1", "document_id": "d1", "title": "T", "source": "S", "content": "hello", "embedding": [1.0, 0.0, 0.0]}
        ]
        m = _make_memory(long_term_store=items)
        with patch.object(m, "_postgres_ready", return_value=False):
            provider, results = m.query_long_term_memory(
                tenant_id="t1", query="test", top_k=5, min_score=0.0, fallback_items=items
            )
        assert provider == "in_memory"
        assert len(results) > 0

    def test_query_fallback_scores_and_sorts(self):
        items = [
            {"chunk_id": "c1", "title": "A", "content": "a", "embedding": [1.0, 0.0, 0.0]},
            {"chunk_id": "c2", "title": "B", "content": "b", "embedding": [0.0, 1.0, 0.0]},
        ]

        def embed_fn(texts):
            return "local", [[1.0, 0.0, 0.0]]  # aligns with c1

        m = _make_memory(embed_texts=embed_fn)
        with patch.object(m, "_postgres_ready", return_value=False):
            _, results = m.query_long_term_memory(
                tenant_id="t1", query="a", top_k=5, min_score=0.0, fallback_items=items
            )
        assert results[0]["chunk_id"] == "c1"

    def test_query_respects_min_score(self):
        items = [
            {"chunk_id": "c1", "title": "A", "content": "a", "embedding": [0.0, 1.0, 0.0]},
        ]

        def embed_fn(texts):
            return "local", [[1.0, 0.0, 0.0]]  # orthogonal → score 0.0

        m = _make_memory(embed_texts=embed_fn)
        with patch.object(m, "_postgres_ready", return_value=False):
            _, results = m.query_long_term_memory(
                tenant_id="t1", query="q", top_k=5, min_score=0.5, fallback_items=items
            )
        assert results == []


# --------------------------------------------------------------------------- #
#  Internal helpers
# --------------------------------------------------------------------------- #

class TestInternalHelpers:
    def test_redis_key_format(self):
        m = _make_memory()
        key = m._redis_key("tenant-123")
        assert "tenant-123" in key
        assert "short_term" in key

    def test_short_term_limit_default(self):
        m = _make_memory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IRA_SHORT_TERM_MEMORY_LIMIT", None)
            assert m._short_term_limit() == 40

    def test_short_term_limit_from_env(self):
        m = _make_memory()
        with patch.dict(os.environ, {"IRA_SHORT_TERM_MEMORY_LIMIT": "100"}):
            assert m._short_term_limit() == 100

    def test_trim_does_nothing_when_small(self):
        store = [{"id": i} for i in range(5)]
        m = _make_memory(short_term_store=store)
        m._trim_short_term_store()
        assert len(store) == 5

    def test_trim_trims_large_store(self):
        store = [{"id": i} for i in range(1000)]
        m = _make_memory(short_term_store=store)
        with patch.dict(os.environ, {"IRA_SHORT_TERM_MEMORY_LIMIT": "10"}):
            m._trim_short_term_store()
        assert len(store) <= 100  # 10 * 10

    def test_postgres_ready_with_url(self):
        m = _make_memory()
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgres://host/db"}):
            assert m._postgres_ready() is True

    def test_postgres_not_ready_without_config(self):
        m = _make_memory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUPABASE_DB_URL", None)
            os.environ.pop("POSTGRES_HOST", None)
            assert m._postgres_ready() is False

    def test_redis_client_none_when_no_host(self):
        m = _make_memory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REDIS_HOST", None)
            assert m._redis_client() is None

    def test_pinecone_not_ready_when_missing_vars(self):
        m = _make_memory()
        with patch.dict(os.environ, {"PINECONE_API_KEY": "", "PINECONE_INDEX_HOST": ""}):
            assert m._pinecone_ready() is False

    def test_weaviate_not_ready_when_missing(self):
        m = _make_memory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WEAVIATE_URL", None)
            assert m._weaviate_ready() is False


# --------------------------------------------------------------------------- #
#  Overview
# --------------------------------------------------------------------------- #

class TestOverview:
    def test_overview_structure(self):
        store = [{"tenant_id": "t1", "role": "user", "content": "hi"}]
        m = _make_memory(short_term_store=store)
        with patch.object(m, "_postgres_ready", return_value=False), \
             patch.object(m, "_redis_client", return_value=None):
            result = m.overview("t1")
        assert "providers" in result
        assert "summary" in result
        assert "recent_short_term" in result
        assert "structured_records" in result
        assert result["summary"]["short_term_messages"] == 1

    def test_overview_counts_long_term_documents(self):
        lt_store = [
            {"tenant_id": "t1", "document_id": "doc1"},
            {"tenant_id": "t1", "document_id": "doc1"},  # duplicate
            {"tenant_id": "t1", "document_id": "doc2"},
            {"tenant_id": "t2", "document_id": "doc3"},
        ]
        m = _make_memory(long_term_store=lt_store)
        with patch.object(m, "_postgres_ready", return_value=False), \
             patch.object(m, "_redis_client", return_value=None):
            result = m.overview("t1")
        assert result["summary"]["long_term_documents"] == 2  # doc1, doc2
        assert result["summary"]["long_term_chunks"] == 3  # 3 chunks for t1


# --------------------------------------------------------------------------- #
#  Pinecone/Weaviate sync
# --------------------------------------------------------------------------- #

class TestPineconeSync:
    def test_sync_pinecone_returns_zero_without_config(self):
        m = _make_memory()
        with patch.dict(os.environ, {"PINECONE_API_KEY": "", "PINECONE_INDEX_HOST": ""}):
            result = m._sync_pinecone(tenant_id="t1", records=[{"chunk_id": "c1", "embedding": [0.1]}])
        assert result == 0

    def test_sync_pinecone_sends_vectors(self):
        m = _make_memory()
        env = {"PINECONE_API_KEY": "key", "PINECONE_INDEX_HOST": "index.pinecone.io"}
        records = [{"chunk_id": "c1", "embedding": [0.1, 0.2], "title": "T", "source": "S", "content": "C", "document_id": "d1"}]
        with patch.dict(os.environ, env), \
             patch("backend.fastapi.app.ira_memory.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = m._sync_pinecone(tenant_id="t1", records=records)
        assert result == 1

    def test_sync_pinecone_returns_zero_on_error(self):
        m = _make_memory()
        env = {"PINECONE_API_KEY": "key", "PINECONE_INDEX_HOST": "index.pinecone.io"}
        with patch.dict(os.environ, env), \
             patch("backend.fastapi.app.ira_memory.httpx.Client", side_effect=Exception("err")):
            result = m._sync_pinecone(tenant_id="t1", records=[{"chunk_id": "c1", "embedding": []}])
        assert result == 0


class TestWeaviateSync:
    def test_sync_weaviate_returns_zero_without_url(self):
        m = _make_memory()
        with patch.dict(os.environ, {"WEAVIATE_URL": ""}):
            result = m._sync_weaviate(tenant_id="t1", records=[])
        assert result == 0
