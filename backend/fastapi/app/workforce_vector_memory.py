"""
Workforce Vector Memory Integration

Integrates the autonomous workforce with vector embeddings for:
- Semantic knowledge retrieval
- Context enrichment for agents
- Similar mission lookups
- Agent memory (RAG pattern)

Leverages IRA's embedding infrastructure when available.
"""

from __future__ import annotations

from typing import Any


class VectorMemoryIntegration:
    """Bridge between workforce and vector embeddings."""

    def __init__(self, ai_gateway_url: str, embedding_dimension: int = 1536):
        self.ai_gateway_url = ai_gateway_url
        self.embedding_dimension = embedding_dimension
        self.documents: dict[str, dict[str, Any]] = {}

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text using AI gateway or fallback."""
        # For now, return a mock embedding of the right size
        # In production, call OpenAI, Anthropic, or embedding model via gateway
        hash_val = sum(ord(c) for c in text) % 10000
        import random

        random.seed(hash_val)
        return [random.random() for _ in range(self.embedding_dimension)]

    async def store_knowledge_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store a knowledge document with embedding."""
        embedding = await self.embed_text(content)
        doc = {
            "id": doc_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
        }
        self.documents[doc_id] = doc
        return doc

    async def search_similar_documents(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for semantically similar knowledge documents."""
        query_embedding = await self.embed_text(query)

        # Simple cosine similarity
        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot_product = sum(x * y for x, y in zip(a, b, strict=False))
            mag_a = sum(x * x for x in a) ** 0.5
            mag_b = sum(x * x for x in b) ** 0.5
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot_product / (mag_a * mag_b)

        scores = [
            (doc_id, cosine_similarity(query_embedding, doc["embedding"]))
            for doc_id, doc in self.documents.items()
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [self.documents[doc_id] for doc_id, _ in scores[:top_k]]

    async def build_agent_context(
        self,
        role: str,
        objective: str,
        max_context_docs: int = 3,
    ) -> dict[str, Any]:
        """Build enriched context for an agent from knowledge base."""
        search_query = f"Role: {role}. Objective: {objective}"
        similar_docs = await self.search_similar_documents(search_query, max_context_docs)

        context = {
            "role": role,
            "objective": objective,
            "knowledge_base": [
                {
                    "id": doc["id"],
                    "excerpt": doc["content"][:300],
                    "metadata": doc["metadata"],
                }
                for doc in similar_docs
            ],
            "instruction": f"""Based on these similar past examples:
{chr(10).join(f"- {doc['content'][:100]}" for doc in similar_docs)}

Execute this objective: {objective}""",
        }
        return context

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory usage statistics."""
        total_tokens = sum(len(doc["content"].split()) for doc in self.documents.values())
        return {
            "total_documents": len(self.documents),
            "total_tokens": total_tokens,
            "embedding_dimension": self.embedding_dimension,
        }
