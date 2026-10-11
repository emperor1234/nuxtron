"""Seo/Platform service: get shared job store."""

from ..constants import SEO_PERF_CHROME_PATH
from ..constants import SEO_PERF_CRUX_API_KEY
from ..constants import SEO_PERF_FREE_TIMEOUT_SEC
from ..constants import SEO_PERF_LIGHTHOUSE_PATH
from ..constants import SEO_PERF_PSI_API_KEY
from ..constants import SEO_PERF_WEBPAGETEST_API_KEY
from ..constants import SEO_UPSTASH_TIMEOUT_SEC
from ..constants import _BLOCKED
from ..constants import _STRICT_NO_MOCK_FALSY
from ..constants import _shared_job_store
from ....identity.async_egress import safe_outbound_get_async
from ....identity.secure_egress import resolve_outbound_target
from fastapi import HTTPException
from typing import Any
import asyncio
import httpx
import json
import os
import re
import shutil
import socket
import subprocess
import time


def get_shared_job_store() -> dict[str, dict[str, Any]]:
    """Return the live job store for external readers (e.g. platform_intelligence router)."""
    return _shared_job_store


def _strict_no_mock_mode() -> bool:
    raw = os.getenv("SEO_STRICT_NO_MOCK", "").strip().lower()
    if raw:
        return raw not in _STRICT_NO_MOCK_FALSY
    return os.getenv("ENV", "").strip().lower() == "production"


def _upstash_rest_base_url() -> str:
    return os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")


def _upstash_rest_token() -> str:
    return os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()


def _seo_analysis_dist_cache_enabled() -> bool:
    return bool(_upstash_rest_base_url()) and bool(_upstash_rest_token())


def _upstash_command(command: list[str]) -> object | None:
    base_url = _upstash_rest_base_url()
    token = _upstash_rest_token()
    if not base_url or not token:
        return None
    try:
        with httpx.Client(timeout=SEO_UPSTASH_TIMEOUT_SEC) as client:
            response = client.post(
                f"{base_url}/pipeline",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=[command],
            )
        if not response.is_success:
            return None
        payload_obj = response.json()
        payload_list = payload_obj if isinstance(payload_obj, list) else []
        if payload_list:
            first_obj = payload_list[0]
            if isinstance(first_obj, dict):
                return first_obj.get("result")
        return None
    except Exception:
        return None


def _seo_analysis_cache_key(tenant_id: str, module: str, payload_hash: str) -> str:
    return f"seo:analysis:v1:{tenant_id}:{module}:{payload_hash}"


def _perf_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _perf_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _perf_percentile(values: list[float], percentile: float) -> float:
    cleaned = sorted((value for value in values if value >= 0))
    if not cleaned:
        return 0.0
    rank = max(0, min(len(cleaned) - 1, int(round((len(cleaned) - 1) * percentile))))
    return cleaned[rank]


def _normalize_perf_metric_name(metric_name: str) -> str:
    key = str(metric_name or "").strip().lower().replace("-", "_")
    mapping = {
        "lcp": "lcp",
        "largest_contentful_paint": "lcp",
        "largestcontentfulpaint": "lcp",
        "inp": "inp",
        "interaction_to_next_paint": "inp",
        "interactiontonextpaint": "inp",
        "cls": "cls",
        "cumulative_layout_shift": "cls",
        "cumulativelayoutshift": "cls",
        "ttfb": "ttfb",
        "time_to_first_byte": "ttfb",
        "timetofirstbyte": "ttfb",
        "fcp": "fcp",
        "first_contentful_paint": "fcp",
        "firstcontentfulpaint": "fcp",
    }
    return mapping.get(key, "")


def _performance_score_from_field(field: dict[str, Any]) -> int:
    lcp_ok = _perf_int(field.get("lcp_p75_ms"), 0) <= 2500
    inp_ok = _perf_int(field.get("inp_p75_ms"), 0) <= 200
    cls_ok = _perf_float(field.get("cls_p75"), 0.0) <= 0.1
    ok_count = sum((1 for passed in (lcp_ok, inp_ok, cls_ok) if passed))
    return {0: 55, 1: 70, 2: 85, 3: 96}[ok_count]


def _lighthouse_command_candidates() -> list[list[str]]:
    candidates: list[list[str]] = []
    if SEO_PERF_LIGHTHOUSE_PATH:
        candidates.append([SEO_PERF_LIGHTHOUSE_PATH])
    lh_bin = shutil.which("lighthouse")
    if lh_bin:
        candidates.append([lh_bin])
    npx_bin = shutil.which("npx")
    if npx_bin:
        candidates.append([npx_bin, "--yes", "lighthouse"])
    return candidates


