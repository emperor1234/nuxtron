/**
 * Handler factory for Nuxtron Studio API operations.
 * Generates bound async handlers from endpoint configs.
 * Centralized error handling and state management.
 */

import { useStudioStore } from './state';
import { STUDIO_ENDPOINTS, type EndpointDemoConfig } from './endpoints';

const proxyBaseUrl = '/api/fastapi';

type AnyObject = Record<string, unknown>;

/**
 * Parse JSON response body, throwing on invalid JSON or error responses.
 */
async function parseJsonBody(res: Response): Promise<AnyObject | null> {
  const bodyText = await res.text();
  if (!bodyText) {
    return null;
  }

  try {
    return JSON.parse(bodyText) as AnyObject;
  } catch {
    if (!res.ok) {
      throw new Error(`Request failed: ${res.status}`);
    }
    throw new Error('Server returned an invalid JSON response.');
  }
}

/**
 * Fetch JSON from proxy with common headers.
 */
async function fetchJson(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  payload: AnyObject | null,
  tenantId: string
): Promise<AnyObject | null> {
  const url = `${proxyBaseUrl}${path}`;
  const headers: Record<string, string> = {
    'X-Tenant-Id': tenantId,
  };

  if (method !== 'GET' && method !== 'DELETE') {
    headers['Content-Type'] = 'application/json';
  }

  const options: RequestInit = {
    method,
    headers,
  };

  if (payload) {
    options.body = JSON.stringify(payload);
  }

  const res = await fetch(url, options);
  const data = await parseJsonBody(res);

  if (!res.ok) {
    throw new Error((data?.detail as string) || `Request failed: ${res.status}`);
  }

  return data ?? {};
}

/**
 * Special handler for multi-endpoint operations like listening alerts sweep.
 */
async function runListeningAlertSweep(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  // Step 1: Create alert rule
  await fetchJson(
    'POST',
    '/social/listening/rules',
    {
      name: 'High engagement negative mentions',
      query: 'nuxtron',
      platform: 'x',
      min_engagement: 50,
      negative_only: true,
    },
    tenantId
  );

  // Step 2: Ingest high-risk mention
  await fetchJson(
    'POST',
    '/social/listening/ingest',
    {
      platform: 'x',
      query: 'nuxtron',
      author_handle: '@risk_watch',
      text: 'Product outage discussion is spreading and users are unhappy.',
      sentiment: 'negative',
      engagement_count: 120,
    },
    tenantId
  );

  // Step 3: Fetch all aggregates in parallel
  const [summary, alerts, clusters] = await Promise.all([
    fetchJson('GET', '/social/listening/summary', null, tenantId),
    fetchJson('GET', '/social/listening/alerts', null, tenantId),
    fetchJson('GET', '/social/listening/clusters', null, tenantId),
  ]);

  store.setMultipleOutputs({
    listening: summary,
    listeningAlerts: alerts,
    listeningClusters: clusters,
  });
}

/**
 * Special handler for reviews operations with multi-step flow.
 */
async function runReviewOpsDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  // Step 1: Ingest a review
  const ingest = (await fetchJson(
    'POST',
    '/reviews/ingest',
    {
      platform: 'google',
      reviewer: 'Taylor',
      rating: 2,
      text: 'Great vision but onboarding docs were confusing and support was delayed.',
      category: 'onboarding',
    },
    tenantId
  )) as { review?: { id?: number } };

  const reviewId = ingest.review?.id;
  if (!reviewId) {
    throw new Error('Review id missing from ingest response.');
  }

  // Step 2: Respond to review
  const response = await fetchJson(
    'POST',
    `/reviews/${reviewId}/respond`,
    {
      response: 'Thanks for the feedback. We have updated onboarding docs and assigned a support owner.',
    },
    tenantId
  );

  // Step 3: Get summary
  const summary = await fetchJson('GET', '/reviews/summary', null, tenantId);

  store.setOutput('reviews', { response, summary });
}

/**
 * Special handler for chatbot creation with multi-step flow.
 */
async function runChatbotDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  // Step 1: Create bot
  const created = (await fetchJson(
    'POST',
    '/chatbot',
    {
      name: 'Studio Demo Bot',
      description: 'Demo chatbot',
      language: 'en',
      tone: 'friendly',
    },
    tenantId
  )) as { chatbot: { id: number } };

  const botId = created.chatbot?.id;
  if (!botId) {
    throw new Error('Bot id missing from creation response.');
  }

  // Step 2: Train bot
  await fetchJson(
    'POST',
    `/chatbot/${botId}/train`,
    {
      documents: ['Welcome to Nuxtron Studio! We are open 9am-6pm.'],
      source_type: 'faq',
    },
    tenantId
  );

  // Step 3: Deploy bot
  const deployed = await fetchJson('POST', `/chatbot/${botId}/deploy`, {}, tenantId);

  store.setOutput('chatbot', deployed);
}

/**
 * Special handler for link-in-bio creation with multi-step flow.
 */
