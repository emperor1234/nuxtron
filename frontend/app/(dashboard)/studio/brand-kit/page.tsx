'use client';

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

// ─── Types ────────────────────────────────────────────────────────────────────

type FontSpec = { family: string; weight: string; size_px: number };

type BrandColors = {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
  muted: string;
};

type BrandFonts = {
  heading: FontSpec;
  body: FontSpec;
  display: FontSpec;
};

type BrandLogos = {
  main: string | null;
  icon: string | null;
  dark_variant: string | null;
  light_variant: string | null;
};

type BrandVoice = {
  tone_preset: 'professional' | 'friendly' | 'bold' | 'playful' | 'witty' | 'custom';
  formality: string;
  emotion: string;
  custom_description: string;
};

type BrandMessaging = {
  brand_name: string;
  tagline: string;
  value_proposition: string;
  elevator_pitch: string;
  target_audience: string;
};

type WritingRules = {
  terms_to_use: string[];
  terms_to_avoid: string[];
  preferred_sentences: string;
  use_oxford_comma: boolean;
  notes: string;
};

type BrandKit = {
  tenant_id: string;
  colors: BrandColors;
  fonts: BrandFonts;
  logos: BrandLogos;
  voice: BrandVoice;
  messaging: BrandMessaging;
  writing_rules: WritingRules;
  knowledge_base_count: number;
  created_at: string;
  updated_at: string;
};

type KBEntry = {
  id: string;
  entry_type: 'url' | 'text' | 'pdf_title';
  content: string;
  label: string;
  status: 'indexed' | 'pending' | 'failed';
  created_at: string;
};

type BrandKitAnalytics = {
  total_generations: number;
  by_type: Record<string, number>;
  kit_completeness: number;
  colors_configured: boolean;
  fonts_configured: boolean;
  logos_configured: boolean;
  voice_configured: boolean;
  messaging_configured: boolean;
  writing_rules_configured: boolean;
};

type PreviewResult = {
  content_type: string;
  generated_text: string;
  compliance_check: {
    avoids_banned_terms: boolean;
    uses_preferred_terms: boolean;
    tone_aligned: boolean;
    issues: string[];
  };
  brand_kit_snapshot: { brand_name: string; tagline: string; tone_preset: string };
  generated_at: string;
};

type BrandKitResponse = {
  brand_kit: BrandKit;
};

type BrandKitKnowledgeBaseResponse = {
  entries: KBEntry[];
};

type BrandKitAnalyticsResponse = {
  analytics: BrandKitAnalytics;
};

type BrandKitEntryMutationResponse = {
  entry?: KBEntry;
  deleted?: boolean;
};

type BrandKitPreviewResponse = {
  preview?: PreviewResult;
};

// ─── Fallback defaults ─────────────────────────────────────────────────────

