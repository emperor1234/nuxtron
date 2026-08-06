'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  type CanvaImportJob,
  type IntegrationWebhook,
  socialApi,
  type AutomationFeed,
  type AutomationRule,
  type IntegrationCatalogCategory,
  type PublishingQueueResponse,
  type SocialAIAgentTemplate,
  type SocialIdea,
} from '@/app/lib/social-api';

type CanvaAccountOption = {
  id: number;
  network: string;
  account_name: string;
  handle: string;
};

type IntegrationProvider = 'zapier' | 'make' | 'custom';
type WebhookActionType = 'notify_only' | 'create_idea' | 'queue_post';
type PublishMode = 'auto' | 'now' | 'draft';

function asCleanString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed || fallback;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function normalizeAccountOptions(input: unknown): CanvaAccountOption[] {
  if (Array.isArray(input)) {
    return input
      .map((item) => {
        if (!item || typeof item !== 'object') return null;
        const row = item as Record<string, unknown>;
        const id = Number(row.id);
        if (!Number.isFinite(id) || id <= 0) return null;
        return {
          id,
          network: asCleanString(row.network, 'unknown'),
          account_name: asCleanString(row.account_name, asCleanString(row.accountName, `Account ${id}`)),
          handle: asCleanString(row.handle),
        };
      })
      .filter((item): item is CanvaAccountOption => Boolean(item));
  }

  if (input && typeof input === 'object' && Array.isArray((input as { accounts?: unknown[] }).accounts)) {
    return normalizeAccountOptions((input as { accounts?: unknown[] }).accounts ?? []);
  }

  return [];
}

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

function readQueueValue(item: Record<string, unknown>, keys: string[], fallback: string): string {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }
  }
  return fallback;
}

const DEFAULT_RULE = {
  name: '',
  trigger_type: 'message_spike',
  trigger_value: 'negative-mentions',
  action_type: 'pause_all',
  action_payload: '{"reason":"Automated safeguard triggered"}',
};

const DEFAULT_FEED = {
  name: 'Product updates RSS',
  feed_url: 'https://example.com/rss.xml',
  target_networks: 'linkedin;x',
  cadence_minutes: 180,
  autopublish: false,
};

const DEFAULT_IDEA = {
  title: '',
  body: '',
  source: 'manual',
  tags: 'product;launch',
};

const DEFAULT_REPURPOSE_DRAFT = {
  source_title: 'Quarterly newsletter recap',
  source_url: '',
  source_text:
    'Summarize the key takeaways from a blog post, webinar, newsletter, or launch announcement and create platform-specific social posts.',
  target_platform: 'LinkedIn',
  tone: 'professional',
  variant_count: '3',
  queue_first_variant: false,
};

const DEFAULT_WEBHOOK_DRAFT = {
  name: 'Automation relay',
  provider: 'zapier' as IntegrationProvider,
  url: 'https://example.com/webhook',
  event_types: 'social.idea.create;social.post.queue',
  action_type: 'create_idea' as WebhookActionType,
  enabled: true,
};

const DEFAULT_INCOMING_EVENT_DRAFT = {
  provider: 'zapier' as IntegrationProvider,
  event_type: 'social.idea.create',
  payload:
    '{"title":"Q3 launch concept","body":"Turn webinar highlights into social snippets","tags":["webinar","launch"]}',
};

const DEFAULT_CANVA_IMPORT_DRAFT = {
  account_id: '',
  design_url: 'https://images.unsplash.com/photo-1557683316-973673baf926?w=1600',
  caption: 'Imported creative from Canva bridge.',
  headline: 'Canva import launch asset',
  target_network: 'linkedin',
  publish_mode: 'draft' as PublishMode,
};

