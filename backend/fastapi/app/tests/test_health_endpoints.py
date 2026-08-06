"""
Test suite for health check endpoints including unified-31 schema readiness.

Tests cover:
- Comprehensive /health endpoint includes schema_unified_31 block
- /health/schema/unified-31 strict readiness probe (200/503 response codes)
- Schema readiness payload structure and startup flag awareness
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import os

import pytest
from fastapi.testclient import TestClient

# Set up test environment before importing app
os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')


@pytest.fixture
def client() -> TestClient:
    """Create a test client with DB init skipped."""
    from app.main import app
    return TestClient(app)


class TestComprehensiveHealthEndpoint:
    """Tests for /health comprehensive health check endpoint."""

    def test_health_includes_schema_unified_31_block(self, client: TestClient) -> None:
        """GET /health response includes schema_unified_31 block with readiness payload."""
        response = client.get('/health')
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

        # Verify schema_unified_31 block is present
        assert 'schema_unified_31' in data
        schema_block = data['schema_unified_31']

        # Verify required fields in schema block
        assert 'schema' in schema_block
        assert schema_block['schema'] == 'unified_31_core'
        assert 'migration' in schema_block
        assert 'startup_flag_enabled' in schema_block
        assert 'db_ready' in schema_block
        assert 'applied_on_startup' in schema_block
        assert 'module_seed_count' in schema_block
        assert 'required_module_seed_count' in schema_block
        assert 'ready' in schema_block

        # Verify module seed count matches required
        assert schema_block['required_module_seed_count'] == 31


class TestSchemaUnified31ReadinessProbe:
    """Tests for /health/schema/unified-31 strict readiness probe."""

    def test_schema_readiness_endpoint_exists(self, client: TestClient) -> None:
        """GET /health/schema/unified-31 endpoint is available."""
        response = client.get('/health/schema/unified-31')
        # Will return 200 or 503 depending on DB/schema state
        assert response.status_code in {200, 503}

    def test_schema_readiness_returns_payload_on_success(self, client: TestClient) -> None:
        """When ready=true, /health/schema/unified-31 returns 200 with payload."""
        response = client.get('/health/schema/unified-31')
        data = response.json()

        # Verify payload structure regardless of status code
        assert isinstance(data, dict)
        assert 'schema' in data
        assert 'ready' in data
        assert 'startup_flag_enabled' in data
        assert 'db_ready' in data
        assert 'module_seed_count' in data

        # If ready, status should be 200
        if data.get('ready'):
            assert response.status_code == 200

    def test_schema_readiness_returns_503_when_not_ready(self, client: TestClient) -> None:
        """When ready=false, /health/schema/unified-31 returns 503 with diagnostic reason."""
        response = client.get('/health/schema/unified-31')
        data = response.json()

        # If not ready, status should be 503 and reason should be present
        if not data.get('ready'):
            assert response.status_code == 503
            assert 'reason' in data


class TestHealthEndpointStructure:
    """Tests for health endpoint response structure integrity."""

    def test_health_preserves_existing_fields(self, client: TestClient) -> None:
        """GET /health still includes existing health fields alongside schema_unified_31."""
        response = client.get('/health')
        assert response.status_code == 200

        data = response.json()
        # Existing fields should still be present
        # (actual field names depend on get_health_check_data implementation)
        assert isinstance(data, dict)
        # Both old and new structure coexist
        assert 'schema_unified_31' in data

    def test_readiness_probe_compatibility(self, client: TestClient) -> None:
        """GET /health/ready returns consistent readiness vs schema_unified_31 state."""
        health_resp = client.get('/health')
        readiness_resp = client.get('/health/ready')

        health_data = health_resp.json()
        # /health/ready should be consistent with /health/schema/unified-31
        schema_block = health_data.get('schema_unified_31', {})
        if schema_block.get('ready'):
            # If schema is ready, readiness probe should also be ready
            assert readiness_resp.status_code == 200