async function runLinkinbioDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  // Step 1: Create page
  const page = (await fetchJson(
    'POST',
    '/linkinbio/pages',
    {
      title: 'Studio Links',
      bio: 'Powered by Nuxtron',
      theme: 'minimal',
    },
    tenantId
  )) as { page: { id: number } };

  const pageId = page.page?.id;
  if (!pageId) {
    throw new Error('Page id missing from creation response.');
  }

  // Step 2: Add link to page
  await fetchJson(
    'POST',
    `/linkinbio/pages/${pageId}/links`,
    {
      label: 'Nuxtron',
      url: 'https://nuxtron.io',
      icon: 'globe',
      position: 1,
    },
    tenantId
  );

  store.setOutput('linkinbio', page);
}

/**
 * Special handler for content generation with loading state.
 */
async function runContentDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();
  store.setIsGeneratingContent(true);
  store.setContentError('');

  try {
    const data = await fetchJson(
      'POST',
      '/content/generate',
      {
        topic: 'AI-driven content strategy',
        audience: 'ecommerce founders',
        channel: 'linkedin',
        tone: 'professional',
        include_seo: true,
      },
      tenantId
    );
    store.setOutput('content', data);
  } catch (e) {
    store.setContentError((e as Error).message);
  } finally {
    store.setIsGeneratingContent(false);
  }
}

/**
 * Special handler for TOTP verification that depends on previous setup.
 */
async function runTotpVerifyDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();
  const latestSecret = store.latestTotpSecret;

  if (!latestSecret) {
    throw new Error('Run TOTP Setup first to get a secret.');
  }

  const data = await fetchJson(
    'POST',
    '/auth/totp/verify',
    {
      secret: latestSecret,
      code: '000000',
      window: 1,
    },
    tenantId
  );

  store.setOutput('totpVerify', data);
}

/**
 * Special handler for TOTP setup that stores the secret.
 */
async function runTotpSetupDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  const data = await fetchJson(
    'POST',
    '/auth/totp/setup',
    {
      account_name: `${tenantId}@nuxtron.io`,
      issuer: 'Nuxtron',
    },
    tenantId
  );

  store.setOutput('totpSetup', data);

  const setup = data as { result?: { secret?: string } };
  store.setLatestTotpSecret(setup.result?.secret || '');
}

/**
 * Special handler for JWT verify that depends on previous issue.
 */
async function runJwtVerifyDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();
  const latestToken = store.latestJwtToken;

  if (!latestToken) {
    throw new Error('Run JWT Issue first to get a token.');
  }

  const data = await fetchJson(
    'POST',
    '/auth/jwt/verify',
    {
      token: latestToken,
    },
    tenantId
  );

  store.setOutput('jwtVerify', data);
}

/**
 * Special handler for JWT issue that stores the token.
 */
async function runJwtIssueDemo(tenantId: string): Promise<void> {
  const store = useStudioStore.getState();

  const data = await fetchJson(
    'POST',
    '/auth/jwt/issue',
    {
      subject: `${tenantId}-studio-user`,
      expires_in_seconds: 3600,
      roles: ['admin', 'editor'],
      additional_claims: { source: 'studio' },
    },
    tenantId
  );

  store.setOutput('jwtIssue', data);

  const issued = data as { result?: { token?: string } };
  store.setLatestJwtToken(issued.result?.token || '');
}

/**
 * Create a generic handler function for simple endpoints.
 * Handles single-step POST/GET/PATCH/DELETE operations.
 */
function createSimpleHandler(config: EndpointDemoConfig, tenantId: string) {
  return async () => {
    const store = useStudioStore.getState();
    store.setGlobalError('');

    try {
      const payload = config.buildPayload ? config.buildPayload(tenantId) : null;

      // Handle path templating for PATCH/DELETE with :id
      let path = config.path;
      if (path.includes(':id')) {
        path = path.replace(':id', tenantId);
      }

      const data = await fetchJson(config.method, path, payload, tenantId);

      store.setOutput(config.outputKey, data);

      // Handle custom onSuccess callbacks if needed
      if (config.onSuccess) {
        config.onSuccess(data, { setOutput: store.setOutput });
      }
    } catch (e) {
      store.setGlobalError((e as Error).message);
    }
  };
}

/**
 * Factory function: create all handlers for the studio.
 * Returns a map of handler IDs to bound functions.
 * @param tenantId - Tenant ID for all API calls
 * @returns Handlers map
 */
export function createStudioHandlers(tenantId: string) {
  const handlers: Record<string, () => Promise<void>> = {};

  // Map special handlers
  const specialHandlers: Record<string, (tenantId: string) => Promise<void>> = {
    'listening-alerts': runListeningAlertSweep,
    'reviews-ops': runReviewOpsDemo,
    chatbot: runChatbotDemo,
    linkinbio: runLinkinbioDemo,
    'content-generate': runContentDemo,
    'totp-verify': runTotpVerifyDemo,
    'totp-setup': runTotpSetupDemo,
    'jwt-verify': runJwtVerifyDemo,
    'jwt-issue': runJwtIssueDemo,
  };

  for (const endpoint of STUDIO_ENDPOINTS) {
    if (specialHandlers[endpoint.id]) {
      handlers[endpoint.id] = () => specialHandlers[endpoint.id](tenantId);
    } else {
      handlers[endpoint.id] = createSimpleHandler(endpoint, tenantId);
    }
  }

  return handlers;
}
