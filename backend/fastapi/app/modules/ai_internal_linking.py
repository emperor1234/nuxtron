"""
V1 Module: AI Internal Linking Engine
Module 3 of the closed feedback loop.

Responsibilities:
- Listens to entities_extracted events from entity-first-seo
- Queries the entity graph to find related pages
- Generates contextual internal link suggestions
- Emits links_suggested event for the agent to review

Event emitted: links_suggested
Listens to: entities_extracted
"""

import json
import logging
import time
import uuid
from typing import Any

import psycopg

from ..event_bus import Event, EventBus, EventType
from ..llm_pool import LLMConstraints, LLMPool, invoke_with_pool

logger = logging.getLogger(__name__)

LINK_SYSTEM_PROMPT = (
    "You are an internal linking expert. Given a source page and a list of related pages "
    "connected by shared entities, suggest internal links with natural anchor text. "
    "For each link, provide: from_url, to_url, anchor_text, context_snippet, relevance_score (0-1). "
    "Return JSON: {\"links\": [...]}. Prefer high-relevance, natural-sounding anchor text."
)


class AIInternalLinkingEngine:
    """
    Module 3: AI Internal Linking Engine

    Subscribes to entities_extracted, generates link suggestions, emits links_suggested.
    """

    MODULE_TYPE = "ai-internal-linking-engine"

    def __init__(
        self,
        site_id: str,
        module_id: str,
        db_conn: psycopg.AsyncConnection,
        event_bus: EventBus,
        llm_pool: LLMPool,
    ):
        self.site_id = site_id
        self.module_id = module_id
        self.db = db_conn
        self.bus = event_bus
        self.llm = llm_pool

        # Register event handler
        self.bus.subscribe(
            event_type=EventType.ENTITIES_EXTRACTED,
            handler=self._on_entities_extracted,
            site_id=self.site_id,
        )

    async def _on_entities_extracted(self, event: Event):
        """React to entities_extracted event from entity-first-seo"""
        if event.site_id != self.site_id:
            return

        logger.info(
            f"[ai-internal-linking] Received entities_extracted event {event.id} "
            f"({event.payload.get('entities_extracted', 0)} entities)"
        )

        run_id = str(uuid.uuid4())
        await self.run(run_id=run_id, trigger_event=event)

    async def run(
        self,
        run_id: str,
        trigger_event: Event | None = None,
        entity_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate internal link suggestions based on entity graph.

        Args:
            run_id: UUID for this run
            trigger_event: the entities_extracted event that triggered this
            entity_ids: explicit list of entity IDs to work with

        Returns:
            output dict with link suggestions
        """
        started_at = time.time()
        logger.info(f"[ai-internal-linking] Starting run {run_id}")

        try:
            # 1. Load entity-page pairs
            target_entity_ids = (
                entity_ids
                or (trigger_event.payload.get("entity_ids", []) if trigger_event else [])
                or await self._load_top_entities()
            )

            if not target_entity_ids:
                return {"status": "no_entities", "links_suggested": 0}

            # 2. Build opportunity matrix (shared entities → potential links)
            opportunities = await self._find_link_opportunities(target_entity_ids)
            if not opportunities:
                return {"status": "no_opportunities", "links_suggested": 0}

            # 3. Generate link suggestions via LLM
            suggestions = await self._generate_suggestions(opportunities)

            # 4. Score and filter
            approved = [s for s in suggestions if s.get("relevance_score", 0) >= 0.6]

            # 5. Store suggestions
            await self._store_suggestions(run_id, approved)

            # 6. Emit event
            elapsed_ms = int((time.time() - started_at) * 1000)
            await self.bus.emit(
                event_type=EventType.LINKS_SUGGESTED,
                site_id=self.site_id,
                source_module_id=self.module_id,
                source_module_type=self.MODULE_TYPE,
                source_run_id=run_id,
                payload={
                    "links_suggested": len(approved),
                    "links_pending_review": list(approved[:20]),
                    "run_id": run_id,
                    "trigger_event_id": trigger_event.id if trigger_event else None,
                },
                targets=["autonomous-agent-engine"],
            )

            output = {
                "status": "success",
                "opportunities_found": len(opportunities),
                "links_suggested": len(approved),
                "links_filtered_out": len(suggestions) - len(approved),
                "execution_time_ms": elapsed_ms,
            }
            logger.info(f"[ai-internal-linking] Run {run_id} complete: {output}")
            return output

        except Exception as e:
            logger.error(f"[ai-internal-linking] Run {run_id} failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _load_top_entities(self, limit: int = 20) -> list[str]:
        """Load top entities by signal strength"""
        rows = await self.db.execute(
            "SELECT id FROM entities WHERE site_id = %s "
            "ORDER BY signal_strength DESC LIMIT %s",
            (self.site_id, limit),
        )
        return [str(r[0]) for r in await rows.fetchall()]

    async def _find_link_opportunities(
        self, entity_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Find pairs of pages that share entities but don't already link to each other.

        Opportunity = pages A and B share entity E, but A doesn't link to B.
        Returns list of {from_page, to_page, shared_entity, entity_name}.
        """
        rows = await self.db.execute(
            """
            SELECT
              pe1.page_id  AS from_page_id,
              pe2.page_id  AS to_page_id,
              pe1.entity_id,
              e.name       AS entity_name,
              e.type       AS entity_type,
              p1.url       AS from_url,
              p2.url       AS to_url,
              p1.title     AS from_title,
              p2.title     AS to_title,
              pe1.confidence + pe2.confidence AS combined_confidence
            FROM page_entities pe1
            JOIN page_entities pe2
              ON pe1.entity_id = pe2.entity_id
              AND pe1.page_id <> pe2.page_id
            JOIN entities e ON e.id = pe1.entity_id
            JOIN pages p1 ON p1.id = pe1.page_id
            JOIN pages p2 ON p2.id = pe2.page_id
            WHERE pe1.entity_id = ANY(%s)
              AND p1.site_id = %s
              AND p2.site_id = %s
              AND p1.deleted_at IS NULL
              AND p2.deleted_at IS NULL
            ORDER BY combined_confidence DESC
            LIMIT 30
            """,
            (entity_ids, self.site_id, self.site_id),
        )
        raw = await rows.fetchall()
        return [
            {
                "from_page_id": str(r[0]),
                "to_page_id": str(r[1]),
                "entity_id": str(r[2]),
                "entity_name": r[3],
                "entity_type": r[4],
                "from_url": r[5],
                "to_url": r[6],
                "from_title": r[7],
                "to_title": r[8],
                "confidence": float(r[9]),
            }
            for r in raw
        ]

    async def _generate_suggestions(
        self, opportunities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Use LLM to generate anchor text and context for each link opportunity"""
        prompt = (
            "Here are pages that share entities and could benefit from internal links:\n\n"
            + json.dumps(
                [
                    {
                        "from": o["from_url"],
                        "from_title": o["from_title"],
                        "to": o["to_url"],
                        "to_title": o["to_title"],
                        "shared_entity": o["entity_name"],
                    }
                    for o in opportunities[:15]  # cap for token budget
                ],
                indent=2,
            )
        )

        try:
            response, cost = await invoke_with_pool(
                pool=self.llm,
                task="content_internal_link_generation",
                prompt=prompt,
                system_prompt=LINK_SYSTEM_PROMPT,
                constraints=LLMConstraints(max_cost_usd=0.10),
            )
            parsed = json.loads(response)
            suggestions = parsed.get("links", [])

            # Merge with opportunity context
            for s in suggestions:
                match = next(
                    (o for o in opportunities if o["from_url"] == s.get("from_url")),
                    None,
                )
                if match:
                    s["entity_name"] = match["entity_name"]
                    s["from_page_id"] = match["from_page_id"]
                    s["to_page_id"] = match["to_page_id"]

            return suggestions

        except json.JSONDecodeError as e:
            logger.warning(f"LLM JSON parse error in link generation: {e}")
            return []
        except Exception as e:
            logger.warning(f"Link generation failed: {e}")
            return []

    async def _store_suggestions(
        self, run_id: str, suggestions: list[dict[str, Any]]
    ):
        """Store link suggestions in DB for agent review"""
        for s in suggestions:
            await self.db.execute(
                """
                INSERT INTO metrics (site_id, run_id, module_id, metric_name, value, unit)
                VALUES (%s, %s, %s, 'link_suggestion', %s, 'score')
                """,
                (
                    self.site_id,
                    run_id,
                    self.module_id,
                    s.get("relevance_score", 0),
                ),
            )
        await self.db.commit()
