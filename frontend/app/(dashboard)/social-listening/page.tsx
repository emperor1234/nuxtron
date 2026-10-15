'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent, type KeyboardEvent } from 'react';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { Badge, Button, Card, CardTitle, FieldSelect, Page, PageHeader, Stat } from '../_ui/kit';
import {
  parseListeningAlerts,
  parseListeningMentionResponse,
  parseListeningMentions,
  parseListeningRules,
  parseListeningSummary,
  type ListeningAlert,
  type ListeningMention,
  type ListeningRule,
  type ListeningSummary,
  type SocialPlatform,
} from './social-listening-model';
import styles from './social-listening.module.css';

type Tab = 'overview' | 'mentions' | 'alerts' | 'rules' | 'capture';
type Resource<T> = {
  status: 'loading' | 'refreshing' | 'ready' | 'error' | 'stale' | 'unavailable';
  data: T | null;
  error: string | null;
};
type ResourceKey = 'summary' | 'mentions' | 'alerts' | 'rules';
type ResourceSet = {
  summary: Resource<ListeningSummary>;
  mentions: Resource<ListeningMention[]>;
  alerts: Resource<ListeningAlert[]>;
  rules: Resource<ListeningRule[]>;
};
type MentionDraft = {
  platform: string;
  query: string;
  authorHandle: string;
  text: string;
  sentiment: string;
  engagementCount: string;
};
type RuleDraft = {
  name: string;
  query: string;
  platform: string;
  minEngagement: string;
  negativeOnly: boolean;
};
type FieldErrors = Record<string, string>;

type SettledResource<T> = { data: T | null; error: string | null };

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'mentions', label: 'Mentions' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'rules', label: 'Alert rules' },
  { id: 'capture', label: 'Manual capture' },
];

const PLATFORMS: Array<{ value: SocialPlatform; label: string }> = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'x', label: 'X' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'reddit', label: 'Reddit' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'news', label: 'News' },
];

const EMPTY_MENTION: MentionDraft = {
  platform: '', query: '', authorHandle: '', text: '', sentiment: '', engagementCount: '',
};
const EMPTY_RULE: RuleDraft = {
  name: '', query: '', platform: '', minEngagement: '', negativeOnly: false,
};
const EMPTY_RESOURCE = <T,>(): Resource<T> => ({ status: 'loading', data: null, error: null });
const EMPTY_RESOURCES: ResourceSet = {
  summary: EMPTY_RESOURCE(), mentions: EMPTY_RESOURCE(), alerts: EMPTY_RESOURCE(), rules: EMPTY_RESOURCE(),
};
const NO_MENTIONS: ListeningMention[] = [];
const NO_ALERTS: ListeningAlert[] = [];
const NO_RULES: ListeningRule[] = [];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function settled<T>(
  outcome: PromiseSettledResult<unknown>,
  parse: (value: unknown) => T | null,
  label: string,
): SettledResource<T> {
  if (outcome.status === 'rejected') {
    return { data: null, error: outcome.reason instanceof Error ? outcome.reason.message : `${label} could not be loaded.` };
  }
  const data = parse(outcome.value);
  return data === null ? { data: null, error: `${label} service returned an incomplete response.` } : { data, error: null };
}

function applySettled<T>(current: Resource<T>, result: SettledResource<T>): Resource<T> {
  if (result.error) {
    return current.data === null
      ? { status: 'error', data: null, error: result.error }
      : { status: 'stale', data: current.data, error: result.error };
  }
  return { status: 'ready', data: result.data, error: null };
}

function emptyDraftErrors(): FieldErrors {
  return {};
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
    : 'Time unavailable';
}

function ResourceFeedback({ resource, label }: { resource: Resource<unknown>; label: string }) {
  if (resource.status === 'loading' || resource.status === 'refreshing') {
    return <p className={styles.status} role="status">{resource.status === 'refreshing' ? `Refreshing ${label.toLowerCase()}…` : `Loading ${label.toLowerCase()}…`}</p>;
  }
  if (resource.status === 'error' || resource.status === 'stale') {
    return <p className={styles.error} role="alert">{resource.status === 'stale' ? `Refresh failed; showing the last loaded ${label.toLowerCase()}. ` : ''}{resource.error}</p>;
  }
  if (resource.status === 'unavailable') return <p className={styles.error} role="alert">{resource.error}</p>;
  return null;
}

