"""Seo/Platform service: extract waterfall."""

from ..constants import OLLAMA_BASE_URL
from ..constants import OLLAMA_TIMEOUT
from ..constants import SEO_DEFAULT_MODEL
from ..constants import SEO_OLLAMA_CACHE_MAX_ENTRIES
from ..constants import SEO_OLLAMA_CACHE_TTL_SEC
from ..constants import _OLLAMA_CACHE
from ..constants import _OLLAMA_CACHE_LOCK
from ..constants import _OLLAMA_INFLIGHT
from ..constants import logger
from ..schemas import PerformanceAuditReq
from .get_shared_job_store import _extract_core_vitals
from .get_shared_job_store import _extract_scores
from .get_shared_job_store import _perf_float
from .get_shared_job_store import _perf_int
from .get_shared_job_store import _run_crux
from .get_shared_job_store import _run_http_probe
from .get_shared_job_store import _run_lighthouse
from .get_shared_job_store import _run_network_probe
from .get_shared_job_store import _run_pagespeed
from .get_shared_job_store import _run_webpagetest
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast
import asyncio
import copy
import hashlib
import httpx
import json
import time


def _extract_waterfall(lhr: dict[str, Any]) -> dict[str, Any]:
    audits = lhr.get("audits") if isinstance(lhr.get("audits"), dict) else {}
    diagnostics = audits.get("diagnostics") if isinstance(audits.get("diagnostics"), dict) else {}
    details = diagnostics.get("details") if isinstance(diagnostics.get("details"), dict) else {}
    items = details.get("items") if isinstance(details.get("items"), list) else []
    reqs = 0
    transfer_kb = 0
    if items:
        row = items[0] if isinstance(items[0], dict) else {}
        reqs = _perf_int(row.get("numRequests"), 0)
        transfer_kb = _perf_int(_perf_float(row.get("totalByteWeight"), 0.0) / 1024.0, 0)
    blocking: list[str] = []
    render_blocking = (
        audits.get("render-blocking-resources") if isinstance(audits.get("render-blocking-resources"), dict) else {}
    )
    rb_details = render_blocking.get("details") if isinstance(render_blocking.get("details"), dict) else {}
    rb_items: list[Any] = cast(list[Any], rb_details.get("items")) if isinstance(rb_details.get("items"), list) else []
    for item in rb_items[:10]:
        if isinstance(item, dict):
            item_url = str(item.get("url", "") or "")
            if item_url:
                blocking.append(item_url)
    core = _extract_core_vitals(lhr)
    return {
        "requests": reqs,
        "transfer_kb": transfer_kb,
        "render_blocking": blocking,
        "timeline_ms": {"dns": 0, "tcp": 0, "tls": 0, "ttfb": _perf_int(core.get("ttfb_ms"), 0), "download": 0},
    }


def _extract_filmstrip(lhr: dict[str, Any]) -> list[dict[str, Any]]:
    audits = lhr.get("audits") if isinstance(lhr.get("audits"), dict) else {}
    thumbs = audits.get("screenshot-thumbnails") if isinstance(audits.get("screenshot-thumbnails"), dict) else {}
    details = thumbs.get("details") if isinstance(thumbs.get("details"), dict) else {}
    items: list[Any] = cast(list[Any], details.get("items")) if isinstance(details.get("items"), list) else []
    frames: list[dict[str, Any]] = []
    for idx, item in enumerate(items[:10]):
        if not isinstance(item, dict):
            continue
        frames.append(
            {
                "label": f"frame_{idx + 1}",
                "timestamp_ms": _perf_int(item.get("timing"), 0),
                "asset": str(item.get("data", "") or ""),
            }
        )
    return frames


def _extract_crux_field(crux: dict[str, Any]) -> dict[str, Any]:
    record = crux.get("record") if isinstance(crux.get("record"), dict) else {}
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}

    def _p75(key: str) -> float:
        metric = metrics.get(key) if isinstance(metrics, dict) else None
        percentiles = metric.get("percentiles") if isinstance(metric, dict) else None
        return _perf_float(percentiles.get("p75") if isinstance(percentiles, dict) else 0.0, 0.0)

    lcp = _p75("largest_contentful_paint")
    inp = _p75("interaction_to_next_paint")
    cls = _p75("cumulative_layout_shift")
    return {
        "lcp_p75_ms": _perf_int(lcp, 0),
        "inp_p75_ms": _perf_int(inp, 0),
        "cls_p75": round(cls, 4),
        "sample_size": 0,
        "period": "28d",
        "source": "crux_api",
    }


