import importlib
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated, Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth


def _import_router_module(name: str):
    return importlib.import_module(f'.{name}', package=__package__)


_engagement_retention_module = _import_router_module('engagement_retention')
RetentionContext = _engagement_retention_module.RetentionContext
register_retention_routes = _engagement_retention_module.register_retention_routes

_engagement_companion_social_module = _import_router_module('engagement_companion_social')
CompanionSocialContext = _engagement_companion_social_module.CompanionSocialContext
register_companion_social_routes = _engagement_companion_social_module.register_companion_social_routes

_engagement_dependency_community_module = _import_router_module('engagement_dependency_community')
DependencyCommunityContext = _engagement_dependency_community_module.DependencyCommunityContext
register_dependency_community_routes = _engagement_dependency_community_module.register_dependency_community_routes

_engagement_brand_autopilot_achievements_module = _import_router_module('engagement_brand_autopilot_achievements')
BrandAutopilotAchievementsContext = _engagement_brand_autopilot_achievements_module.BrandAutopilotAchievementsContext
register_brand_autopilot_achievement_routes = _engagement_brand_autopilot_achievements_module.register_brand_autopilot_achievement_routes

_engagement_white_label_module = _import_router_module('engagement_white_label')
WhiteLabelContext = _engagement_white_label_module.WhiteLabelContext
register_white_label_routes = _engagement_white_label_module.register_white_label_routes

_engagement_money_printers_commerce_module = _import_router_module('engagement_money_printers_commerce')
CommerceContext = _engagement_money_printers_commerce_module.CommerceContext
register_commerce_routes = _engagement_money_printers_commerce_module.register_commerce_routes

_engagement_talent_agency_module = _import_router_module('engagement_talent_agency')
TalentAgencyContext = _engagement_talent_agency_module.TalentAgencyContext
register_talent_agency_routes = _engagement_talent_agency_module.register_talent_agency_routes
_engagement_money_printers_bank_module = _import_router_module('engagement_money_printers_bank')
MoneyPrintersBankContext = _engagement_money_printers_bank_module.MoneyPrintersBankContext
register_money_printers_bank_routes = _engagement_money_printers_bank_module.register_money_printers_bank_routes
_engagement_university_module = _import_router_module('engagement_university')
UniversityContext = _engagement_university_module.UniversityContext
register_university_routes = _engagement_university_module.register_university_routes
_engagement_studios_module = _import_router_module('engagement_studios')
StudiosContext = _engagement_studios_module.StudiosContext
register_studios_routes = _engagement_studios_module.register_studios_routes
_engagement_referrals_module = _import_router_module('engagement_referrals')
ReferralsContext = _engagement_referrals_module.ReferralsContext
register_referrals_routes = _engagement_referrals_module.register_referrals_routes

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# Query parameter type alias
PaginationLimit = Annotated[int, Query(ge=1, le=100)]
OptionalQueryStr = Annotated[str | None, Query()]
PayoutAmount = Annotated[float, Query(ge=0.0, le=1000000000.0)]

# Error message constants
FOMO_RULE_NOT_FOUND = 'FOMO rule not found.'
FOMO_RULE_INACTIVE = 'FOMO rule is inactive.'
COMMUNITY_CIRCLE_NOT_FOUND = 'Community circle not found.'
MONEY_PRINTER_IDEA_NOT_FOUND = 'Money printer idea not found.'
UNSUPPORTED_MONEY_PRINTER = 'Unsupported money printer name.'

NO_RECOVERABLE_STREAK = 'No recoverable streak is available today.'
STREAK_RECOVERY_LIMITED = 'Streak recovery is limited to once every 30 days.'
INVALID_OUTCOME = 'Outcome must be validated, invalidated, or inconclusive.'
INSUFFICIENT_BALANCE = 'Insufficient bank wallet balance.'
INSUFFICIENT_PAYOUT_BALANCE = 'Insufficient balance for payout request.'
COURSE_NOT_FOUND = 'University course not found.'
COHORT_NOT_FOUND = 'University cohort not found.'
COHORT_AT_CAPACITY = 'University cohort is at capacity.'
ENROLLMENT_NOT_FOUND = 'University enrollment not found.'
BRIEF_NOT_FOUND = 'Studios brief not found.'
SERVICE_NOT_FOUND = 'Studios service not found.'
PROPOSAL_NOT_FOUND = 'Studios proposal not found.'
ESCROW_NOT_FOUND = 'Studios escrow not found.'
ESCROW_NOT_FUNDED = 'Escrow can only be released from funded state.'
PRODUCT_NOT_FOUND = 'Product not found'
CREATOR_NOT_FOUND = 'Creator not found'
DEAL_NOT_FOUND = 'Deal not found'
REFERRAL_NOT_FOUND = 'Referral code not found.'
SELF_REFERRAL_NOT_ALLOWED = 'Self-referral is not allowed.'

MILESTONE_REWARDS: dict[int, int] = {
    7: 50,
    30: 250,
    90: 1000,
    365: 5000,
}

REFERRAL_REWARDS = {
    'referrer_credits': 120,
    'referred_credits': 80,
}


class ReferralClaimRequest(BaseModel):
    referral_code: str = Field(min_length=4, max_length=40)
    referred_email: str = Field(default='', max_length=320)


class CompanionCheckInRequest(BaseModel):
    mood: str = Field(default='focused', max_length=40)
    energy: int = Field(default=3, ge=1, le=5)
    today_goal: str = Field(default='', max_length=320)


class CompanionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class FomoRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    trigger_type: str = Field(default='limited_slot', max_length=40)
    threshold: int = Field(default=1, ge=1, le=100000)
    window_minutes: int = Field(default=60, ge=1, le=1440)


class FomoTriggerRequest(BaseModel):
    rule_id: int
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=5, max_length=4000)
    priority: str = Field(default='high', max_length=20)


class SocialProofEventRequest(BaseModel):
    headline: str = Field(min_length=3, max_length=180)
    metric_label: str = Field(default='wins', max_length=60)
    metric_value: float = Field(default=1.0, ge=0.0, le=1000000000.0)
    proof_type: str = Field(default='revenue', max_length=40)
    actor_name: str = Field(default='', max_length=80)
    boost_points: int = Field(default=10, ge=1, le=1000)