export default function AutomationPage() {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [queue, setQueue] = useState<PublishingQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pauseReason, setPauseReason] = useState('Operator initiated pause.');
  const [draftRule, setDraftRule] = useState(DEFAULT_RULE);
  const [feeds, setFeeds] = useState<AutomationFeed[]>([]);
  const [ideas, setIdeas] = useState<SocialIdea[]>([]);
  const [draftFeed, setDraftFeed] = useState(DEFAULT_FEED);
  const [draftIdea, setDraftIdea] = useState(DEFAULT_IDEA);
  const [repurposeDraft, setRepurposeDraft] = useState(DEFAULT_REPURPOSE_DRAFT);
  const [repurposeResults, setRepurposeResults] = useState<SocialIdea[]>([]);
  const [repurposeBusy, setRepurposeBusy] = useState(false);
  const [agentTemplates, setAgentTemplates] = useState<SocialAIAgentTemplate[]>([]);
  const [integrationCatalog, setIntegrationCatalog] = useState<IntegrationCatalogCategory[]>([]);
  const [catalogCoverage, setCatalogCoverage] = useState<{
    providers_total: number;
    configured_total: number;
    coverage_percent: number;
  } | null>(null);
  const [webhooks, setWebhooks] = useState<IntegrationWebhook[]>([]);
  const [draftWebhook, setDraftWebhook] = useState(DEFAULT_WEBHOOK_DRAFT);
  const [incomingEventDraft, setIncomingEventDraft] = useState(DEFAULT_INCOMING_EVENT_DRAFT);
  const [canvaAccounts, setCanvaAccounts] = useState<CanvaAccountOption[]>([]);
  const [canvaImports, setCanvaImports] = useState<CanvaImportJob[]>([]);
  const [draftCanvaImport, setDraftCanvaImport] = useState(DEFAULT_CANVA_IMPORT_DRAFT);
  const [webhookBusy, setWebhookBusy] = useState(false);
  const [incomingEventBusy, setIncomingEventBusy] = useState(false);
  const [canvaBusy, setCanvaBusy] = useState(false);

  useEffect(() => {
    void loadAutomation();
  }, []);

  async function loadAutomation() {
    setLoadError(null);
    try {
      const [
        nextRules,
        nextQueue,
        nextFeeds,
        nextIdeas,
        nextTemplates,
        nextCatalog,
        nextWebhooks,
        nextCanvaImports,
        nextAccounts,
      ] = await Promise.all([
        socialApi.listAutomationRules(),
        socialApi.getPublishingQueue(),
        socialApi.listAutomationFeeds(),
        socialApi.listIdeas(),
        socialApi.listAIAgentTemplates(),
        socialApi.listIntegrationCatalog(),
        socialApi.listIntegrationWebhooks(),
        socialApi.listCanvaImports(),
        socialApi.listAccounts() as Promise<unknown>,
      ]);
      setRules(nextRules);
      setQueue(nextQueue);
      setFeeds(nextFeeds);
      setIdeas(nextIdeas);
      setAgentTemplates(nextTemplates);
      setIntegrationCatalog(nextCatalog.categories || []);
      setCatalogCoverage(nextCatalog.summary);
      setWebhooks(nextWebhooks);
      setCanvaImports(nextCanvaImports);
      const accountOptions = normalizeAccountOptions(nextAccounts);
      setCanvaAccounts(accountOptions);
      setDraftCanvaImport((current) => {
        if (current.account_id || accountOptions.length === 0) return current;
        return { ...current, account_id: String(accountOptions[0].id) };
      });
    } catch (error) {
      console.error('Failed to load automation:', error);
      setRules([]);
      setQueue(null);
      setFeeds([]);
      setIdeas([]);
      setAgentTemplates([]);
      setIntegrationCatalog([]);
      setCatalogCoverage(null);
      setWebhooks([]);
      setCanvaImports([]);
      setCanvaAccounts([]);
      setLoadError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Automation backend unavailable in strict no-mock mode.'
          : 'Automation backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleRunTemplate(templateKey: 'social_poster' | 'dm_chatbot' | 'comment_to_dm') {
    try {
      if (templateKey === 'social_poster') {
        await socialApi.executeAIAgentWorkflow({
          template_key: 'social_poster',
          trigger_type: 'scheduled',
          payload: {
            title: 'Automated campaign update',
            body: 'Generated by Social Poster template from the automation command center.',
            network: 'linkedin',
            tags: ['ai-agent', 'scheduled'],
          },
        });
      } else {
        const inbox = await socialApi.listInboxItems(false);
        const first = inbox[0];
        if (!first) {
          alert('No inbox messages found to run this template.');
          return;
        }
        const messageId = Number(first.id);
        if (!Number.isFinite(messageId)) {
          alert('Selected inbox message has an invalid id.');
          return;
        }
        if (templateKey === 'dm_chatbot') {
          await socialApi.executeAIAgentWorkflow({
            template_key: 'dm_chatbot',
            trigger_type: 'new_dm',
            payload: {
              message_id: messageId,
              intent: 'support',
            },
          });
        } else {
          await socialApi.executeAIAgentWorkflow({
            template_key: 'comment_to_dm',
            trigger_type: 'keyword_comment_match',
            payload: {
              message_id: messageId,
              keyword: 'demo',
              offer_link: 'https://nuxtron.local/offers/social-growth',
            },
          });
        }
      }
      await loadAutomation();
    } catch (error) {
      console.error('Failed to run AI agent template:', error);
      alert('AI agent workflow execution failed.');
    }
  }

  const queueItems = (queue?.items || []).map((item, index) => {
    const title = readQueueValue(item, ['title', 'content_preview', 'text'], `Scheduled item ${index + 1}`);
    const status = readQueueValue(item, ['status'], 'scheduled');
    const publishAt = readQueueValue(item, ['publish_at', 'scheduled_time', 'scheduled_at'], '');
    const network = readQueueValue(item, ['platform', 'network'], 'multi-channel');
    const approvalState = readQueueValue(item, ['approval_status', 'review_state'], '');
    return {
      id: readQueueValue(item, ['id'], `queue-${index}`),
      title,
      status,
      publishAt,
      network,
      approvalState,
    };
  });

  async function handleCreateRule() {
    if (!draftRule.name.trim()) return;
    setSaving(true);
    try {
      const actionPayload = JSON.parse(draftRule.action_payload || '{}') as Record<string, unknown>;
      const rule = await socialApi.createAutomationRule({
        name: draftRule.name,
        trigger_type: draftRule.trigger_type,
        trigger_value: draftRule.trigger_value,
        action_type: draftRule.action_type,
        action_payload: actionPayload,
        enabled: true,
      });
      setRules((current) => [rule, ...current]);
      setDraftRule(DEFAULT_RULE);
    } catch (error) {
      console.error('Failed to create automation rule:', error);
      alert('Automation rule could not be created.');
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleRule(rule: AutomationRule) {
    try {
      const updated = await socialApi.updateAutomationRule(rule.id, !rule.enabled);
      setRules((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      console.error('Failed to update automation rule:', error);
      alert('Rule update failed.');
    }
  }

  async function handlePauseAll(paused: boolean) {
    try {
      const pause_all = await socialApi.setPauseAll(paused, pauseReason);
      setQueue((current) =>
        current ? { ...current, pause_all } : { pause_all, summary: { scheduled: 0, drafts: 0 }, items: [] }
      );
    } catch (error) {
      console.error('Failed to update pause-all state:', error);
      alert('Pause-all state could not be updated.');
    }
  }

  async function handleCreateFeed() {
    if (!draftFeed.name.trim() || !draftFeed.feed_url.trim()) return;
    try {
      const created = await socialApi.createAutomationFeed({
        name: draftFeed.name.trim(),
        feed_url: draftFeed.feed_url.trim(),
        target_networks: draftFeed.target_networks
          .split(';')
          .map((item) => item.trim())
          .filter(Boolean),
        cadence_minutes: Number(draftFeed.cadence_minutes) || 180,
        autopublish: draftFeed.autopublish,
      });
      setFeeds((current) => [created, ...current]);
      setDraftFeed(DEFAULT_FEED);
    } catch (error) {
      console.error('Failed to create automation feed:', error);
      alert('Automation feed could not be created.');
    }
  }

  async function handleToggleFeed(feed: AutomationFeed) {
    try {
      const updated = await socialApi.updateAutomationFeed(feed.id, !feed.enabled);
      setFeeds((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      console.error('Failed to update feed status:', error);
      alert('Feed update failed.');
    }
  }

  async function handleSyncFeed(feed: AutomationFeed) {
    try {
      const result = await socialApi.syncAutomationFeed(feed.id, 3);
      if (result.generated_ideas.length > 0) {
        setIdeas((current) => [...result.generated_ideas, ...current]);
      }
      await loadAutomation();
    } catch (error) {
      console.error('Failed to sync feed:', error);
      alert('Feed sync failed.');
    }
  }

  async function handleCreateIdea() {
    if (!draftIdea.title.trim() || !draftIdea.body.trim()) return;
    try {
      const created = await socialApi.createIdea({
        title: draftIdea.title.trim(),
        body: draftIdea.body.trim(),
        source: draftIdea.source.trim() || 'manual',
        tags: draftIdea.tags
          .split(';')
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setIdeas((current) => [created, ...current]);
      setDraftIdea(DEFAULT_IDEA);
    } catch (error) {
      console.error('Failed to create idea:', error);
      alert('Idea could not be created.');
    }
  }

  async function handleQueueIdea(idea: SocialIdea) {
    try {
      await socialApi.queueIdea(idea.id, 'linkedin');
      await loadAutomation();
    } catch (error) {
      console.error('Failed to queue idea:', error);
      alert('Idea could not be queued.');
    }
  }

  async function handleRepurposeLongform() {
    if (!repurposeDraft.source_text.trim()) {
      alert('Add source content before repurposing it.');
      return;
    }

    setRepurposeBusy(true);
    try {
      const result = await socialApi.repurposeLongform({
        source_title: repurposeDraft.source_title.trim(),
        source_url: repurposeDraft.source_url.trim() || undefined,
        source_text: repurposeDraft.source_text.trim(),
        target_platform: repurposeDraft.target_platform.trim() || 'LinkedIn',
        tone: repurposeDraft.tone.trim() || 'professional',
        variant_count: Number(repurposeDraft.variant_count) || 3,
        queue_first_variant: repurposeDraft.queue_first_variant,
      });
      setRepurposeResults(result.generated_variants || []);
      if (result.generated_variants.length > 0) {
        setIdeas((current) => [...result.generated_variants, ...current]);
      }
      await loadAutomation();
    } catch (error) {
      console.error('Failed to repurpose longform asset:', error);
      alert('Longform repurpose failed.');
    } finally {
      setRepurposeBusy(false);
    }
  }

  async function handleCreateWebhook() {
    if (!draftWebhook.name.trim() || !draftWebhook.url.trim()) return;
    setWebhookBusy(true);
    try {
      const created = await socialApi.createIntegrationWebhook({
        name: draftWebhook.name.trim(),
        provider: draftWebhook.provider,
        url: draftWebhook.url.trim(),
        event_types: draftWebhook.event_types
          .split(';')
          .map((item) => item.trim())
          .filter(Boolean),
        action_type: draftWebhook.action_type,
        enabled: draftWebhook.enabled,
      });
      setWebhooks((current) => [created, ...current]);
      setDraftWebhook(DEFAULT_WEBHOOK_DRAFT);
    } catch (error) {
      console.error('Failed to create integration webhook:', error);
      alert('Integration webhook could not be created.');
    } finally {
      setWebhookBusy(false);
    }
  }

  async function handleToggleWebhook(webhook: IntegrationWebhook) {
    try {
      const updated = await socialApi.updateIntegrationWebhook(webhook.id, { enabled: !webhook.enabled });
      setWebhooks((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      console.error('Failed to update webhook status:', error);
      alert('Webhook status update failed.');
    }
  }

  async function handleTestWebhook(webhook: IntegrationWebhook) {
    try {
      const delivery = await socialApi.testIntegrationWebhook(webhook.id, 'social.test_event', {
        source: 'automation-ui',
        at: new Date().toISOString(),
      });
      alert(`Webhook test completed: ${delivery.ok ? 'success' : 'failed'} (status ${delivery.status_code})`);
    } catch (error) {
      console.error('Failed to test webhook:', error);
      alert('Webhook test failed.');
    }
  }

  async function handleSendIncomingEvent() {
    setIncomingEventBusy(true);
    try {
      const parsedPayload = JSON.parse(incomingEventDraft.payload || '{}') as Record<string, unknown>;
      await socialApi.receiveIncomingIntegrationEvent(
        incomingEventDraft.provider,
        incomingEventDraft.event_type.trim() || 'social.idea.create',
        parsedPayload
      );
      await loadAutomation();
    } catch (error) {
      console.error('Failed to send incoming integration event:', error);
      alert('Incoming integration event failed.');
    } finally {
      setIncomingEventBusy(false);
    }
  }

  async function handleCanvaImport() {
    const accountId = Number(draftCanvaImport.account_id);
    if (!Number.isFinite(accountId) || accountId <= 0) {
      alert('Select a connected account before importing from Canva.');
      return;
    }

    setCanvaBusy(true);
    try {
      await socialApi.importFromCanva({
        account_id: accountId,
        design_url: draftCanvaImport.design_url.trim() || undefined,
        caption: draftCanvaImport.caption.trim(),
        headline: draftCanvaImport.headline.trim(),
        target_network: draftCanvaImport.target_network.trim() || 'linkedin',
        publish_mode: draftCanvaImport.publish_mode,
      });
      await loadAutomation();
    } catch (error) {
      console.error('Failed to import from Canva:', error);
      alert('Canva import failed.');
    } finally {
      setCanvaBusy(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Automation Engine</h1>
          <p style={styles.subtitle}>
            Orchestrate queue safeguards, rule-based routing, and automated response handling.
          </p>
        </div>
      </div>

      {loadError ? <div style={styles.errorBanner}>⚠ {loadError}</div> : null}

      {loading ? (
        <div style={styles.loadingCard}>Loading automation controls…</div>
      ) : (
        <div style={styles.layout}>
          <section style={styles.heroCard}>
            <div style={styles.heroTop}>
              <div>
                <p style={styles.eyebrow}>Publishing control</p>
                <h2 style={styles.sectionTitle}>Queue command center</h2>
              </div>
              <div style={styles.pauseActions}>
                <input
                  value={pauseReason}
                  onChange={(event) => setPauseReason(event.target.value)}
                  placeholder="Pause reason"
                  style={styles.input}
                />
                <button
                  onClick={() => handlePauseAll(!(queue?.pause_all.paused ?? false))}
                  style={{
                    ...styles.primaryButton,
                    background: queue?.pause_all.paused ? '#dcfce7' : '#fee2e2',
                  }}
                >
                  {queue?.pause_all.paused ? 'Resume publishing' : 'Pause all publishing'}
                </button>
              </div>
            </div>
            <div style={styles.metricsGrid}>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Scheduled</span>
                <strong style={styles.metricValue}>{queue?.summary.scheduled ?? 0}</strong>
              </div>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Draft backlog</span>
                <strong style={styles.metricValue}>{queue?.summary.drafts ?? 0}</strong>
              </div>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Pause-all</span>
                <strong style={styles.metricValue}>{queue?.pause_all.paused ? 'Active' : 'Live'}</strong>
              </div>
            </div>
            <p style={styles.note}>
              {queue?.pause_all.paused
                ? `Publishing is paused. Reason: ${queue.pause_all.reason || 'No reason provided.'}`
                : 'Publishing is active. Use pause-all to stop every scheduled send during incidents.'}
            </p>

            <div style={styles.queueList}>
              {queueItems.length > 0 ? (
                queueItems.map((item) => (
                  <article key={item.id} style={styles.queueCard}>
                    <div>
                      <strong style={styles.queueTitle}>{item.title}</strong>
                      <p style={styles.queueMeta}>
                        {item.network} • {item.status}
                        {item.publishAt ? ` • ${new Date(item.publishAt).toLocaleString()}` : ''}
                        {item.approvalState ? ` • approval: ${item.approvalState}` : ''}
                      </p>
                    </div>
                    <span style={styles.queueBadge}>{item.status}</span>
                  </article>
                ))
              ) : (
                <div style={styles.emptyState}>No queued publishing items are currently scheduled.</div>
              )}
            </div>
          </section>

          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <p style={styles.eyebrow}>Ocoya-style AI agents</p>
                <h2 style={styles.sectionTitle}>Workflow templates and vendor coverage</h2>
              </div>
            </div>

            <div style={styles.metricsGrid}>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Agent templates</span>
                <strong style={styles.metricValue}>{agentTemplates.length}</strong>
              </div>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Integrations</span>
                <strong style={styles.metricValue}>{catalogCoverage?.providers_total ?? 0}</strong>
              </div>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Configured now</span>
                <strong style={styles.metricValue}>{catalogCoverage?.configured_total ?? 0}</strong>
              </div>
              <div style={styles.metricCard}>
                <span style={styles.metricLabel}>Coverage</span>
                <strong style={styles.metricValue}>{Math.round(catalogCoverage?.coverage_percent ?? 0)}%</strong>
              </div>
            </div>

            <div style={{ ...styles.ruleList, marginTop: 16 }}>
              {agentTemplates.map((template) => {
                const key = template.key as 'social_poster' | 'dm_chatbot' | 'comment_to_dm';
                const runnable = key === 'social_poster' || key === 'dm_chatbot' || key === 'comment_to_dm';
                return (
                  <article key={template.key} style={styles.ruleCard}>
                    <div>
                      <strong style={styles.ruleName}>{template.name}</strong>
                      <p style={styles.ruleMeta}>{template.description}</p>
                      <p style={styles.ruleMeta}>Triggers: {template.trigger_types.join(', ')}</p>
                      <p style={styles.ruleMeta}>Vendors: {template.vendors.join(', ')}</p>
                    </div>
                    <button
                      onClick={() => runnable && void handleRunTemplate(key)}
                      disabled={!runnable}
                      style={styles.secondaryButton}
                    >
                      Run workflow
                    </button>
                  </article>
                );
              })}
            </div>

            <div style={{ ...styles.ruleList, marginTop: 16 }}>
              {integrationCatalog.map((group) => (
                <article key={group.category} style={styles.ruleCard}>
                  <div>
                    <strong style={styles.ruleName}>{group.category.replaceAll('_', ' ')}</strong>
                    <p style={styles.ruleMeta}>
                      {group.providers.length} providers •{' '}
                      {group.providers.filter((provider) => provider.configured).length} configured
                    </p>
                    <p style={styles.ruleMeta}>{group.providers.map((provider) => provider.vendor).join(', ')}</p>
                  </div>
                </article>
              ))}
            </div>

            <div style={{ ...styles.panelHeader, marginTop: 28 }}>
              <div>
                <p style={styles.eyebrow}>Integration automation</p>
                <h2 style={styles.sectionTitle}>Webhook operations (Zapier / Make / Custom)</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <input
                value={draftWebhook.name}
                onChange={(event) => setDraftWebhook((current) => ({ ...current, name: event.target.value }))}
                placeholder="Webhook name"
                style={styles.input}
              />
              <select
                value={draftWebhook.provider}
                onChange={(event) =>
                  setDraftWebhook((current) => ({ ...current, provider: event.target.value as IntegrationProvider }))
                }
                style={styles.input}
              >
                <option value="zapier">Zapier</option>
                <option value="make">Make</option>
                <option value="custom">Custom</option>
              </select>
              <input
                value={draftWebhook.url}
                onChange={(event) => setDraftWebhook((current) => ({ ...current, url: event.target.value }))}
                placeholder="https://example.com/webhook"
                style={styles.input}
              />
              <input
                value={draftWebhook.event_types}
                onChange={(event) => setDraftWebhook((current) => ({ ...current, event_types: event.target.value }))}
                placeholder="social.idea.create;social.post.queue"
                style={styles.input}
              />
              <select
                value={draftWebhook.action_type}
                onChange={(event) =>
                  setDraftWebhook((current) => ({
                    ...current,
                    action_type: event.target.value as WebhookActionType,
                  }))
                }
                style={styles.input}
              >
                <option value="notify_only">notify_only</option>
                <option value="create_idea">create_idea</option>
                <option value="queue_post">queue_post</option>
              </select>
              <button onClick={handleCreateWebhook} disabled={webhookBusy} style={styles.primaryButton}>
                {webhookBusy ? 'Creating…' : 'Create webhook'}
              </button>
            </div>

            <div style={styles.ruleList}>
              {webhooks.length > 0 ? (
                webhooks.map((webhook) => (
                  <article key={webhook.id} style={styles.ruleCard}>
                    <div>
                      <strong style={styles.ruleName}>{webhook.name}</strong>
                      <p style={styles.ruleMeta}>
                        {webhook.provider} • {webhook.action_type} • events: {webhook.event_types.join(', ')}
                      </p>
                      <p style={styles.ruleMeta}>{webhook.url}</p>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={() => void handleTestWebhook(webhook)} style={styles.secondaryButton}>
                        Test
                      </button>
                      <button onClick={() => void handleToggleWebhook(webhook)} style={styles.secondaryButton}>
                        {webhook.enabled ? 'Disable' : 'Enable'}
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div style={styles.emptyState}>No integration webhooks configured yet.</div>
              )}
            </div>

            <div style={styles.formGrid}>
              <select
                value={incomingEventDraft.provider}
                onChange={(event) =>
                  setIncomingEventDraft((current) => ({
                    ...current,
                    provider: event.target.value as IntegrationProvider,
                  }))
                }
                style={styles.input}
              >
                <option value="zapier">zapier</option>
                <option value="make">make</option>
                <option value="custom">custom</option>
              </select>
              <input
                value={incomingEventDraft.event_type}
                onChange={(event) =>
                  setIncomingEventDraft((current) => ({ ...current, event_type: event.target.value }))
                }
                placeholder="social.idea.create"
                style={styles.input}
              />
              <textarea
                value={incomingEventDraft.payload}
                onChange={(event) => setIncomingEventDraft((current) => ({ ...current, payload: event.target.value }))}
                placeholder='{"title":"New launch idea","body":"..."}'
                style={{ ...styles.textarea, gridColumn: '1 / -1' }}
              />
              <button onClick={handleSendIncomingEvent} disabled={incomingEventBusy} style={styles.primaryButton}>
                {incomingEventBusy ? 'Sending…' : 'Simulate incoming event'}
              </button>
            </div>

            <div style={{ ...styles.panelHeader, marginTop: 28 }}>
              <div>
                <p style={styles.eyebrow}>Creative ingestion</p>
                <h2 style={styles.sectionTitle}>Canva import workflow</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <select
                value={draftCanvaImport.account_id}
                onChange={(event) => setDraftCanvaImport((current) => ({ ...current, account_id: event.target.value }))}
                style={styles.input}
              >
                <option value="">Select connected account</option>
                {canvaAccounts.map((account) => (
                  <option key={account.id} value={String(account.id)}>
                    {account.account_name} ({account.network}) {account.handle ? `• ${account.handle}` : ''}
                  </option>
                ))}
              </select>
              <input
                value={draftCanvaImport.design_url}
                onChange={(event) => setDraftCanvaImport((current) => ({ ...current, design_url: event.target.value }))}
                placeholder="Design URL"
                style={styles.input}
              />
              <input
                value={draftCanvaImport.headline}
                onChange={(event) => setDraftCanvaImport((current) => ({ ...current, headline: event.target.value }))}
                placeholder="Headline"
                style={styles.input}
              />
              <input
                value={draftCanvaImport.caption}
                onChange={(event) => setDraftCanvaImport((current) => ({ ...current, caption: event.target.value }))}
                placeholder="Caption"
                style={styles.input}
              />
              <input
                value={draftCanvaImport.target_network}
                onChange={(event) =>
                  setDraftCanvaImport((current) => ({ ...current, target_network: event.target.value }))
                }
                placeholder="Target network"
                style={styles.input}
              />
              <select
                value={draftCanvaImport.publish_mode}
                onChange={(event) =>
                  setDraftCanvaImport((current) => ({ ...current, publish_mode: event.target.value as PublishMode }))
                }
                style={styles.input}
              >
                <option value="draft">draft</option>
                <option value="auto">auto</option>
                <option value="now">now</option>
              </select>
              <button onClick={handleCanvaImport} disabled={canvaBusy} style={styles.primaryButton}>
                {canvaBusy ? 'Importing…' : 'Import from Canva'}
              </button>
            </div>

            <div style={styles.ruleList}>
              {canvaImports.length > 0 ? (
                canvaImports.map((job) => (
                  <article key={job.id} style={styles.ruleCard}>
                    <div>
                      <strong style={styles.ruleName}>Canva import #{job.id}</strong>
                      <p style={styles.ruleMeta}>
                        account {job.account_id} • post {job.post_id} • {job.status}
                      </p>
                      <p style={styles.ruleMeta}>{job.resolved_media_url}</p>
                    </div>
                  </article>
                ))
              ) : (
                <div style={styles.emptyState}>No Canva import jobs yet.</div>
              )}
            </div>

            <div style={styles.panelHeader}>
              <div>
                <p style={styles.eyebrow}>Rules</p>
                <h2 style={styles.sectionTitle}>Automation playbooks</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <input
                value={draftRule.name}
                onChange={(event) => setDraftRule((current) => ({ ...current, name: event.target.value }))}
                placeholder="Rule name"
                style={styles.input}
              />
              <input
                value={draftRule.trigger_type}
                onChange={(event) => setDraftRule((current) => ({ ...current, trigger_type: event.target.value }))}
                placeholder="Trigger type"
                style={styles.input}
              />
              <input
                value={draftRule.trigger_value}
                onChange={(event) => setDraftRule((current) => ({ ...current, trigger_value: event.target.value }))}
                placeholder="Trigger value"
                style={styles.input}
              />
              <input
                value={draftRule.action_type}
                onChange={(event) => setDraftRule((current) => ({ ...current, action_type: event.target.value }))}
                placeholder="Action type"
                style={styles.input}
              />
              <textarea
                value={draftRule.action_payload}
                onChange={(event) => setDraftRule((current) => ({ ...current, action_payload: event.target.value }))}
                placeholder='{"priority":"high"}'
                style={styles.textarea}
              />
              <button onClick={handleCreateRule} disabled={saving} style={styles.primaryButton}>
                {saving ? 'Saving…' : 'Create rule'}
              </button>
            </div>

            <div style={styles.ruleList}>
              {rules.map((rule) => (
                <article key={rule.id} style={styles.ruleCard}>
                  <div>
                    <strong style={styles.ruleName}>{rule.name}</strong>
                    <p style={styles.ruleMeta}>
                      When {rule.trigger_type} = {rule.trigger_value}, then {rule.action_type}
                    </p>
                  </div>
                  <button onClick={() => handleToggleRule(rule)} style={styles.secondaryButton}>
                    {rule.enabled ? 'Disable' : 'Enable'}
                  </button>
                </article>
              ))}
            </div>

            <div style={{ ...styles.panelHeader, marginTop: 28 }}>
              <div>
                <p style={styles.eyebrow}>Feed automations</p>
                <h2 style={styles.sectionTitle}>RSS-to-idea pipeline</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <input
                value={draftFeed.name}
                onChange={(event) => setDraftFeed((current) => ({ ...current, name: event.target.value }))}
                placeholder="Feed name"
                style={styles.input}
              />
              <input
                value={draftFeed.feed_url}
                onChange={(event) => setDraftFeed((current) => ({ ...current, feed_url: event.target.value }))}
                placeholder="https://example.com/rss.xml"
                style={styles.input}
              />
              <input
                value={draftFeed.target_networks}
                onChange={(event) => setDraftFeed((current) => ({ ...current, target_networks: event.target.value }))}
                placeholder="linkedin;x;instagram"
                style={styles.input}
              />
              <input
                value={String(draftFeed.cadence_minutes)}
                onChange={(event) =>
                  setDraftFeed((current) => ({ ...current, cadence_minutes: Number(event.target.value) || 180 }))
                }
                placeholder="Cadence (minutes)"
                style={styles.input}
              />
              <label style={{ ...styles.ruleMeta, display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={draftFeed.autopublish}
                  onChange={(event) => setDraftFeed((current) => ({ ...current, autopublish: event.target.checked }))}
                />
                <span>Autopublish queued posts</span>
              </label>
              <button onClick={handleCreateFeed} style={styles.primaryButton}>
                Create feed automation
              </button>
            </div>

            <div style={styles.ruleList}>
              {feeds.map((feed) => (
                <article key={feed.id} style={styles.ruleCard}>
                  <div>
                    <strong style={styles.ruleName}>{feed.name}</strong>
                    <p style={styles.ruleMeta}>
                      {feed.feed_url} • every {feed.cadence_minutes} min • targets {feed.target_networks.join(', ')}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => void handleSyncFeed(feed)} style={styles.secondaryButton}>
                      Sync now
                    </button>
                    <button onClick={() => void handleToggleFeed(feed)} style={styles.secondaryButton}>
                      {feed.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <div style={{ ...styles.panelHeader, marginTop: 28 }}>
              <div>
                <p style={styles.eyebrow}>Longform repurposing</p>
                <h2 style={styles.sectionTitle}>Blog, newsletter, webinar, and press release repurpose flow</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <input
                value={repurposeDraft.source_title}
                onChange={(event) => setRepurposeDraft((current) => ({ ...current, source_title: event.target.value }))}
                placeholder="Source title"
                style={styles.input}
              />
              <input
                value={repurposeDraft.source_url}
                onChange={(event) => setRepurposeDraft((current) => ({ ...current, source_url: event.target.value }))}
                placeholder="Source URL"
                style={styles.input}
              />
              <input
                value={repurposeDraft.target_platform}
                onChange={(event) =>
                  setRepurposeDraft((current) => ({ ...current, target_platform: event.target.value }))
                }
                placeholder="Target platform"
                style={styles.input}
              />
              <input
                value={repurposeDraft.tone}
                onChange={(event) => setRepurposeDraft((current) => ({ ...current, tone: event.target.value }))}
                placeholder="Tone"
                style={styles.input}
              />
              <input
                value={repurposeDraft.variant_count}
                onChange={(event) =>
                  setRepurposeDraft((current) => ({ ...current, variant_count: event.target.value }))
                }
                placeholder="Variant count"
                style={styles.input}
              />
              <label style={{ ...styles.ruleMeta, display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={repurposeDraft.queue_first_variant}
                  onChange={(event) =>
                    setRepurposeDraft((current) => ({ ...current, queue_first_variant: event.target.checked }))
                  }
                />
                <span>Queue the first variant automatically</span>
              </label>
              <textarea
                value={repurposeDraft.source_text}
                onChange={(event) => setRepurposeDraft((current) => ({ ...current, source_text: event.target.value }))}
                placeholder="Paste the longform article, newsletter, webinar notes, or launch brief here."
                style={{ ...styles.textarea, gridColumn: '1 / -1' }}
              />
              <button onClick={handleRepurposeLongform} disabled={repurposeBusy} style={styles.primaryButton}>
                {repurposeBusy ? 'Repurposing…' : 'Repurpose longform asset'}
              </button>
            </div>

            <div style={styles.ruleList}>
              {repurposeResults.length > 0 ? (
                repurposeResults.map((item) => (
                  <article key={item.id} style={styles.ruleCard}>
                    <div>
                      <strong style={styles.ruleName}>{item.title}</strong>
                      <p style={styles.ruleMeta}>{item.body}</p>
                      <p style={styles.ruleMeta}>
                        source: {item.source} {item.source_ref ? `• ${item.source_ref}` : ''} • status: {item.status}
                      </p>
                    </div>
                    <button onClick={() => void handleQueueIdea(item)} style={styles.secondaryButton}>
                      Queue variant
                    </button>
                  </article>
                ))
              ) : (
                <div style={styles.emptyState}>
                  No repurposed drafts yet. Paste a source asset above to generate publish-ready variants.
                </div>
              )}
            </div>

            <div style={{ ...styles.panelHeader, marginTop: 28 }}>
              <div>
                <p style={styles.eyebrow}>Content ideas</p>
                <h2 style={styles.sectionTitle}>Idea inbox and queue</h2>
              </div>
            </div>

            <div style={styles.formGrid}>
              <input
                value={draftIdea.title}
                onChange={(event) => setDraftIdea((current) => ({ ...current, title: event.target.value }))}
                placeholder="Idea title"
                style={styles.input}
              />
              <textarea
                value={draftIdea.body}
                onChange={(event) => setDraftIdea((current) => ({ ...current, body: event.target.value }))}
                placeholder="Idea body"
                style={styles.textarea}
              />
              <input
                value={draftIdea.tags}
                onChange={(event) => setDraftIdea((current) => ({ ...current, tags: event.target.value }))}
                placeholder="tags separated by ;"
                style={styles.input}
              />
              <button onClick={handleCreateIdea} style={styles.primaryButton}>
                Capture idea
              </button>
            </div>

            <div style={styles.ruleList}>
              {ideas.map((idea) => (
                <article key={idea.id} style={styles.ruleCard}>
                  <div>
                    <strong style={styles.ruleName}>{idea.title}</strong>
                    <p style={styles.ruleMeta}>{idea.body}</p>
                    <p style={styles.ruleMeta}>
                      status: {idea.status} • source: {idea.source}
                    </p>
                  </div>
                  <button
                    onClick={() => void handleQueueIdea(idea)}
                    disabled={idea.status === 'queued' || idea.status === 'published'}
                    style={styles.secondaryButton}
                  >
                    {idea.status === 'queued' || idea.status === 'published' ? 'Queued' : 'Queue to publish'}
                  </button>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    padding: '32px 24px 64px',
    background: 'linear-gradient(180deg, #08111d 0%, #eef0f4 45%, #eef0f4 100%)',
    color: '#e5eef8',
  },
  header: {
    marginBottom: '28px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '14px',
    color: '#8fb9ff',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    margin: '0 0 8px',
    fontSize: '32px',
    fontWeight: 700,
  },
  subtitle: {
    margin: 0,
    maxWidth: '720px',
    color: 'var(--muted)',
    fontSize: '15px',
    lineHeight: 1.6,
  },
  loadingCard: {
    padding: '24px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  errorBanner: {
    marginBottom: '18px',
    padding: '14px 16px',
    borderRadius: '16px',
    background: 'rgba(127, 29, 29, 0.22)',
    border: '1px solid rgba(248, 113, 113, 0.35)',
    color: '#fecaca',
  },
  layout: {
    display: 'grid',
    gap: '20px',
  },
  heroCard: {
    padding: '24px',
    borderRadius: '22px',
    background: 'radial-gradient(circle at top left, rgba(20, 184, 166, 0.18), transparent 42%), rgba(148,163,184,0.10)',
    border: '1px solid rgba(45, 212, 191, 0.24)',
    boxShadow: '0 24px 80px rgba(8, 15, 30, 0.35)',
  },
  heroTop: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
    marginBottom: '18px',
  },
  eyebrow: {
    margin: '0 0 6px',
    color: '#5eead4',
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
    fontSize: '12px',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: 700,
  },
  pauseActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
    gap: '12px',
  },
  metricCard: {
    padding: '18px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  metricLabel: {
    display: 'block',
    marginBottom: '8px',
    color: 'var(--muted)',
    fontSize: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  metricValue: {
    fontSize: '28px',
    fontWeight: 700,
  },
  note: {
    margin: '18px 0 0',
    color: 'var(--muted)',
    lineHeight: 1.6,
  },
  queueList: {
    display: 'grid',
    gap: '12px',
    marginTop: '20px',
  },
  queueCard: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'center',
    padding: '16px 18px',
    borderRadius: '16px',
    background: 'rgba(8, 15, 30, 0.72)',
    border: '1px solid var(--line)',
  },
  queueTitle: {
    display: 'block',
    marginBottom: '6px',
    fontSize: '15px',
  },
  queueMeta: {
    margin: 0,
    color: 'var(--muted)',
    fontSize: '13px',
  },
  queueBadge: {
    padding: '8px 10px',
    borderRadius: '999px',
    background: 'rgba(45, 212, 191, 0.14)',
    border: '1px solid rgba(45, 212, 191, 0.3)',
    color: '#99f6e4',
    fontSize: '12px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  emptyState: {
    padding: '18px',
    borderRadius: '16px',
    background: 'var(--card)',
    border: '1px dashed rgba(148, 163, 184, 0.2)',
    color: 'var(--muted)',
  },
  panel: {
    padding: '24px',
    borderRadius: '22px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
  },
  panelHeader: {
    marginBottom: '18px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
    gap: '12px',
    marginBottom: '20px',
  },
  input: {
    minWidth: '220px',
    padding: '12px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: '#e5eef8',
  },
  textarea: {
    minHeight: '110px',
    padding: '12px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: '#e5eef8',
    resize: 'vertical',
  },
  primaryButton: {
    padding: '12px 16px',
    borderRadius: '12px',
    border: 'none',
    background: '#0f766e',
    color: 'var(--text)',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryButton: {
    padding: '10px 14px',
    borderRadius: '12px',
    border: '1px solid var(--line)',
    background: 'transparent',
    color: '#e5eef8',
    cursor: 'pointer',
  },
  ruleList: {
    display: 'grid',
    gap: '12px',
  },
  ruleCard: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'center',
    padding: '16px 18px',
    borderRadius: '16px',
    background: 'rgba(8, 15, 30, 0.72)',
    border: '1px solid var(--line)',
  },
  ruleName: {
    display: 'block',
    marginBottom: '6px',
    fontSize: '16px',
  },
  ruleMeta: {
    margin: 0,
    color: 'var(--muted)',
    fontSize: '14px',
  },
};
