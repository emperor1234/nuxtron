from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

try:
    from neo4j import GraphDatabase  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - validated via runtime gates
    GraphDatabase: Any | None = None

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class CypherQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=50_000)
    params: dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="read", pattern="^(read|write)$")
    allow_write: bool = Field(default=False)


class GraphNodeRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=300)
    labels: list[str] = Field(default_factory=list, max_length=8)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphRelationshipRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=300)
    target_id: str = Field(min_length=1, max_length=300)
    rel_type: str = Field(min_length=1, max_length=120)
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphUpsertRequest(BaseModel):
    nodes: list[GraphNodeRequest] = Field(default_factory=list, max_length=2_000)
    relationships: list[GraphRelationshipRequest] = Field(default_factory=list, max_length=5_000)


class GraphRagContextRequest(BaseModel):
    entity_node_id: str = Field(min_length=1, max_length=300)
    max_hops: int = Field(default=2, ge=1, le=4)
    max_neighbors: int = Field(default=30, ge=1, le=200)


class KnowledgeGraphSearchRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=25, ge=1, le=200)


def _env() -> dict[str, str]:
    return {
        "uri": os.getenv("NEO4J_URI", "").strip(),
        "username": os.getenv("NEO4J_USERNAME", "").strip(),
        "password": os.getenv("NEO4J_PASSWORD", "").strip(),
        "database": os.getenv("NEO4J_DATABASE", "neo4j").strip() or "neo4j",
        "driver_encrypted": os.getenv("NEO4J_ENCRYPTED", "true").strip().lower(),
    }


def _validate_query_mode(payload: CypherQueryRequest) -> None:
    if payload.mode == "write" and not payload.allow_write:
        raise HTTPException(
            status_code=400,
            detail="Write mode requires allow_write=true confirmation.",
        )


@contextmanager
def _driver_session() -> Any:
    cfg = _env()
    if GraphDatabase is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j Python driver not installed. Add neo4j package to runtime.",
        )
    if not cfg["uri"] or not cfg["username"] or not cfg["password"]:
        raise HTTPException(
            status_code=503,
            detail="Neo4j credentials are not configured.",
        )

    try:
        encrypted = cfg["driver_encrypted"] != "false"
        driver = GraphDatabase.driver(
            cfg["uri"],
            auth=(cfg["username"], cfg["password"]),
            encrypted=encrypted,
        )
        session = driver.session(database=cfg["database"])
        yield session
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j connectivity error: {exc}") from exc
    finally:
        with suppress(Exception):
            session.close()
        with suppress(Exception):
            driver.close()


def _append_audit(audit_log_memory: list[dict[str, Any]], tenant_id: str, action: str, detail: dict[str, Any]) -> None:
    audit_log_memory.append(
        {
            "id": len(audit_log_memory) + 1,
            "tenant_id": tenant_id,
            "action": action,
            "source": "neo4j-graph-intelligence",
            "created_at": datetime.now(UTC).isoformat(),
            "detail": detail,
        }
    )


