'use client';

import { useState } from 'react';
import Link from 'next/link';
import { apiPost, DEFAULT_TENANT_ID } from '@/app/lib/api-client';

export default function ResetPasswordPage() {
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [email, setEmail] = useState('');

  // Step 1: request reset token
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestError, setRequestError] = useState('');
  const [requestSent, setRequestSent] = useState(false);

  // Step 2: confirm new password with token
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [confirmError, setConfirmError] = useState('');
  const [confirmSuccess, setConfirmSuccess] = useState(false);

  async function handleRequest(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim()) return;
    setRequestError('');
    setRequestBusy(true);
    try {
      const response = await apiPost('/auth/password-reset/request', { email: email.trim() }, tenantId);
      const result = response.result as Record<string, unknown> | undefined;
      const devToken = result?.dev_reset_token;
      if (typeof devToken === 'string' && devToken) {
        setToken(devToken);
      }
      setRequestSent(true);
    } catch (ex) {
      setRequestError(ex instanceof Error ? ex.message : 'Could not send reset request.');
    } finally {
      setRequestBusy(false);
    }
  }

  async function handleConfirm(event: React.FormEvent) {
    event.preventDefault();
    if (newPassword.length < 10) {
      setConfirmError('Password must be at least 10 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setConfirmError('Passwords do not match.');
      return;
    }
    setConfirmError('');
    setConfirmBusy(true);
    try {
      await apiPost(
        '/auth/password-reset/confirm',
        { email: email.trim(), token: token.trim(), new_password: newPassword },
        tenantId
      );
      setConfirmSuccess(true);
    } catch (ex) {
      setConfirmError(ex instanceof Error ? ex.message : 'Could not reset password.');
    } finally {
      setConfirmBusy(false);
    }
  }

  return (
    <div
      className="cin-root"
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        background: 'var(--cin-ink)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.3,
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.08) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      <div
        style={{
          position: 'relative',
          zIndex: 10,
          width: '100%',
          maxWidth: 440,
          padding: '2.5rem',
          borderRadius: 'var(--cin-radius-lg)',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <Link
          href="/"
          style={{
            display: 'inline-block',
            fontSize: '1.25rem',
            fontWeight: 800,
            color: '#fff',
            textDecoration: 'none',
            marginBottom: '2rem',
            letterSpacing: '-0.02em',
          }}
        >
          nuxtron
        </Link>

        {confirmSuccess ? (
          <div style={{ textAlign: 'center', padding: '1rem 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✓</div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fff', marginBottom: '0.75rem' }}>
              Password updated.
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.6)', lineHeight: 1.65, marginBottom: '1.5rem' }}>
              Your password has been reset successfully.
            </p>
            <Link
              href="/login"
              style={{
                display: 'inline-block',
                padding: '0.9rem 2rem',
                borderRadius: 'var(--cin-radius-pill)',
                background: '#fff',
                color: 'var(--cin-ink)',
                fontWeight: 700,
                fontSize: '0.95rem',
                textDecoration: 'none',
              }}
            >
              Log in
            </Link>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fff', marginBottom: '0.75rem', letterSpacing: '-0.03em' }}>
              Reset your password.
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.55)', marginBottom: '2rem', fontSize: '0.95rem', lineHeight: 1.65 }}>
              Enter your account email and we&apos;ll send you a secure link to set a new password.
            </p>

            {/* Step 1 — request reset link */}
            <form onSubmit={handleRequest} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <span style={labelStyle}>Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  style={inputStyle}
                  placeholder="you@company.com"
                />
              </label>

              {requestError ? (
                <p style={{ color: '#ef4444', fontSize: '0.85rem' }}>{requestError}</p>
              ) : null}

              <button type="submit" disabled={requestBusy || requestSent} style={primaryBtnStyle}>
                {requestBusy ? 'Sending...' : 'Send Reset Link'}
              </button>
            </form>

            {/* Step 2 — confirm with token + new password */}
            {requestSent ? (
              <form
                onSubmit={handleConfirm}
                style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}
              >
                <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.9rem' }}>
                  Check your inbox — enter the token and your new password below.
                </p>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <span style={labelStyle}>Reset Token</span>
                  <input
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Paste the token from your email"
                    required
                    style={inputStyle}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <span style={labelStyle}>New Password</span>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={10}
                    required
                    style={inputStyle}
                    placeholder="Min. 10 characters"
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <span style={labelStyle}>Confirm New Password</span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    style={inputStyle}
                    placeholder="Re-enter new password"
                  />
                </label>
                {confirmError ? (
                  <p style={{ color: '#ef4444', fontSize: '0.85rem' }}>{confirmError}</p>
                ) : null}
                <button type="submit" disabled={confirmBusy} style={primaryBtnStyle}>
                  {confirmBusy ? 'Updating...' : 'Set New Password'}
                </button>
              </form>
            ) : null}
          </>
        )}

        <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem' }}>
          <Link href="/login" style={{ color: '#a78bfa', textDecoration: 'none', fontWeight: 600 }}>
            ← Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: '0.85rem',
  fontWeight: 500,
  color: 'rgba(255,255,255,0.7)',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.85rem 1rem',
  borderRadius: 'var(--cin-radius-sm)',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  color: '#fff',
  fontSize: '0.95rem',
  fontFamily: 'var(--font-body)',
  outline: 'none',
};

const primaryBtnStyle: React.CSSProperties = {
  padding: '0.9rem 2rem',
  borderRadius: 'var(--cin-radius-pill)',
  border: 'none',
  background: '#fff',
  color: 'var(--cin-ink)',
  fontWeight: 700,
  fontSize: '0.95rem',
  cursor: 'pointer',
};