class DependencyAdvanceRequest(BaseModel):
    action: str = Field(default='complete_milestone', max_length=60)
    points: int = Field(default=12, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class CommunityCircleRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    topic: str = Field(default='growth', max_length=80)
    description: str = Field(default='', max_length=320)


class CommunityPostRequest(BaseModel):
    circle_id: int
    content: str = Field(min_length=3, max_length=2000)
    kind: str = Field(default='win', max_length=40)


class CommunityAmaRequest(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    host_name: str = Field(min_length=2, max_length=80)
    starts_at: str = Field(min_length=10, max_length=40)


class BrandLockCheckpointRequest(BaseModel):
    action: str = Field(default='asset_sync', max_length=80)
    points: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class AutopilotCheckpointRequest(BaseModel):
    action: str = Field(default='automation_alignment', max_length=80)
    points: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class AchievementEvaluateRequest(BaseModel):
    trigger: str = Field(default='manual_refresh', max_length=80)


class MoneyPrinterIdeaRequest(BaseModel):
    printer: str = Field(min_length=3, max_length=80)
    hypothesis: str = Field(min_length=10, max_length=500)
    expected_monthly_revenue_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    owner: str = Field(default='', max_length=80)


class MoneyPrinterValidationRequest(BaseModel):
    idea_id: int
    outcome: str = Field(default='validated', max_length=40)
    confidence: int = Field(default=70, ge=0, le=100)
    evidence: str = Field(default='', max_length=500)


class BankTransferRequest(BaseModel):
    to_tenant_id: str = Field(min_length=2, max_length=120)
    amount: float = Field(gt=0.0, le=1000000000.0)
    note: str = Field(default='', max_length=240)


class BankPayoutRequest(BaseModel):
    amount: float = Field(gt=0.0, le=1000000000.0)
    destination: str = Field(min_length=3, max_length=240)


class UniversityCourseRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    track: str = Field(default='growth', max_length=80)
    level: str = Field(default='beginner', max_length=40)
    price_usd: float = Field(default=0.0, ge=0.0, le=1000000.0)


class UniversityCohortRequest(BaseModel):
    course_id: int
    starts_at: str = Field(min_length=10, max_length=40)
    capacity: int = Field(default=25, ge=1, le=10000)
    mentor_name: str = Field(default='', max_length=120)


class UniversityEnrollRequest(BaseModel):
    cohort_id: int
    learner_email: str = Field(default='', max_length=320)


class UniversityProgressRequest(BaseModel):
    enrollment_id: int
    checkpoint: str = Field(min_length=2, max_length=160)
    completion_delta: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class StudiosServiceRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    category: str = Field(default='creative', max_length=80)
    price_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    turnaround_days: int = Field(default=7, ge=1, le=365)


class StudiosBriefRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    category: str = Field(default='creative', max_length=80)
    budget_usd: float = Field(default=0.0, ge=0.0, le=1000000000.0)
    due_date: str = Field(default='', max_length=40)
    scope: str = Field(default='', max_length=1200)


class StudiosProposalRequest(BaseModel):
    brief_id: int
    service_id: int
    bid_usd: float = Field(gt=0.0, le=1000000000.0)
    message: str = Field(default='', max_length=1200)


class StudiosEscrowRequest(BaseModel):
    proposal_id: int
    milestone_name: str = Field(default='delivery_m1', max_length=160)
    amount_usd: float = Field(gt=0.0, le=1000000000.0)


class StudiosEscrowReleaseRequest(BaseModel):
    escrow_id: int
    approved: bool = Field(default=True)
    note: str = Field(default='', max_length=320)


class CommerceProductRequest(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    description: str = Field(default='', max_length=1000)
    price_usd: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)
    category: str = Field(default='general', max_length=80)
    inventory: int = Field(default=0, ge=0)
    digital: bool = Field(default=False)


class CommerceOrderRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=9999)
    buyer_email: str = Field(min_length=5, max_length=320)
    note: str = Field(default='', max_length=500)


class TalentCreatorRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    niche: str = Field(default='general', max_length=80)
    platform: str = Field(default='instagram', max_length=60)
    followers: int = Field(default=0, ge=0)
    rate_card_usd: float = Field(default=0.0, ge=0.0)
    bio: str = Field(default='', max_length=500)


class TalentDealRequest(BaseModel):
    creator_id: int
    brand_name: str = Field(min_length=2, max_length=200)
    deliverables: str = Field(min_length=2, max_length=500)
    budget_usd: float = Field(ge=0.0)
    currency: str = Field(default='USD', max_length=8)
    note: str = Field(default='', max_length=500)


class TalentDealAcceptRequest(BaseModel):
    deal_id: int
    accepted: bool = Field(default=True)
    counter_rate_usd: float = Field(default=0.0, ge=0.0)
    note: str = Field(default='', max_length=500)


class TalentRateCardRequest(BaseModel):
    creator_id: int
    post_rate_usd: float = Field(default=0.0, ge=0.0)
    story_rate_usd: float = Field(default=0.0, ge=0.0)
    reel_rate_usd: float = Field(default=0.0, ge=0.0)
    package_rate_usd: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default='USD', max_length=8)


class WhiteLabelBrandKitRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=120)
    primary_color: str = Field(default='#0B5FFF', max_length=20)
    accent_color: str = Field(default='#12B886', max_length=20)
    logo_url: str = Field(default='', max_length=500)
    support_email: str = Field(default='', max_length=320)


class WhiteLabelDomainRequest(BaseModel):
    custom_domain: str = Field(min_length=3, max_length=240)
    ssl_enabled: bool = Field(default=True)


class WhiteLabelCheckpointRequest(BaseModel):
    action: str = Field(default='white_label_checkpoint', max_length=80)
    points: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


class AchievementDefinition(TypedDict):
    id: str
    name: str
    points: int