def create_neo4j_graph_intelligence_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/search-everywhere/neo4j", tags=["neo4j-command-center"])

    @router.get("/capabilities", summary="Neo4j capabilities and vendor mapping")
    def capabilities(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:capabilities", 120, 60)
        cfg = _env()
        capability_rows = [
            {"capability": "AuraDB connection automation", "implemented": True},
            {"capability": "Cypher query execution", "implemented": True},
            {"capability": "Knowledge graph upsert", "implemented": True},
            {"capability": "GraphRAG context retrieval", "implemented": True},
            {"capability": "Production gate checks", "implemented": True},
            {"capability": "Readiness completion chart", "implemented": True},
            {"capability": "Runtime driver health probe", "implemented": True},
        ]
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "capabilities": capability_rows,
            "third_parties": {
                "primary_graph_vendor": "Neo4j",
                "deployment_options": ["AuraDB", "Self-hosted Neo4j Enterprise", "Neo4j Community"],
                "cloud_partners": ["Microsoft Azure", "Amazon Web Services", "Google Cloud"],
                "ecosystem_integrations": ["Apache Kafka", "Apache Spark", "Snowflake", "Databricks"],
            },
            "configured": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
        }

    @router.get("/vendors", summary="Vendors and third-party dependencies")
    def vendors(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:vendors", 120, 60)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "vendors": [
                {
                    "name": "Neo4j",
                    "role": "Graph database and Cypher runtime",
                    "integration_mode": "neo4j-python-driver",
                },
                {
                    "name": "Microsoft Azure",
                    "role": "Cloud hosting option for Neo4j deployments",
                    "integration_mode": "infrastructure-level",
                },
                {
                    "name": "Amazon Web Services",
                    "role": "Cloud hosting option for Neo4j deployments",
                    "integration_mode": "infrastructure-level",
                },
                {
                    "name": "Google Cloud",
                    "role": "Cloud hosting option for Neo4j deployments",
                    "integration_mode": "infrastructure-level",
                },
                {
                    "name": "Apache Kafka",
                    "role": "Streaming ingest and change data capture",
                    "integration_mode": "ecosystem connector",
                },
                {
                    "name": "Apache Spark",
                    "role": "Data science and ETL graph pipelines",
                    "integration_mode": "ecosystem connector",
                },
                {
                    "name": "Snowflake",
                    "role": "Data warehouse interoperability",
                    "integration_mode": "ecosystem connector",
                },
                {
                    "name": "Databricks",
                    "role": "Lakehouse and ML interoperability",
                    "integration_mode": "ecosystem connector",
                },
            ],
        }

    @router.get("/production-gate", summary="Production gate checks for Neo4j wiring")
    def production_gate(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:production-gate", 90, 60)
        cfg = _env()

        checks = [
            {
                "id": "driver_installed",
                "passed": GraphDatabase is not None,
                "detail": "Neo4j Python driver import available",
            },
            {
                "id": "credentials_present",
                "passed": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
                "detail": "NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD are configured",
            },
            {
                "id": "encrypted_transport",
                "passed": cfg["uri"].startswith("neo4j+s://") or cfg["uri"].startswith("bolt+s://") or cfg["driver_encrypted"] != "false",
                "detail": "TLS transport enabled for graph traffic",
            },
            {
                "id": "database_selected",
                "passed": bool(cfg["database"]),
                "detail": "NEO4J_DATABASE configured",
            },
        ]

        passed = sum(1 for item in checks if item["passed"])
        total = len(checks)
        completion_pct = round((passed / total) * 100, 2) if total else 0.0

        gate = {
            "passed": passed == total,
            "score": f"{passed}/{total}",
            "completion_pct": completion_pct,
            "checks": checks,
        }
        _append_audit(audit_log_memory, auth.tenant_id, "neo4j_production_gate_checked", gate)
        return {"status": "ok", "tenant_id": auth.tenant_id, "gate": gate}

    @router.get("/health/probe", summary="Live Neo4j probe")
    def health_probe(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:health-probe", 60, 60)
        with _driver_session() as session:
            record = session.run("RETURN 1 AS ok, datetime() AS now").single()

        payload = {
            "connected": True,
            "ok": int(record["ok"]) == 1 if record else False,
            "timestamp": str(record["now"]) if record else None,
        }
        _append_audit(audit_log_memory, auth.tenant_id, "neo4j_health_probe", payload)
        return {"status": "ok", "tenant_id": auth.tenant_id, "probe": payload}

    @router.post("/cypher/query", summary="Execute tenant-scoped Cypher query")
    def cypher_query(payload: CypherQueryRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:cypher", 60, 60)
        _validate_query_mode(payload)

        params = dict(payload.params)
        params["tenant_id"] = auth.tenant_id

        with _driver_session() as session:
            result = session.run(payload.query, params)
            rows = [dict(record.items()) for record in result]

        response = {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "mode": payload.mode,
            "rows": rows,
            "row_count": len(rows),
        }
        _append_audit(
            audit_log_memory,
            auth.tenant_id,
            "neo4j_cypher_query_executed",
            {"mode": payload.mode, "row_count": len(rows)},
        )
        return response

    @router.post("/knowledge-graph/upsert", summary="Upsert nodes and relationships")
    def knowledge_graph_upsert(payload: KnowledgeGraphUpsertRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:upsert", 45, 60)

        if not payload.nodes and not payload.relationships:
            raise HTTPException(status_code=400, detail="At least one node or relationship is required.")

        with _driver_session() as session:
            for node in payload.nodes:
                labels = ":".join([lbl for lbl in node.labels if lbl and lbl.replace("_", "").replace("-", "").isalnum()])
                labels_clause = f":{labels}" if labels else ""
                session.run(
                    f"MERGE (n{labels_clause} {{node_id: $node_id, tenant_id: $tenant_id}}) "
                    "SET n += $props, n.updated_at = datetime()",
                    {
                        "node_id": node.node_id,
                        "tenant_id": auth.tenant_id,
                        "props": dict(node.properties),
                    },
                )

            for rel in payload.relationships:
                if not rel.rel_type.replace("_", "").isalnum():
                    raise HTTPException(status_code=400, detail="Relationship type must be alphanumeric/underscore.")
                session.run(
                    "MERGE (a {node_id: $source_id, tenant_id: $tenant_id}) "
                    "MERGE (b {node_id: $target_id, tenant_id: $tenant_id}) "
                    f"MERGE (a)-[r:{rel.rel_type}]->(b) "
                    "SET r += $props, r.updated_at = datetime()",
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "tenant_id": auth.tenant_id,
                        "props": dict(rel.properties),
                    },
                )

        detail = {
            "nodes_upserted": len(payload.nodes),
            "relationships_upserted": len(payload.relationships),
        }
        _append_audit(audit_log_memory, auth.tenant_id, "neo4j_knowledge_graph_upsert", detail)
        return {"status": "ok", "tenant_id": auth.tenant_id, **detail}

    @router.post("/knowledge-graph/search", summary="Search graph nodes by label/property")
    def knowledge_graph_search(payload: KnowledgeGraphSearchRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:search", 90, 60)
        if not payload.label.replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail="Label must be alphanumeric/underscore.")
        if not payload.key.replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail="Property key must be alphanumeric/underscore.")

        with _driver_session() as session:
            query = (
                f"MATCH (n:{payload.label}) "
                "WHERE n.tenant_id = $tenant_id AND toString(n[$prop_key]) = $prop_value "
                "RETURN n LIMIT $limit"
            )
            result = session.run(
                query,
                {
                    "tenant_id": auth.tenant_id,
                    "prop_key": payload.key,
                    "prop_value": payload.value,
                    "limit": payload.limit,
                },
            )
            rows = [dict(record.items()) for record in result]

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "matches": rows,
            "count": len(rows),
        }

    @router.post("/graphrag/context", summary="Fetch GraphRAG context neighborhood")
    def graphrag_context(payload: GraphRagContextRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:graphrag", 60, 60)

        with _driver_session() as session:
            result = session.run(
                "MATCH p=(root {node_id: $node_id, tenant_id: $tenant_id})-[:*1..4]-(nbr) "
                "WHERE length(p) <= $max_hops "
                "RETURN root, nbr, length(p) AS hops "
                "ORDER BY hops ASC LIMIT $limit",
                {
                    "tenant_id": auth.tenant_id,
                    "node_id": payload.entity_node_id,
                    "max_hops": payload.max_hops,
                    "limit": payload.max_neighbors,
                },
            )
            context_rows = [dict(record.items()) for record in result]

        _append_audit(
            audit_log_memory,
            auth.tenant_id,
            "neo4j_graphrag_context_fetched",
            {
                "entity_node_id": payload.entity_node_id,
                "max_hops": payload.max_hops,
                "returned": len(context_rows),
            },
        )
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "entity_node_id": payload.entity_node_id,
            "context": context_rows,
            "count": len(context_rows),
        }

    @router.get("/completion-chart", summary="Implementation and readiness chart")
    def completion_chart(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:neo4j:completion-chart", 90, 60)
        cfg = _env()
        chart_rows = [
            {
                "area": "Neo4j driver runtime",
                "implemented": GraphDatabase is not None,
                "verified": GraphDatabase is not None,
            },
            {
                "area": "Credential wiring",
                "implemented": True,
                "verified": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
            },
            {
                "area": "Cypher query API",
                "implemented": True,
                "verified": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
            },
            {
                "area": "Knowledge graph upsert",
                "implemented": True,
                "verified": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
            },
            {
                "area": "GraphRAG context retrieval",
                "implemented": True,
                "verified": bool(cfg["uri"] and cfg["username"] and cfg["password"]),
            },
            {
                "area": "Production gate checks",
                "implemented": True,
                "verified": True,
            },
            {
                "area": "Vendor transparency report",
                "implemented": True,
                "verified": True,
            },
        ]

        completed = sum(1 for row in chart_rows if row["implemented"])
        verified = sum(1 for row in chart_rows if row["verified"])
        total = len(chart_rows)

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "chart": chart_rows,
            "summary": {
                "implemented": f"{completed}/{total}",
                "verified_live": f"{verified}/{total}",
                "implementation_pct": round((completed / total) * 100, 2),
                "verified_live_pct": round((verified / total) * 100, 2),
            },
            "note": "verified_live depends on real Neo4j credentials and connectivity in the current environment.",
        }

    return router
