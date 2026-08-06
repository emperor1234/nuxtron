"""
V1 Module: Entity-First SEO
Module 2 of the closed feedback loop.

Responsibilities:
- Listens to pages_analyzed events from seo-ai
- Extracts named entities from each analyzed page
- Stores entities in the entities + page_entities tables
- Updates Neo4j (or PostgreSQL JSON for v1)
- Emits entities_extracted event

Event emitted: entities_extracted, entity_graph_updated
Listens to: pages_analyzed
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

ENTITY_SYSTEM_PROMPT = (
    "You are a knowledge graph expert. Extract all named entities from the page content. "
    "For each entity return: name, type (brand|product|concept|location|person|org), "
    "description (max 100 chars), aliases (list of strings), confidence (0.0-1.0). "
    "Return only valid JSON: {\"entities\": [...]}."
)

RELATIONSHIP_PROMPT = (
    "Given these entities, identify relationships between them. "
    "For each pair return: from_name, to_name, relationship_type (mentions|related|parent|synonym), confidence (0.0-1.0). "
    "Return JSON: {\"relationships\": [...]}."
)


class EntityFirstSEO:
    """
    Module 2: Entity-First SEO

    Subscribes to pages_analyzed, extracts entities, emits entities_extracted.
    This forms the bridge between raw keyword data and the knowledge graph.
    """

    MODULE_TYPE = "entity-first-seo"

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
            event_type=EventType.PAGES_ANALYZED,
            handler=self._on_pages_analyzed,
            site_id=self.site_id,
        )

    async def _on_pages_analyzed(self, event: Event):
        """React to pages_analyzed event from seo-ai"""
        if event.site_id != self.site_id:
            return

        logger.info(
            f"[entity-first-seo] Received pages_analyzed event {event.id} "
            f"({event.payload.get('pages_analyzed', 0)} pages)"
        )

        run_id = str(uuid.uuid4())
        await self.run(run_id=run_id, trigger_event=event)

    async def run(
        self,
        run_id: str,
        trigger_event: Event | None = None,
        pages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Extract entities from analyzed pages.

        Args:
            run_id: UUID for this run
            trigger_event: the pages_analyzed event that triggered this
            pages: explicit page data; if None, loads from DB

        Returns:
            output dict with entities extracted
        """
        started_at = time.time()
        logger.info(f"[entity-first-seo] Starting run {run_id}")

        try:
            # 1. Load page data
            target_pages = pages or await self._load_pages_from_db()
            if not target_pages:
                return {"status": "no_pages", "entities_extracted": 0}

            # 2. Extract entities for each page
            all_entities: list[dict[str, Any]] = []
            all_relationships: list[dict[str, Any]] = []

            for page in target_pages:
                page_entities, page_rels = await self._extract_entities(page)
                all_entities.extend(page_entities)
                all_relationships.extend(page_rels)

                # Store entity-page associations
                if page_entities:
                    await self._store_page_entities(
                        page_id=page.get("id"),
                        entities=page_entities,
                    )

            # 3. Deduplicate + upsert entities
            unique_entities = self._deduplicate_entities(all_entities)
            entity_ids = await self._upsert_entities(unique_entities)

            # 4. Store relationships
            if all_relationships:
                await self._store_relationships(all_relationships, entity_ids)

            # 5. Emit event
            elapsed_ms = int((time.time() - started_at) * 1000)
            await self.bus.emit(
                event_type=EventType.ENTITIES_EXTRACTED,
                site_id=self.site_id,
                source_module_id=self.module_id,
                source_module_type=self.MODULE_TYPE,
                source_run_id=run_id,
                payload={
                    "entities_extracted": len(unique_entities),
                    "relationships_found": len(all_relationships),
                    "entity_ids": list(entity_ids.values()),
                    "top_entities": [
                        {"name": e["name"], "type": e["type"]}
                        for e in unique_entities[:10]
                    ],
                    "run_id": run_id,
                    "trigger_event_id": trigger_event.id if trigger_event else None,
                },
                targets=["ai-internal-linking-engine", "knowledge-graph-management", "topical-map-silo-builder"],
            )

            output = {
                "status": "success",
                "entities_extracted": len(unique_entities),
                "relationships_found": len(all_relationships),
                "entity_ids": list(entity_ids.values()),
                "execution_time_ms": elapsed_ms,
            }
            logger.info(f"[entity-first-seo] Run {run_id} complete: {output}")
            return output

        except Exception as e:
            logger.error(f"[entity-first-seo] Run {run_id} failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _load_pages_from_db(self) -> list[dict[str, Any]]:
        """Load recent pages for this site"""
        rows = await self.db.execute(
            "SELECT id, url, title, h1 FROM pages "
            "WHERE site_id = %s AND deleted_at IS NULL "
            "ORDER BY crawled_at DESC LIMIT 50",
            (self.site_id,),
        )
        return [
            {"id": str(r[0]), "url": r[1], "title": r[2], "h1": r[3]}
            for r in await rows.fetchall()
        ]

    async def _extract_entities(
        self, page: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relationships from a page via LLM"""
        prompt = (
            f"URL: {page.get('url', '')}\n"
            f"Title: {page.get('title', '')}\n"
            f"H1: {page.get('h1', '')}\n"
        )

        try:
            llm_response, _ = await invoke_with_pool(
                pool=self.llm,
                task="entity_extraction",
                prompt=prompt,
                system_prompt=ENTITY_SYSTEM_PROMPT,
                constraints=LLMConstraints(max_cost_usd=0.05),
            )

            parsed = json.loads(llm_response)
            entities = parsed.get("entities", [])

            # Extract relationships if there are multiple entities
            relationships = []
            if len(entities) > 1:
                rel_prompt = (
                    f"Entities found: {json.dumps([e['name'] for e in entities])}\n"
                    f"Page URL: {page.get('url', '')}"
                )
                rel_response, _ = await invoke_with_pool(
                    pool=self.llm,
                    task="entity_relationship_extraction",
                    prompt=rel_prompt,
                    system_prompt=RELATIONSHIP_PROMPT,
                    constraints=LLMConstraints(max_cost_usd=0.02),
                )
                rel_parsed = json.loads(rel_response)
                relationships = rel_parsed.get("relationships", [])

            return entities, relationships

        except json.JSONDecodeError as e:
            logger.warning(f"LLM JSON parse error for {page.get('url')}: {e}")
            return [], []
        except Exception as e:
            logger.warning(f"Entity extraction failed for {page.get('url')}: {e}")
            return [], []

    def _deduplicate_entities(
        self, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Deduplicate by name+type"""
        seen: set[str] = set()
        unique = []
        for e in entities:
            key = f"{e.get('name', '').lower()}:{e.get('type', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique

    async def _upsert_entities(
        self, entities: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Upsert entities into the DB, return {name: id} mapping"""
        entity_ids: dict[str, str] = {}

        for e in entities:
            entity_id = str(uuid.uuid4())
            aliases = e.get("aliases", [])

            row = await self.db.execute(
                """
                INSERT INTO entities (id, site_id, name, type, description, aliases, signal_strength)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (site_id, name, type) DO UPDATE
                  SET description = EXCLUDED.description,
                      aliases = EXCLUDED.aliases,
                      signal_strength = LEAST(entities.signal_strength + 0.05, 1.0),
                      updated_at = NOW()
                RETURNING id
                """,
                (
                    entity_id,
                    self.site_id,
                    e.get("name"),
                    e.get("type", "concept"),
                    e.get("description", ""),
                    aliases,
                    e.get("confidence", 0.5),
                ),
            )
            returned = await row.fetchone()
            if returned:
                entity_ids[e["name"]] = str(returned[0])

        await self.db.commit()
        return entity_ids

    async def _store_page_entities(
        self,
        page_id: str | None,
        entities: list[dict[str, Any]],
    ):
        """Store page-entity associations"""
        if not page_id:
            return

        for i, e in enumerate(entities):
            entity_row = await self.db.execute(
                "SELECT id FROM entities WHERE site_id = %s AND name = %s AND type = %s",
                (self.site_id, e.get("name"), e.get("type", "concept")),
            )
            entity = await entity_row.fetchone()
            if entity:
                await self.db.execute(
                    """
                    INSERT INTO page_entities (page_id, entity_id, confidence, position, mention_count)
                    VALUES (%s, %s, %s, %s, 1)
                    ON CONFLICT (page_id, entity_id) DO UPDATE
                      SET mention_count = page_entities.mention_count + 1,
                          confidence = GREATEST(page_entities.confidence, EXCLUDED.confidence),
                          updated_at = NOW()
                    """,
                    (page_id, str(entity[0]), e.get("confidence", 0.5), i),
                )

        await self.db.commit()

    async def _store_relationships(
        self,
        relationships: list[dict[str, Any]],
        entity_ids: dict[str, str],
    ):
        """Store entity relationships"""
        for rel in relationships:
            from_name = rel.get("from_name")
            to_name = rel.get("to_name")
            from_id = entity_ids.get(from_name)
            to_id = entity_ids.get(to_name)

            if from_id and to_id:
                await self.db.execute(
                    """
                    INSERT INTO entity_relationships (from_id, to_id, relationship_type, confidence)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (from_id, to_id, relationship_type) DO UPDATE
                      SET confidence = GREATEST(entity_relationships.confidence, EXCLUDED.confidence)
                    """,
                    (from_id, to_id, rel.get("relationship_type", "related"), rel.get("confidence", 0.5)),
                )

        await self.db.commit()
