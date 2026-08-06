'use client';

import { FormEvent, useState } from 'react';

import { DEFAULT_TENANT_ID, apiSend } from '@/app/lib/platform-api';

type AssistResponse = {
  status: string;
  assist: {
    answer_summary: string;
    recommended_actions: string[];
    workflow_handoffs: string[];
  };
};

export default function PromptwatchAssistPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [prompt, setPrompt] = useState('Summarize top Promptwatch rollout blockers and recommend release actions.');
  const [response, setResponse] = useState<AssistResponse | null>(null);

  async function submitPrompt(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const result = await apiSend<AssistResponse>(
        '/search-everywhere/promptwatch/assist/chat',
        'POST',
        {
          prompt,
          include_vendor_context: true,
        },
        tenantId
      );
      setResponse(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run Promptwatch Assist prompt');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Promptwatch Assist</p>
        <h1>Assist Prompt Console</h1>
        <p>Run Promptwatch prompts against parity, gate, and vendor context to generate release guidance.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <form onSubmit={(event) => void submitPrompt(event)} style={{ display: 'grid', gap: 12 }}>
          <label htmlFor="prompt" style={{ fontWeight: 600 }}>
            Prompt
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={5}
            style={{ width: '100%' }}
          />
          <div>
            <button type="submit" disabled={loading}>
              {loading ? 'Running...' : 'Run Assist'}
            </button>
          </div>
        </form>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      {response ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Assist Response</h3>
          <p>{response.assist.answer_summary}</p>
          <h4>Recommended Actions</h4>
          <ul className="bullet-list">
            {response.assist.recommended_actions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <h4>Workflow Handoffs</h4>
          <ul className="bullet-list">
            {response.assist.workflow_handoffs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
