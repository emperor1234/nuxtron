import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


@dataclass
class RetentionContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    streaks_memory: list[dict[str, Any]]
    credit_ledger_memory: list[dict[str, Any]]
    notifications_memory: list[dict[str, Any]]
    scheduled_posts_memory: list[dict[str, Any]]
    email_campaigns_memory: list[dict[str, Any]]
    influencer_campaigns_memory: list[dict[str, Any]]
    chatbots_memory: list[dict[str, Any]]
    tenant_profiles_memory: list[dict[str, Any]]
    invoices_memory: list[dict[str, Any]]
    milestone_rewards: dict[int, int]
    no_recoverable_streak: str
    streak_recovery_limited: str
    today_fn: Callable[[], date]
    parse_date_fn: Callable[[str | None], date | None]
    badge_for_streak_fn: Callable[[int], str]
    get_streak_fn: Callable[[str], dict[str, Any]]
    apply_rollover_fn: Callable[[dict[str, Any], date], None]
    snapshot_fn: Callable[[dict[str, Any]], dict[str, Any]]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]


def register_retention_routes(*, router: APIRouter, context: RetentionContext) -> None:  # NOSONAR
    ctx = context

    @router.get('/engagement/streak')
    def get_streak(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:streak:get', 240, 60)
        today = ctx.today_fn()
        with ctx.lock:
            record = ctx.get_streak_fn(auth.tenant_id)
            ctx.apply_rollover_fn(record, today)
            snapshot = ctx.snapshot_fn(record)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'streak': snapshot, 'milestone_rewards': ctx.milestone_rewards}

    @router.post('/engagement/streak/check-in')
    def check_in(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:streak:check-in', 60, 60)
        today = ctx.today_fn()
        today_iso = today.isoformat()
        with ctx.lock:
            record = ctx.get_streak_fn(auth.tenant_id)
            ctx.apply_rollover_fn(record, today)

            if record.get('last_check_in_date') == today_iso:
                snapshot = ctx.snapshot_fn(record)
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'already_checked_in': True,
                    'credits_awarded': 0,
                    'streak': snapshot,
                }

            record['current_streak'] = int(record.get('current_streak', 0)) + 1
            record['longest_streak'] = max(int(record.get('longest_streak', 0)), int(record['current_streak']))
            record['last_check_in_date'] = today_iso
            record['recoverable_streak'] = 0
            record['recoverable_until'] = None
            record['badge'] = ctx.badge_for_streak_fn(int(record['current_streak']))
            record['updated_at'] = datetime.now(UTC).isoformat()

            credits_awarded = 0
            unlocked_milestone: int | None = None
            if int(record['current_streak']) in ctx.milestone_rewards:
                milestone = int(record['current_streak'])
                unlocked = {int(item) for item in record.get('milestones_unlocked', [])}
                if milestone not in unlocked:
                    credits_awarded = ctx.milestone_rewards[milestone]
                    unlocked.add(milestone)
                    record['milestones_unlocked'] = sorted(unlocked)
                    unlocked_milestone = milestone
                    ctx.append_credit_fn(auth.tenant_id, credits_awarded, f'daily_streak_{milestone}_day_bonus')
                    ctx.append_notification_fn(
                        auth.tenant_id,
                        'Daily Streak Milestone',
                        f'You reached a {milestone}-day streak and earned {credits_awarded} AI credits.',
                        'engagement',
                    )

            ctx.append_audit_fn(auth.tenant_id, 'daily_streak_check_in', {
                'current_streak': record['current_streak'],
                'credits_awarded': credits_awarded,
                'milestone': unlocked_milestone,
            })
            snapshot = ctx.snapshot_fn(record)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'already_checked_in': False,
            'credits_awarded': credits_awarded,
            'milestone_unlocked': unlocked_milestone,
            'streak': snapshot,
        }

    @router.post('/engagement/streak/recover', responses={422: {'description': 'No recoverable streak or recovery cooldown active.'}})
    def recover_streak(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:streak:recover', 20, 60)
        today = ctx.today_fn()
        today_iso = today.isoformat()
        with ctx.lock:
            record = ctx.get_streak_fn(auth.tenant_id)
            ctx.apply_rollover_fn(record, today)
            recoverable_streak = int(record.get('recoverable_streak', 0))
            if recoverable_streak <= 0 or record.get('recoverable_until') != today_iso:
                raise HTTPException(status_code=422, detail=ctx.no_recoverable_streak)

            last_recovery_date = ctx.parse_date_fn(record.get('last_recovery_date'))
            if last_recovery_date is not None and (today - last_recovery_date).days < 30:
                raise HTTPException(status_code=422, detail=ctx.streak_recovery_limited)

            record['current_streak'] = recoverable_streak
            record['longest_streak'] = max(int(record.get('longest_streak', 0)), recoverable_streak)
            record['last_check_in_date'] = today_iso
            record['last_recovery_date'] = today_iso
            record['recoverable_streak'] = 0
            record['recoverable_until'] = None
            record['badge'] = ctx.badge_for_streak_fn(recoverable_streak)
            record['updated_at'] = datetime.now(UTC).isoformat()
            ctx.append_audit_fn(auth.tenant_id, 'daily_streak_recovered', {'current_streak': record['current_streak']})
            snapshot = ctx.snapshot_fn(record)

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'recovered': True, 'streak': snapshot}

    @router.get('/engagement/streak/leaderboard')
    def streak_leaderboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:streak:leaderboard', 120, 60)
        today = ctx.today_fn()
        with ctx.lock:
            for record in ctx.streaks_memory:
                ctx.apply_rollover_fn(record, today)
            leaderboard_rows: list[dict[str, Any]] = [
                {
                    'tenant_id': str(item.get('tenant_id') or ''),
                    'current_streak': int(item.get('current_streak', 0)),
                    'longest_streak': int(item.get('longest_streak', 0)),
                    'badge': str(item.get('badge', ctx.badge_for_streak_fn(int(item.get('current_streak', 0))))) or '',
                }
                for item in ctx.streaks_memory
            ]
            leaderboard: list[dict[str, Any]] = sorted(
                leaderboard_rows,
                key=lambda item: (-item['current_streak'], -item['longest_streak'], item['tenant_id']),
            )[:10]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'leaderboard': leaderboard}

    @router.get('/engagement/withdrawal-preview')
    def withdrawal_preview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:withdrawal-preview', 120, 60)
        today = ctx.today_fn()

        with ctx.lock:
            streak_record = ctx.get_streak_fn(auth.tenant_id)
            ctx.apply_rollover_fn(streak_record, today)
            streak_snapshot = ctx.snapshot_fn(streak_record)

            ai_credits_balance = sum(
                int(entry.get('amount', 0))
                for entry in ctx.credit_ledger_memory
                if entry.get('tenant_id') == auth.tenant_id
            )
            unread_notifications = sum(
                1
                for item in ctx.notifications_memory
                if item.get('tenant_id') == auth.tenant_id and not item.get('read', False)
            )
            scheduled_posts = sum(
                1 for item in ctx.scheduled_posts_memory if item.get('tenant_id') == auth.tenant_id
            )
            email_campaigns = sum(
                1 for item in ctx.email_campaigns_memory if item.get('tenant_id') == auth.tenant_id
            )
            influencer_campaigns = sum(
                1 for item in ctx.influencer_campaigns_memory if item.get('tenant_id') == auth.tenant_id
            )
            deployed_chatbots = sum(
                1
                for item in ctx.chatbots_memory
                if item.get('tenant_id') == auth.tenant_id and bool(item.get('deployed'))
            )
            tenant_profile_count = sum(
                1 for item in ctx.tenant_profiles_memory if item.get('tenant_id') == auth.tenant_id
            )

        losses: list[dict[str, Any]] = [
            {
                'item': 'ai_credits_balance',
                'value': ai_credits_balance,
                'impact': 'You will lose available AI credits tied to this tenant account.',
            },
            {
                'item': 'streak_status',
                'value': {
                    'current_streak': streak_snapshot['current_streak'],
                    'longest_streak': streak_snapshot['longest_streak'],
                    'badge': streak_snapshot['badge'],
                },
                'impact': 'Your streak progress, recovery window, and badge tier will reset.',
            },
            {
                'item': 'scheduled_posts',
                'value': scheduled_posts,
                'impact': 'Scheduled social posts and automation queue context will be removed.',
            },
            {
                'item': 'email_campaigns',
                'value': email_campaigns,
                'impact': 'Email campaign history and draft pipeline associated with this tenant will be lost.',
            },
            {
                'item': 'influencer_campaigns',
                'value': influencer_campaigns,
                'impact': 'Influencer campaign records and outreach context tied to this tenant will be lost.',
            },
            {
                'item': 'deployed_chatbots',
                'value': deployed_chatbots,
                'impact': 'Deployed chatbot assets and conversation context will no longer be available.',
            },
            {
                'item': 'unread_notifications',
                'value': unread_notifications,
                'impact': 'Unread operational and growth notifications will be discarded.',
            },
            {
                'item': 'tenant_profile_count',
                'value': tenant_profile_count,
                'impact': 'Tenant profile metadata and account-level configuration will be removed.',
            },
        ]

        dependency_score = min(
            100,
            (12 if ai_credits_balance > 0 else 0)
            + min(20, int(streak_snapshot['current_streak']))
            + min(20, scheduled_posts)
            + min(15, email_campaigns)
            + min(15, influencer_campaigns)
            + min(10, deployed_chatbots)
            + min(8, unread_notifications)
            + (10 if tenant_profile_count > 0 else 0),
        )

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'withdrawal_preview': {
                'dependency_score': dependency_score,
                'recommendation': 'high_retention_risk' if dependency_score >= 60 else 'moderate_retention_risk',
                'what_you_will_lose': losses,
            },
        }

    @router.get('/engagement/earnings-ticker')
    def earnings_ticker(auth: AuthDep, limit: int = 25) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        ctx.enforce_rate_limit(f'{auth.tenant_id}:engagement:earnings-ticker', 240, 60)
        today_iso = ctx.today_fn().isoformat()
        capped_limit = max(1, min(100, int(limit)))

        with ctx.lock:
            credit_entries = [
                entry.copy()
                for entry in ctx.credit_ledger_memory
                if entry.get('tenant_id') == auth.tenant_id and int(entry.get('amount', 0)) > 0
            ]
            paid_invoices = [
                invoice.copy()
                for invoice in ctx.invoices_memory
                if invoice.get('tenant_id') == auth.tenant_id
                and str(invoice.get('status', '')).lower() in ('paid', 'succeeded', 'completed')
                and float(invoice.get('amount', 0.0)) > 0.0
            ]

        credit_events: list[dict[str, Any]] = [
            {
                'type': 'credits',
                'amount': int(entry.get('amount', 0)),
                'currency': 'AI_CREDITS',
                'label': str(entry.get('reason', 'credits_earned')),
                'occurred_at': entry.get('created_at'),
            }
            for entry in credit_entries
        ]
        revenue_events: list[dict[str, Any]] = [
            {
                'type': 'revenue',
                'amount': round(float(invoice.get('amount', 0.0)), 2),
                'currency': str(invoice.get('currency', 'USD')),
                'label': f"invoice_{invoice.get('id')}",
                'occurred_at': invoice.get('created_at'),
            }
            for invoice in paid_invoices
        ]

        combined_events: list[dict[str, Any]] = sorted(
            credit_events + revenue_events,
            key=lambda item: str(item.get('occurred_at', '')),
            reverse=True,
        )[:capped_limit]

        today_credits = sum(
            int(entry.get('amount', 0))
            for entry in credit_entries
            if str(entry.get('created_at', '')).startswith(today_iso)
        )
        today_revenue = round(
            sum(
                float(invoice.get('amount', 0.0))
                for invoice in paid_invoices
                if str(invoice.get('created_at', '')).startswith(today_iso)
            ),
            2,
        )
        lifetime_credits = sum(int(entry.get('amount', 0)) for entry in credit_entries)
        lifetime_revenue = round(sum(float(invoice.get('amount', 0.0)) for invoice in paid_invoices), 2)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generated_at': datetime.now(UTC).isoformat(),
            'ticker': {
                'summary': {
                    'today_credits_earned': today_credits,
                    'today_revenue_usd': today_revenue,
                    'lifetime_credits_earned': lifetime_credits,
                    'lifetime_revenue_usd': lifetime_revenue,
                },
                'events': combined_events,
            },
        }
