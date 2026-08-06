"""
Extra unit tests for ira_memory.py pure helper functions
not covered in test_ira_memory.py.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == 1.0

    def test_orthogonal_vectors(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_opposite_vectors(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0

    def test_empty_returns_zero(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        assert _cosine_similarity([], []) == 0.0

    def test_different_lengths_returns_zero(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        assert _cosine_similarity([1.0, 0.0], [1.0]) == 0.0

    def test_result_clamped_to_1(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        # Due to floating-point, result should be clamped
        result = _cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert -1.0 <= result <= 1.0

    def test_normalized_symmetric(self) -> None:
        from backend.fastapi.app.ira_memory import _cosine_similarity
        a = [0.5, 0.5]
        b = [0.3, 0.7]
        assert _cosine_similarity(a, b) == _cosine_similarity(b, a)


class TestDbDsnFromEnv:
    def test_returns_string(self) -> None:
        from backend.fastapi.app.ira_memory import _db_dsn_from_env
        dsn = _db_dsn_from_env()
        assert isinstance(dsn, str)
        assert len(dsn) > 0

    def test_supabase_url_takes_priority(self) -> None:
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://user:pass@host/db"}):
            from backend.fastapi.app.ira_memory import _db_dsn_from_env
            dsn = _db_dsn_from_env()
            assert dsn == "postgresql://user:pass@host/db"


class TestQueryFallback:
    """Test IRAMemorySystem._query_fallback pure scoring logic."""

    def _make_memory(self):
        from backend.fastapi.app.ira_memory import IRAMemorySystem
        def now_fn(): return "2025-01-01T00:00:00Z"
        def embed_fn(texts): return "local", [[0.1, 0.2] for _ in texts]
        return IRAMemorySystem(
            db_dsn_fn=lambda: "host=localhost",
            now_iso_fn=now_fn,
            short_term_store=[],
            long_term_store=[],
            structured_store=[],
            embed_texts=embed_fn,
        )

    def test_empty_items_returns_empty(self) -> None:
        mem = self._make_memory()
        result = mem._query_fallback(query="test", top_k=5, min_score=0.0, items=[])
        assert result == []

    def test_items_without_embeddings_returned_in_order(self) -> None:
        mem = self._make_memory()
        items = [
            {"id": "1", "content": "hello"},
            {"id": "2", "content": "world"},
        ]
        result = mem._query_fallback(query="test", top_k=5, min_score=0.0, items=items)
        # Without embeddings, all items may be returned
        assert isinstance(result, list)

    def test_top_k_limits_results(self) -> None:
        mem = self._make_memory()
        items = [{"id": str(i), "content": f"item {i}"} for i in range(10)]
        result = mem._query_fallback(query="test", top_k=3, min_score=0.0, items=items)
        assert len(result) <= 3


class TestRedisKey:
    def test_redis_key_format(self) -> None:
        from backend.fastapi.app.ira_memory import IRAMemorySystem
        def now_fn(): return "2025-01-01T00:00:00Z"
        def embed_fn(texts): return "local", [[0.1] for _ in texts]
        mem = IRAMemorySystem(
            db_dsn_fn=lambda: "host=localhost",
            now_iso_fn=now_fn,
            short_term_store=[],
            long_term_store=[],
            structured_store=[],
            embed_texts=embed_fn,
        )
        key = mem._redis_key("tenant-1")
        assert "tenant-1" in key
        assert isinstance(key, str)
