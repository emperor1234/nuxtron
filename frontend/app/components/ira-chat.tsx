'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, DEFAULT_TENANT_ID } from '../lib/api-client';
import {
  buildIraChatContext,
  extractIraBackendMeta,
  extractIraBackendReply,
  getBackendErrorMessage,
  type IraBackendMeta,
  type IraChatProviderPreference,
} from './ira-chat-utils';

type Message = {
  role: 'assistant' | 'user';
  text: string;
  meta?: IraBackendMeta;
};

type IraProviderReadiness = {
  label?: string;
  configured?: boolean;
  model?: string;
  route?: string;
  reason?: string;
};

type IraProviderReadinessMap = Record<string, IraProviderReadiness>;

type IraPlaybookSummary = {
  completionPercentage: number;
  achieved: number;
  total: number;
  leadQuestion: string;
};

const EMPTY_PLAYBOOK_SUMMARY: IraPlaybookSummary = {
  completionPercentage: 0,
  achieved: 0,
  total: 0,
  leadQuestion: '',
};

const IRA_SYSTEM_HINT = 'I can plan SEO, social, ads, billing, or support work and return a guarded next step.';

const QUICK_PROMPTS = ['Run an SEO audit', 'Build a social plan', 'Optimise ad spend', 'Check billing risk'];

function formatConfidence(confidence: number | undefined): string | null {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) {
    return null;
  }

  return `${Math.round(confidence * 100)}% confidence`;
}

function statusClassName(
  status: 'checking' | 'online' | 'degraded',
  checkingClass: string,
  degradedClass: string
): string {
  if (status === 'checking') {
    return checkingClass;
  }

  if (status === 'degraded') {
    return degradedClass;
  }

  return '';
}

function isProviderReady(readiness: IraProviderReadinessMap, providerKey: 'openai' | 'anthropic'): boolean {
  return readiness[providerKey]?.configured === true;
}

function getUnavailableRouteReason(
  providerPreference: IraChatProviderPreference,
  openaiReady: boolean,
  anthropicReady: boolean
): string {
  if (providerPreference === 'openai' && !openaiReady) {
    return 'OpenAI route unavailable until provider is configured.';
  }
  if (providerPreference === 'anthropic' && !anthropicReady) {
    return 'Claude route unavailable until provider is configured.';
  }
  return '';
}

function optionLabel(label: string, ready: boolean): string {
  return ready ? label : `${label} (unavailable)`;
}

function buildUnavailableProviderBadges(readiness: IraProviderReadinessMap): string[] {
  const badges: string[] = [];
  if (readiness.openai?.configured !== true) {
    badges.push(`OpenAI: ${readiness.openai?.reason || 'Missing provider credentials/configuration'}`);
  }
  if (readiness.anthropic?.configured !== true) {
    badges.push(`Claude: ${readiness.anthropic?.reason || 'Missing provider credentials/configuration'}`);
  }
  return badges;
}

function normalizePlaybookSummary(payload: unknown): IraPlaybookSummary {
  const data = typeof payload === 'object' && payload !== null ? (payload as Record<string, unknown>) : {};
  const chart =
    typeof data.completion_chart === 'object' && data.completion_chart !== null
      ? (data.completion_chart as Record<string, unknown>)
      : {};
  const decisionTree = Array.isArray(data.decision_tree) ? data.decision_tree : [];
  const firstNode = decisionTree[0];
  const firstNodeMap = typeof firstNode === 'object' && firstNode !== null ? (firstNode as Record<string, unknown>) : {};

  return {
    completionPercentage:
      typeof chart.percentage === 'number' && Number.isFinite(chart.percentage) ? Number(chart.percentage) : 0,
    achieved: typeof chart.achieved === 'number' && Number.isFinite(chart.achieved) ? Number(chart.achieved) : 0,
    total: typeof chart.total === 'number' && Number.isFinite(chart.total) ? Number(chart.total) : 0,
    leadQuestion: typeof firstNodeMap.question === 'string' ? firstNodeMap.question : '',
  };
}

