'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type Language = {
  code: string;
  name: string;
  rtl: boolean;
  flag: string;
};

type Translation = {
  language_code: string;
  language_name: string;
  translated_copy: string;
  rtl: boolean;
  culturally_adapted: boolean;
  provider: string;
  characters: number;
};

type SupportedLanguagesResponse = {
  languages: Language[];
};

type MultilingualAdsResponse = {
  translations: Translation[];
};

const SOURCE_LANGUAGES = ['en', 'es', 'fr', 'de', 'pt', 'it', 'nl', 'ru', 'zh', 'ja', 'ko', 'ar'];

export default function MultilingualAdsPage() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [loading, setLoading] = useState(true);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Translation[]>([]);

  // Form
  const [sourceCopy, setSourceCopy] = useState('');
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLangs, setTargetLangs] = useState<string[]>(['es', 'fr', 'de']);
  const [culturallyAdapt, setCulturallyAdapt] = useState(true);
  const [adType, setAdType] = useState('social');

  useEffect(() => { loadLanguages(); }, []);

  async function loadLanguages() {
    setLoading(true);
    try {
      const data = await apiGet<SupportedLanguagesResponse>('/ai/social-studio/supported-languages', DEFAULT_TENANT_ID);
      setLanguages(data.languages ?? []);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); }
  }

  async function handleTranslate(e: React.FormEvent) {
    e.preventDefault();
    if (!sourceCopy.trim()) { setError('Ad copy is required.'); return; }
    if (targetLangs.length === 0) { setError('Select at least one target language.'); return; }
    setTranslating(true); setError(null); setResults([]);
    try {
      const data = await apiSend<MultilingualAdsResponse>('/ai/social-studio/multilingual-ads', 'POST', {
        source_copy: sourceCopy,
        source_language: sourceLang,
        target_languages: targetLangs,
        culturally_adapt: culturallyAdapt,
        ad_type: adType,
      }, DEFAULT_TENANT_ID);
      setResults(data.translations ?? []);
    } catch (e: unknown) { setError(String(e)); }
    finally { setTranslating(false); }
  }

  const toggleLang = (code: string) => {
    setTargetLangs((prev) => prev.includes(code) ? prev.filter((l) => l !== code) : [...prev, code]);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--card)', color: 'var(--text)', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ background: 'var(--card)', borderBottom: '1px solid var(--line)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/studio" style={{ color: 'var(--muted)', textDecoration: 'none', fontSize: 14 }}>← Studio</Link>
          <span style={{ color: '#e7e9ef' }}>|</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>🌐 Multilingual Ads</span>
          <span style={{ background: '#6366f122', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600 }}>20+ LANGUAGES · RTL SUPPORT</span>
        </div>
        <Link href="/studio/social-studio/ads" style={{ background: 'var(--card)', color: 'var(--text)', padding: '8px 16px', borderRadius: 8, textDecoration: 'none', fontSize: 13 }}>
          Ads Manager →
        </Link>
      </div>

      {/* Stats */}
      <div style={{ background: 'var(--card)', padding: '12px 32px', display: 'flex', gap: 32, borderBottom: '1px solid var(--line)' }}>
        {[{ label: 'Languages', value: `${languages.length || '20+'}` }, { label: 'RTL Support', value: `${languages.filter((l) => l.rtl).length || '4'}` }, { label: 'Providers', value: 'DeepL · GPT-4 · Google' }, { label: 'Cultural Adapt', value: 'Yes' }].map((s) => (
          <div key={s.label}><div style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>{s.value}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</div></div>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
        {error && <div style={{ background: '#fee2e233', border: '1px solid #EF4444', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626' }}>{error}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 32 }}>
          {/* Left: Input form */}
          <div>
            <form onSubmit={handleTranslate}>
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 20 }}>
                <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Ad Copy</div>

                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>SOURCE LANGUAGE</label>
                  <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}>
                    {SOURCE_LANGUAGES.map((code) => (
                      <option key={code} value={code}>{code.toUpperCase()}</option>
                    ))}
                  </select>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>AD TYPE</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {['social', 'search', 'display', 'email'].map((t) => (
                      <button key={t} type="button" onClick={() => setAdType(t)} style={{ background: adType === t ? '#6366f1' : '#eef0f4', color: adType === t ? '#fff' : 'var(--muted)', border: `1px solid ${adType === t ? '#6366f1' : '#e7e9ef'}`, padding: '6px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 12, textTransform: 'capitalize' }}>
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>SOURCE COPY *</label>
                  <textarea value={sourceCopy} onChange={(e) => setSourceCopy(e.target.value)} placeholder="Paste your ad copy here in the source language…&#10;&#10;e.g. Discover our summer collection. Limited time offer — 30% off all items. Shop now and enjoy free shipping on orders over $50." rows={8} style={{ width: '100%', background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{sourceCopy.trim().split(/\s+/).filter(Boolean).length} words</div>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 20, fontSize: 14, color: 'var(--text)' }}>
                  <input type="checkbox" checked={culturallyAdapt} onChange={(e) => setCulturallyAdapt(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#6366f1' }} />
                  Cultural adaptation (idioms, tone, local references)
                </label>

                <button type="submit" disabled={translating} style={{ width: '100%', background: translating ? '#e7e9ef' : '#6366f1', color: '#fff', border: 'none', padding: '14px 24px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: translating ? 'not-allowed' : 'pointer' }}>
                  {translating ? `⏳ Translating into ${targetLangs.length} languages…` : `🌐 Translate to ${targetLangs.length} Language${targetLangs.length !== 1 ? 's' : ''}`}
                </button>
              </div>

              {/* Target language selector */}
              <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
                  Target Languages
                  <span style={{ marginLeft: 8, background: '#6366f133', color: 'var(--brand)', fontSize: 11, padding: '2px 8px', borderRadius: 10 }}>{targetLangs.length} selected</span>
                </div>
                {loading ? (
                  <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading languages…</div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {languages.map((lang) => (
                      <button key={lang.code} type="button" onClick={() => toggleLang(lang.code)} style={{ background: targetLangs.includes(lang.code) ? '#6366f133' : '#eef0f4', border: `1px solid ${targetLangs.includes(lang.code) ? '#6366f1' : '#e7e9ef'}`, color: targetLangs.includes(lang.code) ? 'var(--brand)' : 'var(--muted)', padding: '6px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span>{lang.flag}</span>
                        <span>{lang.name}</span>
                        {lang.rtl && <span style={{ fontSize: 9, color: '#F59E0B', background: '#fef3c7', padding: '1px 4px', borderRadius: 3 }}>RTL</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </form>

            {/* Providers */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginTop: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600, letterSpacing: 1 }}>AI PROVIDERS</div>
              {[{ name: 'DeepL API', env: 'DEEPL_API_KEY', tier: 'Primary — highest quality' }, { name: 'OpenAI GPT-4', env: 'OPENAI_API_KEY', tier: 'Cultural adaptation' }, { name: 'Google Translate', env: 'GOOGLE_TRANSLATE_KEY', tier: 'Backup' }].map((v) => (
                <div key={v.name} style={{ marginBottom: 8, padding: '8px 10px', background: 'var(--card)', borderRadius: 6 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{v.name}</div>
                  <div style={{ fontSize: 10, color: '#6366f1' }}>{v.env}</div>
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{v.tier}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Results */}
          <div>
            {results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--muted)', background: 'var(--card)', borderRadius: 12, border: '1px dashed #e7e9ef' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🌐</div>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Translations appear here</div>
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>Select target languages and click Translate</div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{results.length} translations ready</span>
                  <button onClick={() => { const text = results.map((r) => `[${r.language_name}]\n${r.translated_copy}`).join('\n\n---\n\n'); navigator.clipboard?.writeText(text); }} style={{ background: '#e7e9ef', color: 'var(--text)', border: 'none', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                    📋 Copy All
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {results.map((t) => (
                    <div key={t.language_code} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 20 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 18 }}>{languages.find((l) => l.code === t.language_code)?.flag ?? '🌐'}</span>
                          <span style={{ fontSize: 15, fontWeight: 700 }}>{t.language_name}</span>
                          {t.rtl && <span style={{ background: '#fef3c7', color: '#F59E0B', fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>RTL</span>}
                          {t.culturally_adapted && <span style={{ background: '#dcfce733', color: '#22c55e', fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>Culturally Adapted</span>}
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>{t.provider} · {t.characters} chars</span>
                          <button onClick={() => navigator.clipboard?.writeText(t.translated_copy)} style={{ background: '#e7e9ef', color: 'var(--text)', border: 'none', padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>Copy</button>
                        </div>
                      </div>
                      <div style={{ background: 'var(--card)', borderRadius: 8, padding: 14, fontSize: 14, lineHeight: 1.6, direction: t.rtl ? 'rtl' : 'ltr', textAlign: t.rtl ? 'right' : 'left', color: 'var(--text)' }}>
                        {t.translated_copy}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
