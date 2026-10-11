'use client';

import { useState } from 'react';

interface Demographics {
  age_distribution?: Record<string, number>;
  gender_distribution?: { male: number; female: number };
  country_distribution?: { country: string; percentage: number }[];
  device_distribution?: Record<string, number>;
}

interface Interest {
  category: string;
  affinity_pct: number;
}

export default function AudienceIntelligencePage() {
  const [domains, setDomains] = useState('');
  const [loading, setLoading] = useState(false);
  const [demographics, setDemographics] = useState<Demographics | null>(null);
  const [interests, setInterests] = useState<Interest[]>([]);
  const [adTargeting, setAdTargeting] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'demographics' | 'interests' | 'targeting'>('demographics');

  async function analyze() {
    const d = domains.split(',')[0]?.trim();
    if (!d) return;
    setLoading(true);
    setError('');
    try {
      const [demRes, intRes, adRes] = await Promise.all([
        fetch(`/api/one2target/demographics?domain=${encodeURIComponent(d)}`),
        fetch(`/api/one2target/interests?domain=${encodeURIComponent(d)}`),
        fetch(`/api/one2target/ad-targeting?domain=${encodeURIComponent(d)}`),
      ]);
      const [dem, int_, ad] = await Promise.all([demRes.json(), intRes.json(), adRes.json()]);
      setDemographics(dem);
      setInterests(int_.interests || []);
      setAdTargeting(ad);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  const TABS = [
    { id: 'demographics', label: 'Demographics' },
    { id: 'interests', label: 'Interests' },
    { id: 'targeting', label: 'Ad Targeting' },
  ] as const;

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <div className="bg-[var(--card)] border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-[var(--brand)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-[var(--text)]">Audience Intelligence</h1>
          <p className="text-sm text-[var(--muted)]">Audience demographics, interests, behaviour &amp; ad targeting</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Input */}
        <div className="bg-[var(--card)] rounded-xl border shadow-sm p-6 mb-6">
          <label className="block text-sm font-medium text-[var(--muted)] mb-2">Competitor Domains (comma-separated)</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={domains}
              onChange={(e) => setDomains(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && analyze()}
              placeholder="example.com, example.org"
              className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
            />
            <button
              onClick={analyze}
              disabled={loading || !domains.trim()}
              className="bg-[var(--brand)] hover:bg-[var(--brand)] text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
            >
              {loading ? 'Analyzing…' : 'Analyze Audience'}
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>

        {(demographics || interests.length > 0) && (
          <>
            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-[var(--card)] shadow text-[var(--brand)]' : 'text-[var(--muted)] hover:text-[var(--text)]'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Demographics */}
            {activeTab === 'demographics' && demographics && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Age */}
                {demographics.age_distribution && (
                  <div className="bg-[var(--card)] rounded-xl border p-5">
                    <h3 className="font-semibold text-[var(--muted)] mb-3">Age Distribution</h3>
                    {Object.entries(demographics.age_distribution).map(([age, pct]) => (
                      <div key={age} className="mb-2">
                        <div className="flex justify-between text-sm mb-0.5">
                          <span>{age}</span>
                          <span className="font-medium">{pct}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full">
                          <div className="h-2 bg-[var(--brand)] rounded-full" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {/* Gender */}
                {demographics.gender_distribution && (
                  <div className="bg-[var(--card)] rounded-xl border p-5">
                    <h3 className="font-semibold text-[var(--muted)] mb-4">Gender</h3>
                    <div className="flex gap-4 justify-center">
                      {[
                        { label: 'Male', value: demographics.gender_distribution.male, color: 'bg-[var(--brand)]' },
                        { label: 'Female', value: demographics.gender_distribution.female, color: 'bg-pink-400' },
                      ].map((g) => (
                        <div key={g.label} className="text-center">
                          <div
                            className="w-20 h-20 rounded-full flex items-center justify-center text-[var(--text)] font-bold text-xl mx-auto mb-2"
                            style={{ background: g.color === 'bg-[var(--brand)]' ? 'var(--info)' : 'var(--series-5)' }}
                          >
                            {g.value}%
                          </div>
                          <p className="text-sm text-[var(--muted)]">{g.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* Countries */}
                {demographics.country_distribution && (
                  <div className="bg-[var(--card)] rounded-xl border p-5 md:col-span-2">
                    <h3 className="font-semibold text-[var(--muted)] mb-3">Top Countries</h3>
                    {demographics.country_distribution.slice(0, 5).map((c, i) => (
                      <div key={i} className="mb-2">
                        <div className="flex justify-between text-sm mb-0.5">
                          <span>{c.country}</span>
                          <span className="font-medium">{c.percentage}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full">
                          <div className="h-2 bg-teal-400 rounded-full" style={{ width: `${c.percentage}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Interests */}
            {activeTab === 'interests' && (
              <div className="bg-[var(--card)] rounded-xl border shadow-sm p-6">
                <h2 className="font-semibold text-[var(--text)] mb-4">Audience Interests</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {interests.slice(0, 16).map((interest, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex justify-between text-sm mb-0.5">
                          <span className="font-medium text-[var(--muted)]">{interest.category}</span>
                          <span className="text-[var(--muted)]">{interest.affinity_pct?.toFixed(1)}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full">
                          <div
                            className="h-2 bg-[var(--brand)] rounded-full"
                            style={{ width: `${Math.min(interest.affinity_pct, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ad Targeting */}
            {activeTab === 'targeting' && adTargeting && (
              <div className="bg-[var(--card)] rounded-xl border shadow-sm p-6">
                <h2 className="font-semibold text-[var(--text)] mb-4">Ad Targeting Parameters</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {Object.entries(adTargeting)
                    .filter(([k]) => !k.startsWith('_') && k !== 'domain')
                    .map(([platform, params]) => (
                      <div key={platform} className="border rounded-lg p-4">
                        <h3 className="font-semibold text-[var(--muted)] mb-3 capitalize">
                          {String(platform).replace(/_/g, ' ')}
                        </h3>
                        <div className="text-sm text-[var(--muted)]">
                          {typeof params === 'object' && params !== null && !Array.isArray(params) ? (
                            <ul className="space-y-1">
                              {Object.entries(params as Record<string, unknown>)
                                .slice(0, 6)
                                .map(([k, v]) => (
                                  <li key={k} className="flex justify-between">
                                    <span className="text-[var(--muted)]">{k.replace(/_/g, ' ')}</span>
                                    <span className="font-medium truncate ml-2 max-w-[180px]">
                                      {Array.isArray(v) ? (v as unknown[]).join(', ') : String(v)}
                                    </span>
                                  </li>
                                ))}
                            </ul>
                          ) : (
                            <p>{JSON.stringify(params)}</p>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
