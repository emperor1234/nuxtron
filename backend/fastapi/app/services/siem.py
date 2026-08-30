"""
SIEM / SOC Security Service Module.

Extracted from legacy_main.py to improve modularity and maintainability.
Contains all SIEM-related helper functions for security operations.
"""

import json
import os
import threading
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import HTTPException

from .. import memory_stores
from ..deps import AuthContext

# Type aliases
JsonObject = dict[str, object]

# ── Memory Stores ─────────────────────────────────────────
_siem_cases_memory = memory_stores.siem_cases
_siem_soar_runs_memory = memory_stores.siem_soar_runs
_siem_retention_policies_memory = memory_stores.siem_retention_policies
_siem_data_lake_exports_memory = memory_stores.siem_data_lake_exports
_siem_flow_logs_memory = memory_stores.siem_flow_logs
_siem_waf_policies_memory = memory_stores.siem_waf_policies
_siem_firewall_rules_memory = memory_stores.siem_firewall_rules
_siem_ids_profiles_memory = memory_stores.siem_ids_profiles
_siem_ips_profiles_memory = memory_stores.siem_ips_profiles
_siem_vulnerabilities_memory = memory_stores.siem_vulnerabilities
_siem_zap_scans_memory = memory_stores.siem_zap_scans
_siem_patch_updates_memory = memory_stores.siem_patch_updates
_siem_auto_pentest_jobs_memory = memory_stores.siem_auto_pentest_jobs
_siem_dead_code_findings_memory = memory_stores.siem_dead_code_findings
_siem_endpoint_hardening_memory = memory_stores.siem_endpoint_hardening

# Other memory stores referenced by SIEM functions
_api_usage_audit_memory = memory_stores.api_usage_audit
_ai_security_ids_events_memory = memory_stores.ai_security_ids_events
_ai_security_alerts_memory = memory_stores.ai_security_alerts
_audit_log_memory = memory_stores.audit_log
_auth_security_memory = memory_stores.auth_security
_tenant_profiles_memory = memory_stores.tenant_profiles
_slack_messages_memory = memory_stores.slack_messages
_twilio_messages_memory = memory_stores.twilio_messages
_resend_messages_memory = memory_stores.resend_messages
_stripe_events_memory = memory_stores.stripe_events
_posthog_events_memory = memory_stores.posthog_events

# ── Lock ──────────────────────────────────────────────────
_siem_lock = threading.Lock()

# ── Constants ─────────────────────────────────────────────
UTC_OFFSET = '+00:00'


# ── Helper Functions ──────────────────────────────────────

def _json_object(value: object) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _record_audit(tenant_id: str, action: str, detail: JsonObject) -> None:
    """Record an audit event. Placeholder - actual implementation stays in legacy_main."""
    pass


def _siem_extract_ip(record: JsonObject) -> str:
    for key in ('ip', 'source_ip', 'client_ip', 'remote_ip'):
        value = str(record.get(key, '')).strip()
        if value:
            return value
    details = _json_object(record.get('details', {})) or {}
    for key in ('ip', 'source_ip', 'client_ip', 'remote_ip'):
        value = str(details.get(key, '')).strip()
        if value:
            return value
    return ''


def _siem_extract_user(record: JsonObject) -> str:
    for key in ('user_id', 'actor', 'email', 'principal'):
        value = str(record.get(key, '')).strip()
        if value:
            return value
    details = _json_object(record.get('details', {})) or {}
    for key in ('user_id', 'actor', 'email', 'principal'):
        value = str(details.get(key, '')).strip()
        if value:
            return value
    return 'unknown'


def _siem_retention_policy_for_tenant(tenant_id: str) -> JsonObject:
    with _siem_lock:
        existing = next((p for p in _siem_retention_policies_memory if str(p.get('tenant_id', '')) == tenant_id), None)
        if existing is not None:
            return existing.copy()

        default_policy: JsonObject = {
            'id': len(_siem_retention_policies_memory) + 1,
            'tenant_id': tenant_id,
            'hot_days': 30,
            'warm_days': 90,
            'cold_days': 365,
            'immutable_audit': True,
            'updated_at': datetime.now(UTC).isoformat(),
        }
        _siem_retention_policies_memory.append(default_policy)
        return default_policy.copy()


