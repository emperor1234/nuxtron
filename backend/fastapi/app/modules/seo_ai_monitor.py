"""
V1 Module: SEO-AI Monitor
Module 1 of the closed feedback loop.

Responsibilities:
- Crawl pages for a site
- Extract keywords via LLM pool
- Compute core metrics (crawl health, keyword signals)
- Store metrics in PostgreSQL
- Emit pages_analyzed event

Event emitted: pages_analyzed
Listens to: schedule_fired, page_updated
"""

import asyncio
import hashlib
import logging
import time
from typing import Any

import httpx
import psycopg

from ..event_bus import EventBus, EventType
from ..llm_pool import LLMConstraints, LLMPool, invoke_with_pool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert SEO analyst. Extract the top 10 keywords and their "
    "search intent from the given page content. Return JSON with keys: "
    "'keywords' (array of {keyword, intent, priority}) and 'title_assessment' (string)."
)


class SEOAIMonitor:
    """
    Module 1: SEO-AI Monitor
    
    Crawls pages, extracts keywords via LLM, stores metrics, emits events.
    """

    MODULE_TYPE = "seo-ai"

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
        self.http = httpx.AsyncClient(timeout=15)

    async def run(
        self,
        run_id: str,
        pages: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Main entry point. Crawl pages, extract signals, emit event.

        Args:
            run_id: UUID of this run (persisted to DB)
            pages: explicit URL list; if None, loads from DB
            limit: max pages to crawl in this run

        Returns:
            output dict stored in runs.output_data
        """
        started_at = time.time()
        logger.info(f"[seo-ai] Starting run {run_id} for site {self.site_id}")

        try:
            # 1. Load pages
            target_pages = pages or await self._load_pages_from_db(limit)
            if not target_pages:
                return {"status": "no_pages", "pages_analyzed": 0}

            # 2. Crawl + extract
            results = await self._crawl_pages(target_pages)

            # 3. Store metrics
            metrics = await self._store_metrics(run_id, results)

            # 4. Emit event
            await self.bus.emit(
                event_type=EventType.PAGES_ANALYZED,
                site_id=self.site_id,
                source_module_id=self.module_id,
                source_module_type=self.MODULE_TYPE,
                source_run_id=run_id,
                payload={
                    "pages_analyzed": len(results),
                    "pages_ok": sum(1 for r in results if r["status_code"] == 200),
                    "pages_error": sum(1 for r in results if r["status_code"] != 200),
                    "keywords_extracted": sum(len(r.get("keywords", [])) for r in results),
                    "technical_issues": [
                        {"type": i["type"], "page": i["page"]}
                        for r in results for i in r.get("issues", [])
                    ],
                    "run_id": run_id,
                },
                targets=["entity-first-seo", "ux-conversion-optimizer", "ai-schema-engine"],
            )

            elapsed_ms = int((time.time() - started_at) * 1000)
            output = {
                "status": "success",
                "pages_analyzed": len(results),
                "keywords_extracted": metrics["keywords_total"],
                "technical_issues": metrics["issue_count"],
                "execution_time_ms": elapsed_ms,
            }
            logger.info(f"[seo-ai] Run {run_id} complete: {output}")
            return output

        except Exception as e:
            logger.error(f"[seo-ai] Run {run_id} failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _load_pages_from_db(self, limit: int) -> list[str]:
        """Load page URLs for this site from DB"""
        rows = await self.db.execute(
            "SELECT url FROM pages WHERE site_id = %s AND deleted_at IS NULL "
            "ORDER BY crawled_at ASC NULLS FIRST LIMIT %s",
            (self.site_id, limit),
        )
        return [row[0] for row in await rows.fetchall()]

    async def _crawl_pages(self, urls: list[str]) -> list[dict[str, Any]]:
        """Crawl pages concurrently and extract signals"""
        tasks = [self._crawl_one(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _crawl_one(self, url: str) -> dict[str, Any]:
        """Crawl a single page and extract SEO signals"""
        result: dict[str, Any] = {"url": url, "status_code": 0, "keywords": [], "issues": []}

        try:
            resp = await self.http.get(url, follow_redirects=True)
            result["status_code"] = resp.status_code
            result["content_hash"] = hashlib.sha256(resp.text.encode()).hexdigest()[:16]

            if resp.status_code == 200:
                body_preview = resp.text[:3000]  # token-efficient

                # LLM keyword extraction
                try:
                    llm_response, cost = await invoke_with_pool(
                        pool=self.llm,
                        task="keyword_extraction",
                        prompt=f"Page URL: {url}\n\nContent:\n{body_preview}",
                        system_prompt=SYSTEM_PROMPT,
                        constraints=LLMConstraints(max_cost_usd=0.05),
                    )
                    import json as _json
                    parsed = _json.loads(llm_response)
                    result["keywords"] = parsed.get("keywords", [])
                    result["title_assessment"] = parsed.get("title_assessment", "")
                    result["llm_cost"] = cost
                except Exception as e:
                    logger.warning(f"LLM extraction failed for {url}: {e}")
                    result["keywords"] = []

                # Basic technical checks
                issues = []
                if "<h1" not in resp.text.lower():
                    issues.append({"type": "missing_h1", "page": url})
                if 'rel="canonical"' not in resp.text.lower():
                    issues.append({"type": "missing_canonical", "page": url})
                result["issues"] = issues

        except httpx.TimeoutException:
            result["status_code"] = 408
            result["issues"] = [{"type": "timeout", "page": url}]
        except Exception as e:
            result["status_code"] = 0
            result["issues"] = [{"type": "crawl_error", "page": url, "error": str(e)}]

        return result

    async def _store_metrics(self, run_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Persist metrics to the metrics table"""
        keywords_total = sum(len(r.get("keywords", [])) for r in results)
        issue_count = sum(len(r.get("issues", [])) for r in results)
        ok_count = sum(1 for r in results if r["status_code"] == 200)

        metrics_rows = [
            (self.site_id, run_id, self.module_id, "pages_analyzed", len(results), "count"),
            (self.site_id, run_id, self.module_id, "pages_ok", ok_count, "count"),
            (self.site_id, run_id, self.module_id, "keywords_extracted", keywords_total, "count"),
            (self.site_id, run_id, self.module_id, "technical_issues", issue_count, "count"),
        ]

        await self.db.executemany(
            "INSERT INTO metrics (site_id, run_id, module_id, metric_name, value, unit) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            metrics_rows,
        )
        await self.db.commit()

        return {"keywords_total": keywords_total, "issue_count": issue_count}

    async def close(self):
        await self.http.aclose()
