#!/usr/bin/env python3
"""Smoke gate for God Intelligence endpoints (11 core + 5 Frase-style)."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

import httpx


@dataclass
class EndpointResult:
    name: str
    method: str
    path: str
    status: int
    ok: bool
    detail: str


def _print_result(result: EndpointResult) -> None:
    icon = "PASS" if result.ok else "FAIL"
    print(f"[{icon}] {result.method:<4} {result.path:<40} status={result.status:<3} {result.name}")
    if result.detail:
        print(f"       -> {result.detail}")


def _record(results: list[EndpointResult], name: str, method: str, path: str, response: httpx.Response, ok: bool, detail: str = "") -> None:
    result = EndpointResult(name=name, method=method, path=path, status=response.status_code, ok=ok, detail=detail)
    results.append(result)
    _print_result(result)


def wait_for_health(client: httpx.Client, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = client.get("/health")
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke gate for intelligence endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="FastAPI base URL")
    parser.add_argument("--org-id", default="test-org-001", help="Org id header value")
    parser.add_argument("--token", default="test-token", help="Bearer token value")
    parser.add_argument("--health-timeout", type=int, default=30, help="Seconds to wait for /health")
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Org-ID": args.org_id,
        "Content-Type": "application/json",
    }

    results: list[EndpointResult] = []

    with httpx.Client(base_url=args.base_url, timeout=30.0, headers=headers) as client:
        if not wait_for_health(client, args.health_timeout):
            print("[FAIL] GET  /health                                  status=0   Health check not ready")
            return 2

        target_payload = {
            "name": f"SmokeTarget-{int(time.time())}",
            "domain": "example.com",
            "twitter_handle": "example",
            "reddit_username": "example",
            "category": "competitor",
            "priority": 3,
            "track_website": True,
            "track_ads": True,
            "track_social": True,
            "track_news": True,
        }

        response = client.post("/api/intel/targets", json=target_payload)
        add_ok = response.status_code == 200 and response.json().get("success") is True
        target_id = response.json().get("target_id") if add_ok else None
        _record(results, "Add target", "POST", "/api/intel/targets", response, add_ok)

        response = client.get("/api/intel/targets")
        _record(results, "List targets", "GET", "/api/intel/targets", response, response.status_code == 200)

        if target_id:
            response = client.post(f"/api/intel/targets/{target_id}/scan")
            _record(results, "Trigger target scan", "POST", f"/api/intel/targets/{target_id}/scan", response, response.status_code == 200)
        else:
            results.append(EndpointResult("Trigger target scan", "POST", "/api/intel/targets/{id}/scan", 0, False, "Skipped: no target_id"))
            _print_result(results[-1])

        response = client.get("/api/intel/posts?limit=10")
        _record(results, "Get posts", "GET", "/api/intel/posts", response, response.status_code == 200)

        response = client.get("/api/intel/posts/viral?limit=10")
        _record(results, "Get viral posts", "GET", "/api/intel/posts/viral", response, response.status_code == 200)

        response = client.get("/api/intel/ads?limit=10")
        _record(results, "Get ads", "GET", "/api/intel/ads", response, response.status_code == 200)

        trend_payload = {"keywords": ["ai seo", "competitive intelligence"], "platforms": ["reddit", "twitter"]}
        response = client.post("/api/intel/trends/scan", json=trend_payload)
        _record(results, "Scan trends", "POST", "/api/intel/trends/scan", response, response.status_code == 200)

        response = client.get("/api/intel/trends?limit=10")
        _record(results, "Get trends", "GET", "/api/intel/trends", response, response.status_code == 200)

        roi_payload = {
            "content_brief": "Production smoke: AI content strategy for enterprise teams.",
            "platform": "linkedin",
            "audience_size": 50000,
            "trend_phase": "growing",
            "budget_usd": 1000,
        }
        response = client.post("/api/intel/roi/predict", json=roi_payload)
        _record(results, "Predict ROI", "POST", "/api/intel/roi/predict", response, response.status_code == 200)

        brief_payload = {"platform": "twitter", "topic": "AI content operations"}
        response = client.post("/api/intel/content-brief", json=brief_payload)
        _record(results, "Generate content brief", "POST", "/api/intel/content-brief", response, response.status_code == 200)

        response = client.get("/api/intel/dashboard")
        _record(results, "Load dashboard", "GET", "/api/intel/dashboard", response, response.status_code == 200)

        # Frase-style endpoints
        serp_payload = {"keyword": "competitive intelligence software", "location": "com", "language": "en", "limit": 5}
        response = client.post("/api/intel/frase/serp-analyze", json=serp_payload)
        _record(results, "Frase SERP analyze", "POST", "/api/intel/frase/serp-analyze", response, response.status_code == 200)

        questions_payload = {"keyword": "competitive intelligence", "limit": 20}
        response = client.post("/api/intel/frase/questions", json=questions_payload)
        _record(results, "Frase question mining", "POST", "/api/intel/frase/questions", response, response.status_code == 200)

        clusters_payload = {
            "seed_keywords": [
                "competitive intelligence platform",
                "competitor analysis workflow",
                "topic clusters for seo",
                "serp research software",
            ],
            "max_clusters": 4,
        }
        response = client.post("/api/intel/frase/topic-clusters", json=clusters_payload)
        _record(results, "Frase topic clusters", "POST", "/api/intel/frase/topic-clusters", response, response.status_code == 200)

        draft = (
            "Competitive intelligence software helps teams monitor market changes. "
            "This draft explains data collection, analysis, and execution workflows across channels."
        )
        gap_payload = {"keyword": "competitive intelligence software", "draft_content": draft, "limit": 5}
        response = client.post("/api/intel/frase/content-gap", json=gap_payload)
        gap_ok = response.status_code == 200
        missing_terms: list[str] = []
        if gap_ok:
            missing_terms = response.json().get("content_gap", {}).get("missing_terms", [])
        _record(
            results,
            "Frase content gap",
            "POST",
            "/api/intel/frase/content-gap",
            response,
            gap_ok,
            detail=f"missing_terms={len(missing_terms)}",
        )

        optimize_payload = {
            "keyword": "competitive intelligence software",
            "draft_content": draft,
            "required_terms": missing_terms[:10],
            "recommended_questions": ["How does it work?", "What are the best tools?"],
        }
        response = client.post("/api/intel/frase/optimize", json=optimize_payload)
        optimize_ok = response.status_code == 200
        score = None
        if optimize_ok:
            score = response.json().get("audit", {}).get("optimization_score")
        _record(
            results,
            "Frase optimize",
            "POST",
            "/api/intel/frase/optimize",
            response,
            optimize_ok,
            detail=f"optimization_score={score}",
        )

    passed = sum(1 for r in results if r.ok)
    total = len(results)
    print("\n=== INTELLIGENCE SMOKE SUMMARY ===")
    print(f"Passed: {passed}/{total}")

    if passed != total:
        print("Failed endpoints:")
        for item in results:
            if not item.ok:
                print(f"- {item.method} {item.path} ({item.status}) {item.name}")
        return 1

    print("All intelligence endpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