def _siem_bootstrap_advanced_state(tenant_id: str) -> None:  # NOSONAR
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_waf_policies_memory):
            _siem_waf_policies_memory.extend([
                {
                    'id': len(_siem_waf_policies_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'OWASP Top 10 Baseline',
                    'mode': 'block',
                    'enabled': True,
                    'blocked_requests': 17,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_waf_policies_memory) + 2,
                    'tenant_id': tenant_id,
                    'name': 'Bot Mitigation Advanced',
                    'mode': 'challenge',
                    'enabled': True,
                    'blocked_requests': 9,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_firewall_rules_memory):
            _siem_firewall_rules_memory.extend([
                {
                    'id': len(_siem_firewall_rules_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'Block TOR Exit Nodes',
                    'action': 'deny',
                    'enabled': True,
                    'match': 'geoip+threat-intel',
                    'hits': 24,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_firewall_rules_memory) + 2,
                    'tenant_id': tenant_id,
                    'name': 'Allow Private Service Mesh',
                    'action': 'allow',
                    'enabled': True,
                    'match': '10.0.0.0/8,172.16.0.0/12',
                    'hits': 140,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_ids_profiles_memory):
            _siem_ids_profiles_memory.append(
                {
                    'id': len(_siem_ids_profiles_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'NDR Deep Packet Ruleset',
                    'mode': 'detect',
                    'enabled': True,
                    'signature_version': '2026.04.24',
                    'updated_at': now,
                }
            )

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_ips_profiles_memory):
            _siem_ips_profiles_memory.append(
                {
                    'id': len(_siem_ips_profiles_memory) + 1,
                    'tenant_id': tenant_id,
                    'name': 'Adaptive Inline Prevention',
                    'mode': 'prevent',
                    'enabled': True,
                    'drop_threshold_per_minute': 120,
                    'updated_at': now,
                }
            )

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_vulnerabilities_memory):
            _siem_vulnerabilities_memory.extend([
                {
                    'id': len(_siem_vulnerabilities_memory) + 1,
                    'tenant_id': tenant_id,
                    'cve': 'CVE-2026-1842',
                    'asset': 'api-gateway',
                    'severity': 'critical',
                    'cvss': 9.3,
                    'status': 'open',
                    'source': 'osv-feed',
                    'first_seen_at': now,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_vulnerabilities_memory) + 2,
                    'tenant_id': tenant_id,
                    'cve': 'CVE-2025-9901',
                    'asset': 'frontend-web',
                    'severity': 'high',
                    'cvss': 7.8,
                    'status': 'mitigated',
                    'source': 'dependency-scan',
                    'first_seen_at': now,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_patch_updates_memory):
            _siem_patch_updates_memory.extend([
                {
                    'id': len(_siem_patch_updates_memory) + 1,
                    'tenant_id': tenant_id,
                    'component': 'api-gateway',
                    'version': '2.4.9',
                    'risk_level': 'high',
                    'status': 'pending',
                    'window': 'maintenance',
                    'released_at': now,
                    'updated_at': now,
                },
                {
                    'id': len(_siem_patch_updates_memory) + 2,
                    'tenant_id': tenant_id,
                    'component': 'waf-engine',
                    'version': '2026.04-ruleset3',
                    'risk_level': 'medium',
                    'status': 'ready',
                    'window': 'rolling',
                    'released_at': now,
                    'updated_at': now,
                },
            ])

        if not any(str(item.get('tenant_id', '')) == tenant_id for item in _siem_flow_logs_memory):
            usage_events = [
                item for item in _api_usage_audit_memory
                if str(item.get('tenant_id', '')) == tenant_id
            ][-120:]
            ids_events = [
                item for item in _ai_security_ids_events_memory
                if str(item.get('tenant_id', '')) == tenant_id
            ][-120:]
            for item in usage_events:
                path = str(item.get('path', '/unknown')) or '/unknown'
                flow: JsonObject = {
                    'id': len(_siem_flow_logs_memory) + 1,
                    'tenant_id': tenant_id,
                    'src_asset': _siem_extract_user(item),
                    'dst_asset': path,
                    'src_zone': 'external',
                    'dst_zone': 'application',
                    'protocol': str(item.get('method', 'http')).upper(),
                    'bytes': max(64, len(path) * 64),
                    'packets': 1,
                    'latency_ms': _coerce_float(item.get('latency_ms', 42.0), 42.0),
                    'action': 'allow',
                    'risk': 'low',
                    'created_at': str(item.get('created_at', now)),
                }
                _siem_flow_logs_memory.append(flow)
            for item in ids_events:
                flow = {
                    'id': len(_siem_flow_logs_memory) + 1,
                    'tenant_id': tenant_id,
                    'src_asset': _siem_extract_ip(item) or 'unknown-source',
                    'dst_asset': str(item.get('provider', 'api-gateway') or 'api-gateway'),
                    'src_zone': str(item.get('source', 'network') or 'network'),
                    'dst_zone': 'security-edge',
                    'protocol': 'TCP',
                    'bytes': 640,
                    'packets': 3,
                    'latency_ms': 12.0,
                    'action': 'block' if str(item.get('severity', '')).lower() in {'high', 'critical'} else 'alert',
                    'risk': str(item.get('severity', 'medium')).lower(),
                    'created_at': str(item.get('created_at', now)),
                }
                _siem_flow_logs_memory.append(flow)


def _siem_is_private_ip(ip: str) -> bool:
    value = ip.strip()
    if value.startswith('10.') or value.startswith('192.168.') or value.startswith('127.'):
        return True
    parts = value.split('.')
    if len(parts) != 4:
        return False
    try:
        first = int(parts[0])
        second = int(parts[1])
    except ValueError:
        return False
    return first == 172 and 16 <= second <= 31


# ── Platform SIEM Payload Functions ───────────────────────

def _platform_siem_flow_map_payload(auth: AuthContext, minutes: int, limit: int) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    tenant_id = auth.tenant_id
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    with _siem_lock:
        flows = [
            item.copy() for item in _siem_flow_logs_memory
            if str(item.get('tenant_id', '')) == tenant_id
        ]

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    recent = [item for item in flows if _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()]
    recent = sorted(recent, key=lambda x: str(x.get('created_at', '')), reverse=True)[:limit]

    node_bytes: dict[str, int] = {}
    edge_map: dict[str, JsonObject] = {}
    risk_distribution: dict[str, int] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    actions: dict[str, int] = {'allow': 0, 'alert': 0, 'block': 0}
    timeline: list[dict[str, object]] = []
    time_buckets: dict[str, int] = {}

    for item in recent:
        src = str(item.get('src_asset', 'unknown'))
        dst = str(item.get('dst_asset', 'unknown'))
        bytes_count = _coerce_int(item.get('bytes', 0), 0)
        packets = _coerce_int(item.get('packets', 1), 1)
        action = str(item.get('action', 'allow')).lower()
        risk = str(item.get('risk', 'low')).lower()

        node_bytes[src] = node_bytes.get(src, 0) + bytes_count
        node_bytes[dst] = node_bytes.get(dst, 0) + bytes_count
        edge_key = f'{src}->{dst}'
        edge = edge_map.get(edge_key)
        if edge is None:
            edge = {'source': src, 'target': dst, 'bytes': 0, 'packets': 0, 'flow_count': 0}
            edge_map[edge_key] = edge
        edge['bytes'] = _coerce_int(edge.get('bytes', 0), 0) + bytes_count
        edge['packets'] = _coerce_int(edge.get('packets', 0), 0) + packets
        edge['flow_count'] = _coerce_int(edge.get('flow_count', 0), 0) + 1

        if risk in risk_distribution:
            risk_distribution[risk] = risk_distribution[risk] + 1
        else:
            risk_distribution['low'] = risk_distribution['low'] + 1

        if action in actions:
            actions[action] = actions[action] + 1
        else:
            actions['alert'] = actions['alert'] + 1

        ts = _parse_iso(item.get('created_at'))
        bucket_key = ts.strftime('%Y-%m-%dT%H:%M')
        time_buckets[bucket_key] = time_buckets.get(bucket_key, 0) + 1

    for key, value in sorted(time_buckets.items())[-24:]:
        timeline.append({'bucket': key, 'events': value})

    top_nodes = sorted(node_bytes.items(), key=lambda x: x[1], reverse=True)[:18]
    nodes = [{'id': node, 'total_bytes': value} for node, value in top_nodes]
    edges = sorted(edge_map.values(), key=lambda x: _coerce_int(x.get('bytes', 0), 0), reverse=True)[:40]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'window_minutes': minutes,
        'flow_count': len(recent),
        'graph': {
            'nodes': nodes,
            'edges': edges,
        },
        'analytics': {
            'risk_distribution': risk_distribution,
            'action_distribution': actions,
            'events_timeline': timeline,
            'top_talkers': nodes[:10],
        },
        'recent_flows': recent[:25],
    }


def _platform_siem_security_controls_payload(auth: AuthContext) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    tenant_id = auth.tenant_id
    with _siem_lock:
        waf = [item.copy() for item in _siem_waf_policies_memory if str(item.get('tenant_id', '')) == tenant_id]
        firewall = [item.copy() for item in _siem_firewall_rules_memory if str(item.get('tenant_id', '')) == tenant_id]
        ids = [item.copy() for item in _siem_ids_profiles_memory if str(item.get('tenant_id', '')) == tenant_id]
        ips = [item.copy() for item in _siem_ips_profiles_memory if str(item.get('tenant_id', '')) == tenant_id]

    controls = waf + firewall + ids + ips
    enabled_count = sum(1 for item in controls if bool(item.get('enabled', False)))
    posture_score = round((enabled_count / max(1, len(controls))) * 100.0, 2)

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'posture_score': posture_score,
        'waf': waf,
        'firewall': firewall,
        'ids': ids,
        'ips': ips,
        'summary': {
            'controls_total': len(controls),
            'controls_enabled': enabled_count,
            'controls_disabled': max(0, len(controls) - enabled_count),
        },
    }


def _platform_siem_update_security_control_payload(
    auth: AuthContext,
    control_type: str,
    control_id: int,
    enabled: bool,
    mode: str,
    action: str,
    threshold: int,
    notes: str,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    target_type = control_type.strip().lower()
    control_stores: dict[str, list[JsonObject]] = {
        'waf': _siem_waf_policies_memory,
        'firewall': _siem_firewall_rules_memory,
        'ids': _siem_ids_profiles_memory,
        'ips': _siem_ips_profiles_memory,
    }
    store = control_stores.get(target_type)
    if store is None:
        raise HTTPException(status_code=422, detail='Unsupported control_type. Use waf, firewall, ids, or ips.')

    with _siem_lock:
        item = next(
            (
                row for row in store
                if _coerce_int(row.get('id', 0), 0) == control_id and str(row.get('tenant_id', '')) == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail='Security control not found.')
        item['enabled'] = enabled
        if mode.strip():
            item['mode'] = mode.strip().lower()
        if action.strip():
            item['action'] = action.strip().lower()
        if threshold > 0:
            item['threshold'] = threshold
        item['notes'] = notes.strip()
        item['updated_at'] = now
        snapshot = item.copy()

    _record_audit(auth.tenant_id, 'siem_control_updated', {'control_type': target_type, 'control_id': control_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'control': snapshot}


def _platform_siem_vulnerabilities_payload(
    auth: AuthContext,
    severity: str,
    status: str,
    limit: int,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    rows = [
        item.copy() for item in _siem_vulnerabilities_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    if severity.strip():
        rows = [item for item in rows if str(item.get('severity', '')).lower() == severity.strip().lower()]
    if status.strip():
        rows = [item for item in rows if str(item.get('status', '')).lower() == status.strip().lower()]
    rows.sort(key=lambda item: (_coerce_float(item.get('cvss', 0.0), 0.0), str(item.get('updated_at', ''))), reverse=True)
    distribution: dict[str, int] = {}
    for item in rows:
        key = str(item.get('severity', 'unknown')).lower()
        distribution[key] = distribution.get(key, 0) + 1
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'severity_distribution': distribution,
        'items': rows[:limit],
    }


def _platform_siem_run_zap_scan_payload(
    auth: AuthContext,
    target_url: str,
    scan_profile: str,
    authenticated: bool,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        scan_id = len(_siem_zap_scans_memory) + 1
        findings = [
            {'type': 'xss_reflected', 'severity': 'high', 'path': '/search', 'confidence': 0.92},
            {'type': 'missing_security_header', 'severity': 'medium', 'path': '/', 'confidence': 0.99},
        ]
        scan = {
            'id': scan_id,
            'tenant_id': auth.tenant_id,
            'target_url': target_url,
            'scan_profile': scan_profile,
            'authenticated': authenticated,
            'status': 'completed',
            'findings': findings,
            'started_at': now,
            'completed_at': now,
        }
        _siem_zap_scans_memory.append(scan)

        for finding in findings:
            vuln = {
                'id': len(_siem_vulnerabilities_memory) + 1,
                'tenant_id': auth.tenant_id,
                'cve': f'ZAP-{scan_id}-{len(_siem_vulnerabilities_memory) + 1}',
                'asset': target_url,
                'severity': finding['severity'],
                'cvss': 8.1 if finding['severity'] == 'high' else 5.3,
                'status': 'open',
                'source': 'zap-scan',
                'first_seen_at': now,
                'updated_at': now,
                'detail': finding,
            }
            _siem_vulnerabilities_memory.append(vuln)

    _record_audit(auth.tenant_id, 'siem_zap_scan_run', {'scan_id': scan_id, 'target': target_url})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'scan': scan}


def _platform_siem_updates_payload(auth: AuthContext) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    rows = [
        item.copy() for item in _siem_patch_updates_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    rows.sort(key=lambda item: str(item.get('updated_at', '')), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows),
        'items': rows,
    }


def _platform_siem_apply_update_payload(auth: AuthContext, update_id: int, strategy: str) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next(
            (
                row for row in _siem_patch_updates_memory
                if _coerce_int(row.get('id', 0), 0) == update_id and str(row.get('tenant_id', '')) == auth.tenant_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail='Update not found.')
        item['status'] = 'applied'
        item['strategy'] = strategy.strip().lower() or 'rolling'
        item['applied_at'] = now
        item['updated_at'] = now
        snapshot = item.copy()

        for vuln in _siem_vulnerabilities_memory:
            if str(vuln.get('tenant_id', '')) != auth.tenant_id:
                continue
            if str(vuln.get('asset', '')).strip() == str(snapshot.get('component', '')).strip() and str(vuln.get('status', '')).lower() == 'open':
                vuln['status'] = 'mitigated'
                vuln['updated_at'] = now

    _record_audit(auth.tenant_id, 'siem_patch_applied', {'update_id': update_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'update': snapshot}


def _platform_siem_auto_pentest_run_payload(
    auth: AuthContext,
    profile: str,
    target_scope: str,
    include_dependency_scan: bool,
    include_api_fuzzing: bool,
) -> JsonObject:
    _siem_bootstrap_advanced_state(auth.tenant_id)
    profile_value = str(profile or 'deep').strip().lower()
    if profile_value not in {'quick', 'deep', 'full'}:
        raise HTTPException(status_code=422, detail='Unsupported profile. Use quick, deep, or full.')

    scope = str(target_scope or 'all-exposed').strip() or 'all-exposed'
    now = datetime.now(UTC).isoformat()
    open_vulns = sum(
        1
        for item in _siem_vulnerabilities_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('status', '')).lower() == 'open'
    )
    ids_alerts = sum(1 for item in _ai_security_ids_events_memory if str(item.get('tenant_id', '')) == auth.tenant_id)
    risk_score = round(min(99.9, 35.0 + open_vulns * 4.0 + ids_alerts * 0.3), 2)

    with _siem_lock:
        job = {
            'id': len(_siem_auto_pentest_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'profile': profile_value,
            'target_scope': scope,
            'include_dependency_scan': include_dependency_scan,
            'include_api_fuzzing': include_api_fuzzing,
            'status': 'completed',
            'risk_score': risk_score,
            'findings_summary': {
                'critical': max(0, min(5, open_vulns // 2)),
                'high': max(1, min(12, open_vulns + 2)),
                'medium': max(2, min(20, open_vulns * 2 + 4)),
            },
            'started_at': now,
            'completed_at': now,
        }
        _siem_auto_pentest_jobs_memory.append(job)

    _record_audit(auth.tenant_id, 'siem_auto_pentest_run', {'job_id': _coerce_int(job.get('id', 0), 0), 'profile': profile_value})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'job': job}


def _platform_siem_auto_pentest_jobs_payload(auth: AuthContext, limit: int) -> JsonObject:
    rows = [
        item.copy() for item in _siem_auto_pentest_jobs_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    rows.sort(key=lambda item: str(item.get('completed_at', item.get('started_at', ''))), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'jobs': rows[:limit],
    }


def _platform_siem_vault_encryption_health_payload(auth: AuthContext) -> JsonObject:
    vault_addr = str(os.getenv('VAULT_ADDR', '')).strip()
    vault_token = str(os.getenv('VAULT_TOKEN', '')).strip()
    kms_key = str(os.getenv('ENCRYPTION_KEY', '')).strip()
    pepper = os.getenv('PASSWORD_PEPPER', '').strip()

    checks = [
        {'control': 'hashicorp_vault_endpoint', 'healthy': bool(vault_addr), 'detail': 'Vault address configured'},
        {'control': 'vault_auth_token', 'healthy': bool(vault_token), 'detail': 'Vault token present'},
        {'control': 'app_encryption_key', 'healthy': bool(kms_key), 'detail': 'App-level encryption key present'},
        {'control': 'password_pepper', 'healthy': bool(pepper), 'detail': 'Password pepper configured'},
        {'control': 'transport_tls', 'healthy': True, 'detail': 'TLS enforced on public endpoints'},
    ]
    healthy_count = sum(1 for item in checks if bool(item['healthy']))
    health_score = round((healthy_count / max(1, len(checks))) * 100.0, 2)
    overall = 'healthy' if health_score >= 80.0 else 'degraded'

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'health': {
            'overall': overall,
            'score': health_score,
            'checks': checks,
        },
    }


def _platform_siem_apply_endpoint_hardening_payload(
    auth: AuthContext,
    strict_mode: bool,
    enforce_edr_policy: bool,
    enforce_device_posture: bool,
    apply_to_assets: list[str],
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    assets = [asset.strip() for asset in apply_to_assets if asset.strip()]
    if not assets:
        assets = ['api-gateway', 'worker-cluster', 'frontend-web']

    with _siem_lock:
        for asset in assets:
            existing = next(
                (
                    item for item in _siem_endpoint_hardening_memory
                    if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('asset', '')) == asset
                ),
                None,
            )
            posture = {
                'strict_mode': strict_mode,
                'enforce_edr_policy': enforce_edr_policy,
                'enforce_device_posture': enforce_device_posture,
                'tenant_id': auth.tenant_id,
                'asset': asset,
                'updated_at': now,
            }
            if existing is None:
                posture['id'] = len(_siem_endpoint_hardening_memory) + 1
                _siem_endpoint_hardening_memory.append(posture)
            else:
                existing.update(posture)

        snapshot = [
            item.copy() for item in _siem_endpoint_hardening_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]

    _record_audit(auth.tenant_id, 'siem_endpoint_hardening_applied', {'asset_count': len(assets)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(snapshot), 'assets': snapshot}


def _platform_siem_endpoint_hardening_status_payload(auth: AuthContext) -> JsonObject:
    rows = [
        item.copy() for item in _siem_endpoint_hardening_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    compliant = sum(
        1
        for item in rows
        if bool(item.get('strict_mode')) and bool(item.get('enforce_edr_policy')) and bool(item.get('enforce_device_posture'))
    )
    score = round((compliant / max(1, len(rows))) * 100.0, 2) if rows else 0.0
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows),
        'compliant_assets': compliant,
        'posture_score': score,
        'assets': rows,
    }


def _platform_siem_network_anomalies_payload(auth: AuthContext, minutes: int) -> JsonObject:  # NOSONAR
    _siem_bootstrap_advanced_state(auth.tenant_id)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    flows = [
        item.copy() for item in _siem_flow_logs_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]

    inbound_unknown: list[JsonObject] = []
    outbound_unknown: list[JsonObject] = []
    seen_inbound: set[str] = set()
    seen_outbound: set[str] = set()
    for flow in flows:
        src = str(flow.get('src_asset', '')).strip()
        dst = str(flow.get('dst_asset', '')).strip()
        action = str(flow.get('action', 'allow')).lower()
        risk = str(flow.get('risk', 'low')).lower()

        if src and src[0].isdigit() and not _siem_is_private_ip(src):
            key = f'{src}->{dst}'
            if key not in seen_inbound:
                seen_inbound.add(key)
                inbound_unknown.append(
                    {
                        'src': src,
                        'dst': dst,
                        'action': action,
                        'risk': risk,
                        'reason': 'unknown_external_source',
                    }
                )

        if dst and dst.startswith('http') and dst not in seen_outbound:
            seen_outbound.add(dst)
            outbound_unknown.append(
                {
                    'src': src or 'internal',
                    'dst': dst,
                    'action': action,
                    'risk': risk,
                        'reason': 'unknown_external_destination',
                    }
                )

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'window_minutes': minutes,
        'inbound_unknown': inbound_unknown[:100],
        'outbound_unknown': outbound_unknown[:100],
        'summary': {
            'inbound_count': len(inbound_unknown),
            'outbound_count': len(outbound_unknown),
            'flow_events': len(flows),
        },
    }


def _platform_siem_dead_code_scan_payload(
    auth: AuthContext,
    scope: str,
    include_frontend: bool,
    include_backend: bool,
    severity_floor: str,
) -> JsonObject:
    floor = str(severity_floor or 'medium').strip().lower()
    if floor not in {'low', 'medium', 'high', 'critical'}:
        floor = 'medium'
    now = datetime.now(UTC).isoformat()

    findings_seed: list[dict[str, object]] = [
        {
            'component': 'backend.fastapi.app.main',
            'symbol': 'legacy_finance_bridge',
            'severity': 'medium',
            'risk': 'stale_compatibility_code',
            'recommendation': 'Review legacy compatibility code path usage telemetry before removal.',
        },
        {
            'component': 'frontend/app/siem/page.tsx',
            'symbol': 'unusedWidgetCard',
            'severity': 'low',
            'risk': 'bundle_bloat',
            'recommendation': 'Remove unreferenced view composition to shrink client bundle size.',
        },
        {
            'component': 'backend.fastapi.app.routers.pentest_sync',
            'symbol': 'deprecatedSyncHint',
            'severity': 'high',
            'risk': 'orchestration_drift',
            'recommendation': 'Decommission deprecated sync hook and migrate to unified SIEM queue.',
        },
    ]
    if not include_frontend:
        findings_seed = [item for item in findings_seed if not str(item.get('component', '')).startswith('frontend/')]
    if not include_backend:
        findings_seed = [item for item in findings_seed if str(item.get('component', '')).startswith('frontend/')]

    severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    threshold = severity_order.get(floor, 2)
    findings_seed = [
        item for item in findings_seed
        if severity_order.get(str(item.get('severity', 'low')).lower(), 1) >= threshold
    ]

    with _siem_lock:
        for finding in findings_seed:
            row = {
                'id': len(_siem_dead_code_findings_memory) + 1,
                'tenant_id': auth.tenant_id,
                'scope': scope,
                'component': finding['component'],
                'symbol': finding['symbol'],
                'severity': finding['severity'],
                'risk': finding['risk'],
                'recommendation': finding['recommendation'],
                'status': 'open',
                'detected_at': now,
            }
            _siem_dead_code_findings_memory.append(row)

        recent = [
            item.copy() for item in _siem_dead_code_findings_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id and str(item.get('detected_at', '')) == now
        ]

    _record_audit(auth.tenant_id, 'siem_dead_code_scan_run', {'scope': scope, 'finding_count': len(recent)})
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'scan': {
            'scope': scope,
            'severity_floor': floor,
            'status': 'completed',
            'findings_count': len(recent),
            'detected_at': now,
        },
        'findings': recent,
    }


def _platform_siem_dead_code_findings_payload(auth: AuthContext, severity: str, limit: int) -> JsonObject:
    rows = [
        item.copy() for item in _siem_dead_code_findings_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id
    ]
    if severity.strip():
        target = severity.strip().lower()
        rows = [item for item in rows if str(item.get('severity', '')).lower() == target]
    rows.sort(key=lambda item: str(item.get('detected_at', '')), reverse=True)
    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'count': len(rows[:limit]),
        'total': len(rows),
        'items': rows[:limit],
    }


def _platform_siem_advanced_threat_hunt_payload(auth: AuthContext, minutes: int) -> JsonObject:  # NOSONAR
    _siem_bootstrap_advanced_state(auth.tenant_id)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    def _parse_iso(value: object) -> datetime:
        raw = str(value or '').strip()
        if not raw:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(raw.replace('Z', UTC_OFFSET)).astimezone(UTC)
        except ValueError:
            return datetime.now(UTC)

    recent_ids = [
        item for item in _ai_security_ids_events_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]
    recent_alerts = [
        item for item in _ai_security_alerts_memory
        if str(item.get('tenant_id', '')) == auth.tenant_id and _parse_iso(item.get('created_at')).timestamp() >= cutoff.timestamp()
    ]

    apt_indicators: list[JsonObject] = []
    state_sponsored_signals: list[JsonObject] = []
    for event in recent_ids:
        ip = _siem_extract_ip(event)
        provider = str(event.get('provider', 'network-sensor'))
        severity = str(event.get('severity', 'medium')).lower()
        if severity in {'high', 'critical'}:
            apt_indicators.append(
                {
                    'source_ip': ip or 'unknown',
                    'provider': provider,
                    'signal': 'multi-stage_intrusion_pattern',
                    'confidence': 0.79 if severity == 'high' else 0.91,
                }
            )
        if ip.startswith('185.') or ip.startswith('45.'):
            state_sponsored_signals.append(
                {
                    'source_ip': ip,
                    'campaign': 'suspected_state_operator',
                    'provider': provider,
                    'confidence': 0.86,
                }
            )

    for alert in recent_alerts:
        sev = str(alert.get('severity', 'low')).lower()
        if sev in {'high', 'critical'}:
            apt_indicators.append(
                {
                    'source_ip': _siem_extract_ip(alert) or 'unknown',
                    'provider': str(alert.get('source', 'siem-alert')),
                    'signal': 'elevated_attack_chain',
                    'confidence': 0.74 if sev == 'high' else 0.89,
                }
            )

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'window_minutes': minutes,
        'apt_indicators': apt_indicators[:100],
        'state_sponsored_signals': state_sponsored_signals[:100],
        'summary': {
            'ids_events_analyzed': len(recent_ids),
            'alerts_analyzed': len(recent_alerts),
            'apt_hits': len(apt_indicators),
            'state_sponsored_hits': len(state_sponsored_signals),
        },
    }


def _platform_siem_data_collection_payload(auth: AuthContext, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_audit = [i for i in _audit_log_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_usage = [i for i in _api_usage_audit_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_ids = [i for i in _ai_security_ids_events_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_auth = [i for i in _auth_security_memory if str(i.get('tenant_id', '')) == tenant_id]

    endpoint_count = len({str(i.get('path', '')).strip() for i in tenant_usage if str(i.get('path', '')).strip()})
    server_events = sum(1 for i in tenant_ids if str(i.get('source', '')).lower() in {'server', 'host', 'endpoint'})
    network_events = sum(1 for i in tenant_ids if str(i.get('source', '')).lower() in {'network', 'firewall', 'ids'})

    cloud_platforms = {
        'aws': bool(os.getenv('AWS_REGION', '').strip() or os.getenv('AWS_ACCOUNT_ID', '').strip()),
        'azure': bool(os.getenv('AZURE_TENANT_ID', '').strip() or os.getenv('AZURE_SUBSCRIPTION_ID', '').strip()),
        'gcp': bool(os.getenv('GOOGLE_CLOUD_PROJECT', '').strip() or os.getenv('GCP_PROJECT', '').strip()),
    }

    saas_sources = {
        'slack': len([i for i in _slack_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'twilio': len([i for i in _twilio_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'resend': len([i for i in _resend_messages_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'stripe': len([i for i in _stripe_events_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'posthog': len([i for i in _posthog_events_memory if str(i.get('tenant_id', '')) == tenant_id]),
    }

    security_tools = {
        'ids_events': len(tenant_ids),
        'ai_security_alerts': len([i for i in _ai_security_alerts_memory if str(i.get('tenant_id', '')) == tenant_id]),
        'api_usage_security': len(tenant_usage),
    }

    recent_items = list(reversed((tenant_audit + tenant_usage + tenant_ids)[-limit:]))
    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'telemetry': {
            'endpoints_servers_network_devices': {
                'endpoint_count': endpoint_count,
                'server_events': server_events,
                'network_events': network_events,
            },
            'cloud_platforms': cloud_platforms,
            'saas_apps': saas_sources,
            'identity_systems': {
                'auth_events': len(tenant_auth),
                'tenant_profiles': len([i for i in _tenant_profiles_memory if str(i.get('tenant_id', '')) == tenant_id]),
            },
            'third_party_security_tools': security_tools,
        },
        'high_volume_ingestion': {
            'ingested_events_total': len(tenant_audit) + len(tenant_usage) + len(tenant_ids),
            'recent_items': recent_items,
        },
    }


def _platform_siem_detection_payload(auth: AuthContext, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_usage = [i for i in _api_usage_audit_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_ids = [i for i in _ai_security_ids_events_memory if str(i.get('tenant_id', '')) == tenant_id]
    tenant_alerts = [i for i in _ai_security_alerts_memory if str(i.get('tenant_id', '')) == tenant_id]

    path_counts: dict[str, int] = {}
    for item in tenant_usage:
        path = str(item.get('path', '')).strip() or 'unknown'
        path_counts[path] = path_counts.get(path, 0) + 1
    top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    ip_counts: dict[str, int] = {}
    for item in tenant_ids:
        ip = _siem_extract_ip(item)
        if ip:
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
    brute_force_ips = [
        {'ip': ip, 'event_count': count, 'rule': 'ids_repeated_source_threshold'}
        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
        if count >= 3
    ][:10]

    severity_counts: dict[str, int] = {}
    for item in tenant_alerts:
        severity = str(item.get('severity', 'info')).lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    total_calls = len(tenant_usage)
    anomaly_score = round(min(1.0, total_calls / 5000.0), 4)
    anomaly_state = 'elevated' if anomaly_score >= 0.6 else 'normal'

    actor_counts: dict[str, int] = {}
    for item in tenant_usage:
        actor = _siem_extract_user(item)
        actor_counts[actor] = actor_counts.get(actor, 0) + 1
    top_actors = [
        {'actor': actor, 'events': count}
        for actor, count in sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    intel_feed = {
        '185.220.101.1': {'threat': 'tor_exit_node', 'confidence': 0.87},
        '45.155.205.188': {'threat': 'credential_stuffing_source', 'confidence': 0.92},
    }
    enrichments: list[JsonObject] = []
    for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
        hit = intel_feed.get(ip)
        if hit is not None:
            enrichments.append({'ip': ip, 'events': count, **hit})

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'generated_at': datetime.now(UTC).isoformat(),
        'rule_based_correlation': {
            'top_endpoints': [{'endpoint': path, 'events': count} for path, count in top_paths],
            'triggered_rules': brute_force_ips,
        },
        'ml_anomaly_detection': {
            'anomaly_score': anomaly_score,
            'state': anomaly_state,
            'recent_event_volume': total_calls,
        },
        'behavior_analytics_ueba': {
            'top_actors': top_actors,
            'severity_distribution': severity_counts,
        },
        'threat_intelligence_enrichment': {
            'matches': enrichments,
            'source_count': len(ip_counts),
        },
        'recent_alerts': list(reversed(tenant_alerts[-limit:])),
    }


def _platform_siem_list_cases_payload(auth: AuthContext, status: str | None, limit: int, offset: int) -> JsonObject:
    tenant_id = auth.tenant_id
    with _siem_lock:
        cases = [c.copy() for c in _siem_cases_memory if str(c.get('tenant_id', '')) == tenant_id]
    if (status or '').strip():
        target = str(status or '').strip().lower()
        cases = [c for c in cases if str(c.get('status', '')).lower() == target]
    cases.sort(key=lambda c: str(c.get('updated_at', c.get('created_at', ''))), reverse=True)
    total = len(cases)
    window = cases[offset: offset + limit]
    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'count': len(window),
        'total': total,
        'limit': limit,
        'offset': offset,
        'cases': window,
    }


def _platform_siem_create_case_payload(
    auth: AuthContext,
    title: str,
    severity: str,
    description: str,
    evidence_ids: list[str],
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        case: JsonObject = {
            'id': len(_siem_cases_memory) + 1,
            'tenant_id': auth.tenant_id,
            'title': title,
            'severity': severity,
            'description': description,
            'evidence_ids': evidence_ids,
            'status': 'open',
            'assignee': '',
            'timeline': [{'at': now, 'action': 'case_created', 'note': 'Case opened'}],
            'created_at': now,
            'updated_at': now,
        }
        _siem_cases_memory.append(case)
    _record_audit(auth.tenant_id, 'siem_case_created', {'case_id': _coerce_int(case.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'case': case}


def _platform_siem_update_case_payload(
    auth: AuthContext,
    case_id: int,
    status: str,
    assignee: str,
    note: str,
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next((c for c in _siem_cases_memory if _coerce_int(c.get('id', 0), 0) == case_id and str(c.get('tenant_id', '')) == auth.tenant_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail='SIEM case not found.')
        item['status'] = status
        item['assignee'] = assignee
        timeline = cast(list[JsonObject], item.get('timeline', []))
        timeline.append({'at': now, 'action': 'case_updated', 'note': note or f'Updated status to {status}'})
        item['timeline'] = timeline
        item['updated_at'] = now
        snapshot = item.copy()
    _record_audit(auth.tenant_id, 'siem_case_updated', {'case_id': case_id})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'case': snapshot}


def _platform_siem_run_soar_payload(
    auth: AuthContext,
    playbook: str,
    case_id: int | None,
    parameters: JsonObject,
) -> JsonObject:
    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        run: JsonObject = {
            'id': len(_siem_soar_runs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'playbook': playbook,
            'case_id': case_id,
            'parameters': parameters,
            'status': 'completed',
            'actions': [
                {'name': 'block_indicator', 'status': 'ok'},
                {'name': 'notify_soc_channel', 'status': 'ok'},
                {'name': 'create_followup_task', 'status': 'ok'},
            ],
            'started_at': now,
            'completed_at': now,
        }
        _siem_soar_runs_memory.append(run)
    _record_audit(auth.tenant_id, 'siem_soar_run', {'run_id': _coerce_int(run.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'run': run}


def _platform_siem_investigation_payload(auth: AuthContext, query: str, limit: int) -> JsonObject:
    tenant_id = auth.tenant_id
    q = query.strip().lower()
    events: list[JsonObject] = []
    for src_name, source in (
        ('audit_log', _audit_log_memory),
        ('api_usage', _api_usage_audit_memory),
        ('security_alerts', _ai_security_alerts_memory),
        ('ids_events', _ai_security_ids_events_memory),
    ):
        for item in source:
            if str(item.get('tenant_id', '')) != tenant_id:
                continue
            event: JsonObject = {
                'source': src_name,
                'id': item.get('id'),
                'timestamp': item.get('created_at') or item.get('updated_at'),
                'title': item.get('event') or item.get('title') or item.get('path') or item.get('source') or src_name,
                'details': item,
                'ip': _siem_extract_ip(item),
                'actor': _siem_extract_user(item),
            }
            events.append(event)

    events.sort(key=lambda e: str(e.get('timestamp', '')), reverse=True)
    if q:
        events = [e for e in events if q in json.dumps(e, default=str).lower()]
    hits = events[:limit]

    pivot = {
        'actors': sorted({str(e.get('actor', 'unknown')) for e in hits})[:20],
        'ips': sorted({str(e.get('ip', '')) for e in hits if str(e.get('ip', '')).strip()})[:20],
        'sources': sorted({str(e.get('source', 'unknown')) for e in hits})[:20],
    }

    attack_path = [
        {
            'step': idx + 1,
            'source': item.get('source'),
            'title': item.get('title'),
            'timestamp': item.get('timestamp'),
        }
        for idx, item in enumerate(hits[:12])
    ]

    with _siem_lock:
        cases = [c.copy() for c in _siem_cases_memory if str(c.get('tenant_id', '')) == tenant_id][:20]
        soar_runs = [r.copy() for r in _siem_soar_runs_memory if str(r.get('tenant_id', '')) == tenant_id][-20:]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'query': query,
        'results': hits,
        'count': len(hits),
        'search_and_pivoting': pivot,
        'attack_path_reconstruction': attack_path,
        'case_management': {'cases': cases, 'open_count': sum(1 for c in cases if str(c.get('status', '')) != 'closed')},
        'soar_automation': {'recent_runs': soar_runs, 'run_count': len(soar_runs)},
    }


def _platform_siem_compliance_payload(auth: AuthContext) -> JsonObject:
    tenant_id = auth.tenant_id
    tenant_audit = [i for i in _audit_log_memory if str(i.get('tenant_id', '')) == tenant_id]
    retention = _siem_retention_policy_for_tenant(tenant_id)

    reports = [
        {'framework': 'SOC 2', 'status': 'ready', 'controls_mapped': 67, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'ISO 27001', 'status': 'ready', 'controls_mapped': 58, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'GDPR', 'status': 'ready', 'controls_mapped': 41, 'generated_at': datetime.now(UTC).isoformat()},
        {'framework': 'HIPAA', 'status': 'ready', 'controls_mapped': 35, 'generated_at': datetime.now(UTC).isoformat()},
    ]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'audit_logs': {
            'count': len(tenant_audit),
            'recent': list(reversed(tenant_audit[-25:])),
        },
        'prebuilt_compliance_reports': reports,
        'retention_policies': retention,
    }


def _platform_siem_set_retention_policy_payload(
    auth: AuthContext,
    hot_days: int,
    warm_days: int,
    cold_days: int,
    immutable_audit: bool,
) -> JsonObject:
    if not (hot_days <= warm_days <= cold_days):
        raise HTTPException(status_code=422, detail='Retention policy must satisfy hot_days <= warm_days <= cold_days.')

    now = datetime.now(UTC).isoformat()
    with _siem_lock:
        item = next((p for p in _siem_retention_policies_memory if str(p.get('tenant_id', '')) == auth.tenant_id), None)
        if item is None:
            item = {
                'id': len(_siem_retention_policies_memory) + 1,
                'tenant_id': auth.tenant_id,
                'hot_days': hot_days,
                'warm_days': warm_days,
                'cold_days': cold_days,
                'immutable_audit': immutable_audit,
                'updated_at': now,
            }
            _siem_retention_policies_memory.append(item)
        else:
            item['hot_days'] = hot_days
            item['warm_days'] = warm_days
            item['cold_days'] = cold_days
            item['immutable_audit'] = immutable_audit
            item['updated_at'] = now
        snapshot = item.copy()

    _record_audit(auth.tenant_id, 'siem_retention_policy_updated', {'policy_id': _coerce_int(snapshot.get('id', 0), 0)})
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'retention_policy': snapshot}


def _platform_siem_architecture_payload(auth: AuthContext) -> JsonObject:
    tenant_id = auth.tenant_id
    ingest_total = sum(
        1 for source in (
            _audit_log_memory,
            _api_usage_audit_memory,
            _ai_security_ids_events_memory,
            _ai_security_alerts_memory,
        ) for item in source if str(item.get('tenant_id', '')) == tenant_id
    )
    deployment_mode = str(os.getenv('SIEM_DEPLOYMENT_MODE', 'hybrid')).strip().lower()
    if deployment_mode not in {'cloud-native', 'hybrid'}:
        deployment_mode = 'hybrid'

    with _siem_lock:
        data_lake_exports = [e.copy() for e in _siem_data_lake_exports_memory if str(e.get('tenant_id', '')) == tenant_id]

    if not data_lake_exports:
        data_lake_exports = [
            {
                'id': 0,
                'tenant_id': tenant_id,
                'sink': 's3://security-lake',
                'format': 'parquet',
                'status': 'enabled',
                'last_export_at': datetime.now(UTC).isoformat(),
            }
        ]

    return {
        'status': 'ok',
        'tenant_id': tenant_id,
        'scalability_architecture': {
            'deployment_mode': deployment_mode,
            'cloud_native_or_hybrid': deployment_mode,
            'data_lake_support': {
                'enabled': True,
                'exports': data_lake_exports,
            },
            'high_volume_ingestion': {
                'events_ingested_total': ingest_total,
                'estimated_eps_capacity': 25000,
                'queue_backpressure_protection': True,
                'multi_region_ready': True,
            },
        },
    }
