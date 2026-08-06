'use client';

import { useState, useCallback, useEffect, type ReactNode } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';

// ─── Types ────────────────────────────────────────────────────────────────────

type AnyObject = Record<string, unknown>;

// ─── Constants ────────────────────────────────────────────────────────────────

const PROXY_BASE = '/api/fastapi';
const DEFAULT_TENANT = (
  process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ||
  process.env.DEFAULT_TENANT_ID ||
  'demo-tenant'
).trim();

const ENGINE_META: Record<string, { color: string; glow: string; accent: string }> = {
  auth: { color: '#38bdf8', glow: 'rgba(56,189,248,0.25)', accent: '#0ea5e9' },
  cc: { color: '#a78bfa', glow: 'rgba(167,139,250,0.25)', accent: '#6366f1' },
  analytics: { color: '#34d399', glow: 'rgba(52,211,153,0.25)', accent: '#059669' },
  e01: { color: '#f472b6', glow: 'rgba(244,114,182,0.25)', accent: '#db2777' },
  e02: { color: '#fb923c', glow: 'rgba(251,146,60,0.25)', accent: '#ea580c' },
  e03: { color: '#60a5fa', glow: 'rgba(96,165,250,0.25)', accent: '#6366f1' },
  e04: { color: '#f87171', glow: 'rgba(248,113,113,0.25)', accent: '#dc2626' },
  e05: { color: '#c084fc', glow: 'rgba(192,132,252,0.25)', accent: '#9333ea' },
  e06: { color: '#4ade80', glow: 'rgba(74,222,128,0.25)', accent: '#16a34a' },
  e07: { color: '#fbbf24', glow: 'rgba(251,191,36,0.25)', accent: '#d97706' },
  e08: { color: '#f43f5e', glow: 'rgba(244,63,94,0.25)', accent: '#e11d48' },
  e09: { color: '#f97316', glow: 'rgba(249,115,22,0.25)', accent: '#c2410c' },
  e10: { color: '#22d3ee', glow: 'rgba(34,211,238,0.25)', accent: '#0891b2' },
  e11: { color: '#6366f1', glow: 'rgba(99,102,241,0.25)', accent: '#6366f1' },
  e12: { color: '#e879f9', glow: 'rgba(232,121,249,0.25)', accent: '#c026d3' },
};

// ─── API helpers ──────────────────────────────────────────────────────────────