async function loadIraStatusAndPlaybook(tenantId: string): Promise<{
  status: 'ok' | 'degraded';
  providerReadiness: IraProviderReadinessMap;
  playbookSummary: IraPlaybookSummary;
}> {
  const statusPayload = await apiGet('/ira/status', tenantId);
  const status = typeof statusPayload.status === 'string' && statusPayload.status !== 'ok' ? 'degraded' : 'ok';
  const providerReadiness =
    typeof statusPayload.provider_readiness === 'object' && statusPayload.provider_readiness !== null
      ? (statusPayload.provider_readiness as IraProviderReadinessMap)
      : {};

  try {
    const playbookPayload = await apiGet('/ira/playbook', tenantId);
    return {
      status,
      providerReadiness,
      playbookSummary: normalizePlaybookSummary(playbookPayload),
    };
  } catch {
    return {
      status,
      providerReadiness,
      playbookSummary: EMPTY_PLAYBOOK_SUMMARY,
    };
  }
}

function IraMessageMeta({ meta }: Readonly<{ meta: NonNullable<Message['meta']> }>) {
  return (
    <div style={{ display: 'grid', gap: 6, marginTop: 10 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {formatConfidence(meta.confidence) ? (
          <span style={{ fontSize: 11, opacity: 0.8 }}>{formatConfidence(meta.confidence)}</span>
        ) : null}
        {meta.intent ? <span style={{ fontSize: 11, opacity: 0.8 }}>Intent: {meta.intent}</span> : null}
        {meta.domain ? <span style={{ fontSize: 11, opacity: 0.8 }}>Domain: {meta.domain}</span> : null}
        {meta.riskLevel ? <span style={{ fontSize: 11, opacity: 0.8 }}>Risk: {meta.riskLevel}</span> : null}
        {meta.providerUsed ? <span style={{ fontSize: 11, opacity: 0.8 }}>Provider: {meta.providerUsed}</span> : null}
        {meta.providerStatus ? <span style={{ fontSize: 11, opacity: 0.8 }}>Route: {meta.providerStatus}</span> : null}
      </div>
      {meta.providerModel ? (
        <div style={{ fontSize: 11, opacity: 0.72 }}>Model: {meta.providerModel}</div>
      ) : null}
      {meta.actionLabels?.length ? (
        <div>
          <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Recommended actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {meta.actionLabels.slice(0, 3).map((label) => (
              <span
                key={label}
                style={{
                  fontSize: 11,
                  padding: '4px 8px',
                  borderRadius: 999,
                  border: '1px solid rgba(27, 199, 255, 0.22)',
                  background: 'rgba(27, 199, 255, 0.08)',
                }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {meta.knowledgeHits?.length ? (
        <div style={{ fontSize: 11, opacity: 0.75 }}>Knowledge hits: {meta.knowledgeHits.join(' | ')}</div>
      ) : null}
    </div>
  );
}

function IraMessageRow({ message }: Readonly<{ message: Message }>) {
  return (
    <div className={`ira-row ${message.role === 'user' ? 'ira-row-user' : ''}`}>
      <div className={`ira-avatar ${message.role === 'user' ? 'ira-avatar-user' : 'ira-avatar-bot'}`}>
        {message.role === 'user' ? 'You' : 'IRA'}
      </div>
      <div
        className={`ira-bubble ${message.role === 'user' ? 'ira-bubble-user' : 'ira-bubble-assistant'} ira-msg ira-msg-${message.role}`}
      >
        <div>{message.text}</div>
        {message.meta ? <IraMessageMeta meta={message.meta} /> : null}
      </div>
    </div>
  );
}

function IraProviderRouteSection({
  providerPreference,
  customProvider,
  openaiReady,
  anthropicReady,
  providerReadiness,
  playbookSummary,
  unavailableRouteBadges,
  unavailableRouteReason,
  sending,
  onProviderPreferenceChange,
  onCustomProviderChange,
}: Readonly<{
  providerPreference: IraChatProviderPreference;
  customProvider: string;
  openaiReady: boolean;
  anthropicReady: boolean;
  providerReadiness: IraProviderReadinessMap;
  playbookSummary: IraPlaybookSummary;
  unavailableRouteBadges: string[];
  unavailableRouteReason: string;
  sending: boolean;
  onProviderPreferenceChange: (value: IraChatProviderPreference) => void;
  onCustomProviderChange: (value: string) => void;
}>) {
  const missingCount = unavailableRouteBadges.length;
  return (
    <details className="ira-settings">
      <summary>
        Route and playbook
        {missingCount ? ` · ${missingCount} provider${missingCount === 1 ? '' : 's'} need setup` : ''}
      </summary>
      <div className="ira-settings-body">
      <label style={{ display: 'grid', gap: 4, fontSize: 12 }}>
        <span>Provider route</span>
        <select
          aria-label="IRA provider route"
          value={providerPreference}
          onChange={(event) => onProviderPreferenceChange(event.target.value as IraChatProviderPreference)}
          disabled={sending}
        >
          <option value="auto">Auto / internal default</option>
          <option value="internal">Internal only</option>
          <option value="openai" disabled={!openaiReady}>
            {optionLabel('ChatGPT / OpenAI', openaiReady)}
          </option>
          <option value="anthropic" disabled={!anthropicReady}>
            {optionLabel('Claude / Anthropic', anthropicReady)}
          </option>
          <option value="custom">Custom provider key</option>
        </select>
      </label>
      {providerPreference === 'custom' ? (
        <input
          value={customProvider}
          onChange={(event) => onCustomProviderChange(event.target.value)}
          placeholder="custom provider key, e.g. claude-enterprise"
          aria-label="Custom IRA provider"
          disabled={sending}
        />
      ) : null}
      <div style={{ fontSize: 11, opacity: 0.72 }}>
        Auto uses the internal route until OpenAI or Claude is configured.
      </div>
      <div style={{ fontSize: 11, opacity: 0.72 }}>
        OpenAI: {providerReadiness.openai?.configured ? 'ready' : 'not configured'} | Claude:{' '}
        {providerReadiness.anthropic?.configured ? 'ready' : 'not configured'}
      </div>
      <div style={{ fontSize: 11, opacity: 0.72 }}>OpenAI reason: {providerReadiness.openai?.reason || 'n/a'}</div>
      <div style={{ fontSize: 11, opacity: 0.72 }}>
        Claude reason: {providerReadiness.anthropic?.reason || 'n/a'}
      </div>
      <div style={{ fontSize: 11, opacity: 0.72 }}>
        Playbook completion: {playbookSummary.completionPercentage.toFixed(2)}% ({playbookSummary.achieved}/
        {playbookSummary.total})
      </div>
      {playbookSummary.leadQuestion ? (
        <div style={{ fontSize: 11, opacity: 0.72 }}>Playbook focus: {playbookSummary.leadQuestion}</div>
      ) : null}
      {unavailableRouteBadges.length ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {unavailableRouteBadges.map((badge) => (
            <span
              key={badge}
              style={{
                fontSize: 10,
                padding: '2px 8px',
                borderRadius: 999,
                border: '1px solid rgba(245, 158, 11, 0.35)',
                background: 'rgba(245, 158, 11, 0.12)',
              }}
            >
              {badge}
            </span>
          ))}
        </div>
      ) : null}
      {unavailableRouteReason ? <div style={{ fontSize: 11, color: '#b45309' }}>{unavailableRouteReason}</div> : null}
      </div>
    </details>
  );
}

export default function IraChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', text: IRA_SYSTEM_HINT }]);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'degraded'>('checking');
  const [statusText, setStatusText] = useState('Verifying backend status');
  const [providerPreference, setProviderPreference] = useState<IraChatProviderPreference>('auto');
  const [customProvider, setCustomProvider] = useState('');
  const [providerReadiness, setProviderReadiness] = useState<Record<string, IraProviderReadiness>>({});
  const [playbookSummary, setPlaybookSummary] = useState<IraPlaybookSummary>(EMPTY_PLAYBOOK_SUMMARY);
  const [statusRefreshToken, setStatusRefreshToken] = useState(0);

  const canSend = useMemo(() => input.trim().length > 1, [input]);
  const openaiReady = isProviderReady(providerReadiness, 'openai');
  const anthropicReady = isProviderReady(providerReadiness, 'anthropic');
  const unavailableRouteBadges = buildUnavailableProviderBadges(providerReadiness);
  const unavailableRouteReason = getUnavailableRouteReason(providerPreference, openaiReady, anthropicReady);
  const statusRowClass = statusClassName(backendStatus, 'ira-status-row-checking', 'ira-status-row-degraded');
  const statusDotClass = statusClassName(backendStatus, 'ira-status-dot-checking', 'ira-status-dot-degraded');

  useEffect(() => {
    if (!open) {
      return;
    }

    let active = true;

    async function loadStatus() {
      setBackendStatus('checking');
      setStatusText('Verifying backend status');

      try {
        const payload = await loadIraStatusAndPlaybook(tenantId);
        if (!active) {
          return;
        }

        setBackendStatus(payload.status === 'ok' ? 'online' : 'degraded');
        setStatusText(payload.status === 'ok' ? 'Autonomy and connectors online' : 'Backend returned a degraded status');
        setProviderReadiness(payload.providerReadiness);
        setPlaybookSummary(payload.playbookSummary);
      } catch (err) {
        if (!active) {
          return;
        }

        setBackendStatus('degraded');
        setStatusText(getBackendErrorMessage(err).replace('⚠️ **IRA backend unavailable.** ', ''));
      }
    }

    void loadStatus();

    return () => {
      active = false;
    };
  }, [open, tenantId, statusRefreshToken]);

  useEffect(() => {
    if (providerPreference === 'openai' && !openaiReady) {
      setProviderPreference('auto');
      return;
    }
    if (providerPreference === 'anthropic' && !anthropicReady) {
      setProviderPreference('auto');
    }
  }, [providerPreference, openaiReady, anthropicReady]);

  async function send() {
    const trimmed = input.trim();
    if (!trimmed) return;

    setSending(true);
    const baseline: Message[] = [...messages, { role: 'user', text: trimmed }];
    setMessages(baseline);
    setInput('');

    try {
      const data = await apiPost(
        '/ira/chat',
        {
          role: 'customer',
          channel: 'chat',
          message: trimmed,
          context: buildIraChatContext(
            {
              source: 'floating_widget',
              availability: '24x7',
            },
            {
              providerPreference,
              customProvider,
            }
          ),
        },
        tenantId
      );

      const response =
        extractIraBackendReply(data) ||
        'IRA completed the request, but the backend did not return a response body for this session.';

      setBackendStatus('online');
      setStatusText('Autonomy and connectors online');
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: response, meta: extractIraBackendMeta(data) || undefined },
      ]);
    } catch (ex) {
      setBackendStatus('degraded');
      setStatusText('Chat failed over to degraded mode');
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: getBackendErrorMessage(ex) },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="ira-shell" aria-live="polite">
      <button
        className="ira-trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="ira-panel"
        aria-label="Toggle IRA AI Agent"
      >
        <span className="ira-trigger-label">IRA AI Agent</span>
      </button>
      {open ? (
        <section id="ira-panel" className="ira-panel ira-panel-open" aria-label="IRA assistant chat">
          <header className="ira-head">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="ira-head-avatar">IR</div>
              <div>
                <strong>IRA</strong>
                <div className={`ira-status-row ${statusRowClass}`}>
                  <span className={`ira-status-dot ${statusDotClass}`} />
                  <span>{statusText}</span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                className="ira-close-btn"
                onClick={() => setStatusRefreshToken((current) => current + 1)}
                aria-label="Refresh IRA status"
                disabled={backendStatus === 'checking'}
                title="Refresh status and playbook"
              >
                Refresh
              </button>
              <button className="ira-close-btn" onClick={() => setOpen(false)} aria-label="Close IRA assistant">
                Close
              </button>
            </div>
          </header>
          <div className="ira-messages">
            {messages.map((message, index) => (
              <IraMessageRow key={`${message.role}-${index}`} message={message} />
            ))}
            {sending ? (
              <div className="ira-row">
                <div className="ira-avatar ira-avatar-bot">IRA</div>
                <div className="ira-bubble ira-bubble-assistant">
                  <span className="ira-typing-dots" aria-label="IRA is typing">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              </div>
            ) : null}
          </div>
          <div className="ira-quick-prompts">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="ira-chip"
                onClick={() => setInput(prompt)}
                disabled={sending}
              >
                {prompt}
              </button>
            ))}
          </div>
          <div className="ira-compose">
            <IraProviderRouteSection
              providerPreference={providerPreference}
              customProvider={customProvider}
              openaiReady={openaiReady}
              anthropicReady={anthropicReady}
              providerReadiness={providerReadiness}
              playbookSummary={playbookSummary}
              unavailableRouteBadges={unavailableRouteBadges}
              unavailableRouteReason={unavailableRouteReason}
              sending={sending}
              onProviderPreferenceChange={setProviderPreference}
              onCustomProviderChange={setCustomProvider}
            />
            <div className="ira-compose-row">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask IRA to run Social, Ads, or SEO"
                aria-label="Message IRA"
              />
              <button
                className="ira-send-btn"
                onClick={() => {
                  void send();
                }}
                disabled={!canSend || sending}
              >
                {sending ? '...' : 'Send'}
              </button>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