function statusTone(status: string): 'success' | 'danger' | 'neutral' {
  if (status === 'open') return 'danger';
  if (status === 'closed') return 'success';
  return 'neutral';
}

export default function SocialListeningPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [resources, setResources] = useState<ResourceSet>(EMPTY_RESOURCES);
  const [refreshing, setRefreshing] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [sentimentFilter, setSentimentFilter] = useState('all');
  const [targetMentionId, setTargetMentionId] = useState<number | null>(null);
  const [mentionDraft, setMentionDraft] = useState<MentionDraft>({ ...EMPTY_MENTION });
  const [ruleDraft, setRuleDraft] = useState<RuleDraft>({ ...EMPTY_RULE });
  const [mentionErrors, setMentionErrors] = useState<FieldErrors>({});
  const [ruleErrors, setRuleErrors] = useState<FieldErrors>({});
  const [busyAction, setBusyAction] = useState<'capture' | 'rule' | null>(null);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

  const loadData = useCallback(async () => {
    if (!tenantId) {
      const unavailable = <T,>(): Resource<T> => ({ status: 'unavailable', data: null, error: 'Sign in to a workspace to load Social Listening data.' });
      setResources({ summary: unavailable(), mentions: unavailable(), alerts: unavailable(), rules: unavailable() });
      setRefreshing(false);
      return;
    }

    setRefreshing(true);
    setResources((current) => ({
      summary: { ...current.summary, status: current.summary.data ? 'refreshing' : 'loading', error: null },
      mentions: { ...current.mentions, status: current.mentions.data ? 'refreshing' : 'loading', error: null },
      alerts: { ...current.alerts, status: current.alerts.data ? 'refreshing' : 'loading', error: null },
      rules: { ...current.rules, status: current.rules.data ? 'refreshing' : 'loading', error: null },
    }));

    const results = await Promise.allSettled([
      apiGet<unknown>('/social/listening/summary', tenantId),
      apiGet<unknown>('/social/listening/mentions', tenantId),
      apiGet<unknown>('/social/listening/alerts', tenantId),
      apiGet<unknown>('/social/listening/rules', tenantId),
    ]);
    const [summaryResult, mentionsResult, alertsResult, rulesResult] = results;
    setResources((current) => ({
      summary: applySettled(current.summary, settled(summaryResult, parseListeningSummary, 'Summary')),
      mentions: applySettled(current.mentions, settled(mentionsResult, parseListeningMentions, 'Mentions')),
      alerts: applySettled(current.alerts, settled(alertsResult, parseListeningAlerts, 'Alerts')),
      rules: applySettled(current.rules, settled(rulesResult, parseListeningRules, 'Alert rules')),
    }));
    setLastRefreshedAt(new Date().toISOString());
    setRefreshing(false);
  }, [tenantId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadData(); }, 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  const mentions = resources.mentions.data ?? NO_MENTIONS;
  const alerts = resources.alerts.data ?? NO_ALERTS;
  const rules = resources.rules.data ?? NO_RULES;
  const summary = resources.summary.data;
  const openAlerts = useMemo(() => alerts.filter((alert) => alert.status === 'open'), [alerts]);
  const visibleMentions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return mentions.filter((mention) => {
      const matchesText = !normalizedQuery || [mention.text, mention.query, mention.authorHandle].some((value) => value.toLowerCase().includes(normalizedQuery));
      const matchesPlatform = platformFilter === 'all' || mention.platform === platformFilter;
      const matchesSentiment = sentimentFilter === 'all' || mention.sentiment === sentimentFilter;
      return matchesText && matchesPlatform && matchesSentiment;
    });
  }, [mentions, platformFilter, query, sentimentFilter]);

  function openMention(mentionId: number) {
    setTargetMentionId(mentionId);
    setActiveTab('mentions');
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const current = TABS.findIndex((tab) => tab.id === activeTab);
    let next = current;
    if (event.key === 'ArrowRight') next = (current + 1) % TABS.length;
    else if (event.key === 'ArrowLeft') next = (current - 1 + TABS.length) % TABS.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = TABS.length - 1;
    else return;
    event.preventDefault();
    const tab = TABS[next];
    setActiveTab(tab.id);
    document.getElementById(`social-listening-tab-${tab.id}`)?.focus();
  }

  function updateMentionDraft(key: keyof MentionDraft, value: string) {
    setMentionDraft((current) => ({ ...current, [key]: value }));
    setMentionErrors((current) => { const next = { ...current }; delete next[key]; return next; });
  }

  function updateRuleDraft(key: keyof RuleDraft, value: string | boolean) {
    setRuleDraft((current) => ({ ...current, [key]: value }));
    setRuleErrors((current) => { const next = { ...current }; delete next[key]; return next; });
  }

  async function submitMention(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionMessage('');
    setActionError('');
    const engagement = Number(mentionDraft.engagementCount);
    const errors: FieldErrors = {};
    if (!PLATFORMS.some((item) => item.value === mentionDraft.platform)) errors.platform = 'Choose the source platform.';
    if (mentionDraft.query.trim().length < 2) errors.query = 'Enter the tracked query (at least 2 characters).';
    if (mentionDraft.authorHandle.trim().length < 1) errors.authorHandle = 'Enter the public author handle.';
    if (mentionDraft.text.trim().length < 3) errors.text = 'Enter at least 3 characters of mention text.';
    if (!['positive', 'neutral', 'negative'].includes(mentionDraft.sentiment)) errors.sentiment = 'Choose the observed sentiment.';
    if (!mentionDraft.engagementCount.trim() || !Number.isInteger(engagement) || engagement < 0 || engagement > 1_000_000) errors.engagementCount = 'Enter an observed whole-number count from 0 to 1,000,000.';
    setMentionErrors(errors);
    if (Object.keys(errors).length > 0 || !tenantId) return;

    setBusyAction('capture');
    try {
      const response = await apiSend<unknown>('/social/listening/ingest', 'POST', {
        platform: mentionDraft.platform,
        query: mentionDraft.query.trim(),
        author_handle: mentionDraft.authorHandle.trim(),
        text: mentionDraft.text.trim(),
        sentiment: mentionDraft.sentiment,
        engagement_count: engagement,
      }, tenantId);
      const created = parseListeningMentionResponse(response);
      if (!created) throw new Error('The service did not confirm a valid mention record.');
      setMentionDraft({ ...EMPTY_MENTION });
      setActionMessage('Mention recorded in temporary service memory. It may be lost when the service restarts.');
      await loadData();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'The mention could not be recorded.');
    } finally {
      setBusyAction(null);
    }
  }

  async function submitRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionMessage('');
    setActionError('');
    const minimum = Number(ruleDraft.minEngagement);
    const errors: FieldErrors = {};
    if (ruleDraft.name.trim().length < 2) errors.name = 'Enter a rule name with at least 2 characters.';
    if (!ruleDraft.minEngagement.trim() || !Number.isInteger(minimum) || minimum < 0 || minimum > 1_000_000) errors.minEngagement = 'Enter an observed threshold from 0 to 1,000,000.';
    if (ruleDraft.query.trim().length > 120) errors.query = 'Keep the query to 120 characters or fewer.';
    setRuleErrors(errors);
    if (Object.keys(errors).length > 0 || !tenantId) return;

    setBusyAction('rule');
    try {
      const response = await apiSend<unknown>('/social/listening/rules', 'POST', {
        name: ruleDraft.name.trim(),
        query: ruleDraft.query.trim() || null,
        platform: ruleDraft.platform || null,
        min_engagement: minimum,
        negative_only: ruleDraft.negativeOnly,
      }, tenantId);
      if (!parseListeningRules({ status: 'ok', rules: [isRecord(response) ? response.rule : null] })) {
        throw new Error('The service did not confirm a valid alert rule.');
      }
      setRuleDraft({ ...EMPTY_RULE });
      setActionMessage('Alert rule recorded in temporary service memory. It may be lost when the service restarts.');
      await loadData();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'The alert rule could not be recorded.');
    } finally {
      setBusyAction(null);
    }
  }

  const renderResourceFeedback = (key: ResourceKey, label: string) => <ResourceFeedback resource={resources[key]} label={label} />;
  const tabId = `social-listening-tab-${activeTab}`;
  const panelId = `social-listening-panel-${activeTab}`;

  return (
    <Page>
      <PageHeader
        title="Social Listening"
        subtitle="Review and organize manually captured social mentions and alert rules for this workspace."
        actions={<Button type="button" onClick={() => void loadData()} disabled={refreshing || busyAction !== null}>Refresh data</Button>}
      />

      <div className={styles.notice} role="note">
        <strong>Manual capture only · temporary retention.</strong> This service does not monitor social networks or ingest provider feeds. Mentions, alerts, and rules use process memory and may be lost when the service restarts; do not rely on this page for permanent records or time-critical crisis monitoring.
      </div>

      {!tenantId ? <p className={styles.error} role="alert">Sign in to a workspace before using Social Listening.</p> : null}
      {actionMessage ? <p className={styles.status} role="status">{actionMessage}</p> : null}
      {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}

      <section className={styles.metricGrid} aria-label="Social Listening workspace summary">
        <Card><Stat label="Captured mentions" value={summary ? summary.totalMentions.toLocaleString() : '—'} /></Card>
        <Card><Stat label="Open alerts" value={summary ? summary.openAlerts.toLocaleString() : '—'} /></Card>
        <Card><Stat label="Alert rules" value={summary ? summary.ruleCount.toLocaleString() : '—'} /></Card>
        <Card><Stat label="Negative mentions" value={summary ? summary.sentiment.negative.toLocaleString() : '—'} /></Card>
      </section>
      {renderResourceFeedback('summary', 'Summary')}
      {lastRefreshedAt ? <p className={styles.status}>Latest refresh attempt {formatTimestamp(lastRefreshedAt)}{refreshing ? ' · refresh in progress' : ''}</p> : null}

      <div className={styles.tabs} role="tablist" aria-label="Social Listening sections" onKeyDown={handleTabKeyDown}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            id={`social-listening-tab-${tab.id}`}
            className={styles.tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`social-listening-panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}{tab.id === 'alerts' && openAlerts.length ? ` (${openAlerts.length})` : ''}
          </button>
        ))}
      </div>

      {TABS.filter((tab) => tab.id !== activeTab).map((tab) => (
        <section key={tab.id} id={`social-listening-panel-${tab.id}`} role="tabpanel" aria-labelledby={`social-listening-tab-${tab.id}`} hidden />
      ))}
      <section id={panelId} role="tabpanel" aria-labelledby={tabId} tabIndex={0} className={styles.panel}>
        {activeTab === 'overview' ? (
          <>
            <Card>
              <CardTitle>Open alerts requiring review</CardTitle>
              {renderResourceFeedback('alerts', 'Alerts')}
              {resources.alerts.data !== null && openAlerts.length === 0 ? <p className={styles.status}>No open alerts are recorded in this workspace.</p> : null}
              {openAlerts.slice(0, 5).map((alert) => {
                const related = mentions.find((mention) => mention.id === alert.mentionId);
                return (
                  <article key={alert.id} className={`${styles.row} ${alert.severity === 'high' ? styles.alertHigh : styles.alertMedium}`}>
                    <div className={styles.actions}>
                      <strong>{alert.ruleName}</strong>
                      <Badge tone={alert.severity === 'high' ? 'danger' : 'neutral'}>{alert.severity === 'high' ? 'High' : 'Medium'}</Badge>
                    </div>
                    <p className={styles.meta}>Created {formatTimestamp(alert.createdAt)} · mention {alert.mentionId}</p>
                    {related ? <p>{related.text}</p> : <p className={styles.status}>The related mention is not available in the current feed response.</p>}
                    {related ? <Button type="button" className={styles.action} onClick={() => openMention(related.id)}>View mention</Button> : null}
                  </article>
                );
              })}
            </Card>
            <Card>
              <CardTitle>Recent manual mentions</CardTitle>
              {renderResourceFeedback('mentions', 'Mentions')}
              {resources.mentions.data !== null && mentions.length === 0 ? <p className={styles.status}>No mentions have been captured in this workspace.</p> : null}
              <div className={styles.list}>
                {mentions.slice(0, 5).map((mention) => (
                  <article key={mention.id} className={styles.row}>
                    <div className={styles.actions}><strong>{mention.authorHandle}</strong><Badge tone={mention.sentiment === 'negative' ? 'danger' : mention.sentiment === 'positive' ? 'success' : 'neutral'}>{mention.sentiment}</Badge></div>
                    <p>{mention.text}</p>
                    <p className={styles.meta}>{mention.query} · {PLATFORMS.find((item) => item.value === mention.platform)?.label} · {formatTimestamp(mention.createdAt)}</p>
                  </article>
                ))}
              </div>
            </Card>
          </>
        ) : null}

        {activeTab === 'mentions' ? (
          <Card>
            <CardTitle sub="Only manually captured records are listed; no provider feed is connected here.">Mention log</CardTitle>
            {renderResourceFeedback('mentions', 'Mentions')}
            <div className={styles.formGrid} style={{ margin: '14px 0' }}>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="mention-search">Search mentions</label>
                <input id="mention-search" className={styles.input} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search text, query, or author" />
              </div>
              <FieldSelect id="mention-platform-filter" label="Platform" value={platformFilter} onChange={(event) => setPlatformFilter(event.target.value)}>
                <option value="all">All platforms</option>
                {PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </FieldSelect>
              <FieldSelect id="mention-sentiment-filter" label="Sentiment" value={sentimentFilter} onChange={(event) => setSentimentFilter(event.target.value)}>
                <option value="all">All sentiment</option>
                <option value="positive">Positive</option><option value="neutral">Neutral</option><option value="negative">Negative</option>
              </FieldSelect>
            </div>
            {resources.mentions.data !== null && mentions.length === 0 ? <p className={styles.status}>No mentions have been captured in this workspace.</p> : null}
            {resources.mentions.data !== null && mentions.length > 0 && visibleMentions.length === 0 ? <p className={styles.status}>No captured mentions match these filters.</p> : null}
            <div className={styles.list}>
              {visibleMentions.map((mention) => (
                <article id={`mention-${mention.id}`} key={mention.id} className={`${styles.row} ${targetMentionId === mention.id ? styles.rowTarget : ''}`}>
                  <div className={styles.actions}><strong>{mention.authorHandle}</strong><Badge tone={mention.sentiment === 'negative' ? 'danger' : mention.sentiment === 'positive' ? 'success' : 'neutral'}>{mention.sentiment}</Badge></div>
                  <p>{mention.text}</p>
                  <p className={styles.meta}>{mention.query} · {PLATFORMS.find((item) => item.value === mention.platform)?.label} · {mention.engagementCount.toLocaleString()} engagements · {formatTimestamp(mention.createdAt)}</p>
                </article>
              ))}
            </div>
          </Card>
        ) : null}

        {activeTab === 'alerts' ? (
          <Card>
            <CardTitle sub="Alerts are derived from manually captured mentions and the configured rules; this service does not monitor providers.">Alert review</CardTitle>
            {renderResourceFeedback('alerts', 'Alerts')}
            {resources.alerts.data !== null && alerts.length === 0 ? <p className={styles.status}>No alerts have been recorded in this workspace.</p> : null}
            <div className={styles.list}>
              {alerts.map((alert) => {
                const related = mentions.find((mention) => mention.id === alert.mentionId);
                return (
                  <article key={alert.id} className={`${styles.row} ${alert.severity === 'high' ? styles.alertHigh : styles.alertMedium}`}>
                    <div className={styles.actions}><strong>{alert.ruleName}</strong><Badge tone={alert.severity === 'high' ? 'danger' : 'neutral'}>{alert.severity === 'high' ? 'High' : 'Medium'}</Badge><Badge tone={statusTone(alert.status)}>{alert.status}</Badge></div>
                    <p className={styles.meta}>Created {formatTimestamp(alert.createdAt)} · mention {alert.mentionId}</p>
                    {related ? <p>{related.text}</p> : <p className={styles.status}>The related mention is not available in the current feed response.</p>}
                    {related ? <Button type="button" className={styles.action} onClick={() => openMention(related.id)}>View mention</Button> : null}
                  </article>
                );
              })}
            </div>
          </Card>
        ) : null}

        {activeTab === 'rules' ? (
          <>
            <Card>
              <CardTitle sub="Rules run only when a mention is manually captured. They are kept in temporary service memory.">Create an alert rule</CardTitle>
              <form noValidate onSubmit={(event) => void submitRule(event)} className={styles.formGrid} style={{ marginTop: 14 }}>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="rule-name">Rule name</label>
                  <input id="rule-name" className={styles.input} required maxLength={120} value={ruleDraft.name} onChange={(event) => updateRuleDraft('name', event.target.value)} aria-invalid={Boolean(ruleErrors.name)} aria-describedby={ruleErrors.name ? 'rule-name-error' : undefined} />
                  {ruleErrors.name ? <p id="rule-name-error" className={styles.error}>{ruleErrors.name}</p> : null}
                </div>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="rule-query">Tracked query (optional)</label>
                  <input id="rule-query" className={styles.input} maxLength={120} value={ruleDraft.query} onChange={(event) => updateRuleDraft('query', event.target.value)} aria-invalid={Boolean(ruleErrors.query)} aria-describedby={ruleErrors.query ? 'rule-query-error' : undefined} />
                  {ruleErrors.query ? <p id="rule-query-error" className={styles.error}>{ruleErrors.query}</p> : null}
                </div>
                <FieldSelect id="rule-platform" label="Platform filter (optional)" value={ruleDraft.platform} onChange={(event) => updateRuleDraft('platform', event.target.value)}>
                  <option value="">All platforms</option>{PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </FieldSelect>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="rule-threshold">Minimum engagement (enter 0 if none)</label>
                  <input id="rule-threshold" className={styles.input} type="number" min={0} max={1_000_000} step={1} required value={ruleDraft.minEngagement} onChange={(event) => updateRuleDraft('minEngagement', event.target.value)} aria-invalid={Boolean(ruleErrors.minEngagement)} aria-describedby={ruleErrors.minEngagement ? 'rule-threshold-error' : undefined} />
                  {ruleErrors.minEngagement ? <p id="rule-threshold-error" className={styles.error}>{ruleErrors.minEngagement}</p> : null}
                </div>
                <div className={`${styles.field} ${styles.fieldFull}`}>
                  <label className={styles.actions} htmlFor="rule-negative-only"><input id="rule-negative-only" type="checkbox" checked={ruleDraft.negativeOnly} onChange={(event) => updateRuleDraft('negativeOnly', event.target.checked)} /> Negative sentiment only</label>
                  <p className={styles.help}>Leave unchecked to allow every sentiment to meet this rule.</p>
                </div>
                <div className={`${styles.actions} ${styles.fieldFull}`}>
                  <Button type="submit" variant="primary" disabled={!tenantId || busyAction !== null}>{busyAction === 'rule' ? 'Saving rule…' : 'Create alert rule'}</Button>
                </div>
              </form>
            </Card>
            <Card>
              <CardTitle>Existing rules</CardTitle>
              {renderResourceFeedback('rules', 'Alert rules')}
              {resources.rules.data !== null && rules.length === 0 ? <p className={styles.status}>No alert rules are configured in this workspace.</p> : null}
              <div className={styles.list}>
                {rules.map((rule) => (
                  <article key={rule.id} className={styles.row}>
                    <div className={styles.actions}><strong>{rule.name}</strong><Badge tone={rule.enabled ? 'success' : 'neutral'}>{rule.enabled ? 'Enabled' : 'Disabled'}</Badge></div>
                    <p className={styles.meta}>{rule.query ? `Query: ${rule.query} · ` : ''}{rule.platform ? `Platform: ${PLATFORMS.find((item) => item.value === rule.platform)?.label} · ` : ''}At least {rule.minEngagement.toLocaleString()} engagements · {rule.negativeOnly ? 'Negative sentiment only' : 'All sentiments'}</p>
                  </article>
                ))}
              </div>
            </Card>
          </>
        ) : null}

        {activeTab === 'capture' ? (
          <Card>
            <CardTitle sub="Enter values observed by your team. This form does not collect or fetch posts from social networks.">Capture a mention manually</CardTitle>
            <form noValidate onSubmit={(event) => void submitMention(event)} className={styles.formGrid} style={{ marginTop: 14 }}>
              <FieldSelect id="mention-platform" label="Source platform" value={mentionDraft.platform} onChange={(event) => updateMentionDraft('platform', event.target.value)} aria-invalid={Boolean(mentionErrors.platform)} aria-describedby={mentionErrors.platform ? 'mention-platform-error' : undefined}>
                <option value="">Choose a platform</option>{PLATFORMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </FieldSelect>
              {mentionErrors.platform ? <p id="mention-platform-error" className={styles.error}>{mentionErrors.platform}</p> : null}
              <div className={styles.field}>
                <label className={styles.label} htmlFor="mention-query">Tracked query</label>
                <input id="mention-query" className={styles.input} required minLength={2} maxLength={120} value={mentionDraft.query} onChange={(event) => updateMentionDraft('query', event.target.value)} aria-invalid={Boolean(mentionErrors.query)} aria-describedby={mentionErrors.query ? 'mention-query-error' : undefined} />
                {mentionErrors.query ? <p id="mention-query-error" className={styles.error}>{mentionErrors.query}</p> : null}
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="mention-author">Public author handle</label>
                <input id="mention-author" className={styles.input} required maxLength={120} value={mentionDraft.authorHandle} onChange={(event) => updateMentionDraft('authorHandle', event.target.value)} aria-invalid={Boolean(mentionErrors.authorHandle)} aria-describedby={mentionErrors.authorHandle ? 'mention-author-error' : undefined} />
                {mentionErrors.authorHandle ? <p id="mention-author-error" className={styles.error}>{mentionErrors.authorHandle}</p> : null}
              </div>
              <FieldSelect id="mention-sentiment" label="Observed sentiment" value={mentionDraft.sentiment} onChange={(event) => updateMentionDraft('sentiment', event.target.value)} aria-invalid={Boolean(mentionErrors.sentiment)} aria-describedby={mentionErrors.sentiment ? 'mention-sentiment-error' : undefined}>
                <option value="">Choose sentiment</option><option value="positive">Positive</option><option value="neutral">Neutral</option><option value="negative">Negative</option>
              </FieldSelect>
              {mentionErrors.sentiment ? <p id="mention-sentiment-error" className={styles.error}>{mentionErrors.sentiment}</p> : null}
              <div className={styles.field}>
                <label className={styles.label} htmlFor="mention-engagement">Observed engagement count (enter 0 if none)</label>
                <input id="mention-engagement" className={styles.input} type="number" min={0} max={1_000_000} step={1} required value={mentionDraft.engagementCount} onChange={(event) => updateMentionDraft('engagementCount', event.target.value)} aria-invalid={Boolean(mentionErrors.engagementCount)} aria-describedby={mentionErrors.engagementCount ? 'mention-engagement-error' : undefined} />
                {mentionErrors.engagementCount ? <p id="mention-engagement-error" className={styles.error}>{mentionErrors.engagementCount}</p> : null}
              </div>
              <div className={`${styles.field} ${styles.fieldFull}`}>
                <label className={styles.label} htmlFor="mention-text">Mention text</label>
                <textarea id="mention-text" className={styles.textArea} required minLength={3} maxLength={4000} value={mentionDraft.text} onChange={(event) => updateMentionDraft('text', event.target.value)} aria-invalid={Boolean(mentionErrors.text)} aria-describedby={mentionErrors.text ? 'mention-text-error' : 'mention-text-help'} />
                <p id="mention-text-help" className={styles.help}>{mentionDraft.text.length.toLocaleString()} / 4,000 characters. Avoid entering private or sensitive information.</p>
                {mentionErrors.text ? <p id="mention-text-error" className={styles.error}>{mentionErrors.text}</p> : null}
              </div>
              <div className={`${styles.actions} ${styles.fieldFull}`}>
                <Button type="submit" variant="primary" disabled={!tenantId || busyAction !== null}>{busyAction === 'capture' ? 'Recording…' : 'Record mention'}</Button>
                <Button type="button" disabled={busyAction !== null} onClick={() => { setMentionDraft({ ...EMPTY_MENTION }); setMentionErrors(emptyDraftErrors()); }}>Clear fields</Button>
              </div>
            </form>
          </Card>
        ) : null}
      </section>
    </Page>
  );
}
