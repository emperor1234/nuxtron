import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { apiGet, apiSend, resolveSessionTenant } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiSend: vi.fn(),
  resolveSessionTenant: vi.fn(() => 'workspace-test'),
}));

vi.mock('@/app/lib/api-client', () => ({ resolveSessionTenant }));
vi.mock('@/app/lib/platform-api', () => ({ apiGet, apiSend }));

import SocialListeningPage from './page';

afterEach(() => cleanup());

const emptySummary = {
  status: 'ok',
  tenant_id: 'workspace-test',
  totals: { mentions: 0, alerts: 0, open_alerts: 0, rules: 0 },
  sentiment_breakdown: {},
  platform_distribution: {},
  top_queries: [],
  clusters: [],
  crisis_level: 'normal',
};
const emptyMentions = { status: 'ok', tenant_id: 'workspace-test', count: 0, mentions: [] };
const emptyAlerts = { status: 'ok', tenant_id: 'workspace-test', count: 0, alerts: [] };
const emptyRules = { status: 'ok', tenant_id: 'workspace-test', persistence: 'memory-fallback', count: 0, rules: [] };

const mention = {
  id: 4,
  platform: 'linkedin',
  query: 'brand mention',
  author_handle: '@customer',
  text: 'A manually captured mention.',
  sentiment: 'negative',
  engagement_count: 12,
  created_at: '2026-10-12T12:00:00Z',
};

function installEmptyData() {
  apiGet.mockImplementation((path: string) => Promise.resolve(
    path === '/social/listening/summary' ? emptySummary
      : path === '/social/listening/mentions' ? emptyMentions
        : path === '/social/listening/alerts' ? emptyAlerts
          : path === '/social/listening/rules' ? emptyRules
            : { status: 'error' },
  ));
}

beforeEach(() => {
  apiGet.mockReset();
  apiSend.mockReset();
  resolveSessionTenant.mockReturnValue('workspace-test');
  installEmptyData();
});