def create_engagement_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    **memory_stores: list[dict[str, Any]],
) -> APIRouter:
    streaks_memory = memory_stores['streaks_memory']
    credit_ledger_memory = memory_stores['credit_ledger_memory']
    notifications_memory = memory_stores['notifications_memory']
    scheduled_posts_memory = memory_stores['scheduled_posts_memory']
    email_campaigns_memory = memory_stores['email_campaigns_memory']
    influencer_campaigns_memory = memory_stores['influencer_campaigns_memory']
    chatbots_memory = memory_stores['chatbots_memory']
    tenant_profiles_memory = memory_stores['tenant_profiles_memory']
    crm_contacts_memory = memory_stores['crm_contacts_memory']
    crm_deals_memory = memory_stores['crm_deals_memory']
    linkinbio_pages_memory = memory_stores['linkinbio_pages_memory']
    linkinbio_links_memory = memory_stores['linkinbio_links_memory']
    cms_pages_memory = memory_stores['cms_pages_memory']
    marketplace_installs_memory = memory_stores['marketplace_installs_memory']
    invoices_memory = memory_stores['invoices_memory']
    companion_profiles_memory = memory_stores['companion_profiles_memory']
    companion_messages_memory = memory_stores['companion_messages_memory']
    fomo_rules_memory = memory_stores['fomo_rules_memory']
    fomo_events_memory = memory_stores['fomo_events_memory']
    social_proof_events_memory = memory_stores['social_proof_events_memory']
    dependency_profiles_memory = memory_stores['dependency_profiles_memory']
    dependency_events_memory = memory_stores['dependency_events_memory']
    community_circles_memory = memory_stores['community_circles_memory']
    community_posts_memory = memory_stores['community_posts_memory']
    community_amas_memory = memory_stores['community_amas_memory']
    brand_lock_profiles_memory = memory_stores['brand_lock_profiles_memory']
    brand_lock_events_memory = memory_stores['brand_lock_events_memory']
    autopilot_profiles_memory = memory_stores['autopilot_profiles_memory']
    autopilot_events_memory = memory_stores['autopilot_events_memory']
    achievement_profiles_memory = memory_stores['achievement_profiles_memory']
    achievement_events_memory = memory_stores['achievement_events_memory']
    money_printer_ideas_memory = memory_stores['money_printer_ideas_memory']
    money_printer_validations_memory = memory_stores['money_printer_validations_memory']
    bank_accounts_memory = memory_stores['bank_accounts_memory']
    bank_transactions_memory = memory_stores['bank_transactions_memory']
    bank_payouts_memory = memory_stores['bank_payouts_memory']
    university_courses_memory = memory_stores['university_courses_memory']
    university_cohorts_memory = memory_stores['university_cohorts_memory']
    university_enrollments_memory = memory_stores['university_enrollments_memory']
    studios_services_memory = memory_stores['studios_services_memory']
    studios_briefs_memory = memory_stores['studios_briefs_memory']
    studios_proposals_memory = memory_stores['studios_proposals_memory']
    studios_escrows_memory = memory_stores['studios_escrows_memory']
    commerce_products_memory = memory_stores['commerce_products_memory']
    commerce_orders_memory = memory_stores['commerce_orders_memory']
    talent_creators_memory = memory_stores['talent_creators_memory']
    talent_deals_memory = memory_stores['talent_deals_memory']
    talent_rate_cards_memory = memory_stores['talent_rate_cards_memory']
    white_label_profiles_memory = memory_stores['white_label_profiles_memory']
    white_label_events_memory = memory_stores['white_label_events_memory']
    referrals_memory = memory_stores['referrals_memory']
    referral_claims_memory = memory_stores['referral_claims_memory']
    refferq_jobs_memory = memory_stores['refferq_jobs_memory']
    audit_log_memory = memory_stores['audit_log_memory']

    router = APIRouter()
    lock = threading.Lock()
    dependency_stages = ['explorer', 'builder', 'operator', 'orchestrator', 'locked_in']
    brand_stages = ['starter', 'established', 'moat', 'platform_native']
    achievement_catalog: list[AchievementDefinition] = [
        {'id': 'first_referral', 'name': 'First Referral', 'points': 60},
        {'id': 'social_spotlight', 'name': 'Social Spotlight', 'points': 35},
        {'id': 'community_voice', 'name': 'Community Voice', 'points': 30},
        {'id': 'autopilot_operator', 'name': 'Autopilot Operator', 'points': 50},
        {'id': 'brand_moat', 'name': 'Brand Moat', 'points': 55},
        {'id': 'streak_sprint', 'name': 'Streak Sprint', 'points': 45},
        {'id': 'companion_consistency', 'name': 'Companion Consistency', 'points': 30},
    ]
    money_printers = [
        'nuxtron_bank',
        'nuxtron_university',
        'nuxtron_studios',
        'commerce_pro',
        'insights_dashboard',
        'white_label',
        'talent_agency',
        'nuxtron_fund',
    ]
    white_label_stages = ['foundation', 'branded', 'client_ready', 'agency_grade']

    def _today() -> date:
        return datetime.now(UTC).date()

    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _badge_for_streak(streak: int) -> str:
        if streak >= 365:
            return 'legend'
        if streak >= 90:
            return 'diamond'
        if streak >= 30:
            return 'gold'
        if streak >= 7:
            return 'silver'
        if streak >= 1:
            return 'bronze'
        return 'unranked'

    def _next_milestone(streak: int) -> int | None:
        for milestone in sorted(MILESTONE_REWARDS):
            if streak < milestone:
                return milestone
        return None

    def _append_audit(tenant_id: str, action: str, detail: dict[str, Any]) -> None:
        audit_log_memory.append({
            'id': len(audit_log_memory) + 1,
            'tenant_id': tenant_id,
            'action': action,
            'detail': detail,
            'recorded_at': datetime.now(UTC).isoformat(),
            'source': 'engagement-router',
        })

    def _append_credit(tenant_id: str, amount: int, reason: str) -> None:
        credit_ledger_memory.append({
            'id': len(credit_ledger_memory) + 1,
            'tenant_id': tenant_id,
            'amount': amount,
            'reason': reason,
            'created_at': datetime.now(UTC).isoformat(),
        })

    def _append_notification(tenant_id: str, title: str, message: str, category: str = 'engagement') -> None:
        notifications_memory.append({
            'id': len(notifications_memory) + 1,
            'tenant_id': tenant_id,
            'title': title,
            'message': message,
            'category': category,
            'read': False,
            'read_at': None,
            'created_at': datetime.now(UTC).isoformat(),
            'source': 'engagement-router',
            'persistence': 'memory-fallback',
        })

    def _get_or_create_referral_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in referrals_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            code = f'NUX-{tenant_id[:4].upper()}-{(len(referrals_memory) + 1):04d}'
            profile: dict[str, Any] = {
                'id': len(referrals_memory) + 1,
                'tenant_id': tenant_id,
                'referral_code': code,
                'successful_referrals': 0,
                'total_credits_earned': 0,
                'last_referral_at': None,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            referrals_memory.append(profile)
            return profile
        return existing_profile

    def _get_or_create_streak(tenant_id: str) -> dict[str, Any]:
        existing_record = next((item for item in streaks_memory if item.get('tenant_id') == tenant_id), None)
        if existing_record is None:
            record: dict[str, Any] = {
                'tenant_id': tenant_id,
                'current_streak': 0,
                'longest_streak': 0,
                'last_check_in_date': None,
                'last_recovery_date': None,
                'recoverable_streak': 0,
                'recoverable_until': None,
                'milestones_unlocked': [],
                'badge': 'unranked',
                'updated_at': datetime.now(UTC).isoformat(),
            }
            streaks_memory.append(record)
            return record
        return existing_record

    def _get_or_create_companion_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in companion_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            profile: dict[str, Any] = {
                'id': len(companion_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'nickname': 'Nux Companion',
                'bond_score': 0,
                'total_check_ins': 0,
                'consecutive_days': 0,
                'last_check_in_date': None,
                'last_message_at': None,
                'last_goal': '',
                'last_mood': 'focused',
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            companion_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _companion_reply(profile: dict[str, Any], message: str) -> str:
        text = message.lower()
        if any(token in text for token in ('burnout', 'tired', 'exhausted', 'drained')):
            return 'I hear you. Let us trim today to one meaningful win and protect your energy with a 25-minute focus sprint.'
        if any(token in text for token in ('stuck', 'blocked', 'confused')):
            return 'You are not stuck, you are at a decision point. Pick the smallest shippable step and I will help you sequence the next two.'
        if any(token in text for token in ('launch', 'ship', 'publish')):
            return 'Great momentum. Lock scope, schedule one distribution action, and I will hold you to a clean launch checklist.'

        bond_score = int(profile.get('bond_score', 0))
        if bond_score >= 40:
            return 'We have built solid rhythm. Focus on your top priority, avoid context switches, and report one concrete outcome today.'
        return 'I am here daily for your consistency loop. Share your top goal and I will keep nudging you toward execution.'

    def _get_or_create_default_fomo_rules(tenant_id: str) -> list[dict[str, Any]]:
        existing = [item for item in fomo_rules_memory if item.get('tenant_id') == tenant_id]
        if existing:
            return existing

        now_iso = datetime.now(UTC).isoformat()
        defaults: list[dict[str, Any]] = [
            {
                'id': len(fomo_rules_memory) + 1,
                'tenant_id': tenant_id,
                'name': 'Limited Launch Slot',
                'trigger_type': 'limited_slot',
                'threshold': 5,
                'window_minutes': 180,
                'active': True,
                'created_at': now_iso,
                'updated_at': now_iso,
            },
            {
                'id': len(fomo_rules_memory) + 2,
                'tenant_id': tenant_id,
                'name': 'Competitor Momentum Alert',
                'trigger_type': 'competitor_momentum',
                'threshold': 3,
                'window_minutes': 120,
                'active': True,
                'created_at': now_iso,
                'updated_at': now_iso,
            },
        ]
        fomo_rules_memory.extend(defaults)
        return list(defaults)

    def _tenant_display_name(tenant_id: str) -> str:
        profile = next((item for item in tenant_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if profile is None:
            return tenant_id
        for key in ('display_name', 'name', 'company_name', 'brand_name'):
            value = str(profile.get(key, '')).strip()
            if value:
                return value
        return tenant_id

    def _stage_index(stage: str) -> int:
        try:
            return dependency_stages.index(stage)
        except ValueError:
            return 0

    def _signal_snapshot(tenant_id: str) -> dict[str, int]:
        return {
            'scheduled_posts': sum(1 for item in scheduled_posts_memory if item.get('tenant_id') == tenant_id),
            'email_campaigns': sum(1 for item in email_campaigns_memory if item.get('tenant_id') == tenant_id),
            'influencer_campaigns': sum(1 for item in influencer_campaigns_memory if item.get('tenant_id') == tenant_id),
            'deployed_chatbots': sum(
                1 for item in chatbots_memory if item.get('tenant_id') == tenant_id and bool(item.get('deployed'))
            ),
            'fomo_events': sum(1 for item in fomo_events_memory if item.get('tenant_id') == tenant_id),
            'social_proof_events': sum(1 for item in social_proof_events_memory if item.get('tenant_id') == tenant_id),
        }

    def _target_stage_for_score(score: int) -> str:
        if score >= 85:
            return 'locked_in'
        if score >= 65:
            return 'orchestrator'
        if score >= 45:
            return 'operator'
        if score >= 25:
            return 'builder'
        return 'explorer'

    def _compute_dependency_score(tenant_id: str, manual_points: int) -> tuple[int, dict[str, int]]:
        signals = _signal_snapshot(tenant_id)
        signal_points = (
            min(25, signals['scheduled_posts'])
            + min(20, signals['email_campaigns'])
            + min(15, signals['influencer_campaigns'])
            + min(20, signals['deployed_chatbots'] * 5)
            + min(10, signals['fomo_events'] * 2)
            + min(10, signals['social_proof_events'] * 2)
        )
        return min(100, int(signal_points) + int(manual_points)), signals

    def _get_or_create_dependency_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in dependency_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            now_iso = datetime.now(UTC).isoformat()
            profile: dict[str, Any] = {
                'id': len(dependency_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'stage': 'explorer',
                'manual_points': 0,
                'dependency_score': 0,
                'last_action': None,
                'last_action_at': None,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            dependency_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _get_or_create_default_circle(tenant_id: str) -> dict[str, Any]:
        existing_circle = next(
            (
                item for item in community_circles_memory
                if item.get('tenant_id') == tenant_id and bool(item.get('is_default'))
            ),
            None,
        )
        if existing_circle is None:
            now_iso = datetime.now(UTC).isoformat()
            circle: dict[str, Any] = {
                'id': len(community_circles_memory) + 1,
                'tenant_id': tenant_id,
                'name': 'Founders Mastermind',
                'topic': 'growth',
                'description': 'Daily wins, blockers, and sprint accountability.',
                'members': 1,
                'is_default': True,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            community_circles_memory.append(circle)
            return circle
        return existing_circle

    def _brand_signals_snapshot(tenant_id: str) -> dict[str, int]:
        return {
            'linkinbio_pages': sum(1 for item in linkinbio_pages_memory if item.get('tenant_id') == tenant_id),
            'linkinbio_links': sum(1 for item in linkinbio_links_memory if item.get('tenant_id') == tenant_id),
            'deployed_chatbots': sum(
                1 for item in chatbots_memory if item.get('tenant_id') == tenant_id and bool(item.get('deployed'))
            ),
            'crm_contacts': sum(1 for item in crm_contacts_memory if item.get('tenant_id') == tenant_id),
            'crm_deals': sum(1 for item in crm_deals_memory if item.get('tenant_id') == tenant_id),
            'cms_pages': sum(1 for item in cms_pages_memory if item.get('tenant_id') == tenant_id),
            'marketplace_installs': sum(1 for item in marketplace_installs_memory if item.get('tenant_id') == tenant_id),
            'social_proof_events': sum(1 for item in social_proof_events_memory if item.get('tenant_id') == tenant_id),
        }

    def _brand_stage_for_score(score: int) -> str:
        if score >= 85:
            return 'platform_native'
        if score >= 60:
            return 'moat'
        if score >= 30:
            return 'established'
        return 'starter'

    def _brand_score(signals: dict[str, int], manual_points: int) -> int:
        score = (
            min(20, signals['linkinbio_pages'] * 10)
            + min(12, signals['linkinbio_links'])
            + min(15, signals['deployed_chatbots'] * 5)
            + min(15, signals['crm_contacts'] // 5)
            + min(10, signals['crm_deals'] * 2)
            + min(12, signals['cms_pages'] * 3)
            + min(8, signals['marketplace_installs'] * 2)
            + min(8, signals['social_proof_events'] * 2)
            + int(manual_points)
        )
        return min(100, score)

    def _get_or_create_brand_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in brand_lock_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            now_iso = datetime.now(UTC).isoformat()
            profile: dict[str, Any] = {
                'id': len(brand_lock_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'stage': 'starter',
                'brand_lock_score': 0,
                'manual_points': 0,
                'last_action': None,
                'last_action_at': None,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            brand_lock_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _autopilot_signals_snapshot(tenant_id: str) -> dict[str, int]:
        dependency_profile = next(
            (item for item in dependency_profiles_memory if item.get('tenant_id') == tenant_id),
            None,
        )
        brand_profile = next(
            (item for item in brand_lock_profiles_memory if item.get('tenant_id') == tenant_id),
            None,
        )
        return {
            'scheduled_posts': sum(1 for item in scheduled_posts_memory if item.get('tenant_id') == tenant_id),
            'email_campaigns': sum(1 for item in email_campaigns_memory if item.get('tenant_id') == tenant_id),
            'influencer_campaigns': sum(1 for item in influencer_campaigns_memory if item.get('tenant_id') == tenant_id),
            'deployed_chatbots': sum(
                1 for item in chatbots_memory if item.get('tenant_id') == tenant_id and bool(item.get('deployed'))
            ),
            'fomo_events': sum(1 for item in fomo_events_memory if item.get('tenant_id') == tenant_id),
            'social_proof_events': sum(1 for item in social_proof_events_memory if item.get('tenant_id') == tenant_id),
            'community_posts': sum(1 for item in community_posts_memory if item.get('tenant_id') == tenant_id),
            'dependency_score': int((dependency_profile or {}).get('dependency_score', 0)),
            'brand_lock_score': int((brand_profile or {}).get('brand_lock_score', 0)),
        }

    def _autopilot_maturity_for_score(score: int) -> str:
        if score >= 85:
            return 'self_driving'
        if score >= 60:
            return 'high_automation'
        if score >= 35:
            return 'hybrid'
        return 'manual_plus'

    def _autopilot_score(signals: dict[str, int], manual_points: int) -> int:
        value = (
            min(20, signals['scheduled_posts'])
            + min(15, signals['email_campaigns'])
            + min(12, signals['influencer_campaigns'])
            + min(12, signals['deployed_chatbots'] * 4)
            + min(8, signals['fomo_events'] * 2)
            + min(8, signals['social_proof_events'] * 2)
            + min(8, signals['community_posts'])
            + min(10, signals['dependency_score'] // 10)
            + min(7, signals['brand_lock_score'] // 15)
            + int(manual_points)
        )
        return min(100, value)

    def _get_or_create_autopilot_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in autopilot_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            now_iso = datetime.now(UTC).isoformat()
            profile: dict[str, Any] = {
                'id': len(autopilot_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'maturity': 'manual_plus',
                'autopilot_score': 0,
                'manual_points': 0,
                'last_action': None,
                'last_action_at': None,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            autopilot_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _get_or_create_achievement_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in achievement_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            now_iso = datetime.now(UTC).isoformat()
            profile: dict[str, Any] = {
                'id': len(achievement_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'total_points': 0,
                'unlocked_count': 0,
                'unlocked_ids': [],
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            achievement_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _evaluate_achievements(tenant_id: str, trigger: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        profile = _get_or_create_achievement_profile(tenant_id)
        unlocked_ids = {str(item) for item in profile.get('unlocked_ids', [])}

        streak_record = _get_or_create_streak(tenant_id)
        _apply_rollover(streak_record, _today())
        referral_profile = _get_or_create_referral_profile(tenant_id)
        companion_profile = _get_or_create_companion_profile(tenant_id)
        autopilot_profile = _get_or_create_autopilot_profile(tenant_id)
        brand_profile = _get_or_create_brand_profile(tenant_id)

        conditions = {
            'first_referral': int(referral_profile.get('successful_referrals', 0)) >= 1,
            'social_spotlight': sum(1 for item in social_proof_events_memory if item.get('tenant_id') == tenant_id) >= 1,
            'community_voice': sum(1 for item in community_posts_memory if item.get('tenant_id') == tenant_id) >= 1,
            'autopilot_operator': str(autopilot_profile.get('maturity', 'manual_plus')) in ('high_automation', 'self_driving'),
            'brand_moat': str(brand_profile.get('stage', 'starter')) in ('moat', 'platform_native'),
            'streak_sprint': int(streak_record.get('current_streak', 0)) >= 7,
            'companion_consistency': int(companion_profile.get('total_check_ins', 0)) >= 3,
        }

        now_iso = datetime.now(UTC).isoformat()
        newly_unlocked: list[dict[str, Any]] = []
        for achievement in achievement_catalog:
            achievement_id = str(achievement['id'])
            if achievement_id in unlocked_ids:
                continue
            if not conditions.get(achievement_id, False):
                continue

            unlocked_ids.add(achievement_id)
            event: dict[str, Any] = {
                'id': len(achievement_events_memory) + 1,
                'tenant_id': tenant_id,
                'achievement_id': achievement_id,
                'achievement_name': achievement['name'],
                'points': int(achievement['points']),
                'trigger': trigger,
                'created_at': now_iso,
            }
            achievement_events_memory.append(event)
            newly_unlocked.append(event)

            _append_credit(tenant_id, int(achievement['points']), f'achievement_{achievement_id}')
            _append_notification(
                tenant_id,
                'Achievement Unlocked',
                f"You unlocked '{achievement['name']}' and earned {achievement['points']} AI credits.",
                'achievement',
            )

        profile['unlocked_ids'] = sorted(unlocked_ids)
        profile['unlocked_count'] = len(unlocked_ids)
        profile['total_points'] = sum(
            int(item['points'])
            for item in achievement_catalog
            if str(item['id']) in unlocked_ids
        )
        profile['updated_at'] = now_iso
        return profile.copy(), newly_unlocked

    def _normalize_money_printer(raw: str) -> str:
        value = raw.strip().lower().replace(' ', '_').replace('-', '_')
        if value in money_printers:
            return value
        raise HTTPException(status_code=422, detail=UNSUPPORTED_MONEY_PRINTER)

    def _get_or_create_bank_account(tenant_id: str) -> dict[str, Any]:
        existing_account = next((item for item in bank_accounts_memory if item.get('tenant_id') == tenant_id), None)
        if existing_account is None:
            now_iso = datetime.now(UTC).isoformat()
            account: dict[str, Any] = {
                'id': len(bank_accounts_memory) + 1,
                'tenant_id': tenant_id,
                'account_number': f"NB-{tenant_id[:4].upper()}-{(len(bank_accounts_memory) + 1):06d}",
                'currency': 'USD',
                'status': 'active',
                'settled_invoice_ids': [],
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            bank_accounts_memory.append(account)
            # Seed a one-time activation credit so new wallets can execute payouts/transfers immediately.
            _record_bank_transaction(
                tenant_id,
                'credit',
                100.0,
                'activation_bonus',
                {'reason': 'nuxtron_bank_onboarding'},
            )
            return account
        return existing_account

    def _bank_balance(tenant_id: str) -> float:
        total_credits = sum(
            float(item.get('amount', 0.0))
            for item in bank_transactions_memory
            if item.get('tenant_id') == tenant_id and str(item.get('direction', '')) == 'credit'
        )
        debits = sum(
            float(item.get('amount', 0.0))
            for item in bank_transactions_memory
            if item.get('tenant_id') == tenant_id and str(item.get('direction', '')) == 'debit'
        )
        return round(total_credits - debits, 2)

    def _record_bank_transaction(
        tenant_id: str,
        direction: str,
        amount: float,
        tx_type: str,
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        tx: dict[str, Any] = {
            'id': len(bank_transactions_memory) + 1,
            'tenant_id': tenant_id,
            'direction': direction,
            'amount': round(float(amount), 2),
            'type': tx_type,
            'detail': detail,
            'created_at': datetime.now(UTC).isoformat(),
        }
        bank_transactions_memory.append(tx)
        return tx

    def _sync_invoice_settlements(tenant_id: str) -> list[dict[str, Any]]:
        account = _get_or_create_bank_account(tenant_id)
        settled_ids = {int(item) for item in account.get('settled_invoice_ids', [])}
        new_entries: list[dict[str, Any]] = []
        for invoice in invoices_memory:
            if invoice.get('tenant_id') != tenant_id:
                continue
            if str(invoice.get('status', '')).lower() not in ('paid', 'succeeded', 'completed'):
                continue
            invoice_id = int(invoice.get('id', 0) or 0)
            if invoice_id <= 0 or invoice_id in settled_ids:
                continue
            gross = float(invoice.get('amount', 0.0))
            if gross <= 0:
                continue
            # Reserve 10% for platform/risk operations in this prototype.
            net_settlement = round(gross * 0.9, 2)
            tx = _record_bank_transaction(
                tenant_id,
                'credit',
                net_settlement,
                'invoice_settlement',
                {'invoice_id': invoice_id, 'gross_amount': round(gross, 2)},
            )
            new_entries.append(tx)
            settled_ids.add(invoice_id)

        account['settled_invoice_ids'] = sorted(settled_ids)
        account['updated_at'] = datetime.now(UTC).isoformat()
        return new_entries

    def _studios_bid_status(proposal_count: int, accepted_count: int) -> str:
        if accepted_count >= 1:
            return 'validated_supply'
        if proposal_count >= 3:
            return 'liquid_bidding'
        if proposal_count >= 1:
            return 'early_market'
        return 'seed'

    def _white_label_signals_snapshot(tenant_id: str, profile: dict[str, Any]) -> dict[str, int]:
        return {
            'has_brand_name': 1 if str(profile.get('brand_name', '')).strip() else 0,
            'has_logo': 1 if str(profile.get('logo_url', '')).strip() else 0,
            'has_custom_domain': 1 if str(profile.get('custom_domain', '')).strip() else 0,
            'ssl_enabled': 1 if bool(profile.get('ssl_enabled', False)) else 0,
            'linkinbio_custom_domains': sum(
                1
                for item in linkinbio_pages_memory
                if item.get('tenant_id') == tenant_id and str(item.get('custom_domain', '')).strip()
            ),
            'chatbot_custom_domains': sum(
                1
                for item in chatbots_memory
                if item.get('tenant_id') == tenant_id and str(item.get('deploy_domain', '')).strip()
            ),
            'cms_pages': sum(1 for item in cms_pages_memory if item.get('tenant_id') == tenant_id),
        }

    def _white_label_score(signals: dict[str, int], manual_points: int) -> int:
        return min(
            100,
            signals['has_brand_name'] * 20
            + signals['has_logo'] * 10
            + signals['has_custom_domain'] * 20
            + signals['ssl_enabled'] * 10
            + min(10, signals['linkinbio_custom_domains'] * 5)
            + min(10, signals['chatbot_custom_domains'] * 5)
            + min(10, signals['cms_pages'] * 2)
            + int(manual_points),
        )

    def _white_label_stage_for_score(score: int) -> str:
        if score >= 85:
            return 'agency_grade'
        if score >= 60:
            return 'client_ready'
        if score >= 30:
            return 'branded'
        return 'foundation'

    def _get_or_create_white_label_profile(tenant_id: str) -> dict[str, Any]:
        existing_profile = next((item for item in white_label_profiles_memory if item.get('tenant_id') == tenant_id), None)
        if existing_profile is None:
            now_iso = datetime.now(UTC).isoformat()
            profile: dict[str, Any] = {
                'id': len(white_label_profiles_memory) + 1,
                'tenant_id': tenant_id,
                'stage': 'foundation',
                'white_label_score': 0,
                'manual_points': 0,
                'brand_name': '',
                'primary_color': '#0B5FFF',
                'accent_color': '#12B886',
                'logo_url': '',
                'support_email': '',
                'custom_domain': '',
                'ssl_enabled': False,
                'last_action': None,
                'last_action_at': None,
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            white_label_profiles_memory.append(profile)
            return profile
        return existing_profile

    def _apply_rollover(record: dict[str, Any], today: date) -> None:
        last_check_in = _parse_date(record.get('last_check_in_date'))
        if last_check_in is None:
            return

        gap_days = (today - last_check_in).days
        if gap_days <= 1:
            return

        current_streak = int(record.get('current_streak', 0))
        if gap_days == 2 and current_streak > 0:
            record['recoverable_streak'] = current_streak
            record['recoverable_until'] = today.isoformat()
        elif record.get('recoverable_streak') and record.get('recoverable_until') == today.isoformat():
            # Preserve an already computed same-day recovery window across repeated reads.
            pass
        else:
            record['recoverable_streak'] = 0
            record['recoverable_until'] = None

        record['current_streak'] = 0
        record['badge'] = _badge_for_streak(0)
        record['updated_at'] = datetime.now(UTC).isoformat()

    def _snapshot(record: dict[str, Any]) -> dict[str, Any]:
        current_streak = int(record.get('current_streak', 0))
        recoverable_streak = int(record.get('recoverable_streak', 0))
        return {
            'current_streak': current_streak,
            'longest_streak': int(record.get('longest_streak', 0)),
            'last_check_in_date': record.get('last_check_in_date'),
            'badge': record.get('badge', _badge_for_streak(current_streak)),
            'milestones_unlocked': sorted(int(item) for item in record.get('milestones_unlocked', [])),
            'next_milestone': _next_milestone(current_streak),
            'recoverable': {
                'can_recover': recoverable_streak > 0 and record.get('recoverable_until') == _today().isoformat(),
                'recoverable_streak': recoverable_streak,
                'recoverable_until': record.get('recoverable_until'),
                'last_recovery_date': record.get('last_recovery_date'),
            },
        }

    register_retention_routes(
        router=router,
        context=RetentionContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            streaks_memory=streaks_memory,
            credit_ledger_memory=credit_ledger_memory,
            notifications_memory=notifications_memory,
            scheduled_posts_memory=scheduled_posts_memory,
            email_campaigns_memory=email_campaigns_memory,
            influencer_campaigns_memory=influencer_campaigns_memory,
            chatbots_memory=chatbots_memory,
            tenant_profiles_memory=tenant_profiles_memory,
            invoices_memory=invoices_memory,
            milestone_rewards=MILESTONE_REWARDS,
            no_recoverable_streak=NO_RECOVERABLE_STREAK,
            streak_recovery_limited=STREAK_RECOVERY_LIMITED,
            today_fn=_today,
            parse_date_fn=_parse_date,
            badge_for_streak_fn=_badge_for_streak,
            get_streak_fn=_get_or_create_streak,
            apply_rollover_fn=_apply_rollover,
            snapshot_fn=_snapshot,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
        ),
    )

    register_companion_social_routes(
        router=router,
        context=CompanionSocialContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            companion_profiles_memory=companion_profiles_memory,
            companion_messages_memory=companion_messages_memory,
            fomo_rules_memory=fomo_rules_memory,
            fomo_events_memory=fomo_events_memory,
            social_proof_events_memory=social_proof_events_memory,
            fomo_rule_not_found=FOMO_RULE_NOT_FOUND,
            fomo_rule_inactive=FOMO_RULE_INACTIVE,
            today_fn=_today,
            parse_date_fn=_parse_date,
            get_companion_profile_fn=_get_or_create_companion_profile,
            companion_reply_fn=_companion_reply,
            get_default_fomo_rules_fn=_get_or_create_default_fomo_rules,
            tenant_display_name_fn=_tenant_display_name,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
        ),
    )

    register_dependency_community_routes(
        router=router,
        context=DependencyCommunityContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            dependency_stages=dependency_stages,
            dependency_profiles_memory=dependency_profiles_memory,
            dependency_events_memory=dependency_events_memory,
            community_circles_memory=community_circles_memory,
            community_posts_memory=community_posts_memory,
            community_amas_memory=community_amas_memory,
            community_circle_not_found=COMMUNITY_CIRCLE_NOT_FOUND,
            get_dependency_profile_fn=_get_or_create_dependency_profile,
            compute_dependency_score_fn=_compute_dependency_score,
            target_stage_for_score_fn=_target_stage_for_score,
            stage_index_fn=_stage_index,
            get_default_circle_fn=_get_or_create_default_circle,
            tenant_display_name_fn=_tenant_display_name,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
        ),
    )

    register_brand_autopilot_achievement_routes(
        router=router,
        context=BrandAutopilotAchievementsContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            brand_stages=brand_stages,
            achievement_catalog=achievement_catalog,
            brand_lock_profiles_memory=brand_lock_profiles_memory,
            brand_lock_events_memory=brand_lock_events_memory,
            autopilot_profiles_memory=autopilot_profiles_memory,
            autopilot_events_memory=autopilot_events_memory,
            achievement_profiles_memory=achievement_profiles_memory,
            achievement_events_memory=achievement_events_memory,
            get_brand_profile_fn=_get_or_create_brand_profile,
            brand_signals_snapshot_fn=_brand_signals_snapshot,
            brand_score_fn=_brand_score,
            brand_stage_for_score_fn=_brand_stage_for_score,
            get_autopilot_profile_fn=_get_or_create_autopilot_profile,
            autopilot_signals_snapshot_fn=_autopilot_signals_snapshot,
            autopilot_score_fn=_autopilot_score,
            autopilot_maturity_for_score_fn=_autopilot_maturity_for_score,
            evaluate_achievements_fn=_evaluate_achievements,
            tenant_display_name_fn=_tenant_display_name,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
        ),
    )

    register_money_printers_bank_routes(
        router=router,
        context=MoneyPrintersBankContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            money_printers=money_printers,
            money_printer_ideas_memory=money_printer_ideas_memory,
            money_printer_validations_memory=money_printer_validations_memory,
            bank_transactions_memory=bank_transactions_memory,
            bank_payouts_memory=bank_payouts_memory,
            normalize_printer_fn=_normalize_money_printer,
            get_bank_account_fn=_get_or_create_bank_account,
            sync_settlements_fn=_sync_invoice_settlements,
            bank_balance_fn=_bank_balance,
            record_bank_tx_fn=_record_bank_transaction,
            tenant_display_name_fn=_tenant_display_name,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
            idea_not_found=MONEY_PRINTER_IDEA_NOT_FOUND,
            invalid_outcome=INVALID_OUTCOME,
            insufficient_balance=INSUFFICIENT_BALANCE,
            insufficient_payout_balance=INSUFFICIENT_PAYOUT_BALANCE,
        ),
    )

    register_university_routes(
        router=router,
        context=UniversityContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            university_courses_memory=university_courses_memory,
            university_cohorts_memory=university_cohorts_memory,
            university_enrollments_memory=university_enrollments_memory,
            tenant_display_name_fn=_tenant_display_name,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
            course_not_found=COURSE_NOT_FOUND,
            cohort_not_found=COHORT_NOT_FOUND,
            cohort_at_capacity=COHORT_AT_CAPACITY,
            enrollment_not_found=ENROLLMENT_NOT_FOUND,
        ),
    )

    register_studios_routes(
        router=router,
        context=StudiosContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            studios_services_memory=studios_services_memory,
            studios_briefs_memory=studios_briefs_memory,
            studios_proposals_memory=studios_proposals_memory,
            studios_escrows_memory=studios_escrows_memory,
            studios_bid_status_fn=_studios_bid_status,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
            brief_not_found=BRIEF_NOT_FOUND,
            service_not_found=SERVICE_NOT_FOUND,
            proposal_not_found=PROPOSAL_NOT_FOUND,
            escrow_not_found=ESCROW_NOT_FOUND,
            escrow_not_funded=ESCROW_NOT_FUNDED,
        ),
    )

    register_commerce_routes(
        router=router,
        context=CommerceContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            commerce_products_memory=commerce_products_memory,
            commerce_orders_memory=commerce_orders_memory,
            product_not_found=PRODUCT_NOT_FOUND,
        ),
    )

    register_talent_agency_routes(
        router=router,
        context=TalentAgencyContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            talent_creators_memory=talent_creators_memory,
            talent_deals_memory=talent_deals_memory,
            talent_rate_cards_memory=talent_rate_cards_memory,
            creator_not_found=CREATOR_NOT_FOUND,
            deal_not_found=DEAL_NOT_FOUND,
        ),
    )

    register_white_label_routes(
        router=router,
        context=WhiteLabelContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            white_label_stages=white_label_stages,
            white_label_events_memory=white_label_events_memory,
            get_profile_fn=_get_or_create_white_label_profile,
            signals_snapshot_fn=_white_label_signals_snapshot,
            score_fn=_white_label_score,
            stage_for_score_fn=_white_label_stage_for_score,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
        ),
    )

    register_referrals_routes(
        router=router,
        context=ReferralsContext(
            enforce_rate_limit=enforce_rate_limit,
            lock=lock,
            referrals_memory=referrals_memory,
            referral_claims_memory=referral_claims_memory,
            refferq_jobs_memory=refferq_jobs_memory,
            referral_rewards=REFERRAL_REWARDS,
            get_referral_profile_fn=_get_or_create_referral_profile,
            append_credit_fn=_append_credit,
            append_notification_fn=_append_notification,
            append_audit_fn=_append_audit,
            referral_not_found=REFERRAL_NOT_FOUND,
            self_referral_not_allowed=SELF_REFERRAL_NOT_ALLOWED,
        ),
    )

    return router
