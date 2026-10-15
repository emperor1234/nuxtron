'use client';

import { useState } from 'react';
import Link from 'next/link';
import { apiPost, resolveSessionTenant } from '@/app/lib/api-client';
import { Button, Card, CardTitle, Field, Page, PageHeader } from '../_ui/kit';

type Json = Record<string, unknown>;

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function referralCodeFromResponse(response: unknown): string {
  if (!response || typeof response !== 'object') return '';
  const profile = (response as Json).profile;
  if (!profile || typeof profile !== 'object') return '';
  const code = (profile as Json).referral_code;
  return typeof code === 'string' ? code.trim() : '';
}

export default function AffiliatePage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [referralCode, setReferralCode] = useState('');
  const [claimEmail, setClaimEmail] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);
  const [claiming, setClaiming] = useState(false);

  async function generateCode() {
    setGenerating(true);
    setError('');
    setStatus('');
    try {
      const response = await apiPost('/engagement/referrals/generate-code', {}, tenantId);
      const code = referralCodeFromResponse(response);
      if (!code) throw new Error('The referral service did not return a usable code.');
      setGeneratedCode(code);
      setStatus('Referral code generated.');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to generate a referral code.');
    } finally {
      setGenerating(false);
    }
  }

  async function copyCode() {
    if (!generatedCode) return;
    setError('');
    try {
      await globalThis.navigator.clipboard.writeText(generatedCode);
      setStatus('Referral code copied to clipboard.');
    } catch {
      setError('Clipboard access is unavailable. Select and copy the referral code manually.');
    }
  }

  async function claimReferral() {
    const normalizedEmail = claimEmail.trim();
    const normalizedCode = referralCode.trim().toUpperCase();
    if (!normalizedCode || !isValidEmail(normalizedEmail)) {
      setError('Enter a referral code and a valid email address.');
      return;
    }
    setClaiming(true);
    setError('');
    setStatus('');
    try {
      await apiPost(
        '/engagement/referrals/claim',
        { referral_code: normalizedCode, referred_email: normalizedEmail },
        tenantId,
      );
      setStatus('Referral claimed. Reward credits have been issued to your workspace.');
      setReferralCode('');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to claim the referral.');
    } finally {
      setClaiming(false);
    }
  }

  return (
    <Page>
      <PageHeader
        title="Partner referrals"
        subtitle="Create a referral code, share it with a new customer, or claim a code for this signed-in workspace."
        actions={
          <Link href="/affiliate/dashboard" style={{ color: 'var(--brand)', fontWeight: 700, textDecoration: 'none' }}>
            Partner performance
          </Link>
        }
      />

      {error ? <p role="alert" aria-live="assertive">{error}</p> : null}
      {status ? <p role="status" aria-live="polite">{status}</p> : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: 16 }}>
        <Card>
          <CardTitle sub="Codes are created by the referral service and tied to your signed-in workspace.">
            Invite a customer
          </CardTitle>
          <p style={{ color: 'var(--muted)', lineHeight: 1.55 }}>
            Generate a code and share it with someone who is new to Nuxtron.
          </p>
          <Button variant="primary" onClick={generateCode} disabled={generating || claiming}>
            {generating ? 'Generating…' : 'Generate referral code'}
          </Button>
          {generatedCode ? (
            <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
              <Field label="Your referral code" id="generated-referral-code" value={generatedCode} readOnly />
              <div>
                <Button onClick={copyCode}>Copy referral code</Button>
              </div>
            </div>
          ) : null}
        </Card>

        <Card>
          <CardTitle sub="The claim is recorded against the authenticated workspace; the email is stored as referral metadata.">
            Claim a referral
          </CardTitle>
          <div style={{ display: 'grid', gap: 14, marginTop: 16 }}>
            <Field
              label="Existing referral code"
              id="existing-referral-code"
              autoComplete="off"
              value={referralCode}
              onChange={(event) => setReferralCode(event.target.value)}
              placeholder="Enter the code you received"
            />
            <Field
              label="Email for this referral claim"
              id="referral-claim-email"
              type="email"
              autoComplete="email"
              required
              value={claimEmail}
              onChange={(event) => setClaimEmail(event.target.value)}
              placeholder="name@company.com"
            />
            <div>
              <Button
                variant="primary"
                onClick={claimReferral}
                disabled={claiming || generating || !referralCode.trim() || !isValidEmail(claimEmail)}
              >
                {claiming ? 'Claiming…' : 'Claim referral'}
              </Button>
            </div>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
              Uses your signed-in workspace. No workspace identifier is exposed or editable here.
            </p>
          </div>
        </Card>
      </div>
    </Page>
  );
}
