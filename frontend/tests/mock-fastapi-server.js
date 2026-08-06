const http = require('node:http');

const port = 4101;

const state = {
  totpSecret: '',
  jwtToken: '',
  tenant: null,
  notifications: [],
  notificationClients: [],
  brandProfiles: new Map(),
  listeningMentions: [],
  listeningRules: [],
  listeningAlerts: [],
  reviews: [],
  vseBriefs: [],
  vseNetworkMaps: [],
  vseDetonations: [],
  vseSwarms: [],
  vseMomentum: [],
  vsePaidEvents: [],
  vseDarkSeeds: [],
  vseImmortal: [],
  vseVault: [],
  yextWiredTenants: new Set(),
  brightedgeWiredTenants: new Set(),
  mediaJobs: [],
  mediaDlq: [],
  mediaJobClients: [],
  bufferParity: new Map(),
  latelyParity: new Map(),
  bestStackReports: new Map(),
};

const metricsPayload = {
  status: 'ok',
  tenant_id: 'tenant-demo',
  queues: {
    twilio_messages_memory: 3,
    slack_messages_memory: 2,
    resend_messages_memory: 1,
  },
  rate_limiter: {
    active_keys: 4,
    sample_count: 17,
  },
  generated_at: '2026-04-17T12:00:00Z',
};

const statusPayload = {
  status: 'ok',
  tenant_id: 'tenant-demo',
  integrations: {
    hashicorp_vault_configured: true,
    supabase_configured: true,
    supabase_vault_ready: true,
  },
};

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-Tenant-Id',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    'Content-Type': 'application/json',
  });
  res.end(JSON.stringify(payload));
}

function sendText(res, statusCode, body) {
  res.writeHead(statusCode, {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-Tenant-Id',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    'Content-Type': 'text/plain; charset=utf-8',
  });
  res.end(body);
}

function notificationSnapshot(tenantId) {
  const items = state.notifications
    .filter((item) => item.tenant_id === tenantId)
    .slice()
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return {
    status: 'ok',
    tenant_id: tenantId,
    notifications: items,
    unreadCount: items.filter((item) => !item.read).length,
  };
}

const PRIORITY_VALUES = new Set(['info', 'warning', 'error', 'success', 'critical']);

function normalizedPriority(value) {
  return PRIORITY_VALUES.has(value) ? value : 'info';
}

function notificationListResponse(tenantId, searchParams) {
  const category = searchParams.get('category') || null;
  const priority = searchParams.get('priority') || null;
  const limitRaw = Number(searchParams.get('limit') || 50);
  const offsetRaw = Number(searchParams.get('offset') || 0);
  const limit = Number.isFinite(limitRaw) ? Math.max(1, Math.min(200, limitRaw)) : 50;
  const offset = Number.isFinite(offsetRaw) ? Math.max(0, offsetRaw) : 0;

  const allItems = state.notifications
    .filter((item) => item.tenant_id === tenantId)
    .filter((item) => (category ? item.category === category : true))
    .filter((item) => (priority ? (item.priority || 'info') === priority : true))
    .slice()
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));

  return {
    status: 'ok',
    tenant_id: tenantId,
    notifications: allItems.slice(offset, offset + limit),
    unreadCount: allItems.filter((item) => !item.read).length,
    total: allItems.length,
    limit,
    offset,
  };
}

function sendSse(res, event, payload) {
  res.write(`event: ${event}\n`);
  res.write(`data: ${JSON.stringify(payload)}\n\n`);
}

function safeSendSse(client, event, payload) {
  try {
    sendSse(client.res, event, payload);
    return true;
  } catch {
    return false;
  }
}

function defaultBrandProfile() {
  return {
    business_name: 'Nuxtron',
    industry: 'marketing',
    website: 'https://nuxtron.example',
    description: 'Mock brand profile',
    tone: 'professional',
    logo_url: '',
    logo_dark_url: '',
    keywords: [],
    hashtags: [],
    timezone: 'UTC',
    ethnicity: 'Global / Generic',
    voiceover: '',
    avatar_profile: {
      mode: 'catalog',
      preset_id: 'ava-creator-01',
      name: 'Mila Harper',
      location: 'New York, US',
      ethnicity: 'European',
      gender: 'female',
      age_range: '25-34',
      style: 'Modern Casual',
      face_type: 'Oval',
      eye_style: 'Almond',
      body_shape: 'Athletic',
      body_proportions: 'Balanced',
    },
    voiceover_engine: {
      language: 'English',
      voice_name: 'Liam',
      style: 'Narration',
      tone: 'Confident',
      accent: 'US',
      use_case: 'Narration',
    },
    ugc_template_profile: {
      style_category_id: 'no-discount-promo',
      preview_template_id: 'tpl-value-story',
      caption_pack_id: 'ugc-main-launch',
      platform: 'Instagram',
      objective: 'Sales',
      hook_style: 'Announcement',
      script_style: 'Storytelling',
      aspect_ratio: '9:16',
      auto_adjust_platforms: true,
      background_media: 'AI Videos',
      subtitles_auto: true,
      subtitles_language: 'Auto (detect)',
    },
    brand_colors: ['#f8fafc', '#84cc16', '#93c5fd', '#3b82f6'],
    title_font_family: 'Hanken Grotesk',
    subtitle_font_family: 'Sora',
    title_font_weight: 'Regular',
    subtitle_font_weight: 'Medium',
    title_case_type: 'Auto',
    subtitle_case_type: 'Sentence',
    use_custom_font_title: false,
    use_custom_font_subtitle: false,
    custom_font_title: '',
    custom_font_subtitle: '',
  };
}

function brandProfileForTenant(tenantId) {
  if (!state.brandProfiles.has(tenantId)) {
    state.brandProfiles.set(tenantId, defaultBrandProfile());
  }
  return state.brandProfiles.get(tenantId);
}

function defaultBufferParityState(tenantId) {
  return {
    ideas: [
      {
        id: 1,
        tenant_id: tenantId,
        title: 'Launch customer story carousel',
        body: 'Turn this week customer quote into a 5-card carousel.',
        source: 'instagram',
        tags: ['ugc', 'launch'],
        status: 'new',
        created_at: '2026-05-20T10:00:00Z',
      },
      {
        id: 2,
        tenant_id: tenantId,
        title: 'Founder POV thread',
        body: 'Convert founder note into an X thread with 7 posts.',
        source: 'x',
        tags: ['thought-leadership'],
        status: 'queued',
        created_at: '2026-05-21T11:30:00Z',
      },
    ],
    templates: [
      {
        id: 'tmpl-1',
        tenant_id: tenantId,
        name: 'Product launch',
        content_type: 'post',
        body: 'Launching [feature]. Here is what changes for customers...',
        networks: ['linkedin', 'instagram'],
        tags: ['launch'],
      },
    ],
    hashtagGroups: [
      {
        id: 'hg-1',
        tenant_id: tenantId,
        name: 'Core brand',
        hashtags: ['nuxtron', 'socialmedia', 'growth'],
        description: 'Primary brand tags',
      },
    ],
    queue: [
      {
        id: 'q-1',
        tenant_id: tenantId,
        title: 'Queued launch post',
        caption: 'We are shipping the new workspace today.',
        platforms: ['linkedin', 'instagram'],
        status: 'scheduled',
        scheduled_for: '2026-05-29T14:00:00Z',
        first_comment: 'Tell us which workflow you want next.',
        content_type: 'post',
      },
      {
        id: 'q-2',
        tenant_id: tenantId,
        title: 'Community repurpose draft',
        caption: 'Turning top customer question into a tutorial.',
        platforms: ['x'],
        status: 'draft',
        scheduled_for: '2026-05-30T09:30:00Z',
        thread_count: 6,
        content_type: 'thread',
      },
      {
        id: 'q-3',
        tenant_id: tenantId,
        title: 'Published recap',
        caption: 'Monthly recap is now live.',
        platforms: ['facebook'],
        status: 'sent',
        scheduled_for: '2026-05-18T16:00:00Z',
        content_type: 'post',
      },
    ],
    approvals: [
      {
        id: 1,
        tenant_id: tenantId,
        status: 'pending',
        platform: 'linkedin',
        content_preview: 'Executive launch post for approval',
        requested_by: 'alex',
        approval_levels: ['editor', 'approver'],
        approvals_received: ['editor'],
        created_at: '2026-05-27T12:00:00Z',
      },
    ],
    schedules: [
      {
        id: 'sched-1',
        tenant_id: tenantId,
        network: 'instagram',
        timezone: 'UTC',
        slots: [
          { day: 'Monday', time: '09:00' },
          { day: 'Wednesday', time: '12:00' },
        ],
      },
      {
        id: 'sched-2',
        tenant_id: tenantId,
        network: 'linkedin',
        timezone: 'UTC',
        slots: [{ day: 'Tuesday', time: '10:00' }],
      },
    ],
    comments: [
      {
        id: 'cmt-1',
        tenant_id: tenantId,
        network: 'instagram',
        post_title: 'Launch teaser',
        author: '@jamie',
        text: 'Looks great, when does it launch?',
        sentiment: 'positive',
        replied: false,
        status: 'pending',
        likes: 5,
        created_at: '2026-05-28T08:30:00Z',
      },
    ],
    savedReplies: [
      { id: 'csr-1', tenant_id: tenantId, label: 'Thanks', text: 'Thanks for the support!', shortcut: '/ty' },
    ],
    teamMembers: [
      {
        id: 'mem-1',
        tenant_id: tenantId,
        email: 'admin@example.com',
        name: 'Admin User',
        role: 'admin',
        status: 'active',
        joined_at: '2026-04-01T00:00:00Z',
        channel_ids: [],
      },
      {
        id: 'mem-2',
        tenant_id: tenantId,
        email: 'editor@example.com',
        name: 'Content Editor',
        role: 'editor',
        status: 'active',
        joined_at: '2026-04-02T00:00:00Z',
        channel_ids: [],
      },
    ],
    startPage: {
      id: `sp-${tenantId}`,
      tenant_id: tenantId,
      title: 'Nuxtron',
      bio: 'AI-powered social operations workspace.',
      theme: 'minimal',
      accent_color: '#2563eb',
      background_color: '#ffffff',
      avatar_url: '',
      slug: tenantId,
      links: [
        { id: 'lnk-1', label: 'Book a demo', url: 'https://example.com/demo', active: true, clicks: 12, emoji: '📅' },
        { id: 'lnk-2', label: 'See pricing', url: 'https://example.com/pricing', active: true, clicks: 8, emoji: '💳' },
      ],
      social_links: [{ network: 'linkedin', url: 'https://linkedin.com/company/nuxtron' }],
      views: 144,
    },
    analytics: {
      networks: [
        {
          network: 'instagram',
          followers: 12400,
          follower_growth: 320,
          impressions: 18200,
          reach: 13100,
          engagement: 920,
          engagement_rate: 7.1,
          clicks: 210,
          link_clicks: 160,
          saves: 104,
          shares: 87,
          posts_count: 12,
          best_post_type: 'reel',
        },
        {
          network: 'linkedin',
          followers: 8600,
          follower_growth: 180,
          impressions: 12100,
          reach: 7900,
          engagement: 610,
          engagement_rate: 5.3,
          clicks: 190,
          link_clicks: 122,
          saves: 41,
          shares: 55,
          posts_count: 9,
          best_post_type: 'text',
        },
      ],
      totals: { total_impressions: 30300, total_reach: 21000, total_engagement: 1530, avg_engagement_rate: 6.2 },
      bestTime: {
        instagram: [{ day: 'Wednesday', time: '11:00', engagement_rate: 7.4, recommended: true }],
        linkedin: [{ day: 'Tuesday', time: '09:00', engagement_rate: 6.3, recommended: true }],
      },
      audience: {
        instagram: {
          followers: { total: 12400, growth_30d: 320, growth_pct: 2.6 },
          age_distribution: [
            { range: '25-34', pct: 38 },
            { range: '35-44', pct: 28 },
          ],
          gender_distribution: [
            { gender: 'female', pct: 56 },
            { gender: 'male', pct: 42 },
          ],
          top_countries: [
            { country: 'United States', pct: 40 },
            { country: 'United Kingdom', pct: 13 },
          ],
        },
        linkedin: {
          followers: { total: 8600, growth_30d: 180, growth_pct: 2.1 },
          age_distribution: [
            { range: '25-34', pct: 31 },
            { range: '35-44', pct: 34 },
          ],
          gender_distribution: [
            { gender: 'female', pct: 48 },
            { gender: 'male', pct: 50 },
          ],
          top_countries: [
            { country: 'United States', pct: 44 },
            { country: 'Canada', pct: 9 },
          ],
        },
      },
      reports: [
        {
          id: 'r-1',
          tenant_id: tenantId,
          name: 'Weekly summary',
          export_format: 'pdf',
          status: 'ready',
          created_at: '2026-05-27T09:00:00Z',
          download_url: '/api/v1/social/analytics/reports/r-1/download',
        },
      ],
    },
  };
}

function bestStackReportsForTenant(tenantId) {
  const key = String(tenantId);
  if (!state.bestStackReports.has(key)) {
    state.bestStackReports.set(key, []);
  }
  return state.bestStackReports.get(key);
}

function bufferParityForTenant(tenantId) {
  if (!state.bufferParity.has(tenantId)) {
    state.bufferParity.set(tenantId, defaultBufferParityState(tenantId));
  }
  return state.bufferParity.get(tenantId);
}

