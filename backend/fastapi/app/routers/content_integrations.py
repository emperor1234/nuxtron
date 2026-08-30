from collections.abc import Callable

from fastapi import APIRouter, Depends

from ..deps import require_auth

JsonObject = dict[str, object]


def create_content_integrations_router(
    *,
    handlers: dict[str, Callable[..., JsonObject]],
) -> APIRouter:
    generate_content = handlers['generate_content']
    generate_ads = handlers['generate_ads']
    analyze_seo = handlers['analyze_seo']
    schedule_social_post = handlers['schedule_social_post']
    list_scheduled_posts = handlers['list_scheduled_posts']
    move_scheduled_post = handlers['move_scheduled_post']
    delete_scheduled_post = handlers['delete_scheduled_post']
    ingest_social_listening_mention = handlers['ingest_social_listening_mention']
    list_social_listening_mentions = handlers['list_social_listening_mentions']
    get_social_listening_summary = handlers['get_social_listening_summary']
    create_social_listening_alert_rule = handlers['create_social_listening_alert_rule']
    list_social_listening_alerts = handlers['list_social_listening_alerts']
    get_social_listening_clusters = handlers['get_social_listening_clusters']
    ingest_review = handlers['ingest_review']
    list_reviews = handlers['list_reviews']
    respond_to_review = handlers['respond_to_review']
    get_reviews_summary = handlers['get_reviews_summary']
    create_email_contact = handlers['create_email_contact']
    list_email_contacts = handlers['list_email_contacts']
    create_email_campaign = handlers['create_email_campaign']
    list_email_campaigns = handlers['list_email_campaigns']
    send_test_email_campaign = handlers['send_test_email_campaign']
    upsert_suitecrm_lead = handlers['upsert_suitecrm_lead']
    register_refferq_referral = handlers['register_refferq_referral']
    capture_posthog_event = handlers['capture_posthog_event']
    track_matomo_event = handlers['track_matomo_event']
    track_plausible_event = handlers['track_plausible_event']
    trigger_n8n_webhook = handlers['trigger_n8n_webhook']
    evaluate_growthbook_flag = handlers['evaluate_growthbook_flag']
    receive_webhook = handlers['receive_webhook']
    list_webhook_events = handlers['list_webhook_events']
    appwrite_create_user = handlers['appwrite_create_user']
    appwrite_create_session = handlers['appwrite_create_session']
    drone_trigger_build = handlers['drone_trigger_build']
    directus_create_item = handlers['directus_create_item']
    directus_list_items = handlers['directus_list_items']
    storage_presign = handlers['storage_presign']
    storage_list_objects = handlers['storage_list_objects']
    stripe_create_checkout = handlers['stripe_create_checkout']
    stripe_process_webhook = handlers['stripe_process_webhook']
    stripe_list_events = handlers['stripe_list_events']
    get_audit_log = handlers['get_audit_log']

    router = APIRouter(dependencies=[Depends(require_auth)])

    router.add_api_route('/content/generate', generate_content, methods=['POST'])
    router.add_api_route('/ads/generate', generate_ads, methods=['POST'])
    router.add_api_route('/seo/analyze', analyze_seo, methods=['POST'])
    router.add_api_route('/social/schedule', schedule_social_post, methods=['POST'])
    router.add_api_route('/social/scheduled', list_scheduled_posts, methods=['GET'])
    router.add_api_route('/social/scheduled/{post_id}/move', move_scheduled_post, methods=['PATCH'])
    router.add_api_route('/social/scheduled/{post_id}', delete_scheduled_post, methods=['DELETE'])
    router.add_api_route('/social/listening/ingest', ingest_social_listening_mention, methods=['POST'])
    router.add_api_route('/social/listening/mentions', list_social_listening_mentions, methods=['GET'])
    router.add_api_route('/social/listening/summary', get_social_listening_summary, methods=['GET'])
    router.add_api_route('/social/listening/rules', create_social_listening_alert_rule, methods=['POST'])
    router.add_api_route('/social/listening/alerts', list_social_listening_alerts, methods=['GET'])
    router.add_api_route('/social/listening/clusters', get_social_listening_clusters, methods=['GET'])

    router.add_api_route('/reviews/ingest', ingest_review, methods=['POST'])
    router.add_api_route('/reviews', list_reviews, methods=['GET'])
    router.add_api_route('/reviews/{review_id}/respond', respond_to_review, methods=['POST'])
    router.add_api_route('/reviews/summary', get_reviews_summary, methods=['GET'])

    router.add_api_route('/email/contacts', create_email_contact, methods=['POST'])
    router.add_api_route('/email/contacts', list_email_contacts, methods=['GET'])
    router.add_api_route('/email/campaigns', create_email_campaign, methods=['POST'])
    router.add_api_route('/email/campaigns', list_email_campaigns, methods=['GET'])
    router.add_api_route('/email/campaigns/{campaign_id}/send-test', send_test_email_campaign, methods=['POST'])

    router.add_api_route('/integrations/suitecrm/upsert-lead', upsert_suitecrm_lead, methods=['POST'])
    router.add_api_route('/integrations/refferq/register-referral', register_refferq_referral, methods=['POST'])
    router.add_api_route('/analytics/posthog/capture', capture_posthog_event, methods=['POST'])
    router.add_api_route('/analytics/matomo/track', track_matomo_event, methods=['POST'])
    router.add_api_route('/analytics/plausible/track', track_plausible_event, methods=['POST'])
    router.add_api_route('/integrations/n8n/trigger-webhook', trigger_n8n_webhook, methods=['POST'])
    router.add_api_route('/flags/growthbook/evaluate', evaluate_growthbook_flag, methods=['POST'])

    router.add_api_route('/webhooks/receive/{provider}', receive_webhook, methods=['POST'])
    router.add_api_route('/webhooks/events', list_webhook_events, methods=['GET'])

    router.add_api_route('/integrations/appwrite/create-user', appwrite_create_user, methods=['POST'])
    router.add_api_route('/integrations/appwrite/create-session', appwrite_create_session, methods=['POST'])
    router.add_api_route('/integrations/drone/trigger-build', drone_trigger_build, methods=['POST'])
    router.add_api_route('/integrations/directus/create-item', directus_create_item, methods=['POST'])
    router.add_api_route('/integrations/directus/list-items', directus_list_items, methods=['POST'])

    router.add_api_route('/storage/presign', storage_presign, methods=['POST'])
    router.add_api_route('/storage/list-objects', storage_list_objects, methods=['POST'])

    router.add_api_route('/payments/stripe/create-checkout', stripe_create_checkout, methods=['POST'])
    router.add_api_route('/payments/stripe/process-webhook', stripe_process_webhook, methods=['POST'])
    router.add_api_route('/payments/stripe/events', stripe_list_events, methods=['GET'])

    router.add_api_route('/ops/audit-log', get_audit_log, methods=['GET'])

    return router