def _run_lighthouse_sync(url: str, strategy: str) -> dict[str, Any] | None:
    preset = "desktop" if strategy == "desktop" else "perf"
    for base_cmd in _lighthouse_command_candidates():
        cmd = [
            *base_cmd,
            url,
            "--output=json",
            "--output-path=stdout",
            "--quiet",
            "--only-categories=performance,seo,best-practices,accessibility",
            f"--preset={preset}",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
        ]
        if SEO_PERF_CHROME_PATH:
            cmd.append(f"--chrome-path={SEO_PERF_CHROME_PATH}")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=False, timeout=max(20, int(SEO_PERF_FREE_TIMEOUT_SEC)), check=False
            )
            if proc.returncode != 0:
                continue
            raw_stdout = proc.stdout or b""
            if isinstance(raw_stdout, bytes):
                content = raw_stdout.decode("utf-8", errors="replace").strip()
            else:
                content = str(raw_stdout or "").strip()
            if not content:
                continue
            first_brace = content.find("{")
            last_brace = content.rfind("}")
            candidate = (
                content[first_brace : last_brace + 1] if first_brace >= 0 and last_brace > first_brace else content
            )
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except Exception:
            continue
    return None


async def _run_lighthouse(url: str, strategy: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(_run_lighthouse_sync, url, strategy)


async def _run_pagespeed(url: str, strategy: str) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "seo", "best-practices", "accessibility"],
    }
    if SEO_PERF_PSI_API_KEY:
        params["key"] = SEO_PERF_PSI_API_KEY
    try:
        async with httpx.AsyncClient(timeout=max(5.0, SEO_PERF_FREE_TIMEOUT_SEC)) as client:
            response = await client.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params=params)
        if not response.is_success:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def _run_crux(url: str) -> dict[str, Any] | None:
    endpoint = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
    if SEO_PERF_CRUX_API_KEY:
        endpoint = f"{endpoint}?key={SEO_PERF_CRUX_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=max(5.0, SEO_PERF_FREE_TIMEOUT_SEC)) as client:
            response = await client.post(endpoint, json={"url": url})
        if not response.is_success:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def _run_webpagetest(url: str, location: str, strategy: str) -> dict[str, Any] | None:
    if not SEO_PERF_WEBPAGETEST_API_KEY:
        return None
    try:
        params = {
            "k": SEO_PERF_WEBPAGETEST_API_KEY,
            "url": url,
            "f": "json",
            "runs": "1",
            "location": location or "Dulles:Chrome",
            "mobile": "1" if strategy == "mobile" else "0",
            "lighthouse": "1",
            "video": "1",
        }
        async with httpx.AsyncClient(timeout=max(5.0, SEO_PERF_FREE_TIMEOUT_SEC)) as client:
            create = await client.get("https://www.webpagetest.org/runtest.php", params=params)
        if not create.is_success:
            return None
        created = create.json()
        data = created.get("data") if isinstance(created, dict) else None
        test_id = str(data.get("testId", "") if isinstance(data, dict) else "")
        if not test_id:
            return None
        for _ in range(6):
            await asyncio.sleep(2)
            async with httpx.AsyncClient(timeout=max(5.0, SEO_PERF_FREE_TIMEOUT_SEC)) as client:
                status_resp = await client.get(
                    "https://www.webpagetest.org/testStatus.php", params={"f": "json", "test": test_id}
                )
            if not status_resp.is_success:
                continue
            status_payload = status_resp.json()
            code = _perf_int(status_payload.get("statusCode"), 0)
            if code == 200:
                async with httpx.AsyncClient(timeout=max(5.0, SEO_PERF_FREE_TIMEOUT_SEC)) as client:
                    final_resp = await client.get(
                        "https://www.webpagetest.org/jsonResult.php", params={"f": "json", "test": test_id}
                    )
                if not final_resp.is_success:
                    return None
                final_payload = final_resp.json()
                return final_payload if isinstance(final_payload, dict) else None
    except Exception:
        return None
    return None