function defaultLatelyParityState() {
  return {
    voiceProfiles: [
      {
        profile_key: 'primary-voice',
        headline: 'Direct, evidence-heavy growth language with short punchy sentences.',
        voice_score: 86,
        fingerprint: {
          avg_sentence_length: 14.2,
          signature_words: ['proof', 'pipeline', 'outcomes', 'clarity', 'revenue'],
          punctuation_intensity: 0.28,
          line_break_ratio: 0.21,
        },
        rewrite: 'Ship the post with proof first. Lead with outcomes. Make every line earn attention.',
        updated_at: '2026-05-29T10:00:00Z',
        thumbs_up: 8,
        thumbs_down: 1,
      },
    ],
    keywords: [
      { keyword: 'ai workflow', impressions: 9200, engagement: 640, weight: 92, engagement_rate: 0.0695, platform: 'linkedin' },
      { keyword: 'social automation', impressions: 7800, engagement: 468, weight: 78, engagement_rate: 0.06, platform: 'x' },
      { keyword: 'brand voice', impressions: 5600, engagement: 364, weight: 69, engagement_rate: 0.065, platform: 'instagram' },
      { keyword: 'content repurposing', impressions: 4300, engagement: 189, weight: 56, engagement_rate: 0.044, platform: 'linkedin' },
    ],
    abTests: [
      {
        test_key: 'ab-1',
        name: 'Launch Hook Test',
        channel: 'linkedin',
        goal: 'engagement',
        status: 'running',
        variants_count: 5,
        winner: null,
        created_at: '2026-05-29T09:00:00Z',
        variants: [
          { variant_key: 'v1', content: 'Hook with bold claim and one proof point.', engagement_score: 0 },
          { variant_key: 'v2', content: 'Story-led opening with customer example.', engagement_score: 0 },
          { variant_key: 'v3', content: 'Question-first opener with urgency.', engagement_score: 0 },
          { variant_key: 'v4', content: 'Contrarian point of view then data.', engagement_score: 0 },
          { variant_key: 'v5', content: 'Framework summary with CTA.', engagement_score: 0 },
        ],
      },
    ],
    hierarchy: [
      {
        brand_key: 'nuxtron-hq',
        child_brand_name: 'Nuxtron HQ',
        parent_brand_key: 'root',
        region: 'Global',
        industry: 'SaaS',
        voice_profile_key: 'primary-voice',
      },
      {
        brand_key: 'nuxtron-emea',
        child_brand_name: 'Nuxtron EMEA',
        parent_brand_key: 'nuxtron-hq',
        region: 'EMEA',
        industry: 'SaaS',
        voice_profile_key: 'primary-voice',
      },
    ],
  };
}

function latelyParityForTenant(tenantId) {
  if (!state.latelyParity.has(tenantId)) {
    state.latelyParity.set(tenantId, defaultLatelyParityState());
  }
  return state.latelyParity.get(tenantId);
}

function broadcastNotifications(tenantId) {
  const payload = notificationSnapshot(tenantId);
  const survivors = [];
  for (const client of state.notificationClients) {
    if (client.tenantId !== tenantId) {
      survivors.push(client);
      continue;
    }
    if (safeSendSse(client, 'notifications.updated', payload)) {
      survivors.push(client);
    }
  }
  state.notificationClients = survivors;
}

function mediaJobById(jobId, tenantId) {
  return state.mediaJobs.find((job) => job.id === jobId && job.tenant_id === tenantId) || null;
}

function broadcastMediaJobEvent(jobId, tenantId, eventName, payload) {
  const survivors = [];
  for (const client of state.mediaJobClients) {
    if (client.jobId !== jobId || client.tenantId !== tenantId) {
      survivors.push(client);
      continue;
    }
    if (safeSendSse(client, eventName, payload)) {
      survivors.push(client);
    }
  }
  state.mediaJobClients = survivors;
}

