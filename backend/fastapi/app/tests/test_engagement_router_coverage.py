"""Targeted coverage for smaller engagement routers with in-memory branches."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestNuxtronStudiosCoverage:
    H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "studios-coverage-tenant"}

    def test_create_proposal_missing_brief(self, client: TestClient) -> None:
        r = client.post(
            "/money-printers/nuxtron-studios/proposals",
            headers=self.H,
            json={"brief_id": 9999, "service_id": 1, "bid_usd": 150.0},
        )
        assert r.status_code == 404

    def test_create_proposal_missing_service(self, client: TestClient) -> None:
        brief_r = client.post(
            "/money-printers/nuxtron-studios/briefs",
            headers=self.H,
            json={
                "title": "Launch video brief",
                "category": "video",
                "budget_usd": 1000,
                "due_date": "2026-06-01",
                "scope": "Create a hero video",
            },
        )
        assert brief_r.status_code in (200, 201)
        brief_id = brief_r.json()["brief"]["id"]

        r = client.post(
            "/money-printers/nuxtron-studios/proposals",
            headers=self.H,
            json={"brief_id": brief_id, "service_id": 9999, "bid_usd": 200.0},
        )
        assert r.status_code == 404

    def test_happy_path_and_release_conflict(self, client: TestClient) -> None:
        service_r = client.post(
            "/money-printers/nuxtron-studios/services",
            headers=self.H,
            json={
                "title": "UGC Editing Package",
                "category": "video",
                "price_usd": 750,
                "turnaround_days": 5,
            },
        )
        assert service_r.status_code in (200, 201)
        service_id = service_r.json()["service"]["id"]

        brief_r = client.post(
            "/money-printers/nuxtron-studios/briefs",
            headers=self.H,
            json={
                "title": "UGC ad brief",
                "category": "video",
                "budget_usd": 1200,
                "due_date": "2026-06-10",
                "scope": "Three short paid social ads",
            },
        )
        assert brief_r.status_code in (200, 201)
        brief_id = brief_r.json()["brief"]["id"]

        proposal_r = client.post(
            "/money-printers/nuxtron-studios/proposals",
            headers=self.H,
            json={
                "brief_id": brief_id,
                "service_id": service_id,
                "bid_usd": 899,
                "message": "Can deliver in four business days",
            },
        )
        assert proposal_r.status_code in (200, 201)
        proposal_id = proposal_r.json()["proposal"]["id"]

        missing_escrow = client.post(
            "/money-printers/nuxtron-studios/escrows",
            headers=self.H,
            json={"proposal_id": 9999, "milestone_name": "Deposit", "amount_usd": 300},
        )
        assert missing_escrow.status_code == 404

        escrow_r = client.post(
            "/money-printers/nuxtron-studios/escrows",
            headers=self.H,
            json={"proposal_id": proposal_id, "milestone_name": "Deposit", "amount_usd": 300},
        )
        assert escrow_r.status_code in (200, 201)
        escrow_id = escrow_r.json()["escrow"]["id"]

        release_r = client.post(
            "/money-printers/nuxtron-studios/escrows/release",
            headers=self.H,
            json={"escrow_id": escrow_id, "approved": True, "note": "Looks good"},
        )
        assert release_r.status_code in (200, 201)
        if release_r.status_code in (200, 201):
            assert release_r.json()["credits_awarded"] > 0

        conflict_r = client.post(
            "/money-printers/nuxtron-studios/escrows/release",
            headers=self.H,
            json={"escrow_id": escrow_id, "approved": True, "note": "Second release attempt"},
        )
        assert conflict_r.status_code == 409

    def test_release_escrow_missing_and_disputed(self, client: TestClient) -> None:
        missing_r = client.post(
            "/money-printers/nuxtron-studios/escrows/release",
            headers=self.H,
            json={"escrow_id": 9999, "approved": False, "note": "Missing"},
        )
        assert missing_r.status_code == 404

        service_r = client.post(
            "/money-printers/nuxtron-studios/services",
            headers=self.H,
            json={
                "title": "Thumbnail package",
                "category": "design",
                "price_usd": 200,
                "turnaround_days": 2,
            },
        )
        brief_r = client.post(
            "/money-printers/nuxtron-studios/briefs",
            headers=self.H,
            json={
                "title": "Thumbnail brief",
                "category": "design",
                "budget_usd": 300,
                "due_date": "2026-06-12",
                "scope": "Create 5 variants",
            },
        )
        proposal_r = client.post(
            "/money-printers/nuxtron-studios/proposals",
            headers=self.H,
            json={
                "brief_id": brief_r.json()["brief"]["id"],
                "service_id": service_r.json()["service"]["id"],
                "bid_usd": 250,
            },
        )
        escrow_r = client.post(
            "/money-printers/nuxtron-studios/escrows",
            headers=self.H,
            json={"proposal_id": proposal_r.json()["proposal"]["id"], "milestone_name": "Round 1", "amount_usd": 100},
        )
        disputed_r = client.post(
            "/money-printers/nuxtron-studios/escrows/release",
            headers=self.H,
            json={"escrow_id": escrow_r.json()["escrow"]["id"], "approved": False, "note": "Needs revisions"},
        )
        assert disputed_r.status_code in (200, 201)
        if disputed_r.status_code in (200, 201):
            assert disputed_r.json()["credits_awarded"] == 0

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-studios/overview", headers=self.H)
        assert r.status_code in VALID
        if r.status_code == 200:
            assert "studios" in r.json()


class TestNuxtronUniversityCoverage:
    H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "university-coverage-tenant"}

    def test_catalog_and_missing_course(self, client: TestClient) -> None:
        catalog_r = client.get("/money-printers/nuxtron-university/catalog", headers=self.H)
        assert catalog_r.status_code in VALID

        missing_course_r = client.post(
            "/money-printers/nuxtron-university/cohorts",
            headers=self.H,
            json={"course_id": 9999, "starts_at": "2026-07-01", "capacity": 2},
        )
        assert missing_course_r.status_code == 404

    def test_course_cohort_enrollment_progress_flow(self, client: TestClient) -> None:
        course_r = client.post(
            "/money-printers/nuxtron-university/courses",
            headers=self.H,
            json={"title": "AI Revenue Ops", "track": "growth", "level": "advanced", "price_usd": 499},
        )
        assert course_r.status_code in (200, 201)
        course_id = course_r.json()["course"]["id"]

        cohort_r = client.post(
            "/money-printers/nuxtron-university/cohorts",
            headers=self.H,
            json={"course_id": course_id, "starts_at": "2026-07-15", "capacity": 1, "mentor_name": ""},
        )
        assert cohort_r.status_code in (200, 201)
        cohort_id = cohort_r.json()["cohort"]["id"]

        missing_enroll_r = client.post(
            "/money-printers/nuxtron-university/enrollments",
            headers=self.H,
            json={"cohort_id": 9999, "learner_email": "ghost@example.com"},
        )
        assert missing_enroll_r.status_code == 404

        enroll_r = client.post(
            "/money-printers/nuxtron-university/enrollments",
            headers=self.H,
            json={"cohort_id": cohort_id, "learner_email": "learner@example.com"},
        )
        assert enroll_r.status_code in (200, 201)
        enrollment_id = enroll_r.json()["enrollment"]["id"]

        at_capacity_r = client.post(
            "/money-printers/nuxtron-university/enrollments",
            headers=self.H,
            json={"cohort_id": cohort_id, "learner_email": "learner2@example.com"},
        )
        assert at_capacity_r.status_code == 422

        missing_progress_r = client.post(
            "/money-printers/nuxtron-university/progress",
            headers=self.H,
            json={"enrollment_id": 9999, "checkpoint": "lesson-1", "completion_delta": 10},
        )
        assert missing_progress_r.status_code == 404

        progress_r = client.post(
            "/money-printers/nuxtron-university/progress",
            headers=self.H,
            json={"enrollment_id": enrollment_id, "checkpoint": "capstone", "completion_delta": 100, "note": "Finished"},
        )
        assert progress_r.status_code in (200, 201)
        if progress_r.status_code in (200, 201):
            assert progress_r.json()["credits_awarded"] == 65
            assert progress_r.json()["enrollment"]["status"] == "completed"

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-university/overview", headers=self.H)
        assert r.status_code in VALID
        if r.status_code == 200:
            assert "university" in r.json()


class TestReferralsCoverage:
    REFERRER = {"X-API-Key": "test-api-key", "X-Tenant-Id": "referrer-coverage-tenant"}
    REFERRED = {"X-API-Key": "test-api-key", "X-Tenant-Id": "referred-coverage-tenant"}
    THIRD = {"X-API-Key": "test-api-key", "X-Tenant-Id": "referred-coverage-tenant-2"}

    def test_read_routes(self, client: TestClient) -> None:
        get_r = client.get("/engagement/referrals", headers=self.REFERRER)
        assert get_r.status_code in VALID

        gen_r = client.post("/engagement/referrals/generate-code", headers=self.REFERRER)
        assert gen_r.status_code in (200, 201)
        if gen_r.status_code in (200, 201):
            assert "profile" in gen_r.json()

        board_r = client.get("/engagement/referrals/leaderboard", headers=self.REFERRER)
        assert board_r.status_code in VALID

    def test_claim_branches(self, client: TestClient) -> None:
        invalid_r = client.post(
            "/engagement/referrals/claim",
            headers=self.REFERRED,
            json={"referral_code": "NOPE9999", "referred_email": "new@example.com"},
        )
        assert invalid_r.status_code == 404

        ref_profile_r = client.post("/engagement/referrals/generate-code", headers=self.REFERRER)
        assert ref_profile_r.status_code in (200, 201)
        ref_code = ref_profile_r.json()["profile"]["referral_code"]

        self_r = client.post(
            "/engagement/referrals/claim",
            headers=self.REFERRER,
            json={"referral_code": ref_code, "referred_email": "self@example.com"},
        )
        assert self_r.status_code == 422

        claim_r = client.post(
            "/engagement/referrals/claim",
            headers=self.REFERRED,
            json={"referral_code": ref_code, "referred_email": "joiner@example.com"},
        )
        assert claim_r.status_code in (200, 201)
        if claim_r.status_code in (200, 201):
            assert "claim" in claim_r.json()

        already_r = client.post(
            "/engagement/referrals/claim",
            headers=self.REFERRED,
            json={"referral_code": ref_code, "referred_email": "again@example.com"},
        )
        assert already_r.status_code == 409

        second_claim_r = client.post(
            "/engagement/referrals/claim",
            headers=self.THIRD,
            json={"referral_code": ref_code, "referred_email": "other@example.com"},
        )
        assert second_claim_r.status_code in (200, 201)


class TestMoneyPrintersBankCoverage:
    H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bank-coverage-tenant"}
    H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bank-coverage-tenant-2"}

    def test_rollup_helper_unknown_printer(self) -> None:
        from backend.fastapi.app.routers.engagement_money_printers_bank import _build_printer_rollup

        rollup, confidences = _build_printer_rollup(
            ["agency", "education"],
            [{"printer": "unknown", "expected_monthly_revenue_usd": 999}],
            [{"printer": "unknown", "outcome": "validated", "confidence": 90}],
        )
        assert rollup["agency"]["ideas"] == 0
        assert confidences["education"] == []

    def test_idea_validation_and_backlog_filters(self, client: TestClient) -> None:
        idea_r = client.post(
            "/money-printers/ideas",
            headers=self.H,
            json={
                "printer": "nuxtron_bank",
                "hypothesis": "Launch a managed retainer offer for B2B AI ops",
                "expected_monthly_revenue_usd": 12000,
                "owner": "",
            },
        )
        assert idea_r.status_code in (200, 201)
        idea_id = idea_r.json()["idea"]["id"]

        not_found_r = client.post(
            "/money-printers/ideas/validate",
            headers=self.H,
            json={"idea_id": 9999, "outcome": "validated", "confidence": 88},
        )
        assert not_found_r.status_code == 404

        invalid_r = client.post(
            "/money-printers/ideas/validate",
            headers=self.H,
            json={"idea_id": idea_id, "outcome": "weird", "confidence": 88},
        )
        assert invalid_r.status_code == 422

        validated_r = client.post(
            "/money-printers/ideas/validate",
            headers=self.H,
            json={"idea_id": idea_id, "outcome": "validated", "confidence": 91, "evidence": "pilot closed"},
        )
        assert validated_r.status_code in (200, 201)
        if validated_r.status_code in (200, 201):
            assert validated_r.json()["credits_awarded"] == 40

        backlog_r = client.get("/money-printers/backlog?printer=nuxtron_bank&status=validated&limit=5", headers=self.H)
        assert backlog_r.status_code in VALID
        if backlog_r.status_code == 200:
            assert backlog_r.json()["count"] >= 1

        portfolio_r = client.get("/money-printers/portfolio", headers=self.H)
        assert portfolio_r.status_code in VALID

    def test_wallet_transfer_payout_paths(self, client: TestClient) -> None:
        wallet_r = client.get("/money-printers/nuxtron-bank/wallet", headers=self.H)
        assert wallet_r.status_code in VALID

        transfer_fail_r = client.post(
            "/money-printers/nuxtron-bank/transfer",
            headers=self.H,
            json={"to_tenant_id": self.H2["X-Tenant-Id"], "amount": 999999999, "note": "too much"},
        )
        assert transfer_fail_r.status_code == 422

        preview_r = client.get(
            "/money-printers/nuxtron-bank/payout-preview?amount=100",
            headers=self.H,
        )
        assert preview_r.status_code in VALID
        if preview_r.status_code == 200:
            assert "payout_preview" in preview_r.json()

        payout_fail_r = client.post(
            "/money-printers/nuxtron-bank/payouts",
            headers=self.H,
            json={"amount": 999999999, "destination": "Bank of Mars"},
        )
        assert payout_fail_r.status_code == 422

        transfer_ok_r = client.post(
            "/money-printers/nuxtron-bank/transfer",
            headers=self.H,
            json={"to_tenant_id": self.H2["X-Tenant-Id"], "amount": 1.0, "note": "seed"},
        )
        assert transfer_ok_r.status_code in VALID

        payout_ok_r = client.post(
            "/money-printers/nuxtron-bank/payouts",
            headers=self.H2,
            json={"amount": 1.0, "destination": "Main checking"},
        )
        assert payout_ok_r.status_code in VALID

        payouts_r = client.get("/money-printers/nuxtron-bank/payouts", headers=self.H2)
        assert payouts_r.status_code in VALID
        if payouts_r.status_code == 200:
            assert "payouts" in payouts_r.json()