describe('Social Listening page', () => {
  it('announces manual-only temporary retention and starts with blank capture fields', async () => {
    render(<SocialListeningPage />);

    expect(await screen.findByText(/does not monitor social networks or ingest provider feeds/i)).toBeTruthy();
    expect(screen.getByText(/may be lost when the service restarts/i)).toBeTruthy();
    fireEvent.click(screen.getByRole('tab', { name: 'Manual capture' }));

    expect((screen.getByLabelText('Source platform') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText('Tracked query') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Public author handle') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Observed sentiment') as HTMLSelectElement).value).toBe('');
    expect((screen.getByLabelText(/Observed engagement count/i) as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Mention text') as HTMLTextAreaElement).value).toBe('');
    expect(screen.queryByText(/Real-time brand monitoring/i)).toBeNull();
    expect(apiGet).toHaveBeenCalledWith('/social/listening/summary', 'workspace-test');
    expect(apiGet).toHaveBeenCalledWith('/social/listening/rules', 'workspace-test');
    expect(apiSend).not.toHaveBeenCalled();
  });

  it('supports arrow-key section navigation and valid tab-to-panel relationships', () => {
    render(<SocialListeningPage />);
    const tabs = screen.getAllByRole('tab');
    for (const tab of tabs) {
      const panelId = tab.getAttribute('aria-controls');
      expect(panelId && document.getElementById(panelId)).toBeTruthy();
    }

    const overviewTab = screen.getByRole('tab', { name: 'Overview' });
    fireEvent.keyDown(overviewTab, { key: 'ArrowRight' });
    expect(screen.getByRole('tab', { name: 'Mentions' }).getAttribute('aria-selected')).toBe('true');
    expect(document.activeElement?.id).toBe('social-listening-tab-mentions');
  });

  it('distinguishes a pending alerts request from a confirmed empty alert list', async () => {
    let resolveAlerts!: (value: unknown) => void;
    apiGet.mockImplementation((path: string) => path === '/social/listening/alerts'
      ? new Promise((resolve) => { resolveAlerts = resolve; })
      : Promise.resolve(path === '/social/listening/summary' ? emptySummary : path === '/social/listening/mentions' ? emptyMentions : emptyRules),
    );
    render(<SocialListeningPage />);

    expect(await screen.findByText('Loading alerts…')).toBeTruthy();
    expect(screen.queryByText('No open alerts are recorded in this workspace.')).toBeNull();
    resolveAlerts(emptyAlerts);
    expect(await screen.findByText('No open alerts are recorded in this workspace.')).toBeTruthy();
  });

  it('records a manually entered mention with the authenticated workspace and explicit observed zero', async () => {
    apiSend.mockResolvedValue({ status: 'ok', mention: { ...mention, engagement_count: 0 } });
    render(<SocialListeningPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Manual capture' }));

    fireEvent.change(screen.getByLabelText('Source platform'), { target: { value: 'linkedin' } });
    fireEvent.change(screen.getByLabelText('Tracked query'), { target: { value: 'brand mention' } });
    fireEvent.change(screen.getByLabelText('Public author handle'), { target: { value: '@customer' } });
    fireEvent.change(screen.getByLabelText('Observed sentiment'), { target: { value: 'negative' } });
    fireEvent.change(screen.getByLabelText(/Observed engagement count/i), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Mention text'), { target: { value: 'A manually captured mention.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record mention' }));

    expect(await screen.findByText(/Mention recorded in temporary service memory/i)).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/social/listening/ingest', 'POST', {
      platform: 'linkedin',
      query: 'brand mention',
      author_handle: '@customer',
      text: 'A manually captured mention.',
      sentiment: 'negative',
      engagement_count: 0,
    }, 'workspace-test');
  });

  it('loads existing alert rules and allows deliberate creation without hidden threshold defaults', async () => {
    apiSend.mockResolvedValue({
      status: 'ok',
      persistence: 'memory-fallback',
      rule: { id: 2, name: 'Brand negative mentions', query: null, platform: null, min_engagement: 0, negative_only: true, enabled: true, created_at: '2026-10-12T12:00:00Z' },
    });
    render(<SocialListeningPage />);
    fireEvent.click(screen.getByRole('tab', { name: 'Alert rules' }));

    expect(await screen.findByText('No alert rules are configured in this workspace.')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Rule name'), { target: { value: 'Brand negative mentions' } });
    fireEvent.change(screen.getByLabelText(/Minimum engagement/i), { target: { value: '0' } });
    fireEvent.click(screen.getByLabelText('Negative sentiment only'));
    fireEvent.click(screen.getByRole('button', { name: 'Create alert rule' }));

    expect(await screen.findByText(/Alert rule recorded in temporary service memory/i)).toBeTruthy();
    expect(apiSend).toHaveBeenCalledWith('/social/listening/rules', 'POST', {
      name: 'Brand negative mentions', query: null, platform: null, min_engagement: 0, negative_only: true,
    }, 'workspace-test');
  });

  it('links an open alert to its underlying mention for review', async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(
      path === '/social/listening/summary' ? {
        ...emptySummary,
        totals: { mentions: 1, alerts: 1, open_alerts: 1, rules: 0 },
        sentiment_breakdown: { negative: 1 },
      } : path === '/social/listening/mentions' ? { status: 'ok', mentions: [mention] }
        : path === '/social/listening/alerts' ? { status: 'ok', alerts: [{
          id: 9, rule_name: 'Negative mentions', mention_id: 4, severity: 'high', status: 'open', created_at: '2026-10-12T12:00:00Z',
        }] } : emptyRules,
    ));
    render(<SocialListeningPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'View mention' }));
    expect(screen.getByRole('tab', { name: 'Mentions' }).getAttribute('aria-selected')).toBe('true');
    expect(screen.getByText('A manually captured mention.')).toBeTruthy();
  });

  it('shows source errors instead of converting failed reads into empty states', async () => {
    apiGet.mockImplementation((path: string) => path === '/social/listening/mentions'
      ? Promise.reject(new Error('Mention service unavailable'))
      : Promise.resolve(path === '/social/listening/summary' ? emptySummary : path === '/social/listening/alerts' ? emptyAlerts : emptyRules),
    );
    render(<SocialListeningPage />);

    expect(await screen.findByText('Mention service unavailable')).toBeTruthy();
    expect(screen.queryByText('No mentions have been captured in this workspace.')).toBeNull();
  });

  it('fails closed without a workspace session', () => {
    resolveSessionTenant.mockReturnValue('');
    render(<SocialListeningPage />);

    expect(screen.getByText('Sign in to a workspace before using Social Listening.')).toBeTruthy();
    expect(apiGet).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('tab', { name: 'Manual capture' }));
    expect((screen.getByRole('button', { name: 'Record mention' }) as HTMLButtonElement).disabled).toBe(true);
  });
});