function scheduleMediaJobProgress(jobId, tenantId) {
  const job = mediaJobById(jobId, tenantId);
  if (job?.status !== 'queued') return;

  setTimeout(() => {
    const current = mediaJobById(jobId, tenantId);
    if (current?.status !== 'queued') return;
    current.status = 'processing';
    current.progress_pct = 62;
    current.updated_at = new Date().toISOString();
    broadcastMediaJobEvent(jobId, tenantId, 'job.updated', current);
  }, 600);

  setTimeout(() => {
    const current = mediaJobById(jobId, tenantId);
    if (!current || (current.status !== 'processing' && current.status !== 'queued')) return;

    const shouldFail = String(current.storage_key || '')
      .toLowerCase()
      .includes('fail');
    if (shouldFail) {
      current.status = 'failed';
      current.error = 'Mock sandbox processing failure';
      current.progress_pct = 100;
      current.updated_at = new Date().toISOString();
      state.mediaDlq.push({
        id: state.mediaDlq.length + 1,
        tenant_id: tenantId,
        job_id: current.id,
        reason: current.error,
        failed_at: current.updated_at,
      });
      broadcastMediaJobEvent(jobId, tenantId, 'job.updated', current);
      return;
    }

    current.status = 'complete';
    current.progress_pct = 100;
    current.output_key = `processed/${tenantId}/${current.id}/${String(current.storage_key).split('/').pop()}`;
    current.updated_at = new Date().toISOString();
    current.completed_at = current.updated_at;
    broadcastMediaJobEvent(jobId, tenantId, 'job.updated', current);
  }, 1400);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      if (!body) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(body));
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  // NOSONAR
  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const tenantId = req.headers['x-tenant-id'] || 'tenant-demo';

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-Tenant-Id',
      'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    });
    res.end();
    return;
  }

  if (req.method === 'GET' && url.pathname === '/healthz') {
    sendJson(res, 200, { status: 'ok' });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/django/health') {
    sendJson(res, 200, { status: 'ok' });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/ops/platform/metrics-summary') {
    sendJson(res, 200, metricsPayload);
    return;
  }

  if (req.method === 'GET' && url.pathname === '/ops/platform/status') {
    sendJson(res, 200, statusPayload);
    return;
  }

  if (req.method === 'GET' && url.pathname === '/notifications') {
    sendJson(res, 200, notificationListResponse(String(tenantId), url.searchParams));
    return;
  }

  if (req.method === 'GET' && url.pathname === '/notifications/unread-count') {
    const snapshot = notificationSnapshot(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      unreadCount: snapshot.unreadCount,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/notifications/stream') {
    const streamTenantId = url.searchParams.get('tenant_id') || String(tenantId);
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'Content-Type': 'text/event-stream',
    });

    const client = { tenantId: streamTenantId, res };
    state.notificationClients.push(client);
    sendSse(res, 'notifications.snapshot', notificationSnapshot(streamTenantId));

    req.on('close', () => {
      state.notificationClients = state.notificationClients.filter((item) => item !== client);
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/notifications') {
    const payload = await readJson(req).catch(() => ({}));
    const item = {
      id: state.notifications.length + 1,
      tenant_id: String(tenantId),
      title: payload.title || 'Notification',
      message: payload.message || 'Mock notification',
      category: payload.category || 'general',
      // Enhanced: preserve backend priority contract in frontend smoke tests.
      priority: normalizedPriority(payload.priority),
      read: false,
      read_at: null,
      created_at: new Date().toISOString(),
      source: 'mock-api',
      persistence: 'memory-fallback',
    };
    state.notifications.push(item);
    broadcastNotifications(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, notification: item });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/notifications/read-all') {
    let updated = 0;
    for (const notification of state.notifications) {
      if (notification.tenant_id !== String(tenantId) || notification.read) {
        continue;
      }
      notification.read = true;
      notification.read_at = new Date().toISOString();
      updated += 1;
    }
    broadcastNotifications(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, updated });
    return;
  }

  if (req.method === 'POST' && /^\/notifications\/\d+\/read$/.test(url.pathname)) {
    const match = /^\/notifications\/(\d+)\/read$/.exec(url.pathname);
    const notificationId = Number(match?.[1]);
    const notification = state.notifications.find(
      (item) => item.id === notificationId && item.tenant_id === String(tenantId)
    );
    if (!notification) {
      sendJson(res, 404, { detail: 'Notification not found.' });
      return;
    }
    notification.read = true;
    notification.read_at = new Date().toISOString();
    broadcastNotifications(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, notification });
    return;
  }

  if (req.method === 'DELETE' && /^\/notifications\/\d+$/.test(url.pathname)) {
    const match = /^\/notifications\/(\d+)$/.exec(url.pathname);
    const notificationId = Number(match?.[1]);
    const index = state.notifications.findIndex(
      (item) => item.id === notificationId && item.tenant_id === String(tenantId)
    );
    if (index === -1) {
      sendJson(res, 404, { detail: 'Notification not found.' });
      return;
    }
    const [notification] = state.notifications.splice(index, 1);
    broadcastNotifications(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, deleted: true, notification });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/notifications/twilio/send-sms') {
    sendJson(res, 200, {
      provider: 'twilio',
      sid: 'SM1234567890abcdef',
      status: 'queued',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/notifications/slack/send-message') {
    sendJson(res, 200, {
      provider: 'slack',
      ok: true,
      channel: '#nuxtron-alerts',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/notifications/resend/send-email') {
    sendJson(res, 200, {
      provider: 'resend',
      id: 're_mock_1234567890',
      status: 'queued',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/media/validate-file') {
    const payload = await readJson(req).catch(() => ({}));
    const expectedMime = String(payload.expected_mime || 'application/octet-stream');
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      mime_type: expectedMime,
      validation_token: `mock-validation-${Date.now()}`,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/storage/presign') {
    sendJson(res, 200, {
      status: 'ok',
      result: {
        presigned_url: null,
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/media/jobs') {
    const payload = await readJson(req).catch(() => ({}));
    const mediaType = payload.media_type || 'image';
    const now = new Date().toISOString();
    const job = {
      id: state.mediaJobs.length + 1,
      tenant_id: String(tenantId),
      status: 'queued',
      progress_pct: 0,
      storage_key: payload.storage_key || `raw-input/${tenantId}/mock-file.bin`,
      media_type: mediaType,
      output_bucket: payload.output_bucket || 'processed-output',
      output_key: null,
      error: null,
      created_at: now,
      updated_at: now,
    };
    state.mediaJobs.push(job);
    scheduleMediaJobProgress(job.id, String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, job });
    return;
  }

  if (req.method === 'GET' && /^\/media\/jobs\/\d+\/stream$/.test(url.pathname)) {
    const match = /^\/media\/jobs\/(\d+)\/stream$/.exec(url.pathname);
    const jobId = Number(match?.[1]);
    const streamTenantId = url.searchParams.get('tenant_id') || String(tenantId);
    const job = mediaJobById(jobId, streamTenantId);
    if (!job) {
      sendJson(res, 404, { detail: 'Media job not found.' });
      return;
    }

    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'Content-Type': 'text/event-stream',
    });

    const client = { tenantId: streamTenantId, jobId, res };
    state.mediaJobClients.push(client);
    sendSse(res, 'job.snapshot', job);

    req.on('close', () => {
      state.mediaJobClients = state.mediaJobClients.filter((item) => item !== client);
    });
    return;
  }

  if (req.method === 'POST' && /^\/media\/jobs\/\d+\/output-url$/.test(url.pathname)) {
    const match = /^\/media\/jobs\/(\d+)\/output-url$/.exec(url.pathname);
    const jobId = Number(match?.[1]);
    const job = mediaJobById(jobId, String(tenantId));
    if (!job) {
      sendJson(res, 404, { detail: 'Media job not found.' });
      return;
    }
    if (job.status !== 'complete') {
      sendJson(res, 409, { detail: 'Output URL only available for completed jobs.' });
      return;
    }
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      job_id: jobId,
      output_key: job.output_key,
      signed_url: `https://cdn.example.com/processed-output/${job.output_key}?sig=mock`,
      expires_at: 9999999999,
      expires_seconds: 900,
    });
    return;
  }

  if (req.method === 'DELETE' && /^\/media\/jobs\/\d+$/.test(url.pathname)) {
    const match = /^\/media\/jobs\/(\d+)$/.exec(url.pathname);
    const jobId = Number(match?.[1]);
    const job = mediaJobById(jobId, String(tenantId));
    if (!job) {
      sendJson(res, 404, { detail: 'Media job not found.' });
      return;
    }
    if (job.status === 'queued' || job.status === 'processing') {
      job.status = 'cancelled';
      job.updated_at = new Date().toISOString();
      broadcastMediaJobEvent(jobId, String(tenantId), 'job.updated', job);
    }
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, job });
    return;
  }

  if (req.method === 'POST' && /^\/media\/jobs\/\d+\/retry$/.test(url.pathname)) {
    const match = /^\/media\/jobs\/(\d+)\/retry$/.exec(url.pathname);
    const jobId = Number(match?.[1]);
    const job = mediaJobById(jobId, String(tenantId));
    if (!job) {
      sendJson(res, 404, { detail: 'Media job not found.' });
      return;
    }
    if (job.status !== 'failed') {
      sendJson(res, 409, { detail: 'Job is not retryable.' });
      return;
    }
    job.status = 'queued';
    job.progress_pct = 0;
    job.error = null;
    job.updated_at = new Date().toISOString();
    state.mediaDlq = state.mediaDlq.filter((item) => !(item.job_id === jobId && item.tenant_id === String(tenantId)));
    scheduleMediaJobProgress(job.id, String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, job });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/media/jobs/dlq') {
    const items = state.mediaDlq
      .filter((item) => item.tenant_id === String(tenantId))
      .slice()
      .sort((a, b) => String(b.failed_at).localeCompare(String(a.failed_at)));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, dlq: items, total: items.length });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/brand-profile') {
    const profile = brandProfileForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brand_profile: profile });
    return;
  }

  if (req.method === 'PUT' && url.pathname === '/social/brand-profile') {
    const payload = await readJson(req).catch(() => ({}));
    const current = brandProfileForTenant(String(tenantId));
    const next = {
      ...current,
      ...payload,
      keywords: Array.isArray(payload.keywords) ? payload.keywords : current.keywords,
      hashtags: Array.isArray(payload.hashtags) ? payload.hashtags : current.hashtags,
      brand_colors: Array.isArray(payload.brand_colors) ? payload.brand_colors : current.brand_colors,
      use_custom_font_title: Boolean(payload.use_custom_font_title),
      use_custom_font_subtitle: Boolean(payload.use_custom_font_subtitle),
    };
    state.brandProfiles.set(String(tenantId), next);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brand_profile: next });
    return;
  }

  if (req.method === 'PUT' && url.pathname === '/social/brand-profile/ugc-template') {
    const payload = await readJson(req).catch(() => ({}));
    const current = brandProfileForTenant(String(tenantId));
    const next = {
      ...current,
      ugc_template_profile: {
        ...current.ugc_template_profile,
        ...payload,
        auto_adjust_platforms: payload.auto_adjust_platforms !== false,
        subtitles_auto: payload.subtitles_auto !== false,
        subtitles_language:
          String(payload.subtitles_language || '').trim() || current.ugc_template_profile.subtitles_language,
      },
    };
    state.brandProfiles.set(String(tenantId), next);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      ugc_template_profile: next.ugc_template_profile,
      brand_profile: next,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/brand-profile/fetch-from-website') {
    const payload = await readJson(req).catch(() => ({}));
    const website = String(payload.website || '').trim();
    if (!website) {
      sendJson(res, 400, { detail: 'Website is required.' });
      return;
    }
    const current = brandProfileForTenant(String(tenantId));
    const fetched = {
      ...current,
      website,
      business_name: current.business_name || 'Nuxtron',
      description: current.description || `Fetched details from ${website}`,
    };
    state.brandProfiles.set(String(tenantId), fetched);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brand_profile: fetched });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/intelligence/ingest') {
    const payload = await readJson(req).catch(() => ({}));
    const current = brandProfileForTenant(String(tenantId));
    const domain = String(payload.domain_url || current.website || 'https://nuxtron.local').trim();
    const keywords = ['automation', 'growth', 'social', 'ads', 'roi'];
    const hashtags = ['#growth', '#socialmedia', '#aiautomation', '#marketing', '#roi'];
    const iraAutofill = {
      about_us: `Autofilled from ${domain}`,
      keywords,
      hashtags,
      captions: [
        'Scale your social pipeline with AI-assisted creative and posting intelligence. #growth #roi',
        'From brand data to ad-ready content in minutes. #socialmedia #aiautomation',
      ],
      descriptions: ['Unified social intelligence for campaigns, captions, hashtags, and posting windows.'],
      recommended_daily_budget_usd: 79,
      best_posting_windows: [
        { network: 'instagram', windows: ['Tue 11:00-13:00', 'Thu 17:00-19:00'] },
        { network: 'linkedin', windows: ['Tue 09:00-11:00', 'Wed 09:00-11:00'] },
      ],
      content_trend_generation_prompts: ['Generate this week trend hooks by audience intent and platform.'],
    };
    const next = {
      ...current,
      website: domain,
      keywords,
      hashtags,
      ira_autofill: iraAutofill,
      last_intelligence_ingested_at: new Date().toISOString(),
    };
    state.brandProfiles.set(String(tenantId), next);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      source_summary: {
        social_links: Array.isArray(payload.social_links) ? payload.social_links.length : 0,
        portfolio_links: Array.isArray(payload.portfolio_links) ? payload.portfolio_links.length : 0,
        competitor_links: Array.isArray(payload.competitor_links) ? payload.competitor_links.length : 0,
        accounts_considered: 3,
      },
      ira_autofill: iraAutofill,
      brand_profile: next,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/listening/ingest') {
    const payload = await readJson(req).catch(() => ({}));
    const mention = {
      id: state.listeningMentions.length + 1,
      tenant_id: String(tenantId),
      platform: payload.platform || 'x',
      query: payload.query || 'nuxtron',
      author_handle: payload.author_handle || '@mock_author',
      text: payload.text || 'Mock social listening mention',
      sentiment: payload.sentiment || 'neutral',
      engagement_count: Number(payload.engagement_count || 0),
      created_at: new Date().toISOString(),
      source: 'mock-api',
      persistence: 'memory-fallback',
    };
    state.listeningMentions.push(mention);
    for (const rule of state.listeningRules.filter(
      (item) => item.tenant_id === String(tenantId) && item.enabled !== false
    )) {
      const matchesQuery =
        !rule.query ||
        String(payload.query || '')
          .toLowerCase()
          .includes(String(rule.query).toLowerCase());
      const matchesPlatform = !rule.platform || rule.platform === mention.platform;
      const matchesSentiment = !rule.negative_only || mention.sentiment === 'negative';
      const matchesEngagement = mention.engagement_count >= Number(rule.min_engagement || 0);
      if (!matchesQuery || !matchesPlatform || !matchesSentiment || !matchesEngagement) {
        continue;
      }
      state.listeningAlerts.push({
        id: state.listeningAlerts.length + 1,
        tenant_id: String(tenantId),
        rule_id: rule.id,
        rule_name: rule.name,
        mention_id: mention.id,
        severity: mention.engagement_count >= 100 ? 'high' : 'medium',
        status: 'open',
        created_at: new Date().toISOString(),
      });
    }
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, mention });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/listening/rules') {
    const payload = await readJson(req).catch(() => ({}));
    const rule = {
      id: state.listeningRules.length + 1,
      tenant_id: String(tenantId),
      name: payload.name || 'Listening Alert Rule',
      query: payload.query || null,
      platform: payload.platform || null,
      min_engagement: Number(payload.min_engagement || 0),
      negative_only: payload.negative_only !== false,
      enabled: true,
      created_at: new Date().toISOString(),
      source: 'mock-api',
      persistence: 'memory-fallback',
    };
    state.listeningRules.push(rule);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, rule });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/listening/mentions') {
    const mentions = state.listeningMentions
      .filter((item) => item.tenant_id === String(tenantId))
      .slice()
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: mentions.length, mentions });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/listening/summary') {
    const mentions = state.listeningMentions.filter((item) => item.tenant_id === String(tenantId));
    const sentiment = { positive: 0, neutral: 0, negative: 0 };
    const platforms = {};
    const queries = {};
    let totalEngagement = 0;
    for (const mention of mentions) {
      sentiment[mention.sentiment] = (sentiment[mention.sentiment] || 0) + 1;
      platforms[mention.platform] = (platforms[mention.platform] || 0) + 1;
      queries[mention.query] = (queries[mention.query] || 0) + 1;
      totalEngagement += Number(mention.engagement_count || 0);
    }
    const topQueries = Object.entries(queries)
      .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
      .slice(0, 5)
      .map(([query, count]) => ({ query, mentions: count }));
    const clusterKey = (item) => `${item.query}::${item.platform}`;
    const clusterMap = new Map();
    for (const mention of mentions) {
      const key = clusterKey(mention);
      clusterMap.set(key, (clusterMap.get(key) || 0) + 1);
    }
    const clusters = Array.from(clusterMap.entries()).map(([key, count]) => {
      const [query, platform] = key.split('::');
      return { cluster: `${query}:${platform}`, query, platform, mentions: count };
    });
    const negativeMentions = mentions.filter((item) => item.sentiment === 'negative').length;
    const negativeRatio = mentions.length ? Number((negativeMentions / mentions.length).toFixed(4)) : 0;
    const highNegativeMentions = mentions.filter(
      (item) => item.sentiment === 'negative' && Number(item.engagement_count || 0) >= 50
    ).length;
    let crisisLevel = 'none';
    if (negativeRatio >= 0.4 || highNegativeMentions >= 3) crisisLevel = 'watch';
    if (negativeRatio >= 0.55 || highNegativeMentions >= 5) crisisLevel = 'high';
    if (negativeRatio >= 0.7 || highNegativeMentions >= 7) crisisLevel = 'critical';
    const alertsOpen = state.listeningAlerts.filter(
      (item) => item.tenant_id === String(tenantId) && item.status === 'open'
    ).length;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      summary: {
        total_mentions: mentions.length,
        sentiment,
        platforms,
        top_queries: topQueries,
        avg_engagement: mentions.length ? Number((totalEngagement / mentions.length).toFixed(2)) : 0,
        clusters,
        alerts_open: alertsOpen,
        crisis: {
          triggered: crisisLevel !== 'none',
          level: crisisLevel,
          negative_ratio: negativeRatio,
          high_negative_mentions: highNegativeMentions,
        },
      },
      mentions,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/listening/alerts') {
    const alerts = state.listeningAlerts
      .filter((item) => item.tenant_id === String(tenantId))
      .slice()
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: alerts.length, alerts });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/listening/clusters') {
    const mentions = state.listeningMentions.filter((item) => item.tenant_id === String(tenantId));
    const grouped = new Map();
    for (const mention of mentions) {
      const key = `${mention.query}::${mention.platform}::${mention.sentiment}`;
      grouped.set(key, (grouped.get(key) || 0) + 1);
    }
    const clusters = Array.from(grouped.entries()).map(([key, count]) => {
      const [query, platform, sentiment] = key.split('::');
      return { query, platform, sentiment, mentions: count };
    });
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: clusters.length, clusters });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/ideas') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, items: parity.ideas });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/ideas') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    const idea = {
      id: parity.ideas.length + 1,
      tenant_id: String(tenantId),
      title: payload.title || 'New idea',
      body: payload.body || '',
      source: payload.source || 'manual',
      tags: Array.isArray(payload.tags) ? payload.tags : [],
      status: 'new',
      created_at: new Date().toISOString(),
    };
    parity.ideas.unshift(idea);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, idea });
    return;
  }

  if (req.method === 'POST' && /^\/social\/ideas\/\d+\/queue$/.test(url.pathname)) {
    const payload = await readJson(req).catch(() => ({}));
    const match = /^\/social\/ideas\/(\d+)\/queue$/.exec(url.pathname);
    const ideaId = Number(match?.[1]);
    const parity = bufferParityForTenant(String(tenantId));
    const idea = parity.ideas.find((item) => item.id === ideaId);
    if (!idea) {
      sendJson(res, 404, { detail: 'Idea not found.' });
      return;
    }
    idea.status = 'queued';
    const post = {
      id: `q-${Date.now()}`,
      tenant_id: String(tenantId),
      title: idea.title,
      caption: idea.body,
      platforms: [payload.network || 'instagram'],
      status: 'scheduled',
      scheduled_for: new Date(Date.now() + 86_400_000).toISOString(),
      content_type: 'post',
    };
    parity.queue.unshift(post);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, idea, queued_post: post });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/production-readiness') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      readiness_score: 100,
      production_ready: true,
      capability_summary: {
        total_capabilities: 4,
        fully_wired_capabilities: 4,
        average_completion_percent: 100,
      },
      capability_matrix: [
        { capability_key: 'ai_scheduling', capability: 'AI Scheduling', status: 'done', completion_percent: 100, automation_level_percent: 100 },
        { capability_key: 'ai_repurposing', capability: 'AI Repurposing', status: 'done', completion_percent: 100, automation_level_percent: 100 },
        { capability_key: 'ai_content_engines', capability: 'AI Content Engines', status: 'done', completion_percent: 100, automation_level_percent: 100 },
        { capability_key: 'ai_social_listening', capability: 'AI Social Listening', status: 'done', completion_percent: 100, automation_level_percent: 100 },
      ],
      vendors: {
        registry: [
          { vendor_key: 'brandwatch_meltwater', vendor: 'Brandwatch/Meltwater', configured: true, capabilities: ['listening'] },
          { vendor_key: 'openai', vendor: 'OpenAI', configured: true, capabilities: ['copy', 'repurposing'] },
          { vendor_key: 'canva', vendor: 'Canva', configured: true, capabilities: ['creative'] },
        ],
      },
      stats: {
        queue_items: parity.queue.length,
      },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/integrations/growth-matrix') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      summary: { done: 5, partial: 0, missing: 0 },
      matrix: [],
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/integrations/catalog') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      categories: [],
      summary: { providers_total: 5, configured_total: 5, coverage_percent: 100 },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/automation/repurpose') {
    const payload = await readJson(req).catch(() => ({}));
    const variantCount = Math.max(1, Number(payload.variant_count || 3));
    const variants = Array.from({ length: variantCount }).map((_, idx) => ({
      id: `repurpose-${Date.now()}-${idx + 1}`,
      title: `${String(payload.source_title || 'Repurposed brief')} variant ${idx + 1}`,
      body: `Repurposed copy variant ${idx + 1} for ${String(payload.target_platform || 'linkedin')}.`,
      source: 'repurpose',
      tags: ['repurpose', String(payload.target_platform || 'linkedin')],
      status: 'new',
      created_at: new Date().toISOString(),
    }));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      source_title: String(payload.source_title || 'Repurposed brief'),
      source_url: payload.source_url || null,
      target_platform: String(payload.target_platform || 'linkedin'),
      tone: String(payload.tone || 'professional'),
      variant_count: variantCount,
      generated_variants: variants,
      queued_post: null,
      provider: 'mock-openai',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/ai-assistant') {
    const payload = await readJson(req).catch(() => ({}));
    const original = String(payload.text || '');
    sendJson(res, 200, {
      status: 'ok',
      action: String(payload.action || 'generate'),
      original,
      result: original ? `${original} (optimized)` : 'Generated social copy.',
      platform: String(payload.target_platform || 'linkedin'),
      provider: 'mock-openai',
      tenant_id: tenantId,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/automation/queue') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      items: parity.queue,
      pause_all: { paused: false, reason: '', updated_at: new Date().toISOString() },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/calendar') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, items: parity.queue.slice(0, 10) });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/production-readiness/best-stack-reports') {
    const reports = bestStackReportsForTenant(tenantId);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, reports });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/production-readiness/best-stack-report') {
    const payload = await readJson(req).catch(() => ({}));
    const reports = bestStackReportsForTenant(tenantId);
    const reportId = Date.now();
    const report = {
      id: reportId,
      name: `best-stack-${reportId}`,
      report_type: 'best_stack',
      generated_at: new Date().toISOString(),
      export_url: `/api/fastapi/social/production-readiness/best-stack-report/${reportId}/export`,
    };
    reports.unshift(report);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      report,
      artifact: {
        summary: {
          readiness_score: 100,
          production_ready: true,
          checks_total: Array.isArray(payload.probe_results) ? payload.probe_results.length : 0,
          checks_passed: Array.isArray(payload.probe_results)
            ? payload.probe_results.filter((item) => item && item.ok === true).length
            : 0,
          checks_failed: Array.isArray(payload.probe_results)
            ? payload.probe_results.filter((item) => item && item.ok !== true).length
            : 0,
        },
        stack_coverage: [],
        probe_results: Array.isArray(payload.probe_results) ? payload.probe_results : [],
        generated_at: new Date().toISOString(),
        generated_by: String(payload.generated_by || 'mock-fastapi-server'),
      },
      artifact_markdown: '# Best Stack Report\n\nGenerated by mock server.',
    });
    return;
  }

  if (req.method === 'GET' && /^\/social\/production-readiness\/best-stack-report\/\d+\/export$/.test(url.pathname)) {
    const match = /^\/social\/production-readiness\/best-stack-report\/(\d+)\/export$/.exec(url.pathname);
    const reportId = Number(match?.[1] || 0);
    const reports = bestStackReportsForTenant(tenantId);
    const report = reports.find((item) => Number(item.id) === reportId);
    if (!report) {
      sendJson(res, 404, { detail: 'Best stack report not found.' });
      return;
    }
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      report,
      artifact: { summary: { readiness_score: 100, production_ready: true } },
      artifact_markdown: '# Best Stack Report\n\nExport from mock server.',
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/audit-log') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      audit_log: [
        {
          id: 1,
          tenant_id: String(tenantId),
          action: 'best_stack_probe_run',
          ref_id: null,
          created_at: new Date().toISOString(),
          source: 'mock-fastapi-server',
        },
      ],
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/listening/sentiment') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      window_hours: 24,
      breakdown: { positive: 12, neutral: 7, negative: 2 },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/templates') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      templates: parity.templates,
      count: parity.templates.length,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/hashtag-groups') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      hashtag_groups: parity.hashtagGroups,
      count: parity.hashtagGroups.length,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/hashtag-groups') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    const group = {
      id: `hg-${Date.now()}`,
      tenant_id: String(tenantId),
      name: payload.name || 'Untitled group',
      hashtags: Array.isArray(payload.hashtags) ? payload.hashtags : [],
      description: payload.description || '',
    };
    parity.hashtagGroups.unshift(group);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, hashtag_group: group });
    return;
  }

  if (req.method === 'DELETE' && /^\/social\/hashtag-groups\/[^/]+$/.test(url.pathname)) {
    const match = /^\/social\/hashtag-groups\/([^/]+)$/.exec(url.pathname);
    const groupId = match?.[1];
    const parity = bufferParityForTenant(String(tenantId));
    parity.hashtagGroups = parity.hashtagGroups.filter((item) => item.id !== groupId);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, deleted: true, group_id: groupId });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/queue') {
    const parity = bufferParityForTenant(String(tenantId));
    const requestedStatus = (url.searchParams.get('status') || 'scheduled').toLowerCase();
    const queue =
      requestedStatus === 'all'
        ? parity.queue
        : parity.queue.filter((item) => String(item.status || '').toLowerCase() === requestedStatus);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, queue, count: queue.length });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/queue/reorder') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    const postIds = Array.isArray(payload.post_ids) ? payload.post_ids.map(String) : [];
    const byId = new Map(parity.queue.map((item) => [String(item.id), item]));
    parity.queue = postIds.map((id) => byId.get(id)).filter(Boolean);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, reordered: parity.queue.length });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/content/approval/requests') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      requests: parity.approvals,
      count: parity.approvals.length,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/posting-schedules') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, schedules: parity.schedules });
    return;
  }

  if (req.method === 'PUT' && /^\/social\/posting-schedules\/[^/]+$/.test(url.pathname)) {
    const payload = await readJson(req).catch(() => ({}));
    const match = /^\/social\/posting-schedules\/([^/]+)$/.exec(url.pathname);
    const network = match?.[1] || 'instagram';
    const parity = bufferParityForTenant(String(tenantId));
    const existing = parity.schedules.find((item) => item.network === network);
    if (existing) {
      existing.slots = Array.isArray(payload.slots) ? payload.slots : existing.slots;
      existing.timezone = payload.timezone || existing.timezone;
      sendJson(res, 200, { status: 'ok', tenant_id: tenantId, schedule: existing });
      return;
    }
    const schedule = {
      id: `sched-${Date.now()}`,
      tenant_id: String(tenantId),
      network,
      timezone: payload.timezone || 'UTC',
      slots: Array.isArray(payload.slots) ? payload.slots : [],
    };
    parity.schedules.push(schedule);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, schedule });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/community/comments') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      comments: parity.comments,
      count: parity.comments.length,
      unanswered_count: parity.comments.filter((item) => !item.replied).length,
    });
    return;
  }

  if (req.method === 'POST' && /^\/social\/community\/comments\/[^/]+\/reply$/.test(url.pathname)) {
    const payload = await readJson(req).catch(() => ({}));
    const match = /^\/social\/community\/comments\/([^/]+)\/reply$/.exec(url.pathname);
    const commentId = match?.[1];
    const parity = bufferParityForTenant(String(tenantId));
    const comment = parity.comments.find((item) => item.id === commentId);
    if (!comment) {
      sendJson(res, 404, { detail: 'Comment not found.' });
      return;
    }
    comment.reply = payload.reply || '';
    comment.replied = true;
    comment.status = 'replied';
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, comment, platform_published: true });
    return;
  }

  if (req.method === 'POST' && /^\/social\/community\/comments\/[^/]+\/create-post$/.test(url.pathname)) {
    const match = /^\/social\/community\/comments\/([^/]+)\/create-post$/.exec(url.pathname);
    const commentId = match?.[1];
    const parity = bufferParityForTenant(String(tenantId));
    const comment = parity.comments.find((item) => item.id === commentId);
    const post = {
      id: `q-${Date.now()}`,
      tenant_id: String(tenantId),
      title: `Repurposed: ${comment?.post_title || 'Comment'}`,
      caption: comment?.reply || comment?.text || '',
      platforms: [comment?.network || 'instagram'],
      status: 'draft',
      scheduled_for: new Date(Date.now() + 172_800_000).toISOString(),
      content_type: 'post',
    };
    parity.queue.unshift(post);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, post });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/community/score') {
    const parity = bufferParityForTenant(String(tenantId));
    const total = parity.comments.length;
    const repliedCount = parity.comments.filter((item) => item.replied).length;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      comment_score: {
        response_rate: total ? Number(((repliedCount / total) * 100).toFixed(1)) : 0,
        avg_response_time_minutes: 37,
        consistency_score: 82,
        total_comments: total,
        replied_count: repliedCount,
        pending_count: total - repliedCount,
        grade: repliedCount === total ? 'A' : 'B',
      },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/community/saved-replies') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      saved_replies: parity.savedReplies,
      count: parity.savedReplies.length,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/analytics/custom-report') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    const report = {
      id: `r-${Date.now()}`,
      tenant_id: String(tenantId),
      name: payload.name || 'Custom report',
      export_format: payload.export_format || 'pdf',
      status: 'ready',
      created_at: new Date().toISOString(),
      download_url: '/api/v1/social/analytics/reports/latest/download',
    };
    parity.analytics.reports.unshift(report);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, report });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/analytics/reports') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      reports: parity.analytics.reports,
      count: parity.analytics.reports.length,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/analytics/overview') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      period_days: Number(url.searchParams.get('days') || 30),
      ...parity.analytics,
    });
    return;
  }

  if (req.method === 'GET' && /^\/social\/analytics\/best-time\/[^/]+$/.test(url.pathname)) {
    const match = /^\/social\/analytics\/best-time\/([^/]+)$/.exec(url.pathname);
    const network = match?.[1] || 'instagram';
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      network,
      recommended_slots: parity.analytics.bestTime[network] || parity.analytics.bestTime.instagram || [],
    });
    return;
  }

  if (req.method === 'GET' && /^\/social\/analytics\/audience\/[^/]+$/.test(url.pathname)) {
    const match = /^\/social\/analytics\/audience\/([^/]+)$/.exec(url.pathname);
    const network = match?.[1] || 'instagram';
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      network,
      ...(parity.analytics.audience[network] || parity.analytics.audience.instagram),
    });
    return;
  }

  const latelyPath = url.pathname.startsWith('/api/fastapi')
    ? url.pathname.slice('/api/fastapi'.length)
    : url.pathname;

  if (req.method === 'GET' && latelyPath === '/ai/brand-voice/profiles') {
    const parity = latelyParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, profiles: parity.voiceProfiles });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/ai/brand-voice/profile') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const samplePosts = Array.isArray(payload.sample_posts) ? payload.sample_posts : [];
    const signatureWords = samplePosts
      .flatMap((post) => String(post || '').toLowerCase().split(/\W+/g))
      .filter((word) => word.length >= 5)
      .slice(0, 5);
    const profile = {
      profile_key: String(payload.profile_name || `voice-${Date.now()}`)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, ''),
      headline: 'Mock profile generated from uploaded posts.',
      voice_score: 72,
      fingerprint: {
        avg_sentence_length: 13.4,
        signature_words: signatureWords.length ? signatureWords : ['clarity', 'proof', 'results'],
        punctuation_intensity: 0.24,
        line_break_ratio: 0.19,
      },
      rewrite: String(payload.ai_output || 'AI rewrite in your brand voice.'),
      updated_at: new Date().toISOString(),
      thumbs_up: 0,
      thumbs_down: 0,
    };
    parity.voiceProfiles.unshift(profile);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, profile });
    return;
  }

  if (req.method === 'POST' && /^\/ai\/brand-voice\/[^/]+\/feedback$/.test(latelyPath)) {
    const match = /^\/ai\/brand-voice\/([^/]+)\/feedback$/.exec(latelyPath);
    const profileKey = match?.[1] || '';
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const profile = parity.voiceProfiles.find((item) => item.profile_key === profileKey);
    if (!profile) {
      sendJson(res, 404, { detail: 'Voice profile not found.' });
      return;
    }
    if (payload.signal === 'thumbs_up') {
      profile.thumbs_up += 1;
      profile.voice_score = Math.min(100, profile.voice_score + 2);
    } else {
      profile.thumbs_down += 1;
      profile.voice_score = Math.max(0, profile.voice_score - 3);
      if (payload.edited_output) {
        profile.rewrite = String(payload.edited_output);
      }
    }
    profile.updated_at = new Date().toISOString();
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, profile });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/content/repurpose') {
    const payload = await readJson(req).catch(() => ({}));
    const source = String(payload.source_content || 'source content');
    const snippet = source.slice(0, 90).trim();
    const formats = [
      'thread',
      'carousel',
      'newsletter',
      'podcast_script',
      'faq',
      'press_release',
      'video_script',
      'quote_cards',
      'ad_copy',
      'community_post',
    ];
    const outputs = formats.map((format, idx) => ({
      format,
      title: `${format.replaceAll('_', ' ')} draft ${idx + 1}`,
      summary: `${snippet} ... adapted for ${format.replaceAll('_', ' ')} with platform-fit hooks and CTA.`,
    }));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      repurpose: {
        outputs,
        hours_saved: 18,
      },
    });
    return;
  }

  if (req.method === 'GET' && latelyPath === '/analytics/keywords/top') {
    const parity = latelyParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, keywords: parity.keywords });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/analytics/keywords/track') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const keyword = {
      keyword: String(payload.keyword || 'keyword'),
      platform: String(payload.platform || 'linkedin'),
      impressions: Number(payload.impressions || 0),
      engagement: Number(payload.engagement || 0),
      weight: 55,
      engagement_rate: Number(payload.impressions || 0) > 0 ? Number(payload.engagement || 0) / Number(payload.impressions || 1) : 0,
    };
    parity.keywords.unshift(keyword);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, keyword });
    return;
  }

  if (req.method === 'GET' && latelyPath === '/experiments/ab-tests') {
    const parity = latelyParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, tests: parity.abTests });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/experiments/ab-tests') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const testKey = `ab-${Date.now()}`;
    const base = String(payload.base_content || 'Base content');
    const variants = Array.from({ length: 5 }).map((_, idx) => ({
      variant_key: `v${idx + 1}`,
      content: `${base} (variant ${idx + 1})`,
      engagement_score: 0,
    }));
    const testItem = {
      test_key: testKey,
      name: String(payload.name || 'A/B Test'),
      channel: String(payload.channel || 'linkedin'),
      goal: String(payload.goal || 'engagement'),
      status: 'running',
      variants_count: variants.length,
      winner: null,
      created_at: new Date().toISOString(),
      variants,
    };
    parity.abTests.unshift(testItem);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, test: testItem });
    return;
  }

  if (req.method === 'POST' && /^\/experiments\/ab-tests\/[^/]+\/evaluate$/.test(latelyPath)) {
    const match = /^\/experiments\/ab-tests\/([^/]+)\/evaluate$/.exec(latelyPath);
    const testKey = match?.[1] || '';
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const testItem = parity.abTests.find((item) => item.test_key === testKey);
    if (!testItem) {
      sendJson(res, 404, { detail: 'A/B test not found.' });
      return;
    }
    const scores = payload.engagement_scores || {};
    let winnerKey = null;
    let winnerScore = -Infinity;
    for (const variant of testItem.variants) {
      const score = Number(scores[variant.variant_key] || 0);
      variant.engagement_score = score;
      variant.is_winner = false;
      if (score > winnerScore) {
        winnerScore = score;
        winnerKey = variant.variant_key;
      }
    }
    if (winnerKey) {
      const winnerVariant = testItem.variants.find((item) => item.variant_key === winnerKey);
      if (winnerVariant) winnerVariant.is_winner = true;
    }
    testItem.status = 'concluded';
    testItem.winner = winnerKey;
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, test: testItem });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/forecast/roi') {
    const payload = await readJson(req).catch(() => ({}));
    const impressions = Number(payload.expected_impressions || 0);
    const projected_engagement = Math.round(impressions * 0.065);
    const projected_clicks = Math.round(projected_engagement * 0.38);
    const projected_conversions = Math.max(1, Math.round(projected_clicks * 0.09));
    const projected_revenue = projected_conversions * 420;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      forecast: {
        projected_engagement,
        projected_clicks,
        projected_conversions,
        projected_revenue,
        confidence: 0.74,
        recommended_slot: 'Tue 10:30 AM',
      },
    });
    return;
  }

  if (req.method === 'GET' && latelyPath === '/brand-hierarchy') {
    const parity = latelyParityForTenant(String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brands: parity.hierarchy });
    return;
  }

  if (req.method === 'POST' && latelyPath === '/brand-hierarchy') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = latelyParityForTenant(String(tenantId));
    const childBrand = {
      brand_key: `brand-${Date.now()}`,
      child_brand_name: String(payload.child_brand_name || 'Child Brand'),
      parent_brand_key: String(payload.parent_brand_key || 'root'),
      region: payload.region ? String(payload.region) : null,
      industry: payload.industry ? String(payload.industry) : null,
      voice_profile_key: payload.voice_profile_key ? String(payload.voice_profile_key) : null,
      created_at: new Date().toISOString(),
    };
    parity.hierarchy.push(childBrand);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brand: childBrand });
    return;
  }

  if (req.method === 'GET' && latelyPath === '/analytics/export') {
    const csv = ['platform,text,publish_at,status', 'linkedin,"Mock scheduled post",2026-05-30T09:00:00Z,scheduled'].join('\n');
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, csv, row_count: 1 });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/team/members') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      members: parity.teamMembers,
      count: parity.teamMembers.length,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/social/team/members/invite') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    const member = {
      id: `mem-${Date.now()}`,
      tenant_id: String(tenantId),
      email: payload.email || 'new@example.com',
      name: String(payload.email || 'new@example.com').split('@')[0],
      role: payload.role || 'viewer',
      status: 'invited',
      invited_at: new Date().toISOString(),
      channel_ids: Array.isArray(payload.channel_ids) ? payload.channel_ids : [],
    };
    parity.teamMembers.push(member);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, member, invitation_sent: true });
    return;
  }

  if (req.method === 'PUT' && /^\/social\/team\/members\/[^/]+$/.test(url.pathname)) {
    const payload = await readJson(req).catch(() => ({}));
    const match = /^\/social\/team\/members\/([^/]+)$/.exec(url.pathname);
    const memberId = match?.[1];
    const parity = bufferParityForTenant(String(tenantId));
    const member = parity.teamMembers.find((item) => item.id === memberId);
    if (!member) {
      sendJson(res, 404, { detail: 'Team member not found.' });
      return;
    }
    member.role = payload.role || member.role;
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, member });
    return;
  }

  if (req.method === 'DELETE' && /^\/social\/team\/members\/[^/]+$/.test(url.pathname)) {
    const match = /^\/social\/team\/members\/([^/]+)$/.exec(url.pathname);
    const memberId = match?.[1];
    const parity = bufferParityForTenant(String(tenantId));
    parity.teamMembers = parity.teamMembers.filter((item) => item.id !== memberId);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, deleted: true, member_id: memberId });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/social/start-page') {
    const parity = bufferParityForTenant(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      start_page: parity.startPage,
      public_url: `https://start.page/${parity.startPage.slug}`,
    });
    return;
  }

  if (req.method === 'PUT' && url.pathname === '/social/start-page') {
    const payload = await readJson(req).catch(() => ({}));
    const parity = bufferParityForTenant(String(tenantId));
    parity.startPage = {
      ...parity.startPage,
      ...payload,
      links: Array.isArray(payload.links) ? payload.links : parity.startPage.links,
      social_links: Array.isArray(payload.social_links) ? payload.social_links : parity.startPage.social_links,
    };
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      start_page: parity.startPage,
      public_url: `https://start.page/${parity.startPage.slug}`,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/reviews/ingest') {
    const payload = await readJson(req).catch(() => ({}));
    const rating = Number(payload.rating || 3);
    let sentiment = 'positive';
    if (rating <= 2) {
      sentiment = 'negative';
    } else if (rating === 3) {
      sentiment = 'neutral';
    }
    const review = {
      id: state.reviews.length + 1,
      tenant_id: String(tenantId),
      platform: payload.platform || 'google',
      reviewer: payload.reviewer || 'Customer',
      rating,
      text: payload.text || 'Mock review',
      category: payload.category || 'general',
      sentiment,
      responded: false,
      response: null,
      response_at: null,
      created_at: new Date().toISOString(),
      source: 'mock-api',
      persistence: 'memory-fallback',
    };
    state.reviews.push(review);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, review });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/reviews') {
    const reviews = state.reviews
      .filter((item) => item.tenant_id === String(tenantId))
      .slice()
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: reviews.length, reviews });
    return;
  }

  if (req.method === 'POST' && /^\/reviews\/\d+\/respond$/.test(url.pathname)) {
    const payload = await readJson(req).catch(() => ({}));
    const match = /^\/reviews\/(\d+)\/respond$/.exec(url.pathname);
    const reviewId = Number(match?.[1]);
    const review = state.reviews.find((item) => item.id === reviewId && item.tenant_id === String(tenantId));
    if (!review) {
      sendJson(res, 404, { detail: 'Review not found.' });
      return;
    }
    review.responded = true;
    review.response = payload.response || 'Thank you for your feedback.';
    review.response_at = new Date().toISOString();
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, review });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/reviews/summary') {
    const reviews = state.reviews.filter((item) => item.tenant_id === String(tenantId));
    const sentiment = { positive: 0, neutral: 0, negative: 0 };
    const platforms = {};
    let ratingTotal = 0;
    let responded = 0;
    for (const review of reviews) {
      sentiment[review.sentiment] = (sentiment[review.sentiment] || 0) + 1;
      platforms[review.platform] = (platforms[review.platform] || 0) + 1;
      ratingTotal += Number(review.rating || 0);
      responded += review.responded ? 1 : 0;
    }
    const avgRating = reviews.length ? Number((ratingTotal / reviews.length).toFixed(2)) : 0;
    const reputationScore = reviews.length
      ? Math.max(0, Math.min(100, Math.round((avgRating / 5) * 70 + (responded / reviews.length) * 30)))
      : 0;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      summary: {
        total_reviews: reviews.length,
        avg_rating: avgRating,
        reputation_score: reputationScore,
        responded_ratio: reviews.length ? Number((responded / reviews.length).toFixed(4)) : 0,
        sentiment,
        platforms,
      },
      reviews,
    });
    return;
  }

  // VSE mock endpoints (used by deep tests + VSE UI)
  if (req.method === 'GET' && url.pathname === '/vse/engines') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      engines: Array.from({ length: 12 }).map((_, i) => ({
        id: `VSE-${i + 1}`,
        name: `Engine ${i + 1}`,
      })),
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/command-centre') {
    const tenant = String(tenantId);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenant,
      command_centre: {
        active_viral_events: state.vseDetonations.filter((d) => d.tenant_id === tenant && d.status === 'executed')
          .length,
        active_swarms: state.vseSwarms.filter((s) => s.tenant_id === tenant && s.status === 'active').length,
        momentum_monitoring: state.vseMomentum.filter((m) => m.tenant_id === tenant && m.status === 'monitoring')
          .length,
        live_trend_alerts: 5,
        total_detonations: state.vseDetonations.filter((d) => d.tenant_id === tenant).length,
        viral_vault_entries: state.vseVault.filter((v) => v.tenant_id === tenant).length,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/triggers/library') {
    const triggers = Array.from({ length: 247 }).map((_, i) => ({
      id: i + 1,
      name: i < 20 ? `Core Trigger ${i + 1}` : `Trigger-${i + 1}`,
      category: ['cognitive', 'emotional', 'social', 'moral'][i % 4],
      share_lift: Number((1.5 + (i % 30) * 0.1).toFixed(2)),
    }));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, total: 247, triggers });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/triggers/analyze') {
    const payload = await readJson(req).catch(() => ({}));
    const text = String(payload.content || '').toLowerCase();
    const activeCount = Math.max(1, Math.min(8, Math.floor(text.split(' ').length / 8)));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      analysis: {
        id: `trig-${Date.now()}`,
        active_trigger_count: activeCount,
        viral_probability_score: 80 + activeCount,
        analyzed_at: new Date().toISOString(),
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/brief') {
    const payload = await readJson(req).catch(() => ({}));
    const brief = {
      id: `brief-${Date.now()}`,
      tenant_id: String(tenantId),
      objective: payload.objective || 'reach',
      audience: payload.audience || 'general',
      platforms_prioritised: payload.platforms || ['linkedin'],
      created_at: new Date().toISOString(),
    };
    state.vseBriefs.push(brief);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, brief });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/algorithm/optimize') {
    const payload = await readJson(req).catch(() => ({}));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      optimisation: {
        id: `algo-${Date.now()}`,
        platform: payload.platform || 'linkedin',
        format_compliance_score: 92,
        generated_at: new Date().toISOString(),
      },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/algorithm/models') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      models: [
        { platform: 'linkedin', top_signals: ['comments', 'shares', 'dwell_time'] },
        { platform: 'instagram', top_signals: ['saves', 'shares', 'comments'] },
        { platform: 'tiktok', top_signals: ['completion_rate', 'replay', 'share'] },
      ],
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/algorithm/updates') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      updates: [{ platform: 'linkedin', change: 'Dwell-time signal upweighted', confidence: 0.94 }],
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/network/map') {
    const payload = await readJson(req).catch(() => ({}));
    const map = {
      id: `nmap-${Date.now()}`,
      tenant_id: String(tenantId),
      audience_segment: payload.audience_segment || 'general',
      node_count: 12000,
      superconnectors: [{ node_id: 'sc-1', centrality_score: 0.97 }],
      created_at: new Date().toISOString(),
    };
    state.vseNetworkMaps.push(map);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, map });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/network/superconnectors') {
    const latest = state.vseNetworkMaps.findLast((m) => m.tenant_id === String(tenantId));
    if (!latest) {
      sendJson(res, 404, { detail: 'No network map found. Run POST /vse/network/map first.' });
      return;
    }
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      map_id: latest.id,
      superconnectors: latest.superconnectors,
    });
    return;
  }

  if (req.method === 'POST' && (url.pathname === '/vse/simulate' || url.pathname === '/vse/network/cascade-simulate')) {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      simulation: {
        id: `sim-${Date.now()}`,
        monte_carlo_runs: 10000,
        cascade_stages: {
          stage_1_seeded_distribution: { reach_p50: 2400 },
          stage_2_discovery_feed: { reach_p50: 7600 },
          stage_3_trending: { reach_p50: 13200 },
        },
        simulated_at: new Date().toISOString(),
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/detonation/plan') {
    const payload = await readJson(req).catch(() => ({}));
    const detonation = {
      id: `det-${Date.now()}`,
      tenant_id: String(tenantId),
      status: 'planned',
      platforms: payload.platforms || ['linkedin'],
      created_at: new Date().toISOString(),
    };
    state.vseDetonations.push(detonation);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, detonation });
    return;
  }

  if (req.method === 'POST' && /^\/vse\/detonation\/[^/]+\/execute$/.test(url.pathname)) {
    const match = /^\/vse\/detonation\/([^/]+)\/execute$/.exec(url.pathname);
    const detonationId = match ? match[1] : '';
    const detonation = state.vseDetonations.find((d) => d.id === detonationId && d.tenant_id === String(tenantId));
    if (!detonation) {
      sendJson(res, 404, { detail: 'Detonation plan not found.' });
      return;
    }
    detonation.status = 'executed';
    detonation.executed_at = new Date().toISOString();
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      detonation,
      viral_event: { id: `ve-${Date.now()}`, status: 'active', detonation_id: detonationId },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/detonation') {
    const detonations = state.vseDetonations.filter((d) => d.tenant_id === String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: detonations.length, detonations });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/detonation/history') {
    const detonations = state.vseDetonations.filter((d) => d.tenant_id === String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: detonations.length, detonations });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/swarm/compose') {
    const payload = await readJson(req).catch(() => ({}));
    const swarm = {
      id: `swarm-${Date.now()}`,
      tenant_id: String(tenantId),
      niche: payload.niche || 'general',
      swarm_size: Number(payload.swarm_size || 50),
      status: 'composed',
      created_at: new Date().toISOString(),
    };
    state.vseSwarms.push(swarm);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, swarm });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/swarm/activate') {
    const payload = await readJson(req).catch(() => ({}));
    const swarm = state.vseSwarms.find((s) => s.id === payload.swarm_id && s.tenant_id === String(tenantId));
    if (!swarm) {
      sendJson(res, 404, { detail: 'Swarm not found.' });
      return;
    }
    swarm.status = 'active';
    swarm.activated_at = new Date().toISOString();
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, swarm });
    return;
  }

  if (req.method === 'GET' && /^\/vse\/swarm\/[^/]+\/status$/.test(url.pathname)) {
    const match = /^\/vse\/swarm\/([^/]+)\/status$/.exec(url.pathname);
    const swarmId = match ? match[1] : '';
    const swarm = state.vseSwarms.find((s) => s.id === swarmId && s.tenant_id === String(tenantId));
    if (!swarm) {
      sendJson(res, 404, { detail: 'Swarm not found.' });
      return;
    }
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      swarm_id: swarmId,
      swarm_status: swarm.status,
      active_influencers: swarm.status === 'active' ? Number(swarm.swarm_size || 0) : 0,
      total_influencers: Number(swarm.swarm_size || 0),
      activation_ratio: swarm.status === 'active' ? 1 : 0,
      updated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/swarm/database/stats') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      database: { total_influencers: 12000000, platforms_covered: 25 },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/momentum/start') {
    const payload = await readJson(req).catch(() => ({}));
    const event = {
      id: `mom-${Date.now()}`,
      tenant_id: String(tenantId),
      post_summary: payload.post_summary || '',
      status: 'monitoring',
      started_at: new Date().toISOString(),
    };
    state.vseMomentum.push(event);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, momentum_event: event });
    return;
  }

  if (req.method === 'GET' && /^\/vse\/momentum\/[^/]+$/.test(url.pathname)) {
    const match = /^\/vse\/momentum\/([^/]+)$/.exec(url.pathname);
    const eventId = match ? match[1] : '';
    const event = state.vseMomentum.find((m) => m.id === eventId && m.tenant_id === String(tenantId));
    if (!event) {
      sendJson(res, 404, { detail: 'Momentum event not found.' });
      return;
    }
    event.current_velocity = 88;
    event.half_life_hours = 5.2;
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, momentum_event: event });
    return;
  }

  if (req.method === 'POST' && /^\/vse\/momentum\/[^/]+\/inject$/.test(url.pathname)) {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      injection: {
        type: 'comment_campaign',
        expected_reach_lift: '2.2x',
        fired_at: new Date().toISOString(),
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/content/generate') {
    const payload = await readJson(req).catch(() => ({}));
    const avoidDuplicates = Boolean(payload.avoid_duplicates);
    const uniquenessBoost = String(payload.uniqueness_boost || 'medium');
    const fingerprintSeed = `${payload.topic || 'topic'}::${payload.platform || 'linkedin'}::${payload.format || 'post'}`;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      content: {
        id: `vcf-${Date.now()}`,
        topic: payload.topic || 'topic',
        viral_probability_score: 90,
        generated_at: new Date().toISOString(),
      },
      dedupe: avoidDuplicates
        ? {
            uniqueness_boost: uniquenessBoost,
            is_duplicate: false,
            fingerprint: Buffer.from(fingerprintSeed).toString('base64').slice(0, 24),
          }
        : undefined,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/content/generate-variants') {
    const payload = await readJson(req).catch(() => ({}));
    const requested = Number(payload.count || 3);
    const count = Math.max(1, Math.min(10, Number.isFinite(requested) ? requested : 3));
    const topic = String(payload.topic || 'topic');
    const platform = String(payload.platform || 'linkedin');
    const avoidDuplicates = payload.avoid_duplicates !== false;
    const variants = Array.from({ length: count }).map((_, idx) => ({
      id: `var-${Date.now()}-${idx + 1}`,
      content_id: `content-${idx + 1}`,
      topic,
      platform,
      hook: `Variant hook ${idx + 1} for ${topic}`,
      body: `This is variant ${idx + 1} optimised for ${platform}.`,
      vps_score: 90 - idx,
      viral_probability_score: 90 - idx,
    }));

    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      all_variants: variants,
      variants,
      primary_variant: variants[0],
      batch_dedupe_applied: avoidDuplicates,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/content/hooks') {
    const hooks = Array.from({ length: 50 }).map((_, i) => ({
      rank: i + 1,
      text: `Hook variant ${i + 1}`,
      predicted_score: 95 - i * 0.6,
    }));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      hooks_generated: 50,
      top_hook: hooks[0],
      all_hooks: hooks,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/content/score') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      viral_probability_score: 89,
      passes_threshold: true,
      scored_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/emotion/analyze') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      analysis: {
        id: `emo-${Date.now()}`,
        dominant_emotion: 'curiosity',
        contagion_velocity: '2.1x',
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/emotion/engineer') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      target_vector: 'inspiration',
      engineered_score: 0.82,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/emotion/audience-state') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      dominant_emotions: [{ emotion: 'curiosity', prevalence: 0.34 }],
      sampled_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/trends/live') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      trends: [
        { id: 1, topic: 'AI regulation', velocity: 'breaking', relevance: 0.92 },
        { id: 2, topic: 'Creator economy', velocity: 'building', relevance: 0.87 },
      ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/trends/hijack') {
    const payload = await readJson(req).catch(() => ({}));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      hijack: {
        id: `thj-${Date.now()}`,
        trend_id: Number(payload.trend_id || 1),
        authenticity_score: 93,
        status: 'ready_to_publish',
      },
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/trends/alerts') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      active_trend_alerts: 5,
      trends: [{ id: 1, topic: 'AI regulation' }],
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/paid/assess') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      assessment: {
        id: `assess-${Date.now()}`,
        viral_threshold_passed: true,
        expected_roas_range: '15-40x vs standard boosting',
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/paid/amplify') {
    const payload = await readJson(req).catch(() => ({}));
    const event = {
      id: `paid-${Date.now()}`,
      tenant_id: String(tenantId),
      assessment_id: payload.assessment_id || 'assess-missing',
      status: 'active',
      expected_roas: '22x',
      activated_at: new Date().toISOString(),
    };
    state.vsePaidEvents.push(event);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, paid_event: event });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/paid/events') {
    const events = state.vsePaidEvents.filter((e) => e.tenant_id === String(tenantId));
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, count: events.length, events });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/dark-social/seed') {
    const seed = {
      id: `dark-${Date.now()}`,
      tenant_id: String(tenantId),
      seeded_at: new Date().toISOString(),
    };
    state.vseDarkSeeds.push(seed);
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, seed });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/dark-social/measurement') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      seeds_active: state.vseDarkSeeds.filter((s) => s.tenant_id === String(tenantId)).length,
      dark_social_share_of_total: '70-82%',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/dark-social/attribution') {
    const payload = await readJson(req).catch(() => ({}));
    const campaignId = String(payload.campaign_id || '').trim();
    if (!campaignId) {
      sendJson(res, 422, { detail: 'campaign_id cannot be empty.' });
      return;
    }

    const conversions = Number(payload.conversions || 0);
    const conversionValue = Number(payload.conversion_value || 0);
    if (conversions === 0 && conversionValue > 0) {
      sendJson(res, 422, { detail: 'conversion_value cannot be positive when conversions is 0.' });
      return;
    }

    const rawTouchpoints = Array.isArray(payload.touchpoints) ? payload.touchpoints : [];
    const sanitized = [
      ...new Set(
        rawTouchpoints
          .map((tp) =>
            String(tp || '')
              .trim()
              .toLowerCase()
          )
          .filter((tp) => tp.length > 0)
      ),
    ];
    const notes = [];
    const touchpoints = sanitized.length ? sanitized : ['whatsapp_share', 'slack_thread', 'private_group'];
    if (!sanitized.length) {
      notes.push('No valid touchpoints supplied; applied default dark-social touchpoint set.');
    }

    const denominator = Math.max(1, touchpoints.length);
    let confidence = 'low';
    if (conversions >= 25) confidence = 'high';
    else if (conversions >= 5) confidence = 'medium';

    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      campaign_id: campaignId,
      model: 'position_based_dark_social_proxy',
      conversions,
      conversion_value: conversionValue,
      value_per_conversion: conversions ? Number((conversionValue / conversions).toFixed(2)) : 0,
      attribution_confidence: confidence,
      normalised_touchpoints_count: touchpoints.length,
      notes,
      attribution: touchpoints.map((tp) => ({
        touchpoint: tp,
        weight: Number((1 / denominator).toFixed(3)),
        attributed_conversions: Number((conversions / denominator).toFixed(2)),
      })),
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/vse/immortalise') {
    const payload = await readJson(req).catch(() => ({}));
    const record = {
      id: `imm-${Date.now()}`,
      tenant_id: String(tenantId),
      viral_event_id: payload.viral_event_id || 'event',
      asset_count: 8,
      created_at: new Date().toISOString(),
    };
    state.vseImmortal.push(record);
    state.vseVault.push({
      id: `vault-${Date.now()}`,
      tenant_id: String(tenantId),
      immortal_id: record.id,
      archived_at: new Date().toISOString(),
    });
    sendJson(res, 200, { status: 'ok', tenant_id: tenantId, immortal_record: record });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/vse/immortalise/vault') {
    const vault = state.vseVault.filter((v) => v.tenant_id === String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      vault_entries: vault.length,
      vault,
    });
    return;
  }

  if (req.method === 'GET' && /^\/vse\/immortalise\/[^/]+\/assets$/.test(url.pathname)) {
    const match = /^\/vse\/immortalise\/([^/]+)\/assets$/.exec(url.pathname);
    const immortalId = match ? match[1] : '';
    const record = state.vseImmortal.find((item) => item.id === immortalId && item.tenant_id === String(tenantId));
    if (!record) {
      sendJson(res, 404, { detail: 'Immortalisation record not found.' });
      return;
    }
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      immortal_record: {
        ...record,
        assets_created: [
          { type: 'seo_pillar_page', status: 'created' },
          { type: 'viral_vault_archive', status: 'archived' },
        ],
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/auth/totp/setup') {
    state.totpSecret = 'JBSWY3DPEHPK3PXP';
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      result: {
        secret: state.totpSecret,
        issuer: 'Nuxtron',
        account_name: `${tenantId}@nuxtron.io`,
        otpauth_url: `otpauth://totp/Nuxtron:${tenantId}@nuxtron.io?secret=${state.totpSecret}&issuer=Nuxtron&algorithm=SHA1&digits=6&period=30`,
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/auth/totp/verify') {
    const payload = await readJson(req).catch(() => ({}));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      valid: payload.secret === state.totpSecret,
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/auth/jwt/issue') {
    state.jwtToken = 'mock.header.signature';
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      result: {
        token: state.jwtToken,
        expires_at: '2026-04-17T13:00:00+00:00',
        jti: 'mock-jti-1234567890',
        signing_source: 'fastapi-api-key-fallback',
      },
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/auth/jwt/verify') {
    const payload = await readJson(req).catch(() => ({}));
    const valid = payload.token === state.jwtToken;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      valid,
      claims: valid
        ? {
            sub: `${tenantId}-studio-user`,
            tenant_id: tenantId,
            roles: ['admin', 'editor'],
            source: 'studio',
          }
        : null,
      error: valid ? null : 'Invalid token.',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/tenants') {
    const payload = await readJson(req).catch(() => ({}));
    state.tenant = {
      tenant_id: tenantId,
      display_name: payload.display_name || `${tenantId} Workspace`,
      plan: payload.plan || 'growth',
      status: payload.status || 'active',
      settings: payload.settings || {},
      created_at: '2026-04-17T12:00:00+00:00',
      updated_at: '2026-04-17T12:00:00+00:00',
      persistence: 'memory-fallback',
      encryption: 'application-level',
    };
    sendJson(res, 200, {
      status: 'ok',
      tenant: state.tenant,
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/tenants') {
    const items = state.tenant ? [state.tenant] : [];
    sendJson(res, 200, {
      status: 'ok',
      count: items.length,
      items,
    });
    return;
  }

  if (req.method === 'PATCH' && url.pathname === `/tenants/${tenantId}`) {
    const payload = await readJson(req).catch(() => ({}));
    state.tenant = {
      ...(state.tenant || {
        tenant_id: tenantId,
        created_at: '2026-04-17T12:00:00+00:00',
        persistence: 'memory-fallback',
        encryption: 'application-level',
      }),
      display_name: payload.display_name || `${tenantId} Workspace Updated`,
      plan: payload.plan || 'pro',
      status: state.tenant?.status || 'active',
      settings: payload.settings || { region: 'eu-west-1', source: 'studio-updated' },
      updated_at: '2026-04-17T12:15:00+00:00',
    };
    sendJson(res, 200, {
      status: 'ok',
      tenant: state.tenant,
    });
    return;
  }

  if (req.method === 'DELETE' && url.pathname === `/tenants/${tenantId}`) {
    state.tenant = null;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      deleted: true,
      persistence: 'memory-fallback',
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/cost-savings-calculator') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      output: {
        total_pages_in_scope: 75000,
        manual_monthly_hours: 8750,
        automated_monthly_hours_saved: 7525,
        monthly_labor_cost_saved_usd: 677250,
        net_monthly_savings_usd: 676451,
        annual_net_savings_usd: 8117412,
        payback_days: 0.04,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/ai-search-impact-calculator') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      output: {
        incremental_clicks_monthly: 4800,
        incremental_conversions_monthly: 134,
        incremental_revenue_monthly_usd: 18760,
        incremental_revenue_annual_usd: 225120,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/vendors') {
    const vendors = [
      {
        key: 'cloudflare',
        display_name: 'Cloudflare',
        category: 'WAF / bot allowlisting',
        configured: true,
        mode: 'api',
      },
      {
        key: 'openai',
        display_name: 'OpenAI (GPTBot visibility target)',
        category: 'AI search crawler ecosystem',
        configured: true,
        mode: 'crawler-target',
      },
      {
        key: 'anthropic',
        display_name: 'Anthropic (ClaudeBot visibility target)',
        category: 'AI search crawler ecosystem',
        configured: true,
        mode: 'crawler-target',
      },
      {
        key: 'perplexity',
        display_name: 'Perplexity',
        category: 'AI search crawler ecosystem',
        configured: true,
        mode: 'crawler-target',
      },
      {
        key: 'google',
        display_name: 'Google / Google-Extended',
        category: 'Search + AI overview crawler ecosystem',
        configured: true,
        mode: 'crawler-target',
      },
      { key: 'ollama', display_name: 'Ollama', category: 'Self-hosted AI inference', configured: true, mode: 'api' },
      { key: 'upstash', display_name: 'Upstash Redis', category: 'Distributed cache', configured: false, mode: 'api' },
      { key: 'sentry', display_name: 'Sentry', category: 'Error monitoring', configured: true, mode: 'sdk' },
      { key: 'posthog', display_name: 'PostHog', category: 'Product analytics', configured: true, mode: 'api' },
    ];
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      total: vendors.length,
      configured: vendors.filter((item) => item.configured).length,
      vendors,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/vendors/report/export') {
    const exportRows = [
      {
        source: 'search_everywhere',
        vendor: 'OpenAI',
        category: 'ai_search',
        integration: 'gptbot_visibility',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'search_everywhere',
        vendor: 'Anthropic',
        category: 'ai_search',
        integration: 'claudebot_visibility',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'search_everywhere',
        vendor: 'Perplexity',
        category: 'ai_search',
        integration: 'answer_engine_visibility',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: false,
      },
      {
        source: 'ai_crawler',
        vendor: 'Cloudflare',
        category: 'edge_delivery',
        integration: 'bot_allowlisting',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'cms',
        vendor: 'WordPress',
        category: 'cms',
        integration: 'content_sync',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: true,
      },
      {
        source: 'platform_integrations',
        vendor: 'X',
        category: 'social_distribution',
        integration: 'oauth_connection',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: false,
      },
      {
        source: 'cms',
        vendor: 'PostHog',
        category: 'analytics',
        integration: 'attribution_tracking',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
    ];
    if (url.searchParams.get('format') === 'csv') {
      const headers = [
        'source',
        'vendor',
        'category',
        'integration',
        'configured_units',
        'total_units',
        'runtime_dependency',
      ];
      const lines = [headers.join(',')];
      for (const row of exportRows) {
        lines.push(headers.map((key) => `"${String(row[key] ?? '').replace(/"/g, '""')}"`).join(','));
      }
      sendJson(res, 200, {
        status: 'ok',
        tenant_id: tenantId,
        format: 'csv',
        count: exportRows.length,
        filename: `vendor-inventory-report-${tenantId}.csv`,
        csv: lines.join('\n'),
        generated_at: new Date().toISOString(),
      });
      return;
    }

    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      format: 'json',
      count: exportRows.length,
      filename: `vendor-inventory-report-${tenantId}.json`,
      json: exportRows,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/vendors/report') {
    const exportRows = [
      {
        source: 'search_everywhere',
        vendor: 'OpenAI',
        category: 'ai_search',
        integration: 'gptbot_visibility',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'search_everywhere',
        vendor: 'Anthropic',
        category: 'ai_search',
        integration: 'claudebot_visibility',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'search_everywhere',
        vendor: 'Perplexity',
        category: 'ai_search',
        integration: 'answer_engine_visibility',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: false,
      },
      {
        source: 'ai_crawler',
        vendor: 'Cloudflare',
        category: 'edge_delivery',
        integration: 'bot_allowlisting',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
      {
        source: 'cms',
        vendor: 'WordPress',
        category: 'cms',
        integration: 'content_sync',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: true,
      },
      {
        source: 'platform_integrations',
        vendor: 'X',
        category: 'social_distribution',
        integration: 'oauth_connection',
        configured_units: 1,
        total_units: 2,
        runtime_dependency: false,
      },
      {
        source: 'cms',
        vendor: 'PostHog',
        category: 'analytics',
        integration: 'attribution_tracking',
        configured_units: 1,
        total_units: 1,
        runtime_dependency: true,
      },
    ];
    if (url.searchParams.get('format') === 'csv') {
      const headers = [
        'source',
        'vendor',
        'category',
        'integration',
        'configured_units',
        'total_units',
        'runtime_dependency',
      ];
      const lines = [headers.join(',')];
      for (const row of exportRows) {
        lines.push(headers.map((key) => `"${String(row[key] ?? '').replace(/"/g, '""')}"`).join(','));
      }
      sendJson(res, 200, {
        status: 'ok',
        tenant_id: tenantId,
        format: 'csv',
        count: exportRows.length,
        filename: `vendor-inventory-report-${tenantId}.csv`,
        csv: lines.join('\n'),
        generated_at: new Date().toISOString(),
      });
      return;
    }

    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      summary: {
        domains: 4,
        vendors: 7,
        categories: 5,
      },
      domain_chart: [
        { domain: 'search_everywhere', configured_units: 3, total_units: 4, coverage_pct: 75 },
        { domain: 'ai_crawler', configured_units: 2, total_units: 2, coverage_pct: 100 },
        { domain: 'cms', configured_units: 2, total_units: 3, coverage_pct: 66.7 },
        { domain: 'platform_integrations', configured_units: 1, total_units: 2, coverage_pct: 50 },
      ],
      category_chart: [
        { category: 'ai_search', vendors: 3, configured_units: 3, total_units: 4 },
        { category: 'edge_delivery', vendors: 1, configured_units: 1, total_units: 1 },
        { category: 'cms', vendors: 1, configured_units: 1, total_units: 2 },
        { category: 'social_distribution', vendors: 1, configured_units: 1, total_units: 2 },
        { category: 'analytics', vendors: 1, configured_units: 1, total_units: 1 },
      ],
      vendor_chart: [
        {
          source: 'search_everywhere',
          vendor: 'OpenAI',
          category: 'ai_search',
          integration: 'gptbot_visibility',
          configured_units: 1,
          total_units: 1,
          runtime_dependency: true,
        },
        {
          source: 'search_everywhere',
          vendor: 'Anthropic',
          category: 'ai_search',
          integration: 'claudebot_visibility',
          configured_units: 1,
          total_units: 1,
          runtime_dependency: true,
        },
        {
          source: 'search_everywhere',
          vendor: 'Perplexity',
          category: 'ai_search',
          integration: 'answer_engine_visibility',
          configured_units: 1,
          total_units: 2,
          runtime_dependency: false,
        },
        {
          source: 'ai_crawler',
          vendor: 'Cloudflare',
          category: 'edge_delivery',
          integration: 'bot_allowlisting',
          configured_units: 1,
          total_units: 1,
          runtime_dependency: true,
        },
        {
          source: 'cms',
          vendor: 'WordPress',
          category: 'cms',
          integration: 'content_sync',
          configured_units: 1,
          total_units: 2,
          runtime_dependency: true,
        },
        {
          source: 'platform_integrations',
          vendor: 'X',
          category: 'social_distribution',
          integration: 'oauth_connection',
          configured_units: 1,
          total_units: 2,
          runtime_dependency: false,
        },
        {
          source: 'cms',
          vendor: 'PostHog',
          category: 'analytics',
          integration: 'attribution_tracking',
          configured_units: 1,
          total_units: 1,
          runtime_dependency: true,
        },
      ],
      export_rows: exportRows,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/readiness') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      readiness: {
        configured_integrations: 8,
        total_integrations: 9,
        configured_pct: 88.9,
        grade: 'A',
        production_ready: true,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/parity-audit') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      yext_parity_chart: [
        { key: 'listings', product: 'Listings', implemented: true, e2e_verified: true, integration_ready: wired },
        { key: 'reviews', product: 'Reviews', implemented: true, e2e_verified: true, integration_ready: wired },
        { key: 'pages', product: 'Pages', implemented: true, e2e_verified: true, integration_ready: wired },
        { key: 'search', product: 'Search', implemented: true, e2e_verified: true, integration_ready: wired },
        { key: 'chat', product: 'Chat', implemented: true, e2e_verified: true, integration_ready: wired },
        {
          key: 'knowledge-graph',
          product: 'Knowledge Graph',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        { key: 'analytics', product: 'Analytics', implemented: true, e2e_verified: true, integration_ready: wired },
      ],
      summary: {
        modules_total: 7,
        modules_implemented: 7,
        modules_e2e_verified: 7,
        implementation_pct: 100.0,
        e2e_verified_pct: 100.0,
        integration_configured_pct: wired ? 100.0 : 0.0,
        products_total: 7,
        premium_features_total: 35,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/production-gate') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      gate: {
        passed: wired,
        blockers: wired ? [] : ['Provider wiring has not been applied for the Yext command center tenant.'],
        implementation_ok: true,
        e2e_ok: true,
        integration_ok: wired,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/yext/wiring/apply') {
    state.yextWiredTenants.add(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      checklist_summary: {
        configured: 12,
        total: 12,
        configured_pct: 100,
      },
      gate: {
        passed: true,
        blockers: [],
        implementation_ok: true,
        e2e_ok: true,
        integration_ok: true,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/vendors') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    const vendorChart = [
      { vendor: 'Yext', configured: true },
      { vendor: 'Google Business Profile', configured: wired },
      { vendor: 'Apple Business Connect', configured: wired },
      { vendor: 'Bing Places', configured: wired },
      { vendor: 'Yelp', configured: wired },
      { vendor: 'Tripadvisor', configured: wired },
      { vendor: 'Zendesk', configured: wired },
    ];
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      vendors_total: vendorChart.length,
      vendors_configured: vendorChart.filter((item) => item.configured).length,
      vendor_chart: vendorChart,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/provider-checklist') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    const checklist = [
      { provider: 'Yext', kind: 'core', configured: true, required_missing: [] },
      {
        provider: 'Google Business Profile',
        kind: 'publisher',
        configured: wired,
        required_missing: wired ? [] : ['oauth_client'],
      },
      {
        provider: 'Apple Business Connect',
        kind: 'publisher',
        configured: wired,
        required_missing: wired ? [] : ['publisher_token'],
      },
      { provider: 'Bing Places', kind: 'publisher', configured: wired, required_missing: wired ? [] : ['api_key'] },
      { provider: 'Yelp', kind: 'reviews', configured: wired, required_missing: wired ? [] : ['oauth_client'] },
      { provider: 'Tripadvisor', kind: 'reviews', configured: wired, required_missing: wired ? [] : ['oauth_client'] },
      { provider: 'Zendesk', kind: 'support', configured: wired, required_missing: wired ? [] : ['subdomain'] },
    ];
    const configured = checklist.filter((item) => item.configured).length;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      configured,
      total: checklist.length,
      configured_pct: Math.round((configured / Math.max(checklist.length, 1)) * 1000) / 10,
      checklist,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/preflight') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      configured_pct: wired ? 100 : 14.3,
      missing_provider_steps: wired
        ? []
        : [
            { provider: 'Google Business Profile', priority: 'high', required_missing: ['oauth_client'] },
            { provider: 'Apple Business Connect', priority: 'high', required_missing: ['publisher_token'] },
            { provider: 'Bing Places', priority: 'medium', required_missing: ['api_key'] },
          ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/yext/remediation-bundle') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      remediation_steps: wired
        ? []
        : [
            { provider: 'Google Business Profile', priority: 'high', required_missing: ['oauth_client'] },
            { provider: 'Apple Business Connect', priority: 'high', required_missing: ['publisher_token'] },
            { provider: 'Bing Places', priority: 'medium', required_missing: ['api_key'] },
          ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/yext/assist/chat') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      assist: {
        answer_summary: wired
          ? 'Yext rollout is healthy and production ready for this tenant.'
          : 'Yext rollout is code-complete but still needs provider wiring for production readiness.',
        recommended_actions: wired
          ? ['Rotate publisher credentials quarterly and monitor listing drift alerts.']
          : ['Apply provider wiring and validate publisher authentication before release.'],
        workflow_handoffs: [
          'Listings operations -> publisher network provisioning',
          'Reviews operations -> support escalation and moderation',
          'Experience operations -> pages/search/chat release governance',
        ],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/yext/full-automation') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      run_mode: 'full_automation',
      yext_modules: {
        presence: ['listings sync', 'publisher health', 'duplicate suppression'],
        reputation: ['review response', 'sentiment clustering', 'escalation routing'],
        experience: ['pages publishing', 'search experiences', 'chat deflection'],
        graph: ['entity governance', 'field lineage', 'publisher-ready attributes'],
        operations: ['provider checklist', 'wiring apply', 'production gate', 'verification report'],
      },
      third_parties_and_vendors: [
        { vendor: 'Yext', configured: true },
        { vendor: 'Google Business Profile', configured: wired },
        { vendor: 'Apple Business Connect', configured: wired },
        { vendor: 'Bing Places', configured: wired },
      ],
      how_it_works: [
        'Knowledge Graph data acts as the source of truth for entity and location attributes.',
        'Listings, reviews, pages, search, and chat reuse shared entity context across channels.',
        'Operational workflows route unresolved issues into support and governance queues.',
        'Provider checklist and production gate separate code-complete from integration-ready.',
      ],
      production_gate: {
        passed: wired,
        blockers: wired ? [] : ['Provider wiring has not been applied for the Yext command center tenant.'],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/verification-report') {
    const wired = state.yextWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      verification: {
        slice_ready: wired,
        slice_gate: {
          passed: wired,
          blockers: wired ? [] : ['Provider wiring has not been applied for the Yext command center tenant.'],
        },
        evidence_table: [
          { key: 'listings', implemented: true, e2e_verified: true },
          { key: 'reviews', implemented: true, e2e_verified: true },
          { key: 'pages', implemented: true, e2e_verified: true },
          { key: 'search', implemented: true, e2e_verified: true },
          { key: 'chat', implemented: true, e2e_verified: true },
          { key: 'knowledge-graph', implemented: true, e2e_verified: true },
          { key: 'analytics', implemented: true, e2e_verified: true },
        ],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/projects') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      projects: [{ id: 'yext-proj-1', name: 'Yext Automation Project', primary_domain: 'nuxtron.ai' }],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/yext/projects') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      project: { id: `yext-proj-${Date.now()}`, name: 'Yext Automation Project', primary_domain: 'nuxtron.ai' },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/yext/runs') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      runs: [
        {
          id: 'yext-run-1',
          project_id: 'yext-proj-1',
          strict_probe_status: state.yextWiredTenants.has(String(tenantId)) ? 'passed' : 'pending',
          completed_at: new Date().toISOString(),
        },
      ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && /^\/search-everywhere\/yext\/projects\/[^/]+\/run$/.test(url.pathname)) {
    const match = /^\/search-everywhere\/yext\/projects\/([^/]+)\/run$/.exec(url.pathname);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      run: {
        id: `yext-run-${Date.now()}`,
        project_id: match?.[1] || 'yext-proj-1',
        strict_probe_status: state.yextWiredTenants.has(String(tenantId)) ? 'passed' : 'pending',
        completed_at: new Date().toISOString(),
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/parity-audit') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      brightedge_parity_chart: [
        { key: 'data-cube-x', product: 'Data Cube X', implemented: true, e2e_verified: true, integration_ready: wired },
        {
          key: 'ai-hypercube',
          product: 'AI HyperCube',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        {
          key: 'copilot-autopilot',
          product: 'Copilot and Autopilot',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        {
          key: 'content-workflows',
          product: 'Content Workflows',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        {
          key: 'contentiq-audit',
          product: 'ContentIQ Site Audits',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        {
          key: 'local-presence',
          product: 'Local Presence',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
        {
          key: 'storybuilder-analytics',
          product: 'StoryBuilder Analytics',
          implemented: true,
          e2e_verified: true,
          integration_ready: wired,
        },
      ],
      summary: {
        modules_total: 7,
        modules_implemented: 7,
        modules_e2e_verified: 7,
        implementation_pct: 100.0,
        e2e_verified_pct: 100.0,
        integration_configured_pct: wired ? 100.0 : 0.0,
        products_total: 7,
        premium_features_total: 35,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/production-gate') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      gate: {
        passed: wired,
        blockers: wired ? [] : ['Provider wiring has not been applied for the BrightEdge command center tenant.'],
        implementation_ok: true,
        e2e_ok: true,
        integration_ok: wired,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/brightedge/wiring/apply') {
    state.brightedgeWiredTenants.add(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      checklist_summary: {
        configured: 12,
        total: 12,
        configured_pct: 100,
      },
      gate: {
        passed: true,
        blockers: [],
        implementation_ok: true,
        e2e_ok: true,
        integration_ok: true,
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/vendors') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    const vendorChart = [
      { vendor: 'BrightEdge', configured: true },
      { vendor: 'Google Search Console', configured: wired },
      { vendor: 'GA4', configured: wired },
      { vendor: 'Adobe Analytics', configured: wired },
      { vendor: 'OpenAI', configured: wired },
      { vendor: 'Perplexity', configured: wired },
      { vendor: 'Google Business Profile', configured: wired },
    ];
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      vendors_total: vendorChart.length,
      vendors_configured: vendorChart.filter((item) => item.configured).length,
      vendor_chart: vendorChart,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/provider-checklist') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    const checklist = [
      { provider: 'BrightEdge', kind: 'core', configured: true, required_missing: [] },
      {
        provider: 'Google Search Console',
        kind: 'search',
        configured: wired,
        required_missing: wired ? [] : ['oauth_client'],
      },
      { provider: 'GA4', kind: 'analytics', configured: wired, required_missing: wired ? [] : ['measurement_config'] },
      { provider: 'Adobe Analytics', kind: 'analytics', configured: wired, required_missing: wired ? [] : ['api_key'] },
      { provider: 'OpenAI', kind: 'ai-search', configured: wired, required_missing: wired ? [] : ['api_key'] },
      { provider: 'Perplexity', kind: 'ai-search', configured: wired, required_missing: wired ? [] : ['api_key'] },
      {
        provider: 'Google Business Profile',
        kind: 'local',
        configured: wired,
        required_missing: wired ? [] : ['oauth_client'],
      },
    ];
    const configured = checklist.filter((item) => item.configured).length;
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      configured,
      total: checklist.length,
      configured_pct: Math.round((configured / Math.max(checklist.length, 1)) * 1000) / 10,
      checklist,
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/preflight') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      configured_pct: wired ? 100 : 14.3,
      missing_provider_steps: wired
        ? []
        : [
            { provider: 'Google Search Console', priority: 'high', required_missing: ['oauth_client'] },
            { provider: 'GA4', priority: 'high', required_missing: ['measurement_config'] },
            { provider: 'OpenAI', priority: 'medium', required_missing: ['api_key'] },
          ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/brightedge/remediation-bundle') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      remediation_steps: wired
        ? []
        : [
            { provider: 'Google Search Console', priority: 'high', required_missing: ['oauth_client'] },
            { provider: 'GA4', priority: 'high', required_missing: ['measurement_config'] },
            { provider: 'OpenAI', priority: 'medium', required_missing: ['api_key'] },
          ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/brightedge/assist/chat') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      assist: {
        answer_summary: wired
          ? 'BrightEdge rollout is healthy and production ready for this tenant.'
          : 'BrightEdge rollout is code-complete but still needs provider wiring for production readiness.',
        recommended_actions: wired
          ? ['Rotate analytics and AI credentials quarterly and monitor demand-intelligence drift.']
          : ['Apply provider wiring and validate analytics plus AI visibility connectors before release.'],
        workflow_handoffs: [
          'Demand intelligence -> content optimization squads',
          'Technical audit ops -> web engineering remediation',
          'Executive reporting -> growth and market leadership reviews',
        ],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/brightedge/full-automation') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      run_mode: 'full_automation',
      brightedge_modules: {
        search_intelligence: ['data cube x', 'share of voice', 'trend forecasting'],
        ai_search: ['ai hypercube', 'citation visibility', 'answer sentiment'],
        optimization: ['copilot guidance', 'autopilot execution', 'on-page recommendations'],
        technical: ['contentiq audits', 'crawl diagnostics', 'schema validation'],
        operations: ['provider checklist', 'wiring apply', 'production gate', 'verification report'],
      },
      third_parties_and_vendors: [
        { vendor: 'BrightEdge', configured: true },
        { vendor: 'Google Search Console', configured: wired },
        { vendor: 'OpenAI', configured: wired },
        { vendor: 'Perplexity', configured: wired },
      ],
      how_it_works: [
        'Data Cube X and AI HyperCube prioritize demand opportunities across search and AI surfaces.',
        'Copilot and Autopilot translate opportunities into governed optimization workflows.',
        'Content and technical workflows share a common context for release decisions.',
        'Provider checklist and production gate separate code-complete from integration-ready.',
      ],
      production_gate: {
        passed: wired,
        blockers: wired ? [] : ['Provider wiring has not been applied for the BrightEdge command center tenant.'],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/verification-report') {
    const wired = state.brightedgeWiredTenants.has(String(tenantId));
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      verification: {
        slice_ready: wired,
        slice_gate: {
          passed: wired,
          blockers: wired ? [] : ['Provider wiring has not been applied for the BrightEdge command center tenant.'],
        },
        evidence_table: [
          { key: 'data-cube-x', implemented: true, e2e_verified: true },
          { key: 'ai-hypercube', implemented: true, e2e_verified: true },
          { key: 'copilot-autopilot', implemented: true, e2e_verified: true },
          { key: 'content-workflows', implemented: true, e2e_verified: true },
          { key: 'contentiq-audit', implemented: true, e2e_verified: true },
          { key: 'local-presence', implemented: true, e2e_verified: true },
          { key: 'storybuilder-analytics', implemented: true, e2e_verified: true },
        ],
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/projects') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      projects: [{ id: 'brightedge-proj-1', name: 'BrightEdge Automation Project', primary_domain: 'nuxtron.ai' }],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/search-everywhere/brightedge/projects') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      project: {
        id: `brightedge-proj-${Date.now()}`,
        name: 'BrightEdge Automation Project',
        primary_domain: 'nuxtron.ai',
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/search-everywhere/brightedge/runs') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      runs: [
        {
          id: 'brightedge-run-1',
          project_id: 'brightedge-proj-1',
          strict_probe_status: state.brightedgeWiredTenants.has(String(tenantId)) ? 'passed' : 'pending',
          completed_at: new Date().toISOString(),
        },
      ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'POST' && /^\/search-everywhere\/brightedge\/projects\/[^/]+\/run$/.test(url.pathname)) {
    const match = /^\/search-everywhere\/brightedge\/projects\/([^/]+)\/run$/.exec(url.pathname);
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      run: {
        id: `brightedge-run-${Date.now()}`,
        project_id: match?.[1] || 'brightedge-proj-1',
        strict_probe_status: state.brightedgeWiredTenants.has(String(tenantId)) ? 'passed' : 'pending',
        completed_at: new Date().toISOString(),
      },
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/ai-crawler/dashboard') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      summary: {
        total_hits: 1262,
        ai_crawler_hits: 882,
        ssr_served_hits: 741,
        blocked_hits: 18,
        avg_render_time_ms: 142.6,
        visibility_score: 84.0,
        sites_registered: 2,
        sites_with_snippet: 2,
      },
      top_crawlers: [
        { name: 'GPTBot', hits: 342 },
        { name: 'ClaudeBot', hits: 261 },
        { name: 'PerplexityBot', hits: 176 },
      ],
      top_pages: [
        { url: 'https://example.com/pricing', hits: 214 },
        { url: 'https://example.com/features', hits: 178 },
      ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/ai-crawler/sites') {
    sendJson(res, 200, {
      status: 'ok',
      tenant_id: tenantId,
      count: 2,
      sites: [
        {
          id: 'site-1',
          domain: 'example.com',
          snippet_installed: true,
          ssr_enabled: true,
          ai_crawlers_detected_total: 521,
        },
        {
          id: 'site-2',
          domain: 'shop.example.com',
          snippet_installed: true,
          ssr_enabled: true,
          ai_crawlers_detected_total: 361,
        },
      ],
      generated_at: new Date().toISOString(),
    });
    return;
  }

  sendText(res, 404, 'not found');
});

server.listen(port, '127.0.0.1', () => {
  process.stdout.write(`Mock FastAPI server listening on http://127.0.0.1:${port}\n`);
});

process.on('uncaughtException', (error) => {
  process.stderr.write(`Mock FastAPI uncaught exception: ${String(error)}\n`);
});

process.on('unhandledRejection', (reason) => {
  process.stderr.write(`Mock FastAPI unhandled rejection: ${String(reason)}\n`);
});
