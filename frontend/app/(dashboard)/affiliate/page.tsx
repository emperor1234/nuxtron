'use client';

import { useState } from 'react';
import { apiPost, resolveSessionTenant } from '@/app/lib/api-client';

export default function AffiliatePage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [referralCode, setReferralCode] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  async function generateCode() {
    setError('');
    try {
      const response = await apiPost('/engagement/referrals/generate-code', {}, tenantId);
      const profile = response.profile as Record<string, unknown> | undefined;
      const rawCode = profile?.referral_code;
      const code = typeof rawCode === 'string' ? rawCode : '';
      setGeneratedCode(code);
      setStatus('Referral code generated.');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to generate code.');
    }
  }

  async function claimReferral() {
    setError('');
    try {
      await apiPost(
        '/engagement/referrals/claim',
        { referral_code: referralCode, referred_email: 'affiliate@lead.local' },
        tenantId
      );
      setStatus('Referral claimed successfully. Credits were applied.');
      setReferralCode('');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to claim referral.');
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Affiliate Program</p>
        <h1>Grow With Nuxtron As A Partner</h1>
        <p>Promote the platform, track referral performance, and earn recurring commission.</p>
        <p>
          <a href="/affiliate/dashboard">Open Affiliate Dashboard</a>
        </p>
        <div className="auth-form" style={{ marginTop: 12 }}>
          <label>
            <span>Tenant ID</span>
            <input value={tenantId} readOnly />
          </label>
          <div className="hero-cta-row">
            <button onClick={generateCode}>Generate Referral Code</button>
          </div>
          {generatedCode ? <p className="muted">Your referral code: {generatedCode}</p> : null}
          <label>
            <span>Claim Existing Referral Code</span>
            <input
              value={referralCode}
              onChange={(e) => setReferralCode(e.target.value)}
              placeholder="Enter referral code"
            />
          </label>
          <div className="hero-cta-row">
            <button onClick={claimReferral} disabled={!referralCode.trim()}>
              Claim Referral
            </button>
          </div>
          {error ? <p className="auth-errors">{error}</p> : null}
          {status ? <p className="muted">{status}</p> : null}
        </div>
      </section>

      <section className="grid" style={{ marginTop: 20 }}>
        <article className="card">
          <h3>Commission</h3>
          <p>Up to 30% recurring revenue share for qualified subscriptions.</p>
        </article>
        <article className="card">
          <h3>Tracking</h3>
          <p>Real-time referral attribution with payout-safe event logs.</p>
        </article>
        <article className="card">
          <h3>Assets</h3>
          <p>Brand-ready campaigns, copy kits, and landing page templates.</p>
        </article>
      </section>
    </main>
  );
}