async def _run_http_probe(url: str) -> dict[str, Any] | None:
    try:
        started = time.perf_counter()
        target = resolve_outbound_target(url, allow_http=True)
        response = await safe_outbound_get_async(
            target,
            timeout=max(5.0, min(30.0, SEO_PERF_FREE_TIMEOUT_SEC)),
            allow_http=True,
            allowed_host_suffix=target.host,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
            max_response_bytes=2_000_000,
        )
        elapsed_ms = int(max(1.0, (time.perf_counter() - started) * 1000.0))
        body_text = response.text if isinstance(response.text, str) else ""
        transfer_kb = int(round(len(response.content or b"") / 1024.0))
        script_count = len(re.findall("<script\\\\b", body_text, flags=re.IGNORECASE))
        stylesheet_count = len(re.findall("<link[^>]+rel=[\\\"']?stylesheet", body_text, flags=re.IGNORECASE))
        ttfb_ms = min(elapsed_ms, 5000)
        lcp_estimate_ms = min(8000, max(1200, int(ttfb_ms * 2.1)))
        inp_estimate_ms = min(600, max(40, int(70 + script_count * 8)))
        cls_estimate = round(min(0.25, 0.03 + stylesheet_count * 0.003), 4)
        perf_score = max(1, min(100, int(round(100 - lcp_estimate_ms / 80.0 - transfer_kb / 90.0))))
        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "ttfb_ms": ttfb_ms,
            "transfer_kb": transfer_kb,
            "script_count": script_count,
            "stylesheet_count": stylesheet_count,
            "estimated": {
                "performance_score": perf_score,
                "lcp_ms": lcp_estimate_ms,
                "inp_ms": inp_estimate_ms,
                "cls": cls_estimate,
            },
        }
    except Exception:
        return None


def _run_network_probe_sync(url: str) -> dict[str, Any] | None:
    try:
        dns_started = time.perf_counter()
        target = resolve_outbound_target(url, allow_http=True)
        dns_ms = int(max(1.0, (time.perf_counter() - dns_started) * 1000.0))
        tcp_started = time.perf_counter()
        with socket.create_connection((target.address, target.port), timeout=8.0):
            pass
        tcp_ms = int(max(1.0, (time.perf_counter() - tcp_started) * 1000.0))
        ttfb_estimate_ms = min(5000, max(180, dns_ms + tcp_ms + 220))
        lcp_estimate_ms = min(8000, max(1200, int(ttfb_estimate_ms * 2.0)))
        inp_estimate_ms = min(450, max(60, int(90 + tcp_ms * 0.6)))
        cls_estimate = 0.06
        perf_score = max(1, min(100, int(round(100 - lcp_estimate_ms / 85.0))))
        return {
            "host": target.host,
            "ip": target.address,
            "dns_ms": dns_ms,
            "tcp_ms": tcp_ms,
            "estimated": {
                "performance_score": perf_score,
                "lcp_ms": lcp_estimate_ms,
                "inp_ms": inp_estimate_ms,
                "cls": cls_estimate,
                "ttfb_ms": ttfb_estimate_ms,
            },
        }
    except Exception:
        return None


async def _run_network_probe(url: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(_run_network_probe_sync, url)


def _extract_scores(lhr: dict[str, Any]) -> dict[str, int]:
    categories = lhr.get("categories") if isinstance(lhr.get("categories"), dict) else {}

    def _score(key: str) -> int:
        cat = categories.get(key) if isinstance(categories, dict) else None
        raw = _perf_float(cat.get("score") if isinstance(cat, dict) else 0.0, 0.0)
        scaled = raw * 100.0 if raw <= 1.0 else raw
        return max(0, min(100, int(round(scaled))))

    return {
        "performance": _score("performance"),
        "seo": _score("seo"),
        "best_practices": _score("best-practices"),
        "accessibility": _score("accessibility"),
    }


def _extract_core_vitals(lhr: dict[str, Any]) -> dict[str, Any]:
    audits = lhr.get("audits") if isinstance(lhr.get("audits"), dict) else {}

    def _num(key: str) -> float:
        node = audits.get(key) if isinstance(audits, dict) else None
        return _perf_float(node.get("numericValue") if isinstance(node, dict) else 0.0, 0.0)

    return {
        "lcp_ms": _perf_int(_num("largest-contentful-paint"), 0),
        "inp_ms": _perf_int(_num("interaction-to-next-paint"), 0),
        "cls": round(_perf_float(_num("cumulative-layout-shift"), 0.0), 4),
        "ttfb_ms": _perf_int(_num("server-response-time"), 0),
    }


def _clean(text: str, max_len: int = 4000) -> str:
    """Strip dangerous patterns and truncate."""
    if _BLOCKED.search(text):
        raise HTTPException(status_code=400, detail="Input contains blocked content.")
    return text[:max_len]
