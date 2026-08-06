/**
 * Cloudflare Worker - Agent Analytics Logger
 *
 * Deployed at Cloudflare edge to track AI bot traffic in real-time
 * Sends events to the FastAPI backend for aggregation
 *
 * To deploy:
 * - Install Wrangler CLI: npm install -g @cloudflare/wrangler
 * - Run: wrangler publish agent-analytics-worker.js
 */

const ANALYTICS_ENDPOINT = 'https://your-domain.com/api/v1/agent-analytics/log-event';
const TENANT_ID = 'your-tenant-id';

// Bot detection patterns
const BOT_PATTERNS = {
  gptbot: 'ChatGPT',
  googlebot: 'GoogleBot',
  'google-extended': 'GoogleBot',
  gemini: 'Gemini',
  perplexitybot: 'Perplexity',
  'claude-web': 'Claude',
  bravebot: 'Brave Search',
  bingbot: 'BingBot',
  ccbot: 'CCBot',
  amazonbot: 'AmazonBot',
};

/**
 * Identify bot from user-agent string
 */
function identifyBot(userAgent: string): string | null {
  const ua = userAgent.toLowerCase();

  for (const [pattern, botName] of Object.entries(BOT_PATTERNS)) {
    if (ua.includes(pattern)) {
      return botName;
    }
  }

  return null;
}

/**
 * Get country from request
 */
function getCountry(request: Request): string {
  return request.headers.get('cf-ipcountry') || 'Unknown';
}

/**
 * Get ASN from request
 */
function getASN(request: Request): string | null {
  return request.headers.get('cf-asn') || null;
}

/**
 * Check if IP is from datacenter
 */
function isDatacenter(request: Request): boolean {
  const botManagement = (request as Request & { cf?: { botManagement?: { score?: number } } }).cf?.botManagement;
  return (botManagement?.score ?? 0) > 50;
}

/**
 * Hash IP address for privacy
 */
async function hashIP(ip: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(ip);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Main Cloudflare Worker handler
 */
export default {
  async fetch(request: Request, env: Record<string, string>, ctx: { waitUntil(p: Promise<unknown>): void }) {
    const userAgent = request.headers.get('user-agent') || '';
    const bot = identifyBot(userAgent);

    // Only track known bots
    if (!bot) {
      return await fetch(request);
    }

    // Extract request details
    const url = new URL(request.url);
    const path = url.pathname;
    const queryString = url.search.slice(1);
    const method = request.method;

    // Get client IP
    const clientIP =
      request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for')?.split(',')[0] || 'unknown';

    const ipHash = await hashIP(clientIP);

    // Get geographic info
    const country = getCountry(request);
    const asn = getASN(request);
    const dc = isDatacenter(request);

    // Forward original request with timing
    const startTime = Date.now();
    const response = await fetch(request);
    const endTime = Date.now();

    // Get response size (approximate)
    const contentLength = response.headers.get('content-length') || 0;

    // Log event (fire and forget with timeout)
    ctx.waitUntil(
      Promise.race([
        logEvent(
          {
            timestamp: new Date().toISOString(),
            method,
            path,
            queryString,
            userAgent,
            ipHash,
            country,
            asn,
            is_datacenter: dc,
            status_code: response.status,
            response_time_ms: endTime - startTime,
            response_size_bytes: Number.parseInt(String(contentLength), 10) || 0,
          },
          env.ANALYTICS_ENDPOINT
        ),
        new Promise((resolve) => setTimeout(resolve, 1000)), // 1 second timeout
      ])
    );

    // Return original response
    return response;
  },
};

/**
 * Send analytics event to backend
 */
async function logEvent(event: Record<string, unknown>, endpoint: string | undefined): Promise<void> {
  try {
    await fetch(endpoint || ANALYTICS_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': TENANT_ID,
      },
      body: JSON.stringify(event),
    });
  } catch (error) {
    console.error('Failed to log event:', error);
  }
}
