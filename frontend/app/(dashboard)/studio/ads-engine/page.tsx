'use client';

import { useState } from 'react';
import MultimodalCreatorSuite from '@/app/components/multimodal-creator-suite';

export default function AdsEnginePage() {
  const [campaigns, setCampaigns] = useState<
    Array<{ id: string; name: string; status: string; budget: number; roi: number }>
  >([]);
  const [newCampaign, setNewCampaign] = useState('');
  const [budget, setBudget] = useState('1000');

  function createCampaign() {
    if (!newCampaign.trim()) return;
    setCampaigns([
      {
        id: Date.now().toString(),
        name: newCampaign,
        status: 'active',
        budget: Number(budget),
        roi: Math.random() * 300,
      },
      ...campaigns,
    ]);
    setNewCampaign('');
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">AI Ads Engine</p>
        <h1>Creative Testing & Budget Optimization</h1>
        <p>Automated A/B testing, audience strategy, and real-time budget optimization across platforms.</p>
      </section>

      <MultimodalCreatorSuite moduleType="ads-engine" />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginTop: 20 }}>
        <section className="card" style={{ height: 'fit-content', padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Create Campaign</h3>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Campaign Name</label>
            <input
              value={newCampaign}
              onChange={(e) => setNewCampaign(e.target.value)}
              placeholder="e.g., Q2 Launch"
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Budget ($)</label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              min={100}
              step={100}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>

          <button
            onClick={() => createCampaign()}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: 8,
              border: 'none',
              background: 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Launch Campaign
          </button>

          <div
            style={{ marginTop: 16, padding: 10, background: 'rgba(27, 199, 255, 0.1)', borderRadius: 8, fontSize: 12 }}
          >
            <strong>Features:</strong>
            <ul style={{ margin: '8px 0 0', paddingLeft: 16 }}>
              <li>Auto A/B testing</li>
              <li>Cross-platform audience sync</li>
              <li>Real-time ROI tracking</li>
              <li>Budget reallocation AI</li>
            </ul>
          </div>
        </section>

        <section className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Active Campaigns ({campaigns.length})</h3>

          {campaigns.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>No campaigns yet. Create one to get started.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {campaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  style={{
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: 12,
                    background: 'rgba(255, 255, 255, 0.03)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <div>
                      <strong>{campaign.name}</strong>
                      <p style={{ margin: '4px 0', fontSize: 13, color: 'var(--muted)' }}>Budget: ${campaign.budget}</p>
                      <p style={{ margin: '4px 0 0', fontSize: 13 }}>
                        ROI:{' '}
                        <strong style={{ color: campaign.roi > 100 ? '#34d399' : '#dc2626' }}>
                          +{campaign.roi.toFixed(1)}%
                        </strong>
                      </p>
                    </div>
                    <button
                      style={{
                        padding: '6px 10px',
                        borderRadius: 6,
                        border: '1px solid var(--line)',
                        background: 'transparent',
                        color: 'var(--text)',
                        cursor: 'pointer',
                        fontSize: 12,
                      }}
                    >
                      Optimize
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