async def _run_free_performance_stack(req: PerformanceAuditReq) -> dict[str, Any] | None:
    strategy = "desktop" if req.target_device == "desktop" else "mobile"
    lighthouse_task = _run_lighthouse(req.url, strategy)
    pagespeed_task = _run_pagespeed(req.url, strategy)
    crux_task = _run_crux(req.url)
    webpagetest_task = _run_webpagetest(req.url, req.target_region, strategy)
    http_probe_task = _run_http_probe(req.url)
    network_probe_task = _run_network_probe(req.url)
    provider_results: tuple[object, object, object, object, object, object] = await asyncio.gather(
        lighthouse_task,
        pagespeed_task,
        crux_task,
        webpagetest_task,
        http_probe_task,
        network_probe_task,
        return_exceptions=True,
    )
    lighthouse, pagespeed, crux, webpagetest, http_probe, network_probe = provider_results
    lh_payload = cast(dict[str, Any] | None, lighthouse if isinstance(lighthouse, dict) else None)
    psi_payload = cast(dict[str, Any] | None, pagespeed if isinstance(pagespeed, dict) else None)
    crux_payload = cast(dict[str, Any] | None, crux if isinstance(crux, dict) else None)
    wpt_payload = cast(dict[str, Any] | None, webpagetest if isinstance(webpagetest, dict) else None)
    probe_payload = cast(dict[str, Any] | None, http_probe if isinstance(http_probe, dict) else None)
    network_payload = cast(dict[str, Any] | None, network_probe if isinstance(network_probe, dict) else None)
    probe_estimated = (
        probe_payload.get("estimated") if isinstance(probe_payload and probe_payload.get("estimated"), dict) else {}
    )
    network_estimated = (
        network_payload.get("estimated")
        if isinstance(network_payload and network_payload.get("estimated"), dict)
        else {}
    )
    probe_ttfb = _perf_int(probe_payload.get("ttfb_ms") if isinstance(probe_payload, dict) else 0, 0)
    probe_elapsed = _perf_int(probe_payload.get("elapsed_ms") if isinstance(probe_payload, dict) else 0, 0)
    probe_transfer_kb = _perf_int(probe_payload.get("transfer_kb") if isinstance(probe_payload, dict) else 0, 0)
    network_ttfb = _perf_int(network_estimated.get("ttfb_ms"), 0)
    lhr = None
    if lh_payload and isinstance(lh_payload.get("audits"), dict):
        lhr = lh_payload
    elif psi_payload:
        lh_result = psi_payload.get("lighthouseResult")
        lhr = lh_result if isinstance(lh_result, dict) else None
    if not lhr and (not crux_payload) and (not wpt_payload) and (not probe_payload) and (not network_payload):
        return None
    scores = (
        _extract_scores(lhr)
        if isinstance(lhr, dict)
        else {
            "performance": _perf_int(
                probe_estimated.get("performance_score") or network_estimated.get("performance_score"), 0
            ),
            "seo": 0,
            "best_practices": 0,
            "accessibility": 0,
        }
    )
    core = (
        _extract_core_vitals(lhr)
        if isinstance(lhr, dict)
        else {
            "lcp_ms": _perf_int(probe_estimated.get("lcp_ms") or network_estimated.get("lcp_ms"), 0),
            "inp_ms": _perf_int(probe_estimated.get("inp_ms") or network_estimated.get("inp_ms"), 0),
            "cls": _perf_float(probe_estimated.get("cls") or network_estimated.get("cls"), 0.0),
            "ttfb_ms": probe_ttfb or network_ttfb,
        }
    )
    waterfall = (
        _extract_waterfall(lhr)
        if isinstance(lhr, dict)
        else {
            "requests": 1,
            "transfer_kb": probe_transfer_kb,
            "render_blocking": [],
            "timeline_ms": {
                "dns": _perf_int(network_payload.get("dns_ms") if isinstance(network_payload, dict) else 0, 0),
                "tcp": _perf_int(network_payload.get("tcp_ms") if isinstance(network_payload, dict) else 0, 0),
                "tls": 0,
                "ttfb": probe_ttfb or network_ttfb,
                "download": max(0, (probe_elapsed or network_ttfb) - (probe_ttfb or network_ttfb)),
            },
        }
    )
    filmstrip = _extract_filmstrip(lhr) if isinstance(lhr, dict) else []
    field = (
        _extract_crux_field(crux_payload)
        if isinstance(crux_payload, dict)
        else {
            "lcp_p75_ms": core.get("lcp_ms", 0),
            "inp_p75_ms": core.get("inp_ms", 0),
            "cls_p75": core.get("cls", 0.0),
            "sample_size": 0,
            "period": "28d",
            "source": "lab_estimate",
        }
    )
    providers = {
        "lighthouse_cli": bool(lh_payload),
        "pagespeed_api": bool(psi_payload),
        "crux_api": bool(crux_payload),
        "webpagetest_public": bool(wpt_payload),
        "http_probe": bool(probe_payload),
        "network_probe": bool(network_payload),
    }
    return {
        "performance_score": _perf_int(scores.get("performance"), 0),
        "lighthouse": scores,
        "core_web_vitals": core,
        "field_web_vitals": field,
        "waterfall": waterfall,
        "filmstrip": filmstrip,
        "rum_summary": {
            "sessions": _perf_int(field.get("sample_size"), 0),
            "rage_click_rate": 0.0,
            "friction_score": max(0, min(100, 100 - _perf_int(core.get("inp_ms"), 0) // 4)),
            "device_mix": {"mobile": 0.62, "desktop": 0.33, "tablet": 0.05},
            "network_mix": {"3g": 0.14, "4g": 0.56, "5g": 0.22, "wifi": 0.08},
            "geo_isp_breakdown": [],
        },
        "history": {
            "trend": "stable",
            "regression_detected": False,
            "runs": [
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "performance_score": _perf_int(scores.get("performance"), 0),
                    "lcp_ms": _perf_int(core.get("lcp_ms"), 0),
                    "cls": _perf_float(core.get("cls"), 0.0),
                }
            ],
        },
        "recommended_stack": [
            "lighthouse_cli",
            "pagespeed_insights_api",
            "chrome_ux_report_api",
            "webpagetest_public_api",
            "http_probe",
            "network_probe",
            "web_vitals_rum",
            "playwright_cdp",
        ],
        "vendor_stack": [
            {"vendor": "Lighthouse CLI", "usage": "Local synthetic audits"},
            {"vendor": "PageSpeed Insights API", "usage": "Google-run Lighthouse + lab diagnostics"},
            {"vendor": "Chrome UX Report API", "usage": "Field p75 vitals"},
            {"vendor": "WebPageTest Public API", "usage": "Optional global run + waterfall/video"},
            {"vendor": "HTTP Probe", "usage": "Direct real-time origin reachability and latency telemetry"},
            {"vendor": "Network Probe", "usage": "DNS and TCP handshake timing for resilient live telemetry"},
            {"vendor": "web-vitals RUM", "usage": "First-party client field telemetry"},
        ],
        "free_provider_status": providers,
        "data_provenance": {"source": "free_providers", "at": datetime.now(UTC).isoformat()},
    }


async def _ollama_json(
    system: str, user: str, model: str = SEO_DEFAULT_MODEL, timeout_seconds: float | None = None
) -> dict[str, Any]:
    """
    Call Ollama chat API and parse JSON from the response.
    Returns a dict; falls back to {"error": reason, "fallback": True} on failure.
    """
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }
    cache_key = ""
    parsed: dict[str, Any] = {}
    if SEO_OLLAMA_CACHE_TTL_SEC > 0:
        key_source = json.dumps({"model": model, "system": system, "user": user}, sort_keys=True, separators=(",", ":"))
        cache_key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
        now = time.monotonic()
        with _OLLAMA_CACHE_LOCK:
            cached = _OLLAMA_CACHE.get(cache_key)
            if cached and cached[0] > now:
                return copy.deepcopy(cached[1])
            if cached and cached[0] <= now:
                _OLLAMA_CACHE.pop(cache_key, None)
            inflight = _OLLAMA_INFLIGHT.get(cache_key)
            if inflight is None:
                _OLLAMA_INFLIGHT[cache_key] = asyncio.get_running_loop().create_future()
        if inflight is not None:
            return copy.deepcopy(await inflight)
    try:
        timeout = OLLAMA_TIMEOUT if timeout_seconds is None else max(1.0, float(timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            r.raise_for_status()
            raw = r.json().get("message", {}).get("content", "{}")
            parsed = json.loads(raw)
            if cache_key and isinstance(parsed, dict) and (not parsed.get("fallback")) and (not parsed.get("error")):
                expires_at = time.monotonic() + float(SEO_OLLAMA_CACHE_TTL_SEC)
                with _OLLAMA_CACHE_LOCK:
                    if len(_OLLAMA_CACHE) >= SEO_OLLAMA_CACHE_MAX_ENTRIES:
                        oldest_key = next(iter(_OLLAMA_CACHE), None)
                        if oldest_key is not None:
                            _OLLAMA_CACHE.pop(oldest_key, None)
                    _OLLAMA_CACHE[cache_key] = (expires_at, parsed)
            return parsed
    except Exception as exc:
        logger.warning("Ollama SEO call failed: %s", exc)
        parsed = {"error": str(exc), "fallback": True}
        return parsed
    finally:
        if cache_key:
            with _OLLAMA_CACHE_LOCK:
                fut = _OLLAMA_INFLIGHT.pop(cache_key, None)
            if fut is not None and (not fut.done()):
                import contextlib

                with contextlib.suppress(Exception):
                    fut.set_result(parsed)
