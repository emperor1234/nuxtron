"""Full coverage tests for Brand Kit endpoints (Simplified-parity feature)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {
    "X-API-Key": os.getenv("FASTAPI_API_KEY", "test-api-key"),
    "X-Tenant-Id": "brand-kit-test-tenant",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestBrandKitCoverage:
    """End-to-end coverage for /brand-kit endpoints."""

    # ------------------------------------------------------------------
    # GET – auto-create defaults
    # ------------------------------------------------------------------

    def test_get_brand_kit_creates_defaults(self, client: TestClient) -> None:
        r = client.get("/brand-kit", headers=H)
        assert r.status_code == 200
        bk = r.json()["brand_kit"]
        assert "colors" in bk
        assert "fonts" in bk
        assert "logos" in bk
        assert "voice" in bk
        assert "messaging" in bk
        assert "writing_rules" in bk
        assert "knowledge_base_count" in bk
        # Default primary color
        assert bk["colors"]["primary"] == "#3B82F6"

    # ------------------------------------------------------------------
    # PATCH /colors
    # ------------------------------------------------------------------

    def test_patch_colors(self, client: TestClient) -> None:
        r = client.patch("/brand-kit/colors", headers=H, json={"primary": "#FF0000", "accent": "#00FF00"})
        assert r.status_code == 200
        bk = r.json()["brand_kit"]
        assert bk["colors"]["primary"] == "#FF0000"
        assert bk["colors"]["accent"] == "#00FF00"
        # untouched field still present
        assert "secondary" in bk["colors"]

    def test_patch_colors_partial(self, client: TestClient) -> None:
        r = client.patch("/brand-kit/colors", headers=H, json={"muted": "#999"})
        assert r.status_code == 200
        assert r.json()["brand_kit"]["colors"]["muted"] == "#999"

    # ------------------------------------------------------------------
    # PATCH /fonts
    # ------------------------------------------------------------------

    def test_patch_fonts_heading(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/fonts",
            headers=H,
            json={"heading": {"family": "Poppins", "weight": "800", "size_px": 36}},
        )
        assert r.status_code == 200
        heading = r.json()["brand_kit"]["fonts"]["heading"]
        assert heading["family"] == "Poppins"
        assert heading["weight"] == "800"
        assert heading["size_px"] == 36

    def test_patch_fonts_body_only(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/fonts",
            headers=H,
            json={"body": {"family": "Roboto"}},
        )
        assert r.status_code == 200
        assert r.json()["brand_kit"]["fonts"]["body"]["family"] == "Roboto"

    # ------------------------------------------------------------------
    # PATCH /logos
    # ------------------------------------------------------------------

    def test_patch_logos(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/logos",
            headers=H,
            json={
                "main": "https://cdn.example.com/logo.png",
                "icon": "https://cdn.example.com/icon.png",
            },
        )
        assert r.status_code == 200
        logos = r.json()["brand_kit"]["logos"]
        assert logos["main"] == "https://cdn.example.com/logo.png"
        assert logos["icon"] == "https://cdn.example.com/icon.png"

    # ------------------------------------------------------------------
    # PATCH /voice
    # ------------------------------------------------------------------

    def test_patch_voice_valid_preset(self, client: TestClient) -> None:
        r = client.patch("/brand-kit/voice", headers=H, json={"tone_preset": "bold", "formality": "casual"})
        assert r.status_code == 200
        voice = r.json()["brand_kit"]["voice"]
        assert voice["tone_preset"] == "bold"
        assert voice["formality"] == "casual"

    def test_patch_voice_invalid_preset(self, client: TestClient) -> None:
        r = client.patch("/brand-kit/voice", headers=H, json={"tone_preset": "snarky"})
        assert r.status_code == 422

    def test_patch_voice_custom_description(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/voice",
            headers=H,
            json={"tone_preset": "custom", "custom_description": "Dry wit, never cringe."},
        )
        assert r.status_code == 200
        assert r.json()["brand_kit"]["voice"]["custom_description"] == "Dry wit, never cringe."

    # ------------------------------------------------------------------
    # PATCH /messaging
    # ------------------------------------------------------------------

    def test_patch_messaging(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/messaging",
            headers=H,
            json={
                "brand_name": "Nuxtron",
                "tagline": "AI growth, automated.",
                "value_proposition": "The only platform that does everything.",
                "elevator_pitch": "Nuxtron unifies social, ads, and SEO in one AI-powered platform.",
                "target_audience": "Marketing teams and solo creators",
            },
        )
        assert r.status_code == 200
        msg = r.json()["brand_kit"]["messaging"]
        assert msg["brand_name"] == "Nuxtron"
        assert msg["tagline"] == "AI growth, automated."

    # ------------------------------------------------------------------
    # PATCH /writing-rules
    # ------------------------------------------------------------------

    def test_patch_writing_rules(self, client: TestClient) -> None:
        r = client.patch(
            "/brand-kit/writing-rules",
            headers=H,
            json={
                "terms_to_use": ["AI-powered", "growth", "autonomous"],
                "terms_to_avoid": ["cheap", "easy", "simple"],
                "preferred_sentences": "short",
                "use_oxford_comma": True,
            },
        )
        assert r.status_code == 200
        wr = r.json()["brand_kit"]["writing_rules"]
        assert "AI-powered" in wr["terms_to_use"]
        assert "cheap" in wr["terms_to_avoid"]
        assert wr["use_oxford_comma"] is True

    # ------------------------------------------------------------------
    # Knowledge Base CRUD
    # ------------------------------------------------------------------

    def test_knowledge_base_empty_initially(self, client: TestClient) -> None:
        h = {**H, "X-Tenant-Id": "bk-kb-fresh-tenant"}
        r = client.get("/brand-kit/knowledge-base", headers=h)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_add_knowledge_base_url(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/knowledge-base",
            headers=H,
            json={"entry_type": "url", "content": "https://nuxtron.ai/about", "label": "About page"},
        )
        assert r.status_code == 201
        entry = r.json()["entry"]
        assert entry["entry_type"] == "url"
        assert entry["label"] == "About page"
        assert entry["status"] == "indexed"

    def test_add_knowledge_base_text(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/knowledge-base",
            headers=H,
            json={"entry_type": "text", "content": "We are an AI-first growth platform focused on ROI."},
        )
        assert r.status_code == 201
        assert r.json()["entry"]["entry_type"] == "text"

    def test_add_knowledge_base_invalid_type(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/knowledge-base",
            headers=H,
            json={"entry_type": "spreadsheet", "content": "something"},
        )
        assert r.status_code == 422

    def test_add_knowledge_base_empty_content(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/knowledge-base",
            headers=H,
            json={"entry_type": "text", "content": "   "},
        )
        assert r.status_code == 422

    def test_list_knowledge_base_after_adds(self, client: TestClient) -> None:
        r = client.get("/brand-kit/knowledge-base", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2
        assert len(data["entries"]) == data["total"]

    def test_delete_knowledge_base_entry(self, client: TestClient) -> None:
        add_r = client.post(
            "/brand-kit/knowledge-base",
            headers=H,
            json={"entry_type": "pdf_title", "content": "Brand_Guidelines_2026.pdf", "label": "Brand PDF"},
        )
        entry_id = add_r.json()["entry"]["id"]
        del_r = client.delete(f"/brand-kit/knowledge-base/{entry_id}", headers=H)
        assert del_r.status_code == 200
        assert del_r.json()["deleted"] == entry_id
        # Verify it's gone
        list_r = client.get("/brand-kit/knowledge-base", headers=H)
        assert all(e["id"] != entry_id for e in list_r.json()["entries"])

    def test_delete_knowledge_base_not_found(self, client: TestClient) -> None:
        r = client.delete("/brand-kit/knowledge-base/nonexistent-id", headers=H)
        assert r.status_code == 404

    # ------------------------------------------------------------------
    # Generate Preview
    # ------------------------------------------------------------------

    def test_generate_preview_social_caption(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "social_caption", "topic": "AI social scheduling"},
        )
        assert r.status_code == 200
        preview = r.json()["preview"]
        assert preview["content_type"] == "social_caption"
        assert preview["generated_text"]
        assert "compliance_check" in preview
        assert "brand_kit_snapshot" in preview
        assert preview["brand_kit_snapshot"]["brand_name"] == "Nuxtron"

    def test_generate_preview_blog_intro(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "blog_intro", "topic": "Automating your content calendar"},
        )
        assert r.status_code == 200
        assert r.json()["preview"]["generated_text"]

    def test_generate_preview_ad_copy(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "ad_copy", "topic": "Launching a new product"},
        )
        assert r.status_code == 200

    def test_generate_preview_email_subject(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "email_subject", "topic": "Summer campaign launch"},
        )
        assert r.status_code == 200

    def test_generate_preview_tagline_variant(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "tagline_variant", "topic": ""},
        )
        assert r.status_code == 200

    def test_generate_preview_invalid_type(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "press_release", "topic": "test"},
        )
        assert r.status_code == 422

    def test_generate_preview_compliance_avoids_banned_terms(self, client: TestClient) -> None:
        r = client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "social_caption", "topic": "growth platform"},
        )
        assert r.status_code == 200
        compliance = r.json()["preview"]["compliance_check"]
        assert isinstance(compliance["avoids_banned_terms"], bool)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def test_analytics_structure(self, client: TestClient) -> None:
        r = client.get("/brand-kit/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()["analytics"]
        assert "total_generations" in data
        assert "by_type" in data
        assert "kit_completeness" in data
        assert isinstance(data["kit_completeness"], int)
        assert 0 <= data["kit_completeness"] <= 100

    def test_analytics_increments_after_generation(self, client: TestClient) -> None:
        before_r = client.get("/brand-kit/analytics", headers=H)
        before = before_r.json()["analytics"]["total_generations"]

        client.post(
            "/brand-kit/generate-preview",
            headers=H,
            json={"content_type": "social_caption", "topic": "analytics test"},
        )

        after_r = client.get("/brand-kit/analytics", headers=H)
        after = after_r.json()["analytics"]["total_generations"]
        assert after == before + 1

    def test_analytics_fully_configured_kit(self, client: TestClient) -> None:
        r = client.get("/brand-kit/analytics", headers=H)
        data = r.json()["analytics"]
        # After all the PATCH calls above, kit should have high completeness
        assert data["kit_completeness"] >= 62
        assert data["colors_configured"] is True
        assert data["messaging_configured"] is True

    # ------------------------------------------------------------------
    # Tenant isolation
    # ------------------------------------------------------------------

    def test_tenant_isolation(self, client: TestClient) -> None:
        """Different tenants should get independent brand kits."""
        h_a = {**H, "X-Tenant-Id": "isolation-tenant-a"}
        h_b = {**H, "X-Tenant-Id": "isolation-tenant-b"}

        client.patch("/brand-kit/colors", headers=h_a, json={"primary": "#AAAAAA"})
        client.patch("/brand-kit/colors", headers=h_b, json={"primary": "#BBBBBB"})

        r_a = client.get("/brand-kit", headers=h_a)
        r_b = client.get("/brand-kit", headers=h_b)

        assert r_a.json()["brand_kit"]["colors"]["primary"] == "#AAAAAA"
        assert r_b.json()["brand_kit"]["colors"]["primary"] == "#BBBBBB"

    # ------------------------------------------------------------------
    # Auth guard
    # ------------------------------------------------------------------

    def test_requires_auth(self, client: TestClient) -> None:
        r = client.get("/brand-kit")
        assert r.status_code in (401, 403, 422)