const DEFAULT_KIT: BrandKit = {
  tenant_id: DEFAULT_TENANT_ID,
  colors: {
    primary: '#6366f1',
    secondary: '#8B5CF6',
    accent: '#EC4899',
    background: 'var(--card)',
    text: 'var(--text)',
    muted: 'var(--muted)',
  },
  fonts: {
    heading: { family: 'Inter', weight: '700', size_px: 32 },
    body: { family: 'Inter', weight: '400', size_px: 16 },
    display: { family: 'Inter', weight: '800', size_px: 48 },
  },
  logos: { main: null, icon: null, dark_variant: null, light_variant: null },
  voice: { tone_preset: 'professional', formality: 'semi-formal', emotion: 'confident', custom_description: '' },
  messaging: { brand_name: 'Your Brand', tagline: '', value_proposition: '', elevator_pitch: '', target_audience: '' },
  writing_rules: {
    terms_to_use: [],
    terms_to_avoid: [],
    preferred_sentences: 'medium',
    use_oxford_comma: true,
    notes: '',
  },
  knowledge_base_count: 0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// ─── Tab IDs ──────────────────────────────────────────────────────────────────

type Tab = 'colors' | 'fonts' | 'logos' | 'voice' | 'messaging' | 'writing' | 'knowledge' | 'preview' | 'analytics';
const TABS: { id: Tab; label: string }[] = [
  { id: 'colors', label: 'Colors' },
  { id: 'fonts', label: 'Fonts' },
  { id: 'logos', label: 'Logos' },
  { id: 'voice', label: 'Voice & Tone' },
  { id: 'messaging', label: 'Key Messaging' },
  { id: 'writing', label: 'Writing Rules' },
  { id: 'knowledge', label: 'Knowledge Base' },
  { id: 'preview', label: 'AI Preview' },
  { id: 'analytics', label: 'Analytics' },
];

const TONE_PRESETS: BrandVoice['tone_preset'][] = ['professional', 'friendly', 'bold', 'playful', 'witty', 'custom'];

// ─── Completeness ring ────────────────────────────────────────────────────────

function CompletenessRing({ score }: { score: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#F59E0B' : '#EF4444';
  return (
    <svg width={128} height={128} viewBox="0 0 128 128" style={{ display: 'block' }}>
      <circle cx={64} cy={64} r={r} fill="none" stroke="#eef0f4" strokeWidth={12} />
      <circle
        cx={64}
        cy={64}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={12}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 64 64)"
      />
      <text x={64} y={64} textAnchor="middle" dominantBaseline="central" fill={color} fontSize={22} fontWeight="700">
        {score}%
      </text>
    </svg>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function BrandKitPage() {
  const [activeTab, setActiveTab] = useState<Tab>('colors');
  const [kit, setKit] = useState<BrandKit>(DEFAULT_KIT);
  const [kb, setKb] = useState<KBEntry[]>([]);
  const [analytics, setAnalytics] = useState<BrandKitAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [freshness, setFreshness] = useState<'live' | 'unavailable'>('live');
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [strictUnavailable, setStrictUnavailable] = useState(false);

  // Colors tab
  const [draftColors, setDraftColors] = useState<BrandColors>(DEFAULT_KIT.colors);

  // Fonts tab
  const [draftFonts, setDraftFonts] = useState<BrandFonts>(DEFAULT_KIT.fonts);

  // Logos tab
  const [draftLogos, setDraftLogos] = useState<BrandLogos>(DEFAULT_KIT.logos);

  // Voice tab
  const [draftVoice, setDraftVoice] = useState<BrandVoice>(DEFAULT_KIT.voice);

  // Messaging tab
  const [draftMessaging, setDraftMessaging] = useState<BrandMessaging>(DEFAULT_KIT.messaging);

  // Writing rules tab
  const [draftWriting, setDraftWriting] = useState<WritingRules>(DEFAULT_KIT.writing_rules);
  const [termToUseInput, setTermToUseInput] = useState('');
  const [termToAvoidInput, setTermToAvoidInput] = useState('');

  // Knowledge base tab
  const [kbType, setKbType] = useState<'url' | 'text' | 'pdf_title'>('url');
  const [kbContent, setKbContent] = useState('');
  const [kbLabel, setKbLabel] = useState('');

  // Preview tab
  const [previewType, setPreviewType] = useState<string>('social_caption');
  const [previewTopic, setPreviewTopic] = useState('');
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [generating, setGenerating] = useState(false);

  // ── Load data ────────────────────────────────────────────────────────────

  const loadAll = useCallback(async () => {
    try {
      const [kitData, kbData, analyticsData] = await Promise.all([
        apiGet<BrandKitResponse>(`/brand-kit`),
        apiGet<BrandKitKnowledgeBaseResponse>(`/brand-kit/knowledge-base`),
        apiGet<BrandKitAnalyticsResponse>(`/brand-kit/analytics`),
      ]);
      if (!kitData?.brand_kit) {
        throw new Error('Brand Kit response did not include live data.');
      }
      const bk: BrandKit = kitData.brand_kit;
      setKit(bk);
      setDraftColors({ ...bk.colors });
      setDraftFonts(structuredClone(bk.fonts));
      setDraftLogos({ ...bk.logos });
      setDraftVoice({ ...bk.voice });
      setDraftMessaging({ ...bk.messaging });
      setDraftWriting(structuredClone(bk.writing_rules));
      setKb(kbData?.entries ?? []);
      setAnalytics(analyticsData?.analytics ?? null);
      setStrictUnavailable(false);
      setFreshness('live');
    } catch {
      setStrictUnavailable(true);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Brand Kit backend unavailable in strict no-mock mode.'
          : 'Brand Kit backend unavailable in fail-closed mode.'
      );
      setFreshness('unavailable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const flash = (msg: string, isErr = false) => {
    if (isErr) {
      setError(msg);
      setTimeout(() => setError(null), 4000);
    } else {
      setSuccess(msg);
      setTimeout(() => setSuccess(null), 3000);
    }
  };

  const patch = async (path: string, body: object, successMsg: string) => {
    setBusy(true);
    try {
      const res = await apiSend<BrandKitResponse>(`/brand-kit/${path}`, 'PATCH', body);
      if (res?.brand_kit) {
        const bk: BrandKit = res.brand_kit;
        setKit(bk);
        flash(successMsg);
        return bk;
      } else {
        flash('Save failed — check your inputs.', true);
      }
    } catch {
      flash('Network error. Changes not saved.', true);
    } finally {
      setBusy(false);
    }
    return null;
  };

  // ── Tab: Colors ──────────────────────────────────────────────────────────

  const colorFields: { key: keyof BrandColors; label: string }[] = [
    { key: 'primary', label: 'Primary' },
    { key: 'secondary', label: 'Secondary' },
    { key: 'accent', label: 'Accent' },
    { key: 'background', label: 'Background' },
    { key: 'text', label: 'Text' },
    { key: 'muted', label: 'Muted' },
  ];

  const saveColors = () => patch('colors', draftColors, 'Color palette saved');

  // ── Tab: Fonts ───────────────────────────────────────────────────────────

  const saveFonts = () => patch('fonts', draftFonts, 'Fonts saved');

  const updateFont = (slot: keyof BrandFonts, field: keyof FontSpec, val: string | number) => {
    setDraftFonts((prev) => ({
      ...prev,
      [slot]: { ...prev[slot], [field]: val },
    }));
  };

  // ── Tab: Logos ───────────────────────────────────────────────────────────

  const saveLogos = () => patch('logos', draftLogos, 'Logos saved');

  // ── Tab: Voice ───────────────────────────────────────────────────────────

  const saveVoice = () => patch('voice', draftVoice, 'Voice & Tone saved');

  // ── Tab: Messaging ───────────────────────────────────────────────────────

  const saveMessaging = () => patch('messaging', draftMessaging, 'Brand messaging saved');

  // ── Tab: Writing Rules ───────────────────────────────────────────────────

  const saveWriting = () => patch('writing-rules', draftWriting, 'Writing rules saved');

  const addTermToUse = () => {
    const t = termToUseInput.trim();
    if (!t || draftWriting.terms_to_use.includes(t)) return;
    setDraftWriting((prev) => ({ ...prev, terms_to_use: [...prev.terms_to_use, t] }));
    setTermToUseInput('');
  };

  const addTermToAvoid = () => {
    const t = termToAvoidInput.trim();
    if (!t || draftWriting.terms_to_avoid.includes(t)) return;
    setDraftWriting((prev) => ({ ...prev, terms_to_avoid: [...prev.terms_to_avoid, t] }));
    setTermToAvoidInput('');
  };

  // ── Tab: Knowledge Base ──────────────────────────────────────────────────

  const addKBEntry = async () => {
    if (!kbContent.trim()) return;
    setBusy(true);
    try {
      const res = await apiSend<BrandKitEntryMutationResponse>('/brand-kit/knowledge-base', 'POST', {
        entry_type: kbType,
        content: kbContent,
        label: kbLabel || undefined,
      });
      if (res?.entry) {
        setKb((prev) => [...prev, res.entry as KBEntry]);
        setKbContent('');
        setKbLabel('');
        flash('Entry added to knowledge base');
      } else {
        flash('Failed to add entry', true);
      }
    } catch {
      flash('Network error', true);
    } finally {
      setBusy(false);
    }
  };

  const deleteKBEntry = async (id: string) => {
    setBusy(true);
    try {
      const res = await apiSend<BrandKitEntryMutationResponse>(`/brand-kit/knowledge-base/${id}`, 'DELETE', {});
      if (res?.deleted) {
        setKb((prev) => prev.filter((e) => e.id !== id));
        flash('Entry removed');
      }
    } catch {
      flash('Delete failed', true);
    } finally {
      setBusy(false);
    }
  };

  // ── Tab: Preview ─────────────────────────────────────────────────────────

  const generatePreview = async () => {
    setGenerating(true);
    try {
      const res = await apiSend<BrandKitPreviewResponse>('/brand-kit/generate-preview', 'POST', {
        content_type: previewType,
        topic: previewTopic,
      });
      if (res?.preview) {
        setPreviewResult(res.preview as PreviewResult);
        // Refresh analytics count
        const analyticsData = await apiGet<BrandKitAnalyticsResponse>('/brand-kit/analytics');
        if (analyticsData?.analytics) setAnalytics(analyticsData.analytics);
      } else {
        flash('Generation failed — try again.', true);
      }
    } catch {
      flash('Network error during generation', true);
    } finally {
      setGenerating(false);
    }
  };

  // ── Analytics completeness label ─────────────────────────────────────────

  const completenessLabel = useMemo(() => {
    const s = analytics?.kit_completeness ?? 0;
    if (s === 100) return 'Kit complete — every section configured';
    if (s >= 80) return 'Great shape — a few sections left';
    if (s >= 50) return 'Getting there — fill in remaining sections';
    return 'Just getting started — fill in your brand kit';
  }, [analytics]);

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div style={styles.loadWrap}>
        <div style={styles.loadSpinner} />
        <p style={styles.loadText}>Loading Brand Kit…</p>
      </div>
    );
  }

  if (strictUnavailable) {
    return (
      <div style={styles.loadWrap}>
        <div style={{ ...styles.panel, maxWidth: 760, textAlign: 'left' }}>
          <h1 style={{ ...styles.h1, marginBottom: 8 }}>Brand Kit unavailable</h1>
          <p style={{ ...styles.headerSub, marginBottom: 14 }}>
            Live Brand Kit data could not be loaded in fail-closed mode.
          </p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              void loadAll();
            }}
            style={styles.primaryBtn}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.h1}>Brand Kit</h1>
          <p style={styles.headerSub}>
            Centralize your colors, fonts, logos, voice, and messaging so every piece of AI-generated content is
            on-brand.
          </p>
        </div>
        <div style={styles.headerRight}>
          <span style={{ ...styles.freshPill, ...(freshness === 'live' ? styles.freshLive : styles.freshUnavailable) }}>
            {freshness === 'live' ? '● Live' : '⚠ Offline'}
          </span>
          {analytics && <span style={styles.completenessChip}>Kit: {analytics.kit_completeness}% complete</span>}
        </div>
      </div>

      {/* Toast notifications */}
      {success && <div style={styles.toastSuccess}>{success}</div>}
      {error && <div style={styles.toastError}>{error}</div>}

      {/* Tab bar */}
      <div style={styles.tabBar}>
        {TABS.map((t) => (
          <button
            key={t.id}
            style={{ ...styles.tabBtn, ...(activeTab === t.id ? styles.tabBtnActive : {}) }}
            onClick={() => setActiveTab(t.id)}
            type="button"
          >
            {t.label}
            {t.id === 'knowledge' && kb.length > 0 && <span style={styles.tabBadge}>{kb.length}</span>}
          </button>
        ))}
      </div>

      {/* ── Tab: Colors ──────────────────────────────────────────────────── */}
      {activeTab === 'colors' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Color Palette</h2>
            <p style={styles.panelSub}>
              Define your brand colors. These are applied to all AI-generated visuals and content previews.
            </p>
          </div>
          <div style={styles.colorGrid}>
            {colorFields.map(({ key, label }) => (
              <div key={key} style={styles.colorItem}>
                <div style={{ ...styles.colorPreview, background: draftColors[key] }} />
                <label style={styles.fieldLabel}>{label}</label>
                <div style={styles.colorInputRow}>
                  <input
                    type="color"
                    value={draftColors[key]}
                    onChange={(e) => setDraftColors((p) => ({ ...p, [key]: e.target.value }))}
                    style={styles.colorPicker}
                  />
                  <input
                    type="text"
                    value={draftColors[key]}
                    onChange={(e) => setDraftColors((p) => ({ ...p, [key]: e.target.value }))}
                    style={styles.hexInput}
                    placeholder="#000000"
                    maxLength={9}
                  />
                </div>
              </div>
            ))}
          </div>
          <div style={styles.palettePreview}>
            <p style={styles.fieldLabel}>Live Palette Preview</p>
            <div style={styles.paletteRow}>
              {colorFields.map(({ key, label }) => (
                <div key={key} style={styles.paletteSwatch}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 8,
                      background: draftColors[key],
                      border: '2px solid var(--line)',
                    }}
                  />
                  <span style={styles.swatchLabel}>{label}</span>
                </div>
              ))}
            </div>
          </div>
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveColors}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Colors'}
          </button>
        </div>
      )}

      {/* ── Tab: Fonts ───────────────────────────────────────────────────── */}
      {activeTab === 'fonts' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Typography</h2>
            <p style={styles.panelSub}>
              Set font families, weights, and sizes for headings, body copy, and display text.
            </p>
          </div>
          {(['heading', 'body', 'display'] as const).map((slot) => (
            <div key={slot} style={styles.fontRow}>
              <h3 style={styles.fontSlotTitle}>{slot.charAt(0).toUpperCase() + slot.slice(1)}</h3>
              <div style={styles.fontPreviewText} data-slot={slot}>
                <span
                  style={{
                    fontFamily: draftFonts[slot].family,
                    fontWeight: draftFonts[slot].weight,
                    fontSize: Math.min(draftFonts[slot].size_px, 28),
                  }}
                >
                  The quick brown fox
                </span>
              </div>
              <div style={styles.fontFields}>
                <div style={styles.fieldGroup}>
                  <label style={styles.fieldLabel}>Font Family</label>
                  <input
                    style={styles.input}
                    value={draftFonts[slot].family}
                    onChange={(e) => updateFont(slot, 'family', e.target.value)}
                    placeholder="e.g. Inter, Poppins, Playfair Display"
                  />
                </div>
                <div style={styles.fieldGroup}>
                  <label style={styles.fieldLabel}>Weight</label>
                  <select
                    style={styles.select}
                    value={draftFonts[slot].weight}
                    onChange={(e) => updateFont(slot, 'weight', e.target.value)}
                  >
                    {['300', '400', '500', '600', '700', '800', '900'].map((w) => (
                      <option key={w} value={w}>
                        {w}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={styles.fieldGroup}>
                  <label style={styles.fieldLabel}>Size (px)</label>
                  <input
                    style={styles.input}
                    type="number"
                    min={8}
                    max={120}
                    value={draftFonts[slot].size_px}
                    onChange={(e) => updateFont(slot, 'size_px', Number(e.target.value))}
                  />
                </div>
              </div>
            </div>
          ))}
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveFonts}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Fonts'}
          </button>
        </div>
      )}

      {/* ── Tab: Logos ───────────────────────────────────────────────────── */}
      {activeTab === 'logos' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Logo Assets</h2>
            <p style={styles.panelSub}>
              Provide URLs for each logo variant. AI will use the appropriate version based on the content context.
            </p>
          </div>
          <div style={styles.logoGrid}>
            {(
              [
                { key: 'main', label: 'Main Logo', desc: 'Primary logo — light backgrounds' },
                { key: 'dark_variant', label: 'Dark Variant', desc: 'Dark-mode / dark background version' },
                { key: 'light_variant', label: 'Light Variant', desc: 'Light-mode / white background version' },
                { key: 'icon', label: 'Icon / Mark', desc: 'Square logomark — avatars, favicons' },
              ] as const
            ).map(({ key, label, desc }) => (
              <div key={key} style={styles.logoItem}>
                <div style={styles.logoPreviewWrap}>
                  {draftLogos[key] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={draftLogos[key]!} alt={label} style={styles.logoPreviewImg} />
                  ) : (
                    <div style={styles.logoPlaceholder}>No logo</div>
                  )}
                </div>
                <label style={styles.fieldLabel}>{label}</label>
                <p style={styles.fieldHint}>{desc}</p>
                <input
                  style={styles.input}
                  type="url"
                  value={draftLogos[key] ?? ''}
                  onChange={(e) => setDraftLogos((p) => ({ ...p, [key]: e.target.value || null }))}
                  placeholder="https://cdn.example.com/logo.png"
                />
              </div>
            ))}
          </div>
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveLogos}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Logos'}
          </button>
        </div>
      )}

      {/* ── Tab: Voice & Tone ────────────────────────────────────────────── */}
      {activeTab === 'voice' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Voice & Tone</h2>
            <p style={styles.panelSub}>
              Tell the AI how your brand speaks. Every generated caption, headline, or email will match this voice.
            </p>
          </div>
          <div style={styles.voicePresetGrid}>
            {TONE_PRESETS.map((preset) => (
              <button
                key={preset}
                type="button"
                style={{
                  ...styles.voicePresetCard,
                  ...(draftVoice.tone_preset === preset ? styles.voicePresetActive : {}),
                }}
                onClick={() => setDraftVoice((p) => ({ ...p, tone_preset: preset }))}
              >
                <span style={styles.voicePresetIcon}>
                  {preset === 'professional'
                    ? '👔'
                    : preset === 'friendly'
                      ? '😊'
                      : preset === 'bold'
                        ? '💪'
                        : preset === 'playful'
                          ? '🎉'
                          : preset === 'witty'
                            ? '😏'
                            : '✏️'}
                </span>
                <span style={styles.voicePresetName}>{preset.charAt(0).toUpperCase() + preset.slice(1)}</span>
              </button>
            ))}
          </div>
          {draftVoice.tone_preset === 'custom' && (
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Custom Voice Description</label>
              <textarea
                style={styles.textarea}
                value={draftVoice.custom_description}
                onChange={(e) => setDraftVoice((p) => ({ ...p, custom_description: e.target.value }))}
                placeholder="Describe your brand voice in your own words — e.g. 'Dry wit, never cringe. Confident without bragging.'"
                rows={3}
              />
            </div>
          )}
          <div style={styles.fieldRow}>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Formality</label>
              <select
                style={styles.select}
                value={draftVoice.formality}
                onChange={(e) => setDraftVoice((p) => ({ ...p, formality: e.target.value }))}
              >
                {['formal', 'semi-formal', 'casual', 'very-casual'].map((f) => (
                  <option key={f} value={f}>
                    {f.charAt(0).toUpperCase() + f.slice(1).replace('-', ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Emotional Tone</label>
              <select
                style={styles.select}
                value={draftVoice.emotion}
                onChange={(e) => setDraftVoice((p) => ({ ...p, emotion: e.target.value }))}
              >
                {['confident', 'enthusiastic', 'empathetic', 'authoritative', 'warm', 'inspiring', 'direct'].map(
                  (e) => (
                    <option key={e} value={e}>
                      {e.charAt(0).toUpperCase() + e.slice(1)}
                    </option>
                  )
                )}
              </select>
            </div>
          </div>
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveVoice}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Voice & Tone'}
          </button>
        </div>
      )}

      {/* ── Tab: Key Messaging ───────────────────────────────────────────── */}
      {activeTab === 'messaging' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Key Messaging</h2>
            <p style={styles.panelSub}>
              Establish your brand narrative — elevator pitches, taglines, and audience definitions that anchor all
              content.
            </p>
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Brand Name</label>
            <input
              style={styles.input}
              value={draftMessaging.brand_name}
              onChange={(e) => setDraftMessaging((p) => ({ ...p, brand_name: e.target.value }))}
              placeholder="Your brand or company name"
            />
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Tagline</label>
            <input
              style={styles.input}
              value={draftMessaging.tagline}
              onChange={(e) => setDraftMessaging((p) => ({ ...p, tagline: e.target.value }))}
              placeholder="Short, memorable brand tagline"
            />
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Value Proposition</label>
            <textarea
              style={styles.textarea}
              rows={2}
              value={draftMessaging.value_proposition}
              onChange={(e) => setDraftMessaging((p) => ({ ...p, value_proposition: e.target.value }))}
              placeholder="What unique value does your brand deliver?"
            />
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Elevator Pitch (1–2 sentences)</label>
            <textarea
              style={styles.textarea}
              rows={3}
              value={draftMessaging.elevator_pitch}
              onChange={(e) => setDraftMessaging((p) => ({ ...p, elevator_pitch: e.target.value }))}
              placeholder="How you'd describe your brand in 30 seconds"
            />
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Target Audience</label>
            <input
              style={styles.input}
              value={draftMessaging.target_audience}
              onChange={(e) => setDraftMessaging((p) => ({ ...p, target_audience: e.target.value }))}
              placeholder="e.g. Marketing managers at B2B SaaS companies with 50–500 employees"
            />
          </div>
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveMessaging}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Messaging'}
          </button>
        </div>
      )}

      {/* ── Tab: Writing Rules ───────────────────────────────────────────── */}
      {activeTab === 'writing' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Writing Rules</h2>
            <p style={styles.panelSub}>
              Guardrails for AI-generated copy — preferred terms, banned words, sentence style preferences.
            </p>
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Terms to Use</label>
            <div style={styles.tagInputRow}>
              <input
                style={{ ...styles.input, flex: 1 }}
                value={termToUseInput}
                onChange={(e) => setTermToUseInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTermToUse())}
                placeholder="Type a preferred term and press Enter"
              />
              <button style={styles.tagAddBtn} type="button" onClick={addTermToUse}>
                Add
              </button>
            </div>
            <div style={styles.tagCloud}>
              {draftWriting.terms_to_use.map((t) => (
                <span key={t} style={styles.tagGreen}>
                  {t}
                  <button
                    type="button"
                    style={styles.tagRemove}
                    onClick={() =>
                      setDraftWriting((p) => ({ ...p, terms_to_use: p.terms_to_use.filter((x) => x !== t) }))
                    }
                  >
                    ×
                  </button>
                </span>
              ))}
              {draftWriting.terms_to_use.length === 0 && <span style={styles.tagEmpty}>No preferred terms yet</span>}
            </div>
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Terms to Avoid</label>
            <div style={styles.tagInputRow}>
              <input
                style={{ ...styles.input, flex: 1 }}
                value={termToAvoidInput}
                onChange={(e) => setTermToAvoidInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTermToAvoid())}
                placeholder="Type a banned term and press Enter"
              />
              <button style={styles.tagAddBtn} type="button" onClick={addTermToAvoid}>
                Add
              </button>
            </div>
            <div style={styles.tagCloud}>
              {draftWriting.terms_to_avoid.map((t) => (
                <span key={t} style={styles.tagRed}>
                  {t}
                  <button
                    type="button"
                    style={styles.tagRemove}
                    onClick={() =>
                      setDraftWriting((p) => ({ ...p, terms_to_avoid: p.terms_to_avoid.filter((x) => x !== t) }))
                    }
                  >
                    ×
                  </button>
                </span>
              ))}
              {draftWriting.terms_to_avoid.length === 0 && <span style={styles.tagEmpty}>No banned terms yet</span>}
            </div>
          </div>
          <div style={styles.fieldRow}>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Sentence Length Preference</label>
              <select
                style={styles.select}
                value={draftWriting.preferred_sentences}
                onChange={(e) => setDraftWriting((p) => ({ ...p, preferred_sentences: e.target.value }))}
              >
                <option value="short">Short — punchy and direct</option>
                <option value="medium">Medium — balanced and readable</option>
                <option value="long">Long — detailed and thorough</option>
              </select>
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Oxford Comma</label>
              <div style={styles.toggleRow}>
                <button
                  type="button"
                  style={{ ...styles.toggleBtn, ...(draftWriting.use_oxford_comma ? styles.toggleBtnOn : {}) }}
                  onClick={() => setDraftWriting((p) => ({ ...p, use_oxford_comma: true }))}
                >
                  Use it
                </button>
                <button
                  type="button"
                  style={{ ...styles.toggleBtn, ...(!draftWriting.use_oxford_comma ? styles.toggleBtnOn : {}) }}
                  onClick={() => setDraftWriting((p) => ({ ...p, use_oxford_comma: false }))}
                >
                  Skip it
                </button>
              </div>
            </div>
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.fieldLabel}>Additional Notes for AI</label>
            <textarea
              style={styles.textarea}
              rows={3}
              value={draftWriting.notes}
              onChange={(e) => setDraftWriting((p) => ({ ...p, notes: e.target.value }))}
              placeholder="Any other editorial guidelines, style preferences, or special instructions"
            />
          </div>
          <button
            style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
            onClick={saveWriting}
            disabled={busy}
            type="button"
          >
            {busy ? 'Saving…' : 'Save Writing Rules'}
          </button>
        </div>
      )}

      {/* ── Tab: Knowledge Base ──────────────────────────────────────────── */}
      {activeTab === 'knowledge' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Knowledge Base</h2>
            <p style={styles.panelSub}>
              Feed the AI context about your brand — web pages, text excerpts, and PDF documents it can reference when
              generating content.
            </p>
          </div>
          <div style={styles.kbAddBox}>
            <h3 style={styles.kbAddTitle}>Add New Entry</h3>
            <div style={styles.fieldRow}>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Entry Type</label>
                <select
                  style={styles.select}
                  value={kbType}
                  onChange={(e) => setKbType(e.target.value as 'url' | 'text' | 'pdf_title')}
                >
                  <option value="url">URL — Website or web page</option>
                  <option value="text">Text — Paste content directly</option>
                  <option value="pdf_title">PDF Title — Reference by filename</option>
                </select>
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Label (optional)</label>
                <input
                  style={styles.input}
                  value={kbLabel}
                  onChange={(e) => setKbLabel(e.target.value)}
                  placeholder="E.g. About page, Q3 Brief"
                />
              </div>
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>
                {kbType === 'url' ? 'URL' : kbType === 'text' ? 'Content' : 'PDF Filename'}
              </label>
              {kbType === 'text' ? (
                <textarea
                  style={styles.textarea}
                  rows={4}
                  value={kbContent}
                  onChange={(e) => setKbContent(e.target.value)}
                  placeholder="Paste the text content to add to the knowledge base"
                />
              ) : (
                <input
                  style={styles.input}
                  value={kbContent}
                  onChange={(e) => setKbContent(e.target.value)}
                  placeholder={kbType === 'url' ? 'https://example.com/about' : 'Brand_Guidelines_2026.pdf'}
                />
              )}
            </div>
            <button
              style={{ ...styles.saveBtn, ...(busy ? styles.saveBtnDisabled : {}) }}
              onClick={addKBEntry}
              disabled={busy || !kbContent.trim()}
              type="button"
            >
              {busy ? 'Adding…' : 'Add to Knowledge Base'}
            </button>
          </div>
          <div style={styles.kbList}>
            <h3 style={styles.kbAddTitle}>Indexed Entries ({kb.length})</h3>
            {kb.length === 0 && <p style={styles.emptyState}>No entries yet. Add URLs, text, or PDF titles above.</p>}
            {kb.map((entry) => (
              <div key={entry.id} style={styles.kbEntry}>
                <div style={styles.kbEntryLeft}>
                  <span style={styles.kbEntryType}>{entry.entry_type}</span>
                  <div style={styles.kbEntryContent}>{entry.label || entry.content}</div>
                  {entry.label && <div style={styles.kbEntryMeta}>{entry.content}</div>}
                </div>
                <div style={styles.kbEntryRight}>
                  <span
                    style={{
                      ...styles.kbStatusBadge,
                      background:
                        entry.status === 'indexed' ? '#dcfce7' : entry.status === 'pending' ? '#fef3c7' : '#fee2e2',
                      color:
                        entry.status === 'indexed' ? '#15803d' : entry.status === 'pending' ? '#b45309' : '#dc2626',
                    }}
                  >
                    {entry.status}
                  </span>
                  <button
                    type="button"
                    style={styles.kbDeleteBtn}
                    onClick={() => deleteKBEntry(entry.id)}
                    disabled={busy}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tab: AI Preview ──────────────────────────────────────────────── */}
      {activeTab === 'preview' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>AI Brand Preview</h2>
            <p style={styles.panelSub}>
              Generate sample content using your brand kit settings. See exactly how the AI applies your voice,
              messaging, and style rules.
            </p>
          </div>
          <div style={styles.previewControls}>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Content Type</label>
              <select style={styles.select} value={previewType} onChange={(e) => setPreviewType(e.target.value)}>
                <option value="social_caption">Social Media Caption</option>
                <option value="blog_intro">Blog Post Intro</option>
                <option value="ad_copy">Ad Copy</option>
                <option value="email_subject">Email Subject Line</option>
                <option value="tagline_variant">Tagline Variant</option>
              </select>
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Topic / Context (optional)</label>
              <input
                style={styles.input}
                value={previewTopic}
                onChange={(e) => setPreviewTopic(e.target.value)}
                placeholder="e.g. Summer sale launch, new product announcement, Q4 campaign"
              />
            </div>
            <button
              type="button"
              style={{ ...styles.generateBtn, ...(generating ? styles.saveBtnDisabled : {}) }}
              onClick={generatePreview}
              disabled={generating}
            >
              {generating ? '⟳ Generating…' : '✦ Generate Preview'}
            </button>
          </div>
          {previewResult && (
            <div style={styles.previewCard}>
              <div style={styles.previewCardHeader}>
                <span style={styles.previewTypeLabel}>{previewResult.content_type.replace('_', ' ')}</span>
                <span style={styles.previewTimestamp}>{new Date(previewResult.generated_at).toLocaleTimeString()}</span>
              </div>
              <p style={styles.previewText}>{previewResult.generated_text}</p>
              <div style={styles.complianceSection}>
                <h4 style={styles.complianceTitle}>Brand Compliance Check</h4>
                <div style={styles.complianceGrid}>
                  {[
                    { label: 'Avoids banned terms', ok: previewResult.compliance_check.avoids_banned_terms },
                    { label: 'Uses preferred terms', ok: previewResult.compliance_check.uses_preferred_terms },
                    { label: 'Tone aligned', ok: previewResult.compliance_check.tone_aligned },
                  ].map(({ label, ok }) => (
                    <div key={label} style={styles.complianceItem}>
                      <span style={{ color: ok ? '#15803d' : '#EF4444' }}>{ok ? '✓' : '✗'}</span>
                      <span style={styles.complianceLabel}>{label}</span>
                    </div>
                  ))}
                </div>
                {previewResult.compliance_check.issues.length > 0 && (
                  <div style={styles.complianceIssues}>
                    {previewResult.compliance_check.issues.map((issue, i) => (
                      <p key={i} style={styles.complianceIssue}>
                        ⚠ {issue}
                      </p>
                    ))}
                  </div>
                )}
              </div>
              <div style={styles.previewSnapWrap}>
                <span style={styles.fieldLabel}>Applied brand kit — </span>
                <span style={styles.previewSnapText}>
                  {previewResult.brand_kit_snapshot.brand_name} · {previewResult.brand_kit_snapshot.tagline} · Tone:{' '}
                  {previewResult.brand_kit_snapshot.tone_preset}
                </span>
              </div>
            </div>
          )}
          {!previewResult && !generating && (
            <div style={styles.previewEmpty}>
              <p>Click "Generate Preview" to see AI-generated content using your brand kit.</p>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Analytics ───────────────────────────────────────────────── */}
      {activeTab === 'analytics' && (
        <div style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Brand Kit Analytics</h2>
            <p style={styles.panelSub}>
              Track how your brand kit is being used and how complete your brand profile is.
            </p>
          </div>
          {analytics ? (
            <>
              <div style={styles.analyticsTopRow}>
                <div style={styles.completenessCard}>
                  <CompletenessRing score={analytics.kit_completeness} />
                  <div style={styles.completenessInfo}>
                    <h3 style={styles.completenessTitle}>Kit Completeness</h3>
                    <p style={styles.completenessSub}>{completenessLabel}</p>
                  </div>
                </div>
                <div style={styles.statCard}>
                  <span style={styles.statNum}>{analytics.total_generations}</span>
                  <span style={styles.statLabel}>AI generations using this kit</span>
                </div>
              </div>
              <div style={styles.sectionStatusGrid}>
                {(
                  [
                    { key: 'colors_configured', label: 'Colors' },
                    { key: 'fonts_configured', label: 'Fonts' },
                    { key: 'logos_configured', label: 'Logos' },
                    { key: 'voice_configured', label: 'Voice' },
                    { key: 'messaging_configured', label: 'Messaging' },
                    { key: 'writing_rules_configured', label: 'Writing Rules' },
                  ] as const
                ).map(({ key, label }) => (
                  <div
                    key={key}
                    style={{
                      ...styles.sectionStatusItem,
                      borderColor: analytics[key] ? '#dcfce7' : '#fee2e2',
                      background: analytics[key] ? '#0F2719' : '#1C0F0F',
                    }}
                  >
                    <span style={{ color: analytics[key] ? '#15803d' : '#EF4444', fontSize: 18 }}>
                      {analytics[key] ? '✓' : '○'}
                    </span>
                    <span style={styles.sectionStatusLabel}>{label}</span>
                  </div>
                ))}
              </div>
              {Object.keys(analytics.by_type).length > 0 && (
                <div style={styles.byTypeSection}>
                  <h3 style={styles.byTypeTitle}>Generations by Content Type</h3>
                  {Object.entries(analytics.by_type).map(([type, count]) => {
                    const maxCount = Math.max(1, ...Object.values(analytics.by_type));
                    const pct = (count / maxCount) * 100;
                    return (
                      <div key={type} style={styles.byTypeRow}>
                        <span style={styles.byTypeLabel}>{type.replace(/_/g, ' ')}</span>
                        <div style={styles.byTypeBarWrap}>
                          <div style={{ ...styles.byTypeBar, width: `${pct}%` }} />
                        </div>
                        <span style={styles.byTypeCount}>{count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
              {Object.keys(analytics.by_type).length === 0 && (
                <p style={styles.emptyState}>No AI generations yet. Use the AI Preview tab to generate content.</p>
              )}
            </>
          ) : (
            <p style={styles.emptyState}>Loading analytics…</p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: 'var(--card)',
    color: 'var(--text)',
    padding: '32px 40px',
    fontFamily: 'Inter, sans-serif',
  },
  loadWrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '60vh',
    gap: 16,
  },
  loadSpinner: {
    width: 36,
    height: 36,
    border: '3px solid var(--line)',
    borderTopColor: '#6366F1',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadText: { color: 'var(--muted)', fontSize: 14 },

  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 },
  h1: { fontSize: 28, fontWeight: 700, color: 'var(--text)', margin: 0 },
  headerSub: { fontSize: 14, color: 'var(--muted)', margin: '6px 0 0', maxWidth: 560 },
  headerRight: { display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 },
  freshPill: { fontSize: 12, fontWeight: 600, padding: '4px 10px', borderRadius: 16 },
  freshLive: { background: '#dcfce7', color: '#15803d' },
  freshUnavailable: { background: '#fef3c7', color: '#b45309' },
  completenessChip: { fontSize: 12, color: 'var(--muted)', background: 'var(--card)', padding: '4px 10px', borderRadius: 16 },

  toastSuccess: {
    background: '#dcfce7',
    color: '#15803d',
    padding: '10px 16px',
    borderRadius: 8,
    marginBottom: 16,
    fontSize: 14,
  },
  toastError: {
    background: '#fee2e2',
    color: '#dc2626',
    padding: '10px 16px',
    borderRadius: 8,
    marginBottom: 16,
    fontSize: 14,
  },

  tabBar: { display: 'flex', flexWrap: 'wrap', gap: 4, borderBottom: '1px solid var(--line)', marginBottom: 28 },
  tabBtn: {
    padding: '10px 18px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--muted)',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    borderRadius: '4px 4px 0 0',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    transition: 'color 0.15s',
  },
  tabBtnActive: { color: '#6366F1', borderBottomColor: '#6366F1', background: 'var(--card)' },
  tabBadge: {
    background: 'var(--card)',
    color: 'var(--muted)',
    fontSize: 11,
    fontWeight: 700,
    padding: '1px 6px',
    borderRadius: 10,
  },

  panel: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: '28px 32px' },
  panelHead: { marginBottom: 24 },
  panelTitle: { fontSize: 20, fontWeight: 700, color: 'var(--text)', margin: '0 0 6px' },
  panelSub: { fontSize: 14, color: 'var(--muted)', margin: 0, lineHeight: 1.5 },

  saveBtn: {
    marginTop: 24,
    padding: '11px 24px',
    background: '#6366F1',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  saveBtnDisabled: { opacity: 0.5, cursor: 'not-allowed' },

  // Colors
  colorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
    gap: 20,
    marginBottom: 24,
  },
  colorItem: { display: 'flex', flexDirection: 'column', gap: 6 },
  colorPreview: { height: 60, borderRadius: 8, border: '1px solid var(--line)' },
  colorInputRow: { display: 'flex', gap: 6, alignItems: 'center' },
  colorPicker: {
    width: 36,
    height: 36,
    border: 'none',
    padding: 0,
    borderRadius: 4,
    cursor: 'pointer',
    background: 'transparent',
  },
  hexInput: {
    flex: 1,
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 6,
    color: 'var(--text)',
    padding: '6px 8px',
    fontSize: 13,
    fontFamily: 'monospace',
  },
  palettePreview: { background: 'var(--card)', borderRadius: 8, padding: 16, marginBottom: 8 },
  paletteRow: { display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8 },
  paletteSwatch: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 },
  swatchLabel: { fontSize: 11, color: 'var(--muted)' },

  // Fonts
  fontRow: { background: 'var(--card)', borderRadius: 10, padding: '18px 20px', marginBottom: 16 },
  fontSlotTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--muted)',
    textTransform: 'uppercase',
    letterSpacing: 1,
    margin: '0 0 10px',
  },
  fontPreviewText: {
    background: 'var(--card)',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 12,
    color: 'var(--text)',
    overflow: 'hidden',
  },
  fontFields: { display: 'grid', gridTemplateColumns: '1fr 120px 120px', gap: 12 },

  // Logos
  logoGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 20 },
  logoItem: { background: 'var(--card)', borderRadius: 10, padding: 16 },
  logoPreviewWrap: {
    height: 80,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    background: 'var(--card)',
    borderRadius: 8,
    border: '1px solid var(--line)',
  },
  logoPreviewImg: { maxHeight: 68, maxWidth: '100%', objectFit: 'contain' },
  logoPlaceholder: { fontSize: 12, color: '#e7e9ef' },
  fieldHint: { fontSize: 11, color: '#e7e9ef', margin: '2px 0 8px' },

  // Voice
  voicePresetGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 130px), 1fr))',
    gap: 12,
    marginBottom: 24,
  },
  voicePresetCard: {
    background: 'var(--card)',
    border: '2px solid var(--line)',
    borderRadius: 10,
    padding: '14px 10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  voicePresetActive: { borderColor: '#6366F1', background: 'var(--text)' },
  voicePresetIcon: { fontSize: 24 },
  voicePresetName: { fontSize: 13, fontWeight: 600, color: 'var(--text)' },

  // Knowledge Base
  kbAddBox: { background: 'var(--card)', borderRadius: 10, padding: '20px 22px', marginBottom: 24 },
  kbAddTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--muted)',
    margin: '0 0 14px',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  kbList: { display: 'flex', flexDirection: 'column', gap: 8 },
  kbEntry: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '12px 16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  kbEntryLeft: { flex: 1, minWidth: 0 },
  kbEntryType: {
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: '#6366F1',
    background: 'var(--text)',
    padding: '2px 6px',
    borderRadius: 4,
    marginRight: 8,
  },
  kbEntryContent: {
    fontSize: 14,
    color: 'var(--text)',
    marginTop: 6,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  kbEntryMeta: {
    fontSize: 11,
    color: '#e7e9ef',
    marginTop: 2,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  kbEntryRight: { display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 },
  kbStatusBadge: { fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10 },
  kbDeleteBtn: {
    background: 'transparent',
    border: '1px solid #fee2e2',
    color: '#dc2626',
    fontSize: 12,
    padding: '4px 10px',
    borderRadius: 6,
    cursor: 'pointer',
  },

  // Preview
  previewControls: { display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 },
  generateBtn: {
    padding: '12px 28px',
    background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    alignSelf: 'flex-start',
  },
  previewCard: { background: 'var(--card)', border: '1px solid #6366F1', borderRadius: 12, padding: '20px 24px' },
  previewCardHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 14 },
  previewTypeLabel: {
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: '#6366F1',
    background: 'var(--text)',
    padding: '3px 8px',
    borderRadius: 4,
  },
  previewTimestamp: { fontSize: 12, color: '#e7e9ef' },
  previewText: { fontSize: 16, lineHeight: 1.7, color: 'var(--text)', margin: '0 0 20px', whiteSpace: 'pre-wrap' },
  complianceSection: { background: 'var(--card)', borderRadius: 8, padding: '14px 16px', marginBottom: 14 },
  complianceTitle: {
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    color: 'var(--muted)',
    margin: '0 0 10px',
  },
  complianceGrid: { display: 'flex', gap: 20, flexWrap: 'wrap' },
  complianceItem: { display: 'flex', alignItems: 'center', gap: 6 },
  complianceLabel: { fontSize: 13, color: 'var(--muted)' },
  complianceIssues: { marginTop: 10 },
  complianceIssue: { fontSize: 12, color: '#b45309', margin: '3px 0' },
  previewSnapWrap: { fontSize: 12, color: '#e7e9ef' },
  previewSnapText: { color: 'var(--muted)' },
  previewEmpty: {
    background: 'var(--card)',
    borderRadius: 10,
    padding: '40px 24px',
    textAlign: 'center',
    color: '#e7e9ef',
    fontSize: 14,
  },

  // Analytics
  analyticsTopRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 20, marginBottom: 24 },
  completenessCard: {
    background: 'var(--card)',
    borderRadius: 12,
    padding: '20px 24px',
    display: 'flex',
    alignItems: 'center',
    gap: 20,
  },
  completenessInfo: {},
  completenessTitle: { fontSize: 16, fontWeight: 700, color: 'var(--text)', margin: '0 0 6px' },
  completenessSub: { fontSize: 13, color: 'var(--muted)', margin: 0 },
  statCard: {
    background: 'var(--card)',
    borderRadius: 12,
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  statNum: { fontSize: 40, fontWeight: 800, color: '#6366F1', lineHeight: 1 },
  statLabel: { fontSize: 12, color: 'var(--muted)', textAlign: 'center' },
  sectionStatusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))',
    gap: 10,
    marginBottom: 24,
  },
  sectionStatusItem: {
    border: '1px solid',
    borderRadius: 8,
    padding: '12px 14px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  sectionStatusLabel: { fontSize: 13, color: 'var(--text)', fontWeight: 500 },
  byTypeSection: { background: 'var(--card)', borderRadius: 10, padding: '18px 20px' },
  byTypeTitle: { fontSize: 14, fontWeight: 600, color: 'var(--muted)', margin: '0 0 14px' },
  byTypeRow: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 },
  byTypeLabel: { fontSize: 13, color: 'var(--muted)', width: 160, flexShrink: 0, textTransform: 'capitalize' },
  byTypeBarWrap: { flex: 1, height: 6, background: 'var(--card)', borderRadius: 3, overflow: 'hidden' },
  byTypeBar: {
    height: '100%',
    background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
    borderRadius: 3,
    transition: 'width 0.4s',
  },
  byTypeCount: { fontSize: 13, color: 'var(--muted)', width: 30, textAlign: 'right', flexShrink: 0 },

  // Shared form
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 6 },
  fieldRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 },
  fieldLabel: { fontSize: 12, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 0.8 },
  input: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '10px 12px',
    fontSize: 14,
    outline: 'none',
  },
  select: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '10px 12px',
    fontSize: 14,
    outline: 'none',
  },
  textarea: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '10px 12px',
    fontSize: 14,
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  tagInputRow: { display: 'flex', gap: 8 },
  tagAddBtn: {
    padding: '10px 16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--muted)',
    fontSize: 13,
    cursor: 'pointer',
    flexShrink: 0,
  },
  tagCloud: { display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  tagGreen: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    background: '#dcfce7',
    color: '#15803d',
    fontSize: 12,
    padding: '3px 8px 3px 10px',
    borderRadius: 16,
  },
  tagRed: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    background: '#fee2e2',
    color: '#dc2626',
    fontSize: 12,
    padding: '3px 8px 3px 10px',
    borderRadius: 16,
  },
  tagRemove: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    color: 'inherit',
    lineHeight: 1,
    padding: 0,
  },
  tagEmpty: { fontSize: 12, color: '#e7e9ef' },
  toggleRow: { display: 'flex', gap: 8 },
  toggleBtn: {
    padding: '8px 16px',
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--muted)',
    fontSize: 13,
    cursor: 'pointer',
  },
  toggleBtnOn: { background: 'var(--text)', borderColor: '#6366F1', color: 'var(--brand)' },
  emptyState: { color: '#e7e9ef', fontSize: 14, padding: '20px 0', textAlign: 'center' },
};
