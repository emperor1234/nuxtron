'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type CxaoFrictionPoint = {
  issue?: string;
  impact?: string;
  fix?: string;
};

type CxaoResponseTemplate = {
  opening?: string;
  structure?: string[];
  cta?: string;
};

type CxaoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  experience_optimization_score?: number;
  conversation_clarity_score?: number;
  answer_relevance_score?: number;
  actionability_score?: number;
  friction_points?: CxaoFrictionPoint[];
  optimization_playbook?: string[];
  response_template?: CxaoResponseTemplate;
};

export default function CxaoPage() {
  const [assistantSurface, setAssistantSurface] = useState('chat_assistant');
  const [primaryIntent, setPrimaryIntent] = useState(
    'Help users choose the right plan with clear, confidence-building answers'
  );
  const [conversationContext, setConversationContext] = useState(
    'User asks pricing differences, onboarding effort, and expected ROI. Assistant should provide concise comparison and a clear next step.'
  );
  const [successCriteria, setSuccessCriteria] = useState(
    'higher answer clarity, faster task completion, stronger CTA follow-through'
  );
  const [aiModel, setAiModel] = useState('llama3');
  const [ragEnabled, setRagEnabled] = useState(true);
  const [posthogEnabled, setPosthogEnabled] = useState(true);
  const [posthogEvents, setPosthogEvents] = useState('chat_started\nchat_completed\ncta_clicked');
  const [result, setResult] = useState<CxaoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!primaryIntent.trim() || !conversationContext.trim()) {
      setError('Primary intent and conversation context are required.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await apiSend<CxaoResult>(
        '/seo-platform/cxao/analyze',
        'POST',
        {
          assistant_surface: assistantSurface.trim(),
          primary_intent: primaryIntent.trim(),
          conversation_context: conversationContext.trim(),
          success_criteria: successCriteria
            .split(',')
            .map((v) => v.trim())
            .filter(Boolean),
          ai_model: aiModel.trim(),
          rag_enabled: ragEnabled,
          chat_ui_framework: 'nextjs',
          posthog_enabled: posthogEnabled,
          posthog_events: posthogEvents
            .split('\n')
            .map((v) => v.trim())
            .filter(Boolean),
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }

      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Experience optimization analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const card = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 980, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>CXAO</h1>
        <p style={{ color: 'var(--muted)' }}>Conversational experience answer optimization for assistants and chat.</p>

        {error && <div style={{ ...card, color: '#f87171' }}>{error}</div>}

        <section style={card}>
          <label htmlFor="cxao-surface" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            Assistant Surface
          </label>
          <input
            id="cxao-surface"
            style={input}
            value={assistantSurface}
            onChange={(e) => setAssistantSurface(e.target.value)}
            placeholder="chat_assistant"
          />

          <label
            htmlFor="cxao-primary-intent"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Primary Intent
          </label>
          <input
            id="cxao-primary-intent"
            style={input}
            value={primaryIntent}
            onChange={(e) => setPrimaryIntent(e.target.value)}
            placeholder="What should the assistant optimize for?"
          />

          <label
            htmlFor="cxao-conversation-context"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Conversation Context
          </label>
          <textarea
            id="cxao-conversation-context"
            style={{ ...input, minHeight: 120 }}
            value={conversationContext}
            onChange={(e) => setConversationContext(e.target.value)}
            placeholder="Paste representative dialogue or scenario context"
          />

          <label
            htmlFor="cxao-success-criteria"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            Success Criteria
          </label>
          <input
            id="cxao-success-criteria"
            style={input}
            value={successCriteria}
            onChange={(e) => setSuccessCriteria(e.target.value)}
            placeholder="comma-separated goals"
          />

          <label htmlFor="cxao-ai-model" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
            AI Model
          </label>
          <input
            id="cxao-ai-model"
            style={{ ...input, maxWidth: 280 }}
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
            placeholder="llama3"
          />

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 8 }}>
            <input type="checkbox" checked={ragEnabled} onChange={(e) => setRagEnabled(e.target.checked)} /> Enable RAG
            context
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 8 }}>
            <input type="checkbox" checked={posthogEnabled} onChange={(e) => setPosthogEnabled(e.target.checked)} />{' '}
            Enable PostHog flow optimization
          </label>

          <label
            htmlFor="cxao-posthog-events"
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
          >
            PostHog Events (one per line)
          </label>
          <textarea
            id="cxao-posthog-events"
            style={{ ...input, minHeight: 80 }}
            value={posthogEvents}
            onChange={(e) => setPosthogEvents(e.target.value)}
            placeholder="chat_started&#10;chat_completed&#10;cta_clicked"
          />

          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Optimizing conversation experience...' : 'Analyze Experience Optimization'}
          </button>
          {loading && (
            <div
              style={{
                marginTop: 12,
                padding: '10px 14px',
                borderRadius: 8,
                background: 'rgba(27,199,255,0.08)',
                border: '1px solid rgba(27,199,255,0.2)',
                fontSize: 13,
                color: 'var(--muted)',
              }}
            >
              AI is analyzing conversational friction and response quality. This may take 20-40 s.
            </div>
          )}
        </section>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background:
                        result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: 'rgba(56,189,248,0.12)',
                      color: '#38bdf8',
                    }}
                  >
                    Cached result
                  </span>
                )}
              </div>
            )}

            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Experience Optimization</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.experience_optimization_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Conversation Clarity</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.conversation_clarity_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Answer Relevance</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.answer_relevance_score ?? '--'}</div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Actionability</div>
                <div style={{ fontSize: 24, fontWeight: 800 }}>{result.actionability_score ?? '--'}</div>
              </div>
            </section>

            {(result.friction_points ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Friction Points</h3>
                {(result.friction_points ?? []).map((item) => (
                  <div
                    key={`${item.issue ?? 'friction'}-${item.fix ?? 'fix'}`}
                    style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.issue ?? '--'} {item.impact ? `(${item.impact})` : ''}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.fix ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.optimization_playbook ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Optimization Playbook</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.optimization_playbook ?? []).map((item) => (
                    <li key={item} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {result.response_template && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Response Template</h3>
                <div style={{ fontSize: 12, marginBottom: 6 }}>
                  <strong>Opening:</strong> {result.response_template.opening ?? '--'}
                </div>
                <div style={{ fontSize: 12, marginBottom: 6 }}>
                  <strong>Structure:</strong> {(result.response_template.structure ?? []).join(' -> ')}
                </div>
                <div style={{ fontSize: 12 }}>
                  <strong>CTA:</strong> {result.response_template.cta ?? '--'}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