async function postJson(path: string, payload: AnyObject, tenantId: string): Promise<AnyObject> {
  const res = await fetch(`${PROXY_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Tenant-Id': tenantId },
    body: JSON.stringify(payload),
  });
  const data = (await res.json()) as AnyObject;
  if (!res.ok) throw new Error((data?.detail as string) || `Request failed: ${res.status}`);
  return data;
}

async function getJson(path: string, tenantId: string): Promise<AnyObject> {
  const res = await fetch(`${PROXY_BASE}${path}`, {
    method: 'GET',
    headers: { 'X-Tenant-Id': tenantId },
  });
  const data = (await res.json()) as AnyObject;
  if (!res.ok) throw new Error((data?.detail as string) || `Request failed: ${res.status}`);
  return data;
}

// ─── Custom hook ──────────────────────────────────────────────────────────────

function useVSE() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnyObject | null>(null);
  const [success, setSuccess] = useState(false);

  const run = useCallback(async (fn: () => Promise<AnyObject>) => {
    setLoading(true);
    setError('');
    setResult(null);
    setSuccess(false);
    try {
      const data = await fn();
      setResult(data);
      setSuccess(true);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, result, success, run };
}

// ─── Design primitives ────────────────────────────────────────────────────────

function Card({
  children,
  engineKey,
  className = '',
}: {
  children: ReactNode;
  engineKey: keyof typeof ENGINE_META;
  className?: string;
}) {
  const m = ENGINE_META[engineKey];
  return (
    <section
      style={{
        border: `1px solid ${m.color}30`,
        boxShadow: `0 0 32px ${m.glow}, inset 0 1px 0 ${m.color}15`,
        background: 'linear-gradient(135deg, rgba(10,10,20,0.95) 0%, rgba(15,10,30,0.97) 100%)',
        borderRadius: 16,
        padding: 'clamp(16px, 2.2vw, 28px) clamp(16px, 2.2vw, 28px) clamp(14px, 2vw, 24px)',
        marginBottom: 'clamp(14px, 1.8vw, 24px)',
        position: 'relative',
        overflow: 'hidden',
      }}
      className={className}
    >
      <div
        style={{
          position: 'absolute',
          top: -60,
          right: -60,
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: m.glow,
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      {children}
    </section>
  );
}

function CardTitle({
  icon,
  title,
  badge,
  engineKey,
}: {
  icon: string;
  title: string;
  badge?: string;
  engineKey: keyof typeof ENGINE_META;
}) {
  const m = ENGINE_META[engineKey];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
      <span
        style={{
          fontSize: 22,
          width: 44,
          height: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: `${m.color}18`,
          border: `1px solid ${m.color}40`,
          borderRadius: 12,
          flexShrink: 0,
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1 }}>
        <h2
          style={{
            fontSize: 'clamp(18px, 1.25vw, 24px)',
            fontWeight: 800,
            color: m.color,
            letterSpacing: '-0.01em',
            lineHeight: 1.2,
          }}
        >
          {title}
        </h2>
      </div>
      {badge && (
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            padding: '4px 11px',
            borderRadius: 999,
            background: `${m.color}18`,
            color: m.color,
            border: `1px solid ${m.color}40`,
            letterSpacing: '0.06em',
            textTransform: 'uppercase' as const,
          }}
        >
          {badge}
        </span>
      )}
    </div>
  );
}

function Field({
  label,
  id,
  value,
  onChange,
  placeholder,
  type = 'text',
  rows,
  engineKey,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  rows?: number;
  engineKey?: keyof typeof ENGINE_META;
}) {
  const color = engineKey ? ENGINE_META[engineKey].color : '#a78bfa';
  const shared = {
    width: '100%',
    background: 'rgba(0,0,0,0.4)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 10,
    padding: '11px 14px',
    fontSize: 14,
    color: '#f1f5f9',
    outline: 'none',
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.2s',
  };
  return (
    <div style={{ marginBottom: 12 }}>
      <label
        htmlFor={id}
        style={{
          display: 'block',
          fontSize: 12,
          fontWeight: 600,
          color: '#94a3b8',
          marginBottom: 5,
          letterSpacing: '0.04em',
          textTransform: 'uppercase' as const,
        }}
      >
        {label}
      </label>
      {rows ? (
        <textarea
          id={id}
          rows={rows}
          style={shared}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = color;
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
          }}
        />
      ) : (
        <input
          id={id}
          type={type}
          style={shared}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = color;
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
          }}
        />
      )}
    </div>
  );
}

function Btn({
  onClick,
  loading,
  children,
  variant = 'primary',
  engineKey = 'cc',
}: {
  onClick: () => void;
  loading: boolean;
  children: ReactNode;
  variant?: 'primary' | 'outline' | 'ghost';
  engineKey?: keyof typeof ENGINE_META;
}) {
  const m = ENGINE_META[engineKey];
  const base: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '10px 20px',
    fontSize: 14,
    fontWeight: 700,
    borderRadius: 11,
    cursor: loading ? 'not-allowed' : 'pointer',
    transition: 'all 0.18s ease',
    border: 'none',
    letterSpacing: '0.02em',
    position: 'relative' as const,
    overflow: 'hidden' as const,
  };
  const styles: Record<string, React.CSSProperties> = {
    primary: {
      ...base,
      background: loading ? 'rgba(100,100,120,0.3)' : `linear-gradient(135deg, ${m.color} 0%, ${m.accent} 100%)`,
      color: '#fff',
      boxShadow: loading ? 'none' : `0 4px 20px ${m.glow}, 0 0 0 1px ${m.color}30 inset`,
    },
    outline: {
      ...base,
      background: 'transparent',
      color: m.color,
      border: `1px solid ${m.color}50`,
      boxShadow: loading ? 'none' : `0 0 12px ${m.glow}`,
    },
    ghost: {
      ...base,
      background: `${m.color}12`,
      color: m.color,
    },
  };

  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={styles[variant]}
      onMouseEnter={(e) => {
        if (!loading) {
          if (variant === 'primary') e.currentTarget.style.transform = 'translateY(-1px)';
          if (variant === 'outline') e.currentTarget.style.background = `${m.color}15`;
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        if (variant === 'outline') e.currentTarget.style.background = 'transparent';
      }}
    >
      {loading ? (
        <>
          <span
            style={{
              width: 12,
              height: 12,
              border: '2px solid rgba(255,255,255,0.3)',
              borderTopColor: '#fff',
              borderRadius: '50%',
              display: 'inline-block',
              animation: 'spin 0.7s linear infinite',
            }}
          />
          Working…
        </>
      ) : (
        children
      )}
    </button>
  );
}

function ResultBox({ data, success }: { data: AnyObject | null; success?: boolean }) {
  if (!data) return null;
  const json = JSON.stringify(data, null, 2);
  return (
    <div
      style={{
        marginTop: 14,
        borderRadius: 12,
        border: `1px solid ${success ? 'rgba(52,211,153,0.3)' : 'rgba(255,255,255,0.08)'}`,
        background: 'rgba(0,0,0,0.55)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: success ? 'rgba(52,211,153,0.07)' : 'rgba(255,255,255,0.03)',
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: success ? '#34d399' : '#64748b',
            textTransform: 'uppercase',
          }}
        >
          {success ? '✓ Response' : 'Response'}
        </span>
        <button
          onClick={() => void navigator.clipboard.writeText(json)}
          style={{
            fontSize: 11,
            color: '#64748b',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '3px 8px',
          }}
        >
          copy
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '12px 14px',
          fontSize: 12,
          color: '#86efac',
          maxHeight: 320,
          overflowY: 'auto',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {json}
      </pre>
    </div>
  );
}

function ErrorMsg({ msg }: { msg: string }) {
  if (!msg) return null;
  return (
    <div
      style={{
        marginTop: 10,
        padding: '8px 12px',
        borderRadius: 8,
        background: 'rgba(248,113,113,0.1)',
        border: '1px solid rgba(248,113,113,0.3)',
        color: '#f87171',
        fontSize: 12,
      }}
    >
      ⚠ {msg}
    </div>
  );
}

function Divider({ engineKey }: { engineKey: keyof typeof ENGINE_META }) {
  return (
    <div
      style={{
        height: 1,
        background: `linear-gradient(90deg, transparent, ${ENGINE_META[engineKey].color}30, transparent)`,
        margin: '18px 0',
      }}
    />
  );
}

function BtnRow({ children }: { children: ReactNode }) {
  return <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 4 }}>{children}</div>;
}

function Grid2({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
      {children}
    </div>
  );
}

function SubPanel({ children, engineKey }: { children: ReactNode; engineKey: keyof typeof ENGINE_META }) {
  const m = ENGINE_META[engineKey];
  return (
    <div
      style={{
        marginTop: 18,
        padding: '16px 18px',
        borderRadius: 12,
        border: `1px solid ${m.color}20`,
        background: `${m.color}06`,
      }}
    >
      {children}
    </div>
  );
}

function IdBadge({ label, id }: { label: string; id: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
      <span style={{ fontSize: 11, color: '#94a3b8' }}>{label}:</span>
      <code
        style={{
          fontSize: 12,
          color: '#fbbf24',
          background: 'rgba(251,191,36,0.1)',
          border: '1px solid rgba(251,191,36,0.3)',
          borderRadius: 6,
          padding: '2px 8px',
        }}
      >
        {id}
      </code>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function VSEPage() {
  const [isShortViewport, setIsShortViewport] = useState(false);

  useEffect(() => {
    const applyViewportMode = () => {
      setIsShortViewport(window.innerHeight <= 620 || window.innerWidth <= 720);
    };

    applyViewportMode();
    window.addEventListener('resize', applyViewportMode);
    return () => {
      window.removeEventListener('resize', applyViewportMode);
    };
  }, []);

  const [apiKey, setApiKey] = useState('');
  // Bound to the authenticated session; not user-editable (A01/IDOR).
  const [tenantId] = useState(() => resolveSessionTenant() || DEFAULT_TENANT);

  // Command Centre
  const vseCC = useVSE();
  const vseEngines = useVSE();

  // Analytics
  const vseDashboard = useVSE();
  const vseKFactor = useVSE();
  const vseCascade = useVSE();
  const vseRoi = useVSE();

  // VS-01 Brief
  const [briefObjective, setBriefObjective] = useState('Grow LinkedIn following by 10k this quarter');
  const [briefAudience, setBriefAudience] = useState('B2B marketing executives');
  const [briefPlatforms, setBriefPlatforms] = useState('linkedin,x,instagram');
  const [briefTone, setBriefTone] = useState('professional');
  const vseBrief = useVSE();

  // VSE-1 Psych
  const [trigContent, setTrigContent] = useState(
    'Discover the hidden growth loop that doubled inbound demos in 30 days.'
  );
  const [trigPlatform, setTrigPlatform] = useState('linkedin');
  const vseTrigLib = useVSE();
  const vseTrigAnalyze = useVSE();

  // VSE-2 Algorithm
  const [algoContent, setAlgoContent] = useState(
    'The B2B growth playbook most teams miss: identify one bottleneck and fix it this week.'
  );
  const [algoPlatform, setAlgoPlatform] = useState('linkedin');
  const vseAlgoOptimize = useVSE();
  const vseAlgoModels = useVSE();
  const vseAlgoUpdates = useVSE();

  // VSE-3 Network
  const [netAudience, setNetAudience] = useState('B2B SaaS founders');
  const [netDepth, setNetDepth] = useState('2');
  const vseNetMap = useVSE();
  const vseNetSC = useVSE();

  // VS-05 Cascade Simulation
  const [simContent, setSimContent] = useState('Launching a tactical post on reducing CAC for early-stage SaaS teams.');
  const [simPlatform, setSimPlatform] = useState('linkedin');
  const [simAudience, setSimAudience] = useState('50000');
  const vseSim = useVSE();

  // VSE-4 Detonation
  const [detContent, setDetContent] = useState('3 hard lessons from scaling content from 0 to 1M impressions.');
  const [detPlatforms, setDetPlatforms] = useState('linkedin,x,instagram,tiktok');
  const [lastDetId, setLastDetId] = useState('');
  const vseDetPlan = useVSE();
  const vseDetExecute = useVSE();
  const vseDetList = useVSE();

  // VSE-5 Swarm
  const [swarmSummary, setSwarmSummary] = useState('A practical teardown of high-converting LinkedIn organic funnels.');
  const [swarmNiche, setSwarmNiche] = useState('B2B marketing');
  const [swarmPlatforms, setSwarmPlatforms] = useState('linkedin');
  const [swarmSize, setSwarmSize] = useState('50');
  const [lastSwarmId, setLastSwarmId] = useState('');
  const vseSwarmCompose = useVSE();
  const vseSwarmActivate = useVSE();
  const vseSwarmStats = useVSE();

  // VSE-6 Momentum
  const [momSummary, setMomSummary] = useState('Monitoring momentum for a post about pipeline acceleration tactics.');
  const [momPlatform, setMomPlatform] = useState('linkedin');
  const [lastMomId, setLastMomId] = useState('');
  const vseMomStart = useVSE();
  const vseMomGet = useVSE();
  const vseMomInject = useVSE();

  // VSE-7 Content Factory
  const [cfTopic, setCfTopic] = useState('B2B lead generation');
  const [cfPlatform, setCfPlatform] = useState('linkedin');
  const [cfObjective, setCfObjective] = useState('reach');
  const [cfEmotion, setCfEmotion] = useState('curiosity');
  const [cfFormat, setCfFormat] = useState('auto');
  const [cfAvoidDups, setCfAvoidDups] = useState(true);
  const [cfUniqueness, setCfUniqueness] = useState('medium');
  const [varCount, setVarCount] = useState('3');
  const [hookTopic, setHookTopic] = useState('B2B marketing');
  const [scoreContent, setScoreContent] = useState(
    'Stop writing generic posts. Use one hard insight, one proof point, and one sharp CTA.'
  );
  const [scorePlatform, setScorePlatform] = useState('linkedin');
  const vseContentGen = useVSE();
  const vseVariants = useVSE();
  const vseHooks = useVSE();
  const vseScore = useVSE();

  // VSE-8 Emotion
  const [emoContent, setEmoContent] = useState(
    'This result looked impossible until we tested a counterintuitive strategy and won.'
  );
  const [emoTarget, setEmoTarget] = useState('inspiration');
  const [emoIntensity, setEmoIntensity] = useState('medium');
  const vseEmoAnalyze = useVSE();
  const vseEmoEngineer = useVSE();
  const vseEmoAudienceState = useVSE();

  // VSE-9 Trends
  const [trendId, setTrendId] = useState('1');
  const [trendVoice, setTrendVoice] = useState('professional');
  const [trendPlatform, setTrendPlatform] = useState('linkedin');
  const vseTrendsLive = useVSE();
  const vseTrendsHijack = useVSE();
  const vseTrendsAlerts = useVSE();

  // VSE-10 Paid
  const [paidSummary, setPaidSummary] = useState('Organic post showing strong early engagement on B2B lead gen.');
  const [paidER, setPaidER] = useState('4.5');
  const [paidImpressions, setPaidImpressions] = useState('1200');
  const [paidMinutes, setPaidMinutes] = useState('25');
  const [lastAssessId, setLastAssessId] = useState('');
  const [paidBudget, setPaidBudget] = useState('500');
  const [paidPlatforms, setPaidPlatforms] = useState('linkedin');
  const vsePaidAssess = useVSE();
  const vsePaidAmplify = useVSE();
  const vsePaidList = useVSE();

  // VSE-11 Dark Social
  const [darkContent, setDarkContent] = useState('Private community drop: CAC benchmark framework for SaaS operators.');
  const [darkChannels, setDarkChannels] = useState('whatsapp,slack,discord');
  const [darkHook, setDarkHook] = useState('');
  const vseDarkSeed = useVSE();
  const vseDarkMeasure = useVSE();

  // VSE-12 Immortalise
  const [immEventId, setImmEventId] = useState('viral-event-001');
  const [immSummary, setImmSummary] = useState('Breakdown of a viral campaign that sustained momentum for 14 days.');
  const [immImpressions, setImmImpressions] = useState('500000');
  const [immPlatforms, setImmPlatforms] = useState('linkedin,x');
  const [immInsight, setImmInsight] = useState('');
  const vseImm = useVSE();
  const vseVault = useVSE();

  // Suppress unused variable warning for apiKey (retained for future API-key auth)
  void apiKey;

  return (
    <>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse-glow { 0%,100%{opacity:0.6} 50%{opacity:1} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        ::-webkit-scrollbar-thumb { background: rgba(167,139,250,0.4); border-radius: 4px; }
      `}</style>
      <main
        style={{
          minHeight: '100vh',
          background:
            'radial-gradient(ellipse 80% 60% at 50% -20%, rgba(120,40,200,0.18) 0%, transparent 70%), #080810',
          color: '#f1f5f9',
          padding: 'clamp(20px, 3.2vw, 40px) clamp(12px, 2vw, 20px) clamp(24px, 4vw, 60px)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 'none',
            margin: '0 auto',
          }}
        >
          {/* ── Hero ── */}
          <div style={{ textAlign: 'center', marginBottom: isShortViewport ? 18 : 48 }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                fontSize: isShortViewport ? 10 : 11,
                fontWeight: 700,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                color: '#a78bfa',
                background: 'rgba(167,139,250,0.12)',
                border: '1px solid rgba(167,139,250,0.3)',
                borderRadius: 999,
                padding: isShortViewport ? '3px 12px' : '4px 14px',
                marginBottom: isShortViewport ? 10 : 18,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#a78bfa',
                  animation: 'pulse-glow 2s ease infinite',
                }}
              />
              Live · 12 Engines Active
            </div>
            <h1
              style={{
                fontSize: isShortViewport ? 'clamp(28px, 4.6vw, 40px)' : 'clamp(32px, 5vw, 52px)',
                fontWeight: 900,
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
                background: 'linear-gradient(135deg, #f8fafc 0%, #a78bfa 50%, #60a5fa 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                margin: isShortViewport ? '0 0 8px' : '0 0 12px',
              }}
            >
              ⚡ Viral Singularity Engine
            </h1>
            <p style={{ color: '#94a3b8', fontSize: isShortViewport ? 13 : 15, margin: 0 }}>
              12 Engines · 47 Sub-systems · 247 Neurological Triggers
            </p>
            {!isShortViewport ? (
              <div
                style={{
                  display: 'flex',
                  gap: 1,
                  justifyContent: 'center',
                  marginTop: 28,
                  flexWrap: 'wrap',
                  borderRadius: 16,
                  overflow: 'hidden',
                  border: '1px solid rgba(255,255,255,0.07)',
                  background: 'rgba(255,255,255,0.02)',
                }}
              >
                {[
                  { label: 'Engines', value: '12', color: '#a78bfa' },
                  { label: 'Sub-systems', value: '47', color: '#60a5fa' },
                  { label: 'Psych Triggers', value: '247', color: '#f472b6' },
                  { label: 'Influencer DB', value: '12M', color: '#34d399' },
                  { label: 'Trend Sources', value: '150M', color: '#fb923c' },
                  { label: 'ROAS Target', value: '40x', color: '#fbbf24' },
                ].map((s) => (
                  <div
                    key={s.label}
                    style={{
                      flex: '1 1 100px',
                      padding: '14px 12px',
                      textAlign: 'center',
                      borderRight: '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 'clamp(22px, 1.8vw, 30px)',
                        fontWeight: 900,
                        color: s.color,
                        letterSpacing: '-0.02em',
                      }}
                    >
                      {s.value}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: '#64748b',
                        marginTop: 2,
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                      }}
                    >
                      {s.label}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {/* ── Authentication ── */}
          <Card engineKey="auth">
            <CardTitle icon="🔑" title="Authentication" badge="LOCAL PROXY" engineKey="auth" />
            <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
              Local mode uses server proxy credentials automatically. API Key is optional.
            </p>
            <Grid2>
              <Field
                label="API Key"
                id="apiKey"
                value={apiKey}
                onChange={setApiKey}
                type="password"
                placeholder="your-api-key"
                engineKey="auth"
              />
              <Field
                label="Tenant ID"
                id="tenantId"
                value={tenantId}
                onChange={() => undefined}
                placeholder="tenant-demo"
                engineKey="auth"
              />
            </Grid2>
          </Card>

          {/* ── Command Centre ── */}
          <Card engineKey="cc">
            <CardTitle icon="🎯" title="Command Centre — Live Overview" badge="CORE" engineKey="cc" />
            <BtnRow>
              <Btn
                onClick={() => vseCC.run(() => getJson('/vse/command-centre', tenantId))}
                loading={vseCC.loading}
                engineKey="cc"
              >
                Load Command Centre
              </Btn>
              <Btn
                onClick={() => vseEngines.run(() => getJson('/vse/engines', tenantId))}
                loading={vseEngines.loading}
                variant="outline"
                engineKey="cc"
              >
                List All 12 Engines
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseCC.error} />
            <ErrorMsg msg={vseEngines.error} />
            <ResultBox data={vseCC.result} success={vseCC.success} />
            <ResultBox data={vseEngines.result} success={vseEngines.success} />
          </Card>

          {/* ── Virality Analytics ── */}
          <Card engineKey="analytics">
            <CardTitle
              icon="📊"
              title="Virality Analytics — Dashboard · K-Factor · Cascade · ROI"
              badge="ANALYTICS"
              engineKey="analytics"
            />
            <BtnRow>
              <Btn
                onClick={() => vseDashboard.run(() => getJson('/vse/dashboard/summary', tenantId))}
                loading={vseDashboard.loading}
                engineKey="analytics"
              >
                Dashboard Summary
              </Btn>
              <Btn
                onClick={() => vseKFactor.run(() => getJson('/vse/analytics/k-factor', tenantId))}
                loading={vseKFactor.loading}
                variant="outline"
                engineKey="analytics"
              >
                K-Factor
              </Btn>
              <Btn
                onClick={() => vseCascade.run(() => getJson('/vse/analytics/cascade-map', tenantId))}
                loading={vseCascade.loading}
                variant="outline"
                engineKey="analytics"
              >
                Cascade Map
              </Btn>
              <Btn
                onClick={() => vseRoi.run(() => getJson('/vse/analytics/roi-report', tenantId))}
                loading={vseRoi.loading}
                variant="ghost"
                engineKey="analytics"
              >
                ROI Report
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseDashboard.error} />
            <ErrorMsg msg={vseKFactor.error} />
            <ErrorMsg msg={vseCascade.error} />
            <ErrorMsg msg={vseRoi.error} />
            <ResultBox data={vseDashboard.result} success={vseDashboard.success} />
            <ResultBox data={vseKFactor.result} success={vseKFactor.success} />
            <ResultBox data={vseCascade.result} success={vseCascade.success} />
            <ResultBox data={vseRoi.result} success={vseRoi.success} />
          </Card>

          {/* ── VS-01 Viral Brief ── */}
          <Card engineKey="e01">
            <CardTitle icon="📋" title="VS-01 — Viral Brief Generator" engineKey="e01" />
            <Grid2>
              <Field
                label="Objective"
                id="briefObjective"
                value={briefObjective}
                onChange={setBriefObjective}
                placeholder="Grow 10k followers"
                engineKey="e01"
              />
              <Field
                label="Target Audience"
                id="briefAudience"
                value={briefAudience}
                onChange={setBriefAudience}
                placeholder="B2B marketing executives"
                engineKey="e01"
              />
              <Field
                label="Platforms (comma-separated)"
                id="briefPlatforms"
                value={briefPlatforms}
                onChange={setBriefPlatforms}
                placeholder="linkedin,x,instagram"
                engineKey="e01"
              />
              <Field
                label="Tone"
                id="briefTone"
                value={briefTone}
                onChange={setBriefTone}
                placeholder="professional | casual | provocative"
                engineKey="e01"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseBrief.run(() =>
                    postJson(
                      '/vse/brief',
                      {
                        objective: briefObjective,
                        audience: briefAudience,
                        platforms: briefPlatforms.split(',').map((p) => p.trim()),
                        tone: briefTone,
                        urgency: 'standard',
                      },
                      tenantId
                    )
                  )
                }
                loading={vseBrief.loading}
                engineKey="e01"
              >
                Generate Viral Brief
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseBrief.error} />
            <ResultBox data={vseBrief.result} success={vseBrief.success} />
          </Card>

          {/* ── VSE-1 Psychological Ignition ── */}
          <Card engineKey="e01">
            <CardTitle icon="🧠" title="VSE-1 — Psychological Ignition Matrix" badge="247 TRIGGERS" engineKey="e01" />
            <BtnRow>
              <Btn
                onClick={() => vseTrigLib.run(() => getJson('/vse/triggers/library', tenantId))}
                loading={vseTrigLib.loading}
                engineKey="e01"
              >
                Load 247-Trigger Library
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseTrigLib.error} />
            <ResultBox data={vseTrigLib.result} success={vseTrigLib.success} />
            <Divider engineKey="e01" />
            <Field
              label="Content to Analyse"
              id="trigContent"
              value={trigContent}
              onChange={setTrigContent}
              rows={3}
              placeholder="Paste content to detect active psychological triggers…"
              engineKey="e01"
            />
            <Field
              label="Platform"
              id="trigPlatform"
              value={trigPlatform}
              onChange={setTrigPlatform}
              placeholder="linkedin"
              engineKey="e01"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseTrigAnalyze.run(() =>
                    postJson(
                      '/vse/triggers/analyze',
                      {
                        content: trigContent,
                        platform: trigPlatform,
                        audience: 'b2b professionals',
                      },
                      tenantId
                    )
                  )
                }
                loading={vseTrigAnalyze.loading}
                engineKey="e01"
              >
                Analyse Triggers → VPS Score
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseTrigAnalyze.error} />
            <ResultBox data={vseTrigAnalyze.result} success={vseTrigAnalyze.success} />
          </Card>

          {/* ── VSE-2 Algorithm ── */}
          <Card engineKey="e02">
            <CardTitle icon="⚙️" title="VSE-2 — Algorithmic Gravity System" engineKey="e02" />
            <BtnRow>
              <Btn
                onClick={() => vseAlgoModels.run(() => getJson('/vse/algorithm/models', tenantId))}
                loading={vseAlgoModels.loading}
                engineKey="e02"
              >
                Platform Algorithm Models
              </Btn>
              <Btn
                onClick={() => vseAlgoUpdates.run(() => getJson('/vse/algorithm/updates', tenantId))}
                loading={vseAlgoUpdates.loading}
                variant="outline"
                engineKey="e02"
              >
                Algorithm Change Detections
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseAlgoModels.error} />
            <ErrorMsg msg={vseAlgoUpdates.error} />
            <ResultBox data={vseAlgoModels.result} success={vseAlgoModels.success} />
            <ResultBox data={vseAlgoUpdates.result} success={vseAlgoUpdates.success} />
            <Divider engineKey="e02" />
            <Field
              label="Content to Optimise"
              id="algoContent"
              value={algoContent}
              onChange={setAlgoContent}
              rows={3}
              placeholder="Paste content for platform optimisation…"
              engineKey="e02"
            />
            <Field
              label="Platform"
              id="algoPlatform"
              value={algoPlatform}
              onChange={setAlgoPlatform}
              placeholder="linkedin | tiktok | instagram | x | youtube"
              engineKey="e02"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseAlgoOptimize.run(() =>
                    postJson(
                      '/vse/algorithm/optimize',
                      { content: algoContent, platform: algoPlatform, content_type: 'text' },
                      tenantId
                    )
                  )
                }
                loading={vseAlgoOptimize.loading}
                engineKey="e02"
              >
                Optimise for Algorithm
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseAlgoOptimize.error} />
            <ResultBox data={vseAlgoOptimize.result} success={vseAlgoOptimize.success} />
          </Card>

          {/* ── VSE-3 Network ── */}
          <Card engineKey="e03">
            <CardTitle icon="🕸️" title="VSE-3 — Network Topology Detonator" engineKey="e03" />
            <Grid2>
              <Field
                label="Audience Segment"
                id="netAudience"
                value={netAudience}
                onChange={setNetAudience}
                placeholder="B2B SaaS founders"
                engineKey="e03"
              />
              <Field
                label="Depth (1-3)"
                id="netDepth"
                value={netDepth}
                onChange={setNetDepth}
                type="number"
                engineKey="e03"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseNetMap.run(() =>
                    postJson(
                      '/vse/network/map',
                      { audience_segment: netAudience, depth: Number.parseInt(netDepth, 10) },
                      tenantId
                    )
                  )
                }
                loading={vseNetMap.loading}
                engineKey="e03"
              >
                Generate Network Map
              </Btn>
              <Btn
                onClick={() =>
                  vseNetSC.run(async () => {
                    // Build a fresh map first so the follow-up read is deterministic and avoids transient 404 noise.
                    await postJson(
                      '/vse/network/map',
                      {
                        audience_segment: netAudience,
                        depth: Number.parseInt(netDepth, 10),
                      },
                      tenantId
                    );
                    return getJson('/vse/network/superconnectors', tenantId);
                  })
                }
                loading={vseNetSC.loading}
                variant="outline"
                engineKey="e03"
              >
                Get Superconnectors
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseNetMap.error} />
            <ErrorMsg msg={vseNetSC.error} />
            <ResultBox data={vseNetMap.result} success={vseNetMap.success} />
            <ResultBox data={vseNetSC.result} success={vseNetSC.success} />
          </Card>

          {/* ── VS-05 Cascade Simulation ── */}
          <Card engineKey="e05">
            <CardTitle
              icon="🎲"
              title="VS-05 — Pre-Publication Cascade Simulation"
              badge="MONTE CARLO"
              engineKey="e05"
            />
            <Field
              label="Content Summary"
              id="simContent"
              value={simContent}
              onChange={setSimContent}
              rows={2}
              placeholder="Describe the content you plan to publish…"
              engineKey="e05"
            />
            <Grid2>
              <Field
                label="Platform"
                id="simPlatform"
                value={simPlatform}
                onChange={setSimPlatform}
                placeholder="linkedin"
                engineKey="e05"
              />
              <Field
                label="Audience Size"
                id="simAudience"
                value={simAudience}
                onChange={setSimAudience}
                type="number"
                engineKey="e05"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseSim.run(() =>
                    postJson(
                      '/vse/simulate',
                      {
                        content_summary: simContent,
                        platform: simPlatform,
                        audience_size: Number.parseInt(simAudience, 10),
                        trigger_ids: [1, 3, 5],
                      },
                      tenantId
                    )
                  )
                }
                loading={vseSim.loading}
                engineKey="e05"
              >
                Run 10,000-Run Monte Carlo Simulation
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseSim.error} />
            <ResultBox data={vseSim.result} success={vseSim.success} />
          </Card>

          {/* ── VSE-4 Detonation ── */}
          <Card engineKey="e04">
            <CardTitle icon="💥" title="VSE-4 — Cross-Platform Detonation Matrix" engineKey="e04" />
            <Field
              label="Core Content"
              id="detContent"
              value={detContent}
              onChange={setDetContent}
              rows={3}
              placeholder="The content to detonate across all platforms…"
              engineKey="e04"
            />
            <Field
              label="Platforms (comma-separated)"
              id="detPlatforms"
              value={detPlatforms}
              onChange={setDetPlatforms}
              placeholder="linkedin,x,instagram,tiktok"
              engineKey="e04"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseDetPlan.run(async () => {
                    const data = await postJson(
                      '/vse/detonation/plan',
                      {
                        content: detContent,
                        platforms: detPlatforms.split(',').map((p) => p.trim()),
                        objective: 'reach',
                      },
                      tenantId
                    );
                    if (data?.detonation && typeof (data.detonation as AnyObject).id === 'string') {
                      setLastDetId((data.detonation as AnyObject).id as string);
                    }
                    return data;
                  })
                }
                loading={vseDetPlan.loading}
                engineKey="e04"
              >
                Plan Detonation
              </Btn>
              <Btn
                onClick={() => vseDetList.run(() => getJson('/vse/detonation', tenantId))}
                loading={vseDetList.loading}
                variant="outline"
                engineKey="e04"
              >
                List All Detonations
              </Btn>
            </BtnRow>
            {lastDetId && (
              <SubPanel engineKey="e04">
                <IdBadge label="Planned detonation" id={lastDetId} />
                <Btn
                  onClick={() =>
                    vseDetExecute.run(() => postJson(`/vse/detonation/${lastDetId}/execute`, {}, tenantId))
                  }
                  loading={vseDetExecute.loading}
                  engineKey="e04"
                >
                  🚀 Execute Detonation
                </Btn>
              </SubPanel>
            )}
            <ErrorMsg msg={vseDetPlan.error} />
            <ErrorMsg msg={vseDetExecute.error} />
            <ErrorMsg msg={vseDetList.error} />
            <ResultBox data={vseDetPlan.result} success={vseDetPlan.success} />
            <ResultBox data={vseDetExecute.result} success={vseDetExecute.success} />
            <ResultBox data={vseDetList.result} success={vseDetList.success} />
          </Card>

          {/* ── VSE-5 Swarm ── */}
          <Card engineKey="e05">
            <CardTitle icon="🐝" title="VSE-5 — Influencer Swarm Activator" badge="12M DATABASE" engineKey="e05" />
            <Field
              label="Post Summary"
              id="swarmSummary"
              value={swarmSummary}
              onChange={setSwarmSummary}
              rows={2}
              placeholder="Brief summary of the post to swarm…"
              engineKey="e05"
            />
            <Grid2>
              <Field
                label="Content Niche"
                id="swarmNiche"
                value={swarmNiche}
                onChange={setSwarmNiche}
                placeholder="B2B marketing"
                engineKey="e05"
              />
              <Field
                label="Platforms"
                id="swarmPlatforms"
                value={swarmPlatforms}
                onChange={setSwarmPlatforms}
                placeholder="linkedin"
                engineKey="e05"
              />
              <Field
                label="Swarm Size (5-500)"
                id="swarmSize"
                value={swarmSize}
                onChange={setSwarmSize}
                type="number"
                engineKey="e05"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseSwarmCompose.run(async () => {
                    const data = await postJson(
                      '/vse/swarm/compose',
                      {
                        post_summary: swarmSummary,
                        niche: swarmNiche,
                        platforms: swarmPlatforms.split(',').map((p) => p.trim()),
                        swarm_size: Number.parseInt(swarmSize, 10),
                      },
                      tenantId
                    );
                    if (data?.swarm && typeof (data.swarm as AnyObject).id === 'string') {
                      setLastSwarmId((data.swarm as AnyObject).id as string);
                    }
                    return data;
                  })
                }
                loading={vseSwarmCompose.loading}
                engineKey="e05"
              >
                Compose Swarm
              </Btn>
              <Btn
                onClick={() => vseSwarmStats.run(() => getJson('/vse/swarm/database/stats', tenantId))}
                loading={vseSwarmStats.loading}
                variant="outline"
                engineKey="e05"
              >
                Database Stats
              </Btn>
            </BtnRow>
            {lastSwarmId && (
              <SubPanel engineKey="e05">
                <IdBadge label="Swarm ready" id={lastSwarmId} />
                <Btn
                  onClick={() =>
                    vseSwarmActivate.run(() =>
                      postJson(
                        '/vse/swarm/activate',
                        { swarm_id: lastSwarmId, activation_note: 'Activated via VSE dashboard' },
                        tenantId
                      )
                    )
                  }
                  loading={vseSwarmActivate.loading}
                  engineKey="e05"
                >
                  ⚡ Activate Swarm
                </Btn>
              </SubPanel>
            )}
            <ErrorMsg msg={vseSwarmCompose.error} />
            <ErrorMsg msg={vseSwarmActivate.error} />
            <ErrorMsg msg={vseSwarmStats.error} />
            <ResultBox data={vseSwarmCompose.result} success={vseSwarmCompose.success} />
            <ResultBox data={vseSwarmActivate.result} success={vseSwarmActivate.success} />
            <ResultBox data={vseSwarmStats.result} success={vseSwarmStats.success} />
          </Card>

          {/* ── VSE-6 Momentum ── */}
          <Card engineKey="e06">
            <CardTitle icon="📈" title="VSE-6 — Real-Time Viral Momentum Engine" engineKey="e06" />
            <Field
              label="Post Summary"
              id="momSummary"
              value={momSummary}
              onChange={setMomSummary}
              rows={2}
              placeholder="Describe the post to monitor…"
              engineKey="e06"
            />
            <Field
              label="Platform"
              id="momPlatform"
              value={momPlatform}
              onChange={setMomPlatform}
              placeholder="linkedin"
              engineKey="e06"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseMomStart.run(async () => {
                    const data = await postJson(
                      '/vse/momentum/start',
                      {
                        post_summary: momSummary,
                        platform: momPlatform,
                        target_viral_threshold: 50,
                      },
                      tenantId
                    );
                    if (data?.momentum_event && typeof (data.momentum_event as AnyObject).id === 'string') {
                      setLastMomId((data.momentum_event as AnyObject).id as string);
                    }
                    return data;
                  })
                }
                loading={vseMomStart.loading}
                engineKey="e06"
              >
                Start Monitoring
              </Btn>
            </BtnRow>
            {lastMomId && (
              <SubPanel engineKey="e06">
                <IdBadge label="Monitoring" id={lastMomId} />
                <BtnRow>
                  <Btn
                    onClick={() => vseMomGet.run(() => getJson(`/vse/momentum/${lastMomId}`, tenantId))}
                    loading={vseMomGet.loading}
                    variant="outline"
                    engineKey="e06"
                  >
                    Check Momentum
                  </Btn>
                  <Btn
                    onClick={() =>
                      vseMomInject.run(() =>
                        postJson(
                          `/vse/momentum/${lastMomId}/inject`,
                          { injection_type: 'comment_campaign', intensity: 'medium' },
                          tenantId
                        )
                      )
                    }
                    loading={vseMomInject.loading}
                    engineKey="e06"
                  >
                    Inject Amplification
                  </Btn>
                </BtnRow>
              </SubPanel>
            )}
            <ErrorMsg msg={vseMomStart.error} />
            <ErrorMsg msg={vseMomGet.error} />
            <ErrorMsg msg={vseMomInject.error} />
            <ResultBox data={vseMomStart.result} success={vseMomStart.success} />
            <ResultBox data={vseMomGet.result} success={vseMomGet.success} />
            <ResultBox data={vseMomInject.result} success={vseMomInject.success} />
          </Card>

          {/* ── VSE-7 Content Factory ── */}
          <Card engineKey="e07">
            <CardTitle icon="🏭" title="VSE-7 — Viral Content Factory" badge="VPS ≥85 GATE" engineKey="e07" />
            <Grid2>
              <Field
                label="Topic"
                id="cfTopic"
                value={cfTopic}
                onChange={setCfTopic}
                placeholder="B2B lead generation"
                engineKey="e07"
              />
              <Field
                label="Platform"
                id="cfPlatform"
                value={cfPlatform}
                onChange={setCfPlatform}
                placeholder="linkedin"
                engineKey="e07"
              />
              <Field
                label="Objective"
                id="cfObjective"
                value={cfObjective}
                onChange={setCfObjective}
                placeholder="reach | conversion | engagement | authority"
                engineKey="e07"
              />
              <Field
                label="Emotional Vector"
                id="cfEmotion"
                value={cfEmotion}
                onChange={setCfEmotion}
                placeholder="curiosity | awe | inspiration | anger | identity"
                engineKey="e07"
              />
              <Field
                label="Format"
                id="cfFormat"
                value={cfFormat}
                onChange={setCfFormat}
                placeholder="auto | thread | carousel | short_video"
                engineKey="e07"
              />
              <Field
                label="Uniqueness Boost"
                id="cfUniqueness"
                value={cfUniqueness}
                onChange={setCfUniqueness}
                placeholder="low | medium | high"
                engineKey="e07"
              />
            </Grid2>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                color: '#94a3b8',
                marginBottom: 14,
                cursor: 'pointer',
              }}
            >
              <input
                id="cfAvoidDups"
                type="checkbox"
                checked={cfAvoidDups}
                onChange={(e) => setCfAvoidDups(e.target.checked)}
                style={{ accentColor: '#fbbf24', width: 14, height: 14 }}
              />
              Avoid Duplicate Content (anti-dedup fingerprint)
            </label>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseContentGen.run(() =>
                    postJson(
                      '/vse/content/generate',
                      {
                        topic: cfTopic,
                        platform: cfPlatform,
                        objective: cfObjective,
                        emotional_vector: cfEmotion,
                        format: cfFormat,
                        trigger_ids: [1, 3, 5],
                        avoid_duplicates: cfAvoidDups,
                        uniqueness_boost: cfUniqueness,
                      },
                      tenantId
                    )
                  )
                }
                loading={vseContentGen.loading}
                engineKey="e07"
              >
                Generate Viral Content
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseContentGen.error} />
            <ResultBox data={vseContentGen.result} success={vseContentGen.success} />

            <SubPanel engineKey="e07">
              <p style={{ fontSize: 13, fontWeight: 700, color: '#fbbf24', marginBottom: 4 }}>
                ✨ Multi-Variant Generator — Anti-Duplication Batch
              </p>
              <p style={{ fontSize: 11, color: '#64748b', marginBottom: 12 }}>
                Generates N unique variants in a single call. Intra-batch deduplication applied via topic
                fingerprinting. Reuses Topic, Platform, Objective, Emotional Vector, Format, and Uniqueness Boost.
              </p>
              <Field
                label="Number of Variants (2-8)"
                id="varCount"
                value={varCount}
                onChange={setVarCount}
                placeholder="3"
                type="number"
                engineKey="e07"
              />
              <Btn
                onClick={() =>
                  vseVariants.run(() =>
                    postJson(
                      '/vse/content/generate-variants',
                      {
                        topic: cfTopic,
                        platform: cfPlatform,
                        objective: cfObjective,
                        emotional_vector: cfEmotion,
                        format: cfFormat,
                        trigger_ids: [1, 3, 5],
                        count: Math.min(8, Math.max(2, Number.parseInt(varCount, 10) || 3)),
                        uniqueness_boost: cfUniqueness,
                        avoid_duplicates: cfAvoidDups,
                      },
                      tenantId
                    )
                  )
                }
                loading={vseVariants.loading}
                engineKey="e07"
              >
                Generate {varCount} Variants
              </Btn>
              <ErrorMsg msg={vseVariants.error} />
              {vseVariants.result &&
                (() => {
                  const payload = vseVariants.result as { variants?: AnyObject[]; all_variants?: AnyObject[] };
                  const items = payload.variants ?? payload.all_variants ?? [];
                  return (
                    <div style={{ marginTop: 14 }}>
                      <p style={{ fontSize: 11, color: '#a78bfa', marginBottom: 8 }}>
                        Variants returned: <strong>{items.length}</strong>
                      </p>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {items.map((v, i) => {
                          const stableKey = `v-${String((v as { id?: string }).id ?? i)}`;
                          const vps = String(
                            (v as { viral_probability_score?: number }).viral_probability_score ?? '—'
                          );
                          return (
                            <div
                              key={stableKey}
                              style={{
                                borderRadius: 10,
                                border: '1px solid rgba(251,191,36,0.2)',
                                background: 'rgba(0,0,0,0.4)',
                                overflow: 'hidden',
                              }}
                            >
                              <div
                                style={{
                                  padding: '7px 12px',
                                  background: 'rgba(251,191,36,0.07)',
                                  borderBottom: '1px solid rgba(251,191,36,0.15)',
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: '#fbbf24',
                                }}
                              >
                                Variant {i + 1}
                                {i === 0 ? ' 🥇 Primary' : ''} — VPS: {vps}
                              </div>
                              <pre
                                style={{
                                  margin: 0,
                                  padding: '10px 12px',
                                  fontSize: 11,
                                  color: '#86efac',
                                  maxHeight: 200,
                                  overflow: 'auto',
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {JSON.stringify(v, null, 2)}
                              </pre>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}
            </SubPanel>

            <Divider engineKey="e07" />

            <Field
              label="Hook Topic (50 hooks)"
              id="hookTopic"
              value={hookTopic}
              onChange={setHookTopic}
              placeholder="B2B marketing"
              engineKey="e07"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseHooks.run(() =>
                    postJson('/vse/content/hooks', { topic: hookTopic, platform: cfPlatform, count: 50 }, tenantId)
                  )
                }
                loading={vseHooks.loading}
                variant="outline"
                engineKey="e07"
              >
                Generate 50 Hook Variants
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseHooks.error} />
            <ResultBox data={vseHooks.result} success={vseHooks.success} />

            <Divider engineKey="e07" />

            <Field
              label="Content to Score (VPS)"
              id="scoreContent"
              value={scoreContent}
              onChange={setScoreContent}
              rows={3}
              placeholder="Paste content for VPS scoring…"
              engineKey="e07"
            />
            <Field
              label="Platform"
              id="scorePlatform"
              value={scorePlatform}
              onChange={setScorePlatform}
              placeholder="linkedin"
              engineKey="e07"
            />
            <BtnRow>
              <Btn
                onClick={() =>
                  vseScore.run(() =>
                    postJson(
                      '/vse/content/score',
                      { content: scoreContent, platform: scorePlatform, trigger_ids: [1, 3] },
                      tenantId
                    )
                  )
                }
                loading={vseScore.loading}
                variant="ghost"
                engineKey="e07"
              >
                Score Content (VPS)
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseScore.error} />
            <ResultBox data={vseScore.result} success={vseScore.success} />
          </Card>

          {/* ── VSE-8 Emotion ── */}
          <Card engineKey="e08">
            <CardTitle icon="❤️" title="VSE-8 — Emotional Contagion Amplifier" engineKey="e08" />
            <Field
              label="Content to Analyse"
              id="emoContent"
              value={emoContent}
              onChange={setEmoContent}
              rows={3}
              placeholder="Paste content to analyse emotional signature…"
              engineKey="e08"
            />
            <Grid2>
              <Field
                label="Target Vector"
                id="emoTarget"
                value={emoTarget}
                onChange={setEmoTarget}
                placeholder="awe | anger | inspiration | curiosity | identity | moral_elevation"
                engineKey="e08"
              />
              <Field
                label="Intensity"
                id="emoIntensity"
                value={emoIntensity}
                onChange={setEmoIntensity}
                placeholder="low | medium | high"
                engineKey="e08"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseEmoAnalyze.run(() => postJson('/vse/emotion/analyze', { content: emoContent }, tenantId))
                }
                loading={vseEmoAnalyze.loading}
                engineKey="e08"
              >
                Analyse Emotion
              </Btn>
              <Btn
                onClick={() =>
                  vseEmoEngineer.run(() =>
                    postJson(
                      '/vse/emotion/engineer',
                      { content: emoContent, target_vector: emoTarget, intensity: emoIntensity },
                      tenantId
                    )
                  )
                }
                loading={vseEmoEngineer.loading}
                variant="outline"
                engineKey="e08"
              >
                Engineer Emotion Vector
              </Btn>
              <Btn
                onClick={() => vseEmoAudienceState.run(() => getJson('/vse/emotion/audience-state', tenantId))}
                loading={vseEmoAudienceState.loading}
                variant="ghost"
                engineKey="e08"
              >
                Audience Emotional State
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseEmoAnalyze.error} />
            <ErrorMsg msg={vseEmoEngineer.error} />
            <ErrorMsg msg={vseEmoAudienceState.error} />
            <ResultBox data={vseEmoAnalyze.result} success={vseEmoAnalyze.success} />
            <ResultBox data={vseEmoEngineer.result} success={vseEmoEngineer.success} />
            <ResultBox data={vseEmoAudienceState.result} success={vseEmoAudienceState.success} />
          </Card>

          {/* ── VSE-9 Trend Hijack ── */}
          <Card engineKey="e09">
            <CardTitle icon="🔥" title="VSE-9 — Real-Time Trend Hijack System" badge="60s DETECTION" engineKey="e09" />
            <BtnRow>
              <Btn
                onClick={() => vseTrendsLive.run(() => getJson('/vse/trends/live', tenantId))}
                loading={vseTrendsLive.loading}
                engineKey="e09"
              >
                Live Trends (150M Sources)
              </Btn>
              <Btn
                onClick={() => vseTrendsAlerts.run(() => getJson('/vse/trends/alerts', tenantId))}
                loading={vseTrendsAlerts.loading}
                variant="outline"
                engineKey="e09"
              >
                Trend Alerts
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseTrendsLive.error} />
            <ErrorMsg msg={vseTrendsAlerts.error} />
            <ResultBox data={vseTrendsLive.result} success={vseTrendsLive.success} />
            <ResultBox data={vseTrendsAlerts.result} success={vseTrendsAlerts.success} />
            <Divider engineKey="e09" />
            <Grid2>
              <Field
                label="Trend ID (from Live Trends)"
                id="trendId"
                value={trendId}
                onChange={setTrendId}
                type="number"
                engineKey="e09"
              />
              <Field
                label="Brand Voice"
                id="trendVoice"
                value={trendVoice}
                onChange={setTrendVoice}
                placeholder="professional | casual | provocative"
                engineKey="e09"
              />
              <Field
                label="Platform"
                id="trendPlatform"
                value={trendPlatform}
                onChange={setTrendPlatform}
                placeholder="linkedin"
                engineKey="e09"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseTrendsHijack.run(() =>
                    postJson(
                      '/vse/trends/hijack',
                      {
                        trend_id: Number.parseInt(trendId, 10),
                        brand_voice: trendVoice,
                        platform: trendPlatform,
                      },
                      tenantId
                    )
                  )
                }
                loading={vseTrendsHijack.loading}
                engineKey="e09"
              >
                Hijack This Trend
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseTrendsHijack.error} />
            <ResultBox data={vseTrendsHijack.result} success={vseTrendsHijack.success} />
          </Card>

          {/* ── VSE-10 Paid ── */}
          <Card engineKey="e10">
            <CardTitle icon="💰" title="VSE-10 — Viral Paid Amplification Matrix" badge="15-40x ROAS" engineKey="e10" />
            <Grid2>
              <Field
                label="Post Summary"
                id="paidSummary"
                value={paidSummary}
                onChange={setPaidSummary}
                placeholder="Brief description of post…"
                engineKey="e10"
              />
              <Field
                label="Organic Engagement Rate %"
                id="paidER"
                value={paidER}
                onChange={setPaidER}
                type="number"
                engineKey="e10"
              />
              <Field
                label="Organic Impressions"
                id="paidImpressions"
                value={paidImpressions}
                onChange={setPaidImpressions}
                type="number"
                engineKey="e10"
              />
              <Field
                label="Minutes Live"
                id="paidMinutes"
                value={paidMinutes}
                onChange={setPaidMinutes}
                type="number"
                engineKey="e10"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vsePaidAssess.run(async () => {
                    const data = await postJson(
                      '/vse/paid/assess',
                      {
                        post_summary: paidSummary,
                        organic_engagement_rate: Number.parseFloat(paidER),
                        organic_impressions: Number.parseInt(paidImpressions, 10),
                        minutes_live: Number.parseInt(paidMinutes, 10),
                      },
                      tenantId
                    );
                    if (data?.assessment && typeof (data.assessment as AnyObject).id === 'string') {
                      setLastAssessId((data.assessment as AnyObject).id as string);
                    }
                    return data;
                  })
                }
                loading={vsePaidAssess.loading}
                engineKey="e10"
              >
                Assess Organic Signals
              </Btn>
              <Btn
                onClick={() => vsePaidList.run(() => getJson('/vse/paid/events', tenantId))}
                loading={vsePaidList.loading}
                variant="outline"
                engineKey="e10"
              >
                List Amplification Events
              </Btn>
            </BtnRow>
            {lastAssessId && (
              <SubPanel engineKey="e10">
                <IdBadge label="Assessment" id={lastAssessId} />
                <Grid2>
                  <Field
                    label="Budget (GBP)"
                    id="paidBudget"
                    value={paidBudget}
                    onChange={setPaidBudget}
                    type="number"
                    engineKey="e10"
                  />
                  <Field
                    label="Platforms"
                    id="paidPlatforms"
                    value={paidPlatforms}
                    onChange={setPaidPlatforms}
                    placeholder="linkedin,x"
                    engineKey="e10"
                  />
                </Grid2>
                <Btn
                  onClick={() =>
                    vsePaidAmplify.run(() =>
                      postJson(
                        '/vse/paid/amplify',
                        {
                          assessment_id: lastAssessId,
                          budget_gbp: Number.parseFloat(paidBudget),
                          platforms: paidPlatforms.split(',').map((p) => p.trim()),
                          objective: 'reach',
                        },
                        tenantId
                      )
                    )
                  }
                  loading={vsePaidAmplify.loading}
                  engineKey="e10"
                >
                  Trigger Paid Amplification
                </Btn>
              </SubPanel>
            )}
            <ErrorMsg msg={vsePaidAssess.error} />
            <ErrorMsg msg={vsePaidAmplify.error} />
            <ErrorMsg msg={vsePaidList.error} />
            <ResultBox data={vsePaidAssess.result} success={vsePaidAssess.success} />
            <ResultBox data={vsePaidAmplify.result} success={vsePaidAmplify.success} />
            <ResultBox data={vsePaidList.result} success={vsePaidList.success} />
          </Card>

          {/* ── VSE-11 Dark Social ── */}
          <Card engineKey="e11">
            <CardTitle icon="🌑" title="VSE-11 — Dark Social Penetration System" engineKey="e11" />
            <Field
              label="Content to Seed"
              id="darkContent"
              value={darkContent}
              onChange={setDarkContent}
              rows={3}
              placeholder="Content for dark social seeding (WhatsApp, Slack, Discord…)"
              engineKey="e11"
            />
            <Grid2>
              <Field
                label="Channels (comma-separated)"
                id="darkChannels"
                value={darkChannels}
                onChange={setDarkChannels}
                placeholder="whatsapp,slack,discord,telegram"
                engineKey="e11"
              />
              <Field
                label="Forwarding Hook"
                id="darkHook"
                value={darkHook}
                onChange={setDarkHook}
                placeholder="Share with anyone who cares about this…"
                engineKey="e11"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseDarkSeed.run(() =>
                    postJson(
                      '/vse/dark-social/seed',
                      {
                        content: darkContent,
                        channel_types: darkChannels.split(',').map((c) => c.trim()),
                        ...(darkHook ? { forwarding_hook: darkHook } : {}),
                      },
                      tenantId
                    )
                  )
                }
                loading={vseDarkSeed.loading}
                engineKey="e11"
              >
                Seed Dark Social Channels
              </Btn>
              <Btn
                onClick={() => vseDarkMeasure.run(() => getJson('/vse/dark-social/measurement', tenantId))}
                loading={vseDarkMeasure.loading}
                variant="outline"
                engineKey="e11"
              >
                Dark Social Measurement
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseDarkSeed.error} />
            <ErrorMsg msg={vseDarkMeasure.error} />
            <ResultBox data={vseDarkSeed.result} success={vseDarkSeed.success} />
            <ResultBox data={vseDarkMeasure.result} success={vseDarkMeasure.success} />
          </Card>

          {/* ── VSE-12 Immortalise ── */}
          <Card engineKey="e12">
            <CardTitle icon="♾️" title="VSE-12 — Viral Immortalisation Protocol" engineKey="e12" />
            <Grid2>
              <Field
                label="Viral Event ID"
                id="immEventId"
                value={immEventId}
                onChange={setImmEventId}
                placeholder="e.g. viral-event-001"
                engineKey="e12"
              />
              <Field
                label="Post Summary"
                id="immSummary"
                value={immSummary}
                onChange={setImmSummary}
                placeholder="Brief description of the viral post…"
                engineKey="e12"
              />
              <Field
                label="Total Viral Impressions"
                id="immImpressions"
                value={immImpressions}
                onChange={setImmImpressions}
                type="number"
                engineKey="e12"
              />
              <Field
                label="Platforms (comma-separated)"
                id="immPlatforms"
                value={immPlatforms}
                onChange={setImmPlatforms}
                placeholder="linkedin,x,instagram"
                engineKey="e12"
              />
              <Field
                label="Key Insight (optional)"
                id="immInsight"
                value={immInsight}
                onChange={setImmInsight}
                placeholder="The core insight from this viral event…"
                engineKey="e12"
              />
            </Grid2>
            <BtnRow>
              <Btn
                onClick={() =>
                  vseImm.run(() =>
                    postJson(
                      '/vse/immortalise',
                      {
                        viral_event_id: immEventId,
                        post_summary: immSummary,
                        viral_impressions: Number.parseInt(immImpressions, 10),
                        platforms_achieved: immPlatforms.split(',').map((p) => p.trim()),
                        ...(immInsight ? { key_insight: immInsight } : {}),
                      },
                      tenantId
                    )
                  )
                }
                loading={vseImm.loading}
                engineKey="e12"
              >
                Trigger Immortalisation Protocol
              </Btn>
              <Btn
                onClick={() => vseVault.run(() => getJson('/vse/immortalise/vault', tenantId))}
                loading={vseVault.loading}
                variant="outline"
                engineKey="e12"
              >
                Open Viral Vault
              </Btn>
            </BtnRow>
            <ErrorMsg msg={vseImm.error} />
            <ErrorMsg msg={vseVault.error} />
            <ResultBox data={vseImm.result} success={vseImm.success} />
            <ResultBox data={vseVault.result} success={vseVault.success} />
          </Card>
        </div>
      </main>
    </>
  );
}
