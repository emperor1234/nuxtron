"""Coverage for meetings.py and competitive.py happy paths and edge cases."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "meetings-competitive-coverage-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestMeetingsCoverage:
    """Cover create link, list, get, book, list bookings, update status, analytics."""

    def test_create_meeting_link_default_availability(self, client: TestClient) -> None:
        r = client.post(
            "/meetings/links",
            headers=H,
            json={
                "name": "30-min Discovery Call",
                "slug": "discovery-30",
                "duration_minutes": 30,
                "booking_type": "one_on_one",
                "description": "Quick intro call",
                "buffer_before_minutes": 5,
                "buffer_after_minutes": 5,
                "min_notice_hours": 2,
                "max_bookings_per_day": 6,
                "timezone": "Europe/London",
                "availability": [],  # should default to business hours
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["meeting_link"]["slug"] == "discovery-30"
        assert len(data["meeting_link"]["availability"]) == 5  # Mon-Fri default

    def test_create_meeting_link_with_custom_availability(self, client: TestClient) -> None:
        r = client.post(
            "/meetings/links",
            headers=H,
            json={
                "name": "60-min Deep Dive",
                "slug": "deep-dive-60",
                "duration_minutes": 60,
                "booking_type": "round_robin",
                "availability": [
                    {"day": "mon", "start_time": "10:00", "end_time": "16:00"},
                    {"day": "wed", "start_time": "10:00", "end_time": "16:00"},
                ],
            },
        )
        assert r.status_code in (200, 201)

    def test_create_meeting_link_invalid_booking_type_defaults(self, client: TestClient) -> None:
        r = client.post(
            "/meetings/links",
            headers=H,
            json={
                "name": "Default Type Call",
                "slug": "default-type-call",
                "duration_minutes": 15,
                "booking_type": "totally_invalid_type",  # should default to one_on_one
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["meeting_link"]["booking_type"] == "one_on_one"

    def test_create_meeting_link_duplicate_slug(self, client: TestClient) -> None:
        r = client.post(
            "/meetings/links",
            headers=H,
            json={"name": "Dup Slug", "slug": "discovery-30", "duration_minutes": 30},
        )
        assert r.status_code == 409

    def test_list_meeting_links(self, client: TestClient) -> None:
        r = client.get("/meetings/links", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_get_meeting_link(self, client: TestClient) -> None:
        r = client.get("/meetings/links/discovery-30", headers=H)
        assert r.status_code == 200
        assert r.json()["meeting_link"]["slug"] == "discovery-30"

    def test_get_meeting_link_missing(self, client: TestClient) -> None:
        r = client.get("/meetings/links/no-such-slug", headers=H)
        assert r.status_code == 404

    def test_book_meeting_success(self, client: TestClient) -> None:
        # Book during Monday business hours with notice
        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "discovery-30",
                "attendee_email": "prospect@example.com",
                "attendee_name": "Jane Prospect",
                "attendee_company": "Acme Corp",
                "start_time": "2026-06-01T10:00:00Z",  # Monday
                "timezone": "UTC",
                "notes": "Looking forward to this call",
                "custom_answers": {"how_did_you_hear": "LinkedIn"},
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert "confirmation_code" in data
        assert data["booking"]["attendee_email"] == "prospect@example.com"

    def test_book_meeting_outside_availability(self, client: TestClient) -> None:
        # Book during Saturday when only Mon-Fri is available
        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "discovery-30",
                "attendee_email": "another@example.com",
                "attendee_name": "Sam Outside",
                "start_time": "2026-06-06T10:00:00Z",  # Saturday
                "timezone": "UTC",
            },
        )
        assert r.status_code == 409

    def test_book_meeting_conflict(self, client: TestClient) -> None:
        # Book same slot as previous booking — should conflict
        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "discovery-30",
                "attendee_email": "conflict@example.com",
                "attendee_name": "Conflict Person",
                "start_time": "2026-06-01T10:00:00Z",  # same as booked above
                "timezone": "UTC",
            },
        )
        assert r.status_code == 409

    def test_book_meeting_hits_daily_limit(self, client: TestClient) -> None:
        # Create a dedicated link with one booking per day max.
        create_r = client.post(
            "/meetings/links",
            headers=H,
            json={
                "name": "Daily Limit Link",
                "slug": "daily-limit-1",
                "duration_minutes": 30,
                "max_bookings_per_day": 1,
                "availability": [{"day": "mon", "start_time": "09:00", "end_time": "17:00"}],
            },
        )
        assert create_r.status_code in (200, 201)

        first_r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "daily-limit-1",
                "attendee_email": "limit1@example.com",
                "attendee_name": "Limit One",
                "start_time": "2026-06-08T10:00:00Z",
                "timezone": "UTC",
            },
        )
        assert first_r.status_code in (200, 201)

        second_r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "daily-limit-1",
                "attendee_email": "limit2@example.com",
                "attendee_name": "Limit Two",
                "start_time": "2026-06-08T12:00:00Z",
                "timezone": "UTC",
            },
        )
        assert second_r.status_code == 409

    def test_book_meeting_missing_link(self, client: TestClient) -> None:
        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "no-such-link",
                "attendee_email": "x@example.com",
                "attendee_name": "X Person",
                "start_time": "2026-06-02T10:00:00Z",
                "timezone": "UTC",
            },
        )
        assert r.status_code == 404

    def test_book_meeting_min_notice_violation(self, client: TestClient) -> None:
        # Book at a time that's within the min_notice_hours window (past/too soon)
        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "discovery-30",
                "attendee_email": "soon@example.com",
                "attendee_name": "Too Soon",
                "start_time": "2026-05-05T11:00:00Z",  # in the past
                "timezone": "UTC",
            },
        )
        assert r.status_code == 409

    def test_list_bookings(self, client: TestClient) -> None:
        r = client.get("/meetings/bookings", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_bookings_with_filters(self, client: TestClient) -> None:
        r = client.get("/meetings/bookings?status=confirmed&from_date=2026-06-01&to_date=2026-06-30", headers=H)
        assert r.status_code == 200

    def test_update_booking_status(self, client: TestClient) -> None:
        # Get the first booking id
        list_r = client.get("/meetings/bookings", headers=H)
        booking_id = list_r.json()["bookings"][0]["id"]

        r = client.patch(
            f"/meetings/bookings/{booking_id}",
            headers=H,
            json={"status": "cancelled"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["booking"]["status"] == "cancelled"

    def test_update_booking_missing(self, client: TestClient) -> None:
        r = client.patch("/meetings/bookings/9999", headers=H, json={"status": "no_show"})
        assert r.status_code == 404

    def test_meeting_analytics(self, client: TestClient) -> None:
        r = client.get("/meetings/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "total_bookings" in data
        assert "show_up_rate" in data

    def test_book_meeting_ignores_existing_booking_without_start_time(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import meeting_bookings

        link_r = client.get("/meetings/links/discovery-30", headers=H)
        assert link_r.status_code == 200
        link_id = link_r.json()["meeting_link"]["id"]

        # Inject malformed existing booking for the same link; booking logic should skip it.
        meeting_bookings.append({
            "id": 999001,
            "tenant_id": H["X-Tenant-Id"],
            "meeting_link_id": link_id,
            "meeting_link_slug": "discovery-30",
            "status": "confirmed",
            "start_time": "",
        })

        r = client.post(
            "/meetings/book",
            headers=H,
            json={
                "meeting_link_slug": "discovery-30",
                "attendee_email": "skip-empty-start@example.com",
                "attendee_name": "Skip Empty Start",
                "start_time": "2026-06-15T10:00:00Z",
                "timezone": "UTC",
            },
        )
        assert r.status_code in (200, 201)

    def test_meeting_analytics_handles_malformed_hour(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import meeting_bookings

        link_r = client.get("/meetings/links/discovery-30", headers=H)
        assert link_r.status_code == 200
        link_id = link_r.json()["meeting_link"]["id"]

        meeting_bookings.append({
            "id": 999002,
            "tenant_id": H["X-Tenant-Id"],
            "meeting_link_id": link_id,
            "meeting_link_slug": "discovery-30",
            "status": "confirmed",
            "start_time": "2026-06-20TAB:00:00Z",
        })

        r = client.get("/meetings/analytics", headers=H)
        assert r.status_code == 200


class TestCompetitiveCoverage:
    """Cover add profile, list, delete, snapshots, own profile, report, share-of-voice."""

    def test_add_competitor_profile(self, client: TestClient) -> None:
        r = client.post(
            "/competitive/profiles",
            headers=H,
            json={
                "name": "Competitor Alpha",
                "network": "linkedin",
                "handle": "@competitor_alpha",
                "profile_url": "https://linkedin.com/company/competitor-alpha",
                "industry": "SaaS",
                "notes": "Main competitor in mid-market",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["profile"]["name"] == "Competitor Alpha"
        assert data["created"] is True

    def test_add_duplicate_profile_returns_existing(self, client: TestClient) -> None:
        r = client.post(
            "/competitive/profiles",
            headers=H,
            json={
                "name": "Competitor Alpha",
                "network": "linkedin",
                "handle": "competitor_alpha",  # same handle (without @)
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["created"] is False

    def test_add_second_competitor(self, client: TestClient) -> None:
        r = client.post(
            "/competitive/profiles",
            headers=H,
            json={
                "name": "Competitor Beta",
                "network": "instagram",
                "handle": "competitor_beta",
                "industry": "MarTech",
            },
        )
        assert r.status_code in (200, 201)

    def test_list_competitors(self, client: TestClient) -> None:
        r = client.get("/competitive/profiles", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 2

    def test_list_competitors_network_filter(self, client: TestClient) -> None:
        r = client.get("/competitive/profiles?network=linkedin", headers=H)
        assert r.status_code == 200
        for p in r.json()["profiles"]:
            assert p["network"] == "linkedin"

    def test_add_snapshot_for_competitor(self, client: TestClient) -> None:
        # Get first profile id
        list_r = client.get("/competitive/profiles", headers=H)
        profile_id = list_r.json()["profiles"][0]["id"]

        r = client.post(
            f"/competitive/profiles/{profile_id}/snapshots",
            headers=H,
            json={
                "followers": 50000,
                "following": 200,
                "posts_last_30d": 12,
                "avg_likes_last_30d": 350.0,
                "avg_comments_last_30d": 42.0,
                "avg_shares_last_30d": 18.0,
                "avg_views_last_30d": 0.0,
                "engagement_rate": 2.8,
                "estimated_reach": 75000,
                "estimated_mentions": 420,
                "snapshot_date": "2026-05-01",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["snapshot"]["followers"] == 50000

    def test_delete_competitor_cascades_snapshots(self, client: TestClient) -> None:
        from backend.fastapi.app.memory_stores import competitor_snapshots

        # Create a dedicated competitor.
        prof_r = client.post(
            "/competitive/profiles",
            headers=H,
            json={"name": "Competitor Cascade", "network": "linkedin", "handle": "cascade_target"},
        )
        assert prof_r.status_code in (200, 201)
        profile_id = prof_r.json()["profile"]["id"]

        # Add snapshots that must be removed by cascade delete.
        for day in ("2026-05-02", "2026-05-03"):
            snap_r = client.post(
                f"/competitive/profiles/{profile_id}/snapshots",
                headers=H,
                json={
                    "followers": 1000,
                    "following": 100,
                    "posts_last_30d": 2,
                    "avg_likes_last_30d": 10.0,
                    "avg_comments_last_30d": 1.0,
                    "avg_shares_last_30d": 1.0,
                    "avg_views_last_30d": 0.0,
                    "engagement_rate": 1.1,
                    "estimated_reach": 2000,
                    "estimated_mentions": 20,
                    "snapshot_date": day,
                },
            )
            assert snap_r.status_code in (200, 201)

        del_r = client.delete(f"/competitive/profiles/{profile_id}", headers=H)
        assert del_r.status_code in (200, 201)

        assert not any(
            s.get("tenant_id") == H["X-Tenant-Id"] and s.get("competitor_id") == profile_id
            for s in competitor_snapshots
        )

    def test_add_snapshot_missing_profile(self, client: TestClient) -> None:
        r = client.post(
            "/competitive/profiles/9999/snapshots",
            headers=H,
            json={"followers": 1000, "engagement_rate": 1.0},
        )
        assert r.status_code == 404

    def test_record_own_profile(self, client: TestClient) -> None:
        r = client.post(
            "/competitive/own-profile",
            headers=H,
            json={
                "network": "linkedin",
                "followers": 30000,
                "following": 500,
                "posts_last_30d": 20,
                "avg_likes_last_30d": 200.0,
                "avg_comments_last_30d": 25.0,
                "avg_shares_last_30d": 10.0,
                "engagement_rate": 1.5,
                "estimated_reach": 40000,
                "estimated_mentions": 280,
                "snapshot_date": "2026-05-01",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["record"]["competitor_id"] == 0
        assert r.json()["record"]["competitor_name"] == "__OWN_BRAND__"

    def test_comparison_report(self, client: TestClient) -> None:
        r = client.get("/competitive/report", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "competitors" in data
        assert "own_brand" in data

    def test_comparison_report_network_filter(self, client: TestClient) -> None:
        r = client.get("/competitive/report?network=linkedin", headers=H)
        assert r.status_code == 200
        assert r.json()["network_filter"] == "linkedin"

    def test_share_of_voice(self, client: TestClient) -> None:
        r = client.get("/competitive/share-of-voice", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "share_of_voice" in data
        assert "total_estimated_mentions" in data

    def test_share_of_voice_with_zeros(self, client: TestClient) -> None:
        H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "sov-zero-tenant"}
        r = client.get("/competitive/share-of-voice", headers=H2)
        assert r.status_code == 200
        # Empty tenant — total_mentions should be 0
        assert r.json()["total_estimated_mentions"] == 0

    def test_delete_competitor(self, client: TestClient) -> None:
        # Add a profile to delete
        r = client.post(
            "/competitive/profiles",
            headers=H,
            json={"name": "Delete Me", "network": "instagram", "handle": "delete_me_comp"},
        )
        profile_id = r.json()["profile"]["id"]

        r2 = client.delete(f"/competitive/profiles/{profile_id}", headers=H)
        assert r2.status_code in (200, 201)
        assert r2.json()["deleted"] is True

    def test_delete_missing_competitor(self, client: TestClient) -> None:
        r = client.delete("/competitive/profiles/9999", headers=H)
        assert r.status_code == 404
