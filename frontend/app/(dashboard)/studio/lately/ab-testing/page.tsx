'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type ABVariant = {
  variant_key: string;
  content: string;
  engagement_score?: number;
  is_winner?: boolean;
};

type ABTest = {
  test_key: string;
  name: string;
  channel: string;
  goal: string;
  status: string;
  variants_count: number;
  winner?: string;
  variants?: ABVariant[];
  created_at?: string;
};

type ABTestsResult = { tests?: ABTest[] };

const CHANNELS = ['linkedin', 'x', 'instagram', 'threads', 'tiktok', 'facebook'];
const GOALS = ['engagement', 'clicks', 'impressions', 'conversions', 'reach'];

const STATUS_COLORS: Record<string, string> = {
  draft: 'var(--muted)',
  running: '#facc15',
  concluded: '#15803d',
  archived: 'var(--muted)',
};

export default function ABTestingPage() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [evaluating, setEvaluating] = useState<string | null>(null);

  // Create form
  const [name, setName] = useState('Summer Campaign Test');
  const [baseContent, setBaseContent] = useState(
    'Our AI generates 200% more engagement than manually written posts. Here\'s the proof →'
  );
  const [channel, setChannel] = useState('linkedin');
  const [goal, setGoal] = useState('engagement');

  // Evaluate form: test_key → variant_key → score
  const [scores, setScores] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<ABTestsResult>('/experiments/ab-tests', DEFAULT_TENANT_ID);
      setTests(res.tests ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load tests');
    } finally {
      setLoading(false);
    }
  }

  async function createTest() {
    if (!baseContent.trim()) { setError('Base content is required.'); return; }
    setSubmitting(true);
    setError(null);
    try {
      await apiSend(
        '/experiments/ab-tests',
        'POST',
        { name, base_content: baseContent, channel, goal },
        DEFAULT_TENANT_ID
      );
      setName('Summer Campaign Test');
      setBaseContent('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create test failed');
    } finally {
      setSubmitting(false);
    }
  }

  async function evaluateTest(testKey: string) {
    setEvaluating(testKey);
    setError(null);
    try {
      const test = tests.find((t) => t.test_key === testKey);
      const variants = test?.variants ?? [];
      const engagementScores = variants.reduce<Record<string, number>>((acc, v) => {
        const raw = scores[testKey]?.[v.variant_key] ?? '';
        acc[v.variant_key] = Number.parseFloat(raw) || 0;
        return acc;
      }, {});
      await apiSend(
        `/experiments/ab-tests/${testKey}/evaluate`,
        'POST',
        { engagement_scores: engagementScores },
        DEFAULT_TENANT_ID
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Evaluate failed');
    } finally {
      setEvaluating(null);
    }
  }

  function setScore(testKey: string, variantKey: string, value: string) {
    setScores((prev) => ({
      ...prev,
      [testKey]: { ...prev[testKey], [variantKey]: value },
    }));
  }

  let testsContent: React.ReactNode;
  if (loading) {
    testsContent = <div style={s.skeleton}>Loading tests…</div>;
  } else if (tests.length === 0) {
    testsContent = <div style={s.empty}>No A/B tests yet. Create one above.</div>;
  } else {
    testsContent = tests.map((test) => {
      const isConcluded = test.status === 'concluded';
      return (
        <div key={test.test_key} style={s.testCard}>
          <div style={s.testHeader}>
            <div>
              <span style={s.testName}>{test.name}</span>
              <span style={{ ...s.statusBadge, color: STATUS_COLORS[test.status] ?? 'var(--muted)', borderColor: STATUS_COLORS[test.status] ?? '#e7e9ef' }}>
                {test.status}
              </span>
            </div>
            <div style={s.metaRow}>
              <span style={s.metaChip}>{test.channel}</span>
              <span style={s.metaChip}>goal: {test.goal}</span>
              <span style={s.metaChip}>{test.variants_count} variants</span>
              <button
                onClick={() => setExpanded(expanded === test.test_key ? null : test.test_key)}
                style={s.expandBtn}
              >
                {expanded === test.test_key ? 'Collapse ↑' : 'View Variants ↓'}
              </button>
            </div>
          </div>

          {test.winner ? (
            <div style={s.winnerBanner}>
              🏆 Winner: <strong>{test.winner}</strong>
            </div>
          ) : null}

          {expanded === test.test_key && (test.variants ?? []).length > 0 ? (
            <div style={s.variantGrid}>
              {(test.variants ?? []).map((v) => (
                <div key={v.variant_key} style={{ ...s.variantCard, ...(v.is_winner ? s.winnerCard : {}) }}>
                  <div style={s.variantHeader}>
                    <span style={s.variantKey}>{v.variant_key}</span>
                    {v.is_winner ? <span style={s.winnerChip}>Winner</span> : null}
                    {v.engagement_score !== undefined && v.engagement_score > 0 ? (
                      <span style={s.scoreChip}>{v.engagement_score} eng.</span>
                    ) : null}
                  </div>
                  <p style={s.variantContent}>{v.content}</p>
                  {isConcluded ? null : (
                    <div style={s.scoreRow}>
                      <label htmlFor={`${test.test_key}-${v.variant_key}-score`} style={s.label}>Engagement Score</label>
                      <input
                        id={`${test.test_key}-${v.variant_key}-score`}
                        type="number"
                        value={scores[test.test_key]?.[v.variant_key] ?? ''}
                        onChange={(e) => setScore(test.test_key, v.variant_key, e.target.value)}
                        style={{ ...s.input, width: 100 }}
                        placeholder="0"
                        min={0}
                      />
                    </div>
                  )}
                </div>
              ))}
              {isConcluded ? null : (
                <div style={s.evaluateRow}>
                  <button
                    onClick={() => evaluateTest(test.test_key)}
                    disabled={evaluating === test.test_key}
                    style={s.evaluateBtn}
                  >
                    {evaluating === test.test_key ? 'Evaluating…' : '🏆 Evaluate & Declare Winner'}
                  </button>
                </div>
              )}
            </div>
          ) : null}
        </div>
      );
    });
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>A/B Testing Engine</h1>
        <p style={s.subtitle}>
          Generate 5 content variants from a single base post. Enter real engagement scores to auto-declare the winner
          and republish the top performer at optimal times.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      {/* Create Test */}
      <section style={s.card}>
        <h2 style={s.sectionTitle}>Create New A/B Test</h2>
        <div style={s.formGrid}>
          <div style={s.field}>
            <label htmlFor="ab-test-name" style={s.label}>Test Name</label>
            <input id="ab-test-name" value={name} onChange={(e) => setName(e.target.value)} style={s.input} placeholder="Test name" />
          </div>
          <div style={s.field}>
            <label htmlFor="ab-test-channel" style={s.label}>Channel</label>
            <select id="ab-test-channel" value={channel} onChange={(e) => setChannel(e.target.value)} style={s.input}>
              {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div style={s.field}>
            <label htmlFor="ab-test-goal" style={s.label}>Optimise For</label>
            <select id="ab-test-goal" value={goal} onChange={(e) => setGoal(e.target.value)} style={s.input}>
              {GOALS.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
        </div>
        <div style={s.field}>
          <label htmlFor="ab-test-base-content" style={s.label}>Base Content</label>
          <textarea
            id="ab-test-base-content"
            value={baseContent}
            onChange={(e) => setBaseContent(e.target.value)}
            style={s.textarea}
            placeholder="Paste your original post. The AI will generate 5 variants."
            rows={4}
          />
        </div>
        <button onClick={createTest} disabled={submitting} style={s.btn}>
          {submitting ? 'Creating…' : '🔬 Generate 5 Variants'}
        </button>
      </section>

      {/* Tests List */}
      <h2 style={s.sectionTitle}>All A/B Tests</h2>
      {testsContent}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { maxWidth: 1000, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 32 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 28, fontWeight: 800, margin: '10px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 14, color: 'var(--muted)', maxWidth: 720 },
  errorBanner: { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8, padding: '10px 14px', color: '#dc2626', marginBottom: 20, fontSize: 13 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 28 },
  testCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: '0 0 16px', color: 'var(--text)' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', gap: 14, marginBottom: 14 },
  field: { marginBottom: 14 },
  label: { fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'block' },
  input: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box' as const, width: '100%' },
  textarea: { width: '100%', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '10px 14px', color: 'var(--text)', fontSize: 13, lineHeight: 1.6, boxSizing: 'border-box' as const, resize: 'vertical' as const },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  skeleton: { color: 'var(--muted)', fontSize: 13, padding: 20 },
  empty: { color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 40 },
  testHeader: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap' as const, gap: 8 },
  testName: { fontSize: 15, fontWeight: 700, color: 'var(--text)', marginRight: 8 },
  statusBadge: { fontSize: 11, fontWeight: 600, border: '1px solid', borderRadius: 4, padding: '2px 7px' },
  metaRow: { display: 'flex', gap: 6, flexWrap: 'wrap' as const, alignItems: 'center' },
  metaChip: { fontSize: 11, background: 'var(--card)', color: 'var(--muted)', borderRadius: 4, padding: '2px 7px' },
  expandBtn: { background: 'transparent', color: '#6366f1', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 6, padding: '3px 10px', cursor: 'pointer', fontSize: 12 },
  winnerBanner: { background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, padding: '6px 12px', fontSize: 13, color: '#15803d', margin: '10px 0 0' },
  variantGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 260px), 1fr))', gap: 12, marginTop: 16 },
  variantCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: 14 },
  winnerCard: { border: '1px solid rgba(34,197,94,0.4)', background: 'rgba(34,197,94,0.05)' },
  variantHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 },
  variantKey: { fontSize: 12, fontWeight: 700, color: 'var(--brand)' },
  winnerChip: { fontSize: 10, background: 'rgba(34,197,94,0.15)', color: '#15803d', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 4, padding: '1px 6px' },
  scoreChip: { fontSize: 10, background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 4, padding: '1px 6px', marginLeft: 'auto' },
  variantContent: { fontSize: 12, color: 'var(--muted)', lineHeight: 1.5, margin: '0 0 10px' },
  scoreRow: { display: 'flex', alignItems: 'center', gap: 8 },
  evaluateRow: { gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', paddingTop: 8 },
  evaluateBtn: { background: 'rgba(34,197,94,0.15)', color: '#15803d', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 8, padding: '8px 18px', cursor: 'pointer', fontWeight: 600, fontSize: 13 },
};
