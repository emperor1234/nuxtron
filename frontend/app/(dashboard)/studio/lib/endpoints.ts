/**
 * Declarative endpoint registry for Nuxtron Studio.
 * Maps endpoint categories to their configuration, methods, and output state keys.
 * Single source of truth for all 60+ API demos.
 */

import type { StudioState } from './state';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';
type EndpointOutputKey = keyof StudioState['outputs'];

export interface EndpointDemoConfig {
  id: string;
  category: string;
  title: string;
  description?: string;
  method: HttpMethod;
  path: string;
  outputKey: EndpointOutputKey;
  buildPayload?: (tenantId: string) => Record<string, unknown>;
  onSuccess?: (response: any, setters: any) => void;
  relatedOutputs?: EndpointOutputKey[];
}

export const STUDIO_ENDPOINTS: EndpointDemoConfig[] = [
  // ── Content Generation ───────────────────────────────────
  {
    id: 'content-generate',
    category: 'Content',
    title: 'Content Generator',
    method: 'POST',
    path: '/content/generate',
    outputKey: 'content',
    buildPayload: () => ({
      topic: 'AI-driven content strategy',
      audience: 'ecommerce founders',
      channel: 'linkedin',
      tone: 'professional',
      include_seo: true,
    }),
  },

  // ── Ads Generation ──────────────────────────────────────
  {
    id: 'ads-generate',
    category: 'Ads',
    title: 'Ads Generator',
    method: 'POST',
    path: '/ads/generate',
    outputKey: 'ads',
    buildPayload: () => ({
      product: 'Nuxtron Growth Suite',
      audience: 'B2B SaaS teams',
      platform: 'google',
      objective: 'leads',
    }),
  },

  // ── SEO Analysis ─────────────────────────────────────────
  {
    id: 'seo-analyze',
    category: 'SEO',
    title: 'SEO Analyzer',
    method: 'POST',
    path: '/seo/analyze',
    outputKey: 'seo',
    buildPayload: () => ({
      target_keyword: 'ai content automation',
      content:
        'AI content automation helps teams plan, generate, optimize, and publish at scale. This article explains workflows, quality controls, and ROI metrics in a practical way for growth teams.',
    }),
  },

  // ── Social Scheduling ───────────────────────────────────
  {
    id: 'social-schedule',
    category: 'Social',
    title: 'Social Scheduler',
    method: 'POST',
    path: '/social/schedule',
    outputKey: 'social',
    buildPayload: (tenantId) => ({
      platform: 'linkedin',
      text: 'We just launched the Nuxtron production studio with Content, Social, Ads, and SEO workflows.',
      publish_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      media_urls: [],
    }),
  },

  // ── Social Listening ────────────────────────────────────
  {
    id: 'listening-demo',
    category: 'Social Listening',
    title: 'Social Listening Demo',
    method: 'POST',
    path: '/social/listening/ingest',
    outputKey: 'listening',
    buildPayload: () => ({
      platform: 'x',
      query: 'nuxtron',
      author_handle: '@growth_signal',
      text: 'Nuxtron is getting mentioned in operator circles for realtime campaign signal tracking.',
      sentiment: 'positive',
      engagement_count: 42,
    }),
  },

  {
    id: 'listening-alerts',
    category: 'Social Listening',
    title: 'Listening Alerts Sweep',
    method: 'POST',
    path: '/social/listening/rules',
    outputKey: 'listeningAlerts',
    relatedOutputs: ['listening', 'listeningAlerts', 'listeningClusters'],
    buildPayload: () => ({
      name: 'High engagement negative mentions',
      query: 'nuxtron',
      platform: 'x',
      min_engagement: 50,
      negative_only: true,
    }),
  },

  // ── Reviews Engine ──────────────────────────────────────
  {
    id: 'reviews-ops',
    category: 'Reviews',
    title: 'Reviews Engine',
    method: 'POST',
    path: '/reviews/ingest',
    outputKey: 'reviews',
    buildPayload: () => ({
      platform: 'google',
      reviewer: 'Taylor',
      rating: 2,
      text: 'Great vision but onboarding docs were confusing and support was delayed.',
      category: 'onboarding',
    }),
  },

  // ── CRM & Integration ───────────────────────────────────
  {
    id: 'suitecrm-lead',
    category: 'Integrations',
    title: 'SuiteCRM Lead Bridge',
    method: 'POST',
    path: '/integrations/suitecrm/upsert-lead',
    outputKey: 'suitecrm',
    buildPayload: () => ({
      first_name: 'Alex',
      last_name: 'Founder',
      email: 'alex.founder@example.com',
      company: 'Nuxtron Labs',
      source: 'studio',
    }),
  },

  {
    id: 'refferq-referral',
    category: 'Integrations',
    title: 'RefferQ Referral Bridge',
    method: 'POST',
    path: '/integrations/refferq/register-referral',
    outputKey: 'refferq',
    buildPayload: () => ({
      referrer_email: 'alex.founder@example.com',
      referred_email: 'friend@example.com',
      campaign: 'studio-referral-campaign',
    }),
  },

  // ── Analytics ───────────────────────────────────────────
  {
    id: 'posthog-capture',
    category: 'Analytics',
    title: 'PostHog Event Capture',
    method: 'POST',
    path: '/analytics/posthog/capture',
    outputKey: 'posthog',
    buildPayload: (tenantId) => ({
      event: 'studio_demo_clicked',
      distinct_id: `${tenantId}-operator`,
      properties: {
        module: 'studio',
        action: 'manual-test',
      },
    }),
  },

  {
    id: 'matomo-track',
    category: 'Analytics',
    title: 'Matomo Event Track',
    method: 'POST',
    path: '/analytics/matomo/track',
    outputKey: 'matomo',
    buildPayload: () => ({
      event_name: 'studio_matomo_click',
      action_name: 'Studio Matomo Trigger',
      properties: {
        module: 'studio',
      },
    }),
  },

  {
    id: 'plausible-track',
    category: 'Analytics',
    title: 'Plausible Event Track',
    method: 'POST',
    path: '/analytics/plausible/track',
    outputKey: 'plausible',
    buildPayload: () => ({
      event_name: 'studio_plausible_click',
      properties: {
        module: 'studio',
      },
    }),
  },

  // ── Workflow & Feature Flags ─────────────────────────────
  {
    id: 'n8n-trigger',
    category: 'Workflows',
    title: 'n8n Webhook Trigger',
    method: 'POST',
    path: '/integrations/n8n/trigger-webhook',
    outputKey: 'n8n',
    buildPayload: () => ({
      workflow: 'studio-automation',
      payload: {
        action: 'run',
        module: 'studio',
      },
    }),
  },

  {
    id: 'growthbook-evaluate',
    category: 'Feature Flags',
    title: 'GrowthBook Flag Evaluate',
    method: 'POST',
    path: '/flags/growthbook/evaluate',
    outputKey: 'growthbook',
    buildPayload: (tenantId) => ({
      feature_key: 'studio.experimentalFlows',
      user_id: `${tenantId}-operator`,
      attributes: {
        plan: 'pro',
        source: 'studio',
      },
    }),
  },

  // ── Platform Operations ─────────────────────────────────
  {
    id: 'ops-status',
    category: 'Platform Ops',
    title: 'Platform Ops Status',
    method: 'GET',
    path: '/ops/platform/status',
    outputKey: 'ops',
  },

  {
    id: 'metrics-summary',
    category: 'Platform Ops',
    title: 'Platform Metrics Summary',
    method: 'GET',
    path: '/ops/platform/metrics-summary',
    outputKey: 'metrics',
  },

  // ── Search ──────────────────────────────────────────────
  {
    id: 'search-index',
    category: 'Search',
    title: 'Meilisearch — Index Document',
    method: 'POST',
    path: '/search/index-document',
    outputKey: 'searchIndex',
    buildPayload: () => ({
      index: 'studio-docs',
      document_id: `doc-${Date.now()}`,
      document: {
        title: 'Nuxtron Studio Search Test',
        body: 'Full-text search powered by Meilisearch for tenant-scoped content.',
        tags: ['studio', 'search', 'meilisearch'],
      },
    }),
  },

  {
    id: 'search-query',
    category: 'Search',
    title: 'Meilisearch — Query',
    method: 'POST',
    path: '/search/query',
    outputKey: 'searchQuery',
    buildPayload: () => ({
      index: 'studio-docs',
      query: 'Nuxtron search',
      limit: 10,
      offset: 0,
    }),
  },

  // ── Webhooks ────────────────────────────────────────────
  {
    id: 'webhook-receive',
    category: 'Webhooks',
    title: 'Webhook Receiver',
    method: 'POST',
    path: '/webhooks/receive/generic',
    outputKey: 'webhook',
    buildPayload: (tenantId) => ({
      provider: 'generic',
      event_type: 'studio.test.event',
      payload: {
        source: 'studio',
        triggered_by: tenantId,
        ts: new Date().toISOString(),
      },
    }),
  },

  {
    id: 'webhook-events',
    category: 'Webhooks',
    title: 'Webhook Event Log',
    method: 'GET',
    path: '/webhooks/events',
    outputKey: 'webhookEvents',
  },

  // ── Appwrite ────────────────────────────────────────────
  {
    id: 'appwrite-user',
    category: 'Appwrite',
    title: 'Appwrite — Create User',
    method: 'POST',
    path: '/integrations/appwrite/create-user',
    outputKey: 'appwriteUser',
    buildPayload: (tenantId) => ({
      user_id: `studio-user-${Date.now()}`,
      email: 'studio-test@nuxtron.io',
      name: 'Studio Test User',
      password: generateDemoPassword(tenantId),
    }),
  },

  {
    id: 'appwrite-session',
    category: 'Appwrite',
    title: 'Appwrite — Create Session',
    method: 'POST',
    path: '/integrations/appwrite/create-session',
    outputKey: 'appwriteSession',
    buildPayload: (tenantId) => ({
      email: 'studio-test@nuxtron.io',
      password: generateDemoPassword(tenantId),
    }),
  },

  // ── CI/CD ───────────────────────────────────────────────
  {
    id: 'drone-build',
    category: 'CI/CD',
    title: 'Drone CI — Trigger Build',
    method: 'POST',
    path: '/integrations/drone/trigger-build',
    outputKey: 'drone',
    buildPayload: () => ({
      repo_owner: 'nux-tron',
      repo_name: 'Nuxtron',
      branch: 'main',
      params: { env: 'staging', source: 'studio' },
    }),
  },

  // ── Directus CMS ────────────────────────────────────────
  {
    id: 'directus-create',
    category: 'Directus',
    title: 'Directus — Create Item',
    method: 'POST',
    path: '/integrations/directus/create-item',
    outputKey: 'directusCreate',
    buildPayload: (tenantId) => ({
      collection: 'studio_content',
      data: {
        title: 'Studio Content Entry',
        body: 'Created from Nuxtron Studio.',
        source: tenantId,
        created_at: new Date().toISOString(),
      },
    }),
  },

  {
    id: 'directus-list',
    category: 'Directus',
    title: 'Directus — List Items',
    method: 'POST',
    path: '/integrations/directus/list-items',
    outputKey: 'directusList',
    buildPayload: () => ({
      collection: 'studio_content',
      limit: 10,
      offset: 0,
    }),
  },

  // ── Storage (MinIO) ─────────────────────────────────────
  {
    id: 'minio-presign',
    category: 'Storage',
    title: 'MinIO — Presign URL',
    method: 'POST',
    path: '/storage/presign',
    outputKey: 'minioPresign',
    buildPayload: () => ({
      bucket: 'uploads',
      object_key: `studio/${Date.now()}/asset.bin`,
      method: 'PUT',
      expires_seconds: 600,
    }),
  },

  {
    id: 'minio-list',
    category: 'Storage',
    title: 'MinIO — List Objects',
    method: 'POST',
    path: '/storage/list-objects',
    outputKey: 'minioList',
    buildPayload: () => ({
      bucket: 'uploads',
      prefix: 'studio/',
      max_keys: 20,
    }),
  },

  // ── Payments (Stripe) ───────────────────────────────────
  {
    id: 'stripe-checkout',
    category: 'Payments',
    title: 'Stripe — Create Checkout',
    method: 'POST',
    path: '/payments/stripe/create-checkout',
    outputKey: 'stripeCheckout',
    buildPayload: () => ({
      price_id: 'price_studio_test',
      success_url: 'http://localhost:8001/stripe-success',
      cancel_url: 'http://localhost:8001/stripe-cancel',
      quantity: 1,
      metadata: { source: 'studio' },
    }),
  },

  {
    id: 'stripe-webhook',
    category: 'Payments',
    title: 'Stripe — Process Webhook',
    method: 'POST',
    path: '/payments/stripe/process-webhook',
    outputKey: 'stripeWebhook',
    buildPayload: () => ({
      event_type: 'checkout.session.completed',
      event_id: `evt_studio_${Date.now()}`,
      data: { amount: 4900, currency: 'usd' },
    }),
  },

  {
    id: 'stripe-events',
    category: 'Payments',
    title: 'Stripe — Event Log',
    method: 'GET',
    path: '/payments/stripe/events',
    outputKey: 'stripeEvents',
  },

  // ── Audit & Security ───────────────────────────────────
  {
    id: 'audit-log',
    category: 'Security',
    title: 'Audit Log',
    method: 'GET',
    path: '/ops/audit-log',
    outputKey: 'auditLog',
  },

  // ── Caching ─────────────────────────────────────────────
  {
    id: 'cache-set',
    category: 'Cache',
    title: 'Redis Cache — Set',
    method: 'POST',
    path: '/cache/set',
    outputKey: 'cacheSet',
    buildPayload: (tenantId) => ({
      key: `studio:session:${Date.now()}`,
      value: JSON.stringify({ user: tenantId, ts: new Date().toISOString() }),
      ttl_seconds: 300,
    }),
  },

  {
    id: 'cache-get',
    category: 'Cache',
    title: 'Redis Cache — Get',
    method: 'POST',
    path: '/cache/get',
    outputKey: 'cacheGet',
    buildPayload: () => ({
      key: 'studio:session:demo',
    }),
  },

  // ── Notifications (Twilio) ──────────────────────────────
  {
    id: 'twilio-sms',
    category: 'Notifications',
    title: 'Twilio — Send SMS',
    method: 'POST',
    path: '/notifications/twilio/send-sms',
    outputKey: 'twilioSms',
    buildPayload: (tenantId) => ({
      to: '+15005550006',
      body: `Nuxtron Studio notification for ${tenantId} — ${new Date().toISOString()}`,
    }),
  },

  {
    id: 'twilio-call',
    category: 'Notifications',
    title: 'Twilio — Make Call',
    method: 'POST',
    path: '/notifications/twilio/make-call',
    outputKey: 'twilioCall',
    buildPayload: () => ({
      to: '+15005550006',
      twiml_url: 'http://localhost:8001/twiml/greeting',
    }),
  },

  // ── Slack ───────────────────────────────────────────────
  {
    id: 'slack-message',
    category: 'Notifications',
    title: 'Slack — Send Message',
    method: 'POST',
    path: '/notifications/slack/send-message',
    outputKey: 'slackMessage',
    buildPayload: (tenantId) => ({
      channel: '#nuxtron-alerts',
      text: `Studio event from ${tenantId} at ${new Date().toISOString()}`,
      username: 'Nuxtron Studio',
      icon_emoji: ':zap:',
    }),
  },

  {
    id: 'slack-webhook',
    category: 'Notifications',
    title: 'Slack — Incoming Webhook',
    method: 'POST',
    path: '/notifications/slack/webhook',
    outputKey: 'slackWebhook',
    buildPayload: (tenantId) => ({
      text: `Nuxtron platform webhook notification from ${tenantId}.`,
    }),
  },

  // ── Email ───────────────────────────────────────────────
  {
    id: 'resend-email',
    category: 'Notifications',
    title: 'Resend — Send Transactional Email',
    method: 'POST',
    path: '/notifications/resend/send-email',
    outputKey: 'resend',
    buildPayload: (tenantId) => ({
      to_email: 'growth@nuxtron.io',
      subject: `Nuxtron Studio transactional test (${tenantId})`,
      text: `Transactional message generated from Studio at ${new Date().toISOString()}.`,
    }),
  },

  // ── Search (Algolia) ────────────────────────────────────
  {
    id: 'algolia-index',
    category: 'Search',
    title: 'Algolia — Index Object',
    method: 'POST',
    path: '/search/algolia/index-object',
    outputKey: 'algoliaIndex',
    buildPayload: (tenantId) => ({
      index_name: 'products',
      object_id: `studio-${Date.now()}`,
      document: {
        title: 'Nuxtron Pro Plan',
        category: 'subscription',
        copy: `Generated for ${tenantId}`,
        updated_at: new Date().toISOString(),
      },
    }),
  },

  {
    id: 'algolia-query',
    category: 'Search',
    title: 'Algolia — Query',
    method: 'POST',
    path: '/search/algolia/query',
    outputKey: 'algoliaQuery',
    buildPayload: () => ({
      index_name: 'products',
      query: 'nuxtron',
      page: 0,
      hits_per_page: 10,
    }),
  },

  // ── AI Gateway ──────────────────────────────────────────
  {
    id: 'ai-gateway',
    category: 'AI',
    title: 'AI Gateway — OpenAI/Anthropic',
    method: 'POST',
    path: '/ai/gateway/generate',
    outputKey: 'aiGateway',
    buildPayload: () => ({
      provider: 'openai',
      prompt: 'Generate a concise launch line for Nuxtron platform updates.',
      system_prompt: 'You write short product launch snippets in clear English.',
      max_tokens: 160,
      temperature: 0.5,
    }),
  },

  // ── Authentication ──────────────────────────────────────
  {
    id: 'totp-setup',
    category: 'Auth',
    title: 'Auth — TOTP Setup',
    method: 'POST',
    path: '/auth/totp/setup',
    outputKey: 'totpSetup',
    buildPayload: (tenantId) => ({
      account_name: `${tenantId}@nuxtron.io`,
      issuer: 'Nuxtron',
    }),
  },

  {
    id: 'totp-verify',
    category: 'Auth',
    title: 'Auth — TOTP Verify',
    method: 'POST',
    path: '/auth/totp/verify',
    outputKey: 'totpVerify',
    buildPayload: () => ({
      secret: 'placeholder-secret',
      code: '000000',
      window: 1,
    }),
  },

  {
    id: 'jwt-issue',
    category: 'Auth',
    title: 'Auth — JWT Issue',
    method: 'POST',
    path: '/auth/jwt/issue',
    outputKey: 'jwtIssue',
    buildPayload: (tenantId) => ({
      subject: `${tenantId}-studio-user`,
      expires_in_seconds: 3600,
      roles: ['admin', 'editor'],
      additional_claims: { source: 'studio' },
    }),
  },

  {
    id: 'jwt-verify',
    category: 'Auth',
    title: 'Auth — JWT Verify',
    method: 'POST',
    path: '/auth/jwt/verify',
    outputKey: 'jwtVerify',
    buildPayload: () => ({
      token: 'placeholder-token',
    }),
  },

  // ── Tenant Management ───────────────────────────────────
  {
    id: 'tenant-create',
    category: 'Tenants',
    title: 'Tenant — Create Profile',
    method: 'POST',
    path: '/tenants',
    outputKey: 'tenantCreate',
    buildPayload: (tenantId) => ({
      display_name: `${tenantId} Workspace`,
      plan: 'growth',
      status: 'active',
      settings: { region: 'us-east-1', source: 'studio' },
    }),
  },

  {
    id: 'tenant-list',
    category: 'Tenants',
    title: 'Tenant — List Profiles',
    method: 'GET',
    path: '/tenants',
    outputKey: 'tenantList',
  },

  {
    id: 'tenant-update',
    category: 'Tenants',
    title: 'Tenant — Update Profile',
    method: 'PATCH',
    path: '/tenants/:id',
    outputKey: 'tenantUpdate',
    buildPayload: (tenantId) => ({
      display_name: `${tenantId} Workspace Updated`,
      plan: 'pro',
      settings: { region: 'eu-west-1', source: 'studio-updated' },
    }),
  },

  {
    id: 'tenant-delete',
    category: 'Tenants',
    title: 'Tenant — Delete Profile',
    method: 'DELETE',
    path: '/tenants/:id',
    outputKey: 'tenantDelete',
  },

  // ── CRM ─────────────────────────────────────────────────
  {
    id: 'crm-contact',
    category: 'CRM',
    title: 'CRM — Create Contact',
    method: 'POST',
    path: '/crm/contacts',
    outputKey: 'crmContact',
    buildPayload: () => ({
      first_name: 'Demo',
      last_name: 'User',
      email: 'demo@example.com',
      company: 'Demo Corp',
      source: 'studio',
    }),
  },

  {
    id: 'crm-deals',
    category: 'CRM',
    title: 'CRM — Deals',
    method: 'GET',
    path: '/crm/deals',
    outputKey: 'crmDeals',
  },

  {
    id: 'crm-pipeline',
    category: 'CRM',
    title: 'CRM — Pipeline',
    method: 'GET',
    path: '/crm/pipeline',
    outputKey: 'crmPipeline',
  },

  // ── Influencer ──────────────────────────────────────────
  {
    id: 'influencer-search',
    category: 'Influencer',
    title: 'Influencer — Discovery',
    method: 'POST',
    path: '/influencer/search',
    outputKey: 'influencerSearch',
    buildPayload: () => ({
      niche: 'technology',
      min_followers: 10000,
      platform: 'instagram',
    }),
  },

  {
    id: 'influencer-campaign',
    category: 'Influencer',
    title: 'Influencer — Campaign',
    method: 'POST',
    path: '/influencer/campaigns',
    outputKey: 'influencerCampaign',
    buildPayload: () => ({
      name: 'Studio Demo Campaign',
      budget: 5000,
      objective: 'awareness',
      influencer_ids: [1001],
    }),
  },

  // ── Chatbot ─────────────────────────────────────────────
  {
    id: 'chatbot',
    category: 'AI Tools',
    title: 'AI Chatbot Builder',
    method: 'POST',
    path: '/chatbot',
    outputKey: 'chatbot',
    buildPayload: () => ({
      name: 'Studio Demo Bot',
      description: 'Demo chatbot',
      language: 'en',
      tone: 'friendly',
    }),
  },

  // ── Link in Bio ─────────────────────────────────────────
  {
    id: 'linkinbio',
    category: 'Social Tools',
    title: 'Link-in-Bio',
    method: 'POST',
    path: '/linkinbio/pages',
    outputKey: 'linkinbio',
    buildPayload: () => ({
      title: 'Studio Links',
      bio: 'Powered by Nuxtron',
      theme: 'minimal',
    }),
  },

  // ── Billing ─────────────────────────────────────────────
  {
    id: 'billing-plans',
    category: 'Billing',
    title: 'Billing — Plans',
    method: 'GET',
    path: '/billing/plans',
    outputKey: 'billingPlans',
  },

  {
    id: 'billing-subscribe',
    category: 'Billing',
    title: 'Billing — Subscribe',
    method: 'POST',
    path: '/billing/subscribe',
    outputKey: 'billingSubscribe',
    buildPayload: () => ({
      plan_id: 'studio',
      billing_cycle: 'monthly',
      payment_method_token: 'tok_demo',
    }),
  },

  // ── CMS Integration ────────────────────────────────────
  {
    id: 'cms-connection',
    category: 'Integrations',
    title: 'CMS Integration',
    method: 'POST',
    path: '/cms/connections',
    outputKey: 'cmsConnection',
    buildPayload: () => ({
      cms_type: 'wordpress',
      display_name: 'Demo Blog',
      site_url: 'https://demo.blog',
      api_key: 'demo-key',
    }),
  },

  // ── Marketplace ─────────────────────────────────────────
  {
    id: 'marketplace-plugins',
    category: 'Marketplace',
    title: 'Marketplace — Plugins',
    method: 'GET',
    path: '/marketplace/plugins',
    outputKey: 'marketplacePlugins',
  },

  // ── Analytics Dashboard ─────────────────────────────────
  {
    id: 'analytics-dashboard',
    category: 'Analytics',
    title: 'Analytics Dashboard',
    method: 'GET',
    path: '/analytics/dashboard',
    outputKey: 'analyticsDashboard',
  },

  // ── Notifications Preferences ────────────────────────────
  {
    id: 'notif-prefs',
    category: 'Settings',
    title: 'Notification Preferences',
    method: 'GET',
    path: '/notifications/preferences',
    outputKey: 'notifPrefs',
  },
];

/**
 * Generate a deterministic demo password for a tenant.
 * Pattern: Studio-{slug}-Aa1!
 */
function generateDemoPassword(tenantId: string): string {
  const slug = tenantId.replaceAll(/[^a-zA-Z0-9]/g, '').slice(0, 12) || 'tenantdemo';
  return `Studio-${slug}-Aa1!`;
}

/**
 * Get endpoints grouped by category for UI rendering.
 */
export function getEndpointsByCategory(): Map<string, EndpointDemoConfig[]> {
  const grouped = new Map<string, EndpointDemoConfig[]>();
  for (const endpoint of STUDIO_ENDPOINTS) {
    if (!grouped.has(endpoint.category)) {
      grouped.set(endpoint.category, []);
    }
    grouped.get(endpoint.category)!.push(endpoint);
  }
  return grouped;
}

/**
 * Get endpoint config by id.
 */
export function getEndpointById(id: string): EndpointDemoConfig | undefined {
  return STUDIO_ENDPOINTS.find((ep) => ep.id === id);
}
