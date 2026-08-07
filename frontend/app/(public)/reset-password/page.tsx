'use client';

import { useState } from 'react';
import Link from 'next/link';
import { AuthLayout, AuthAltLinks, AuthSubmit, authLink } from '@/app/components/auth/auth-layout';
import { AuthField } from '@/app/components/auth/auth-field';
import { apiPost, DEFAULT_TENANT_ID } from '@/app/lib/api-client';

const PANEL_POINTS = [
  'A secure, single-use token is required to set a new password.',
  'Reset links and tokens expire after a short window.',
  'Your session is signed out everywhere once the password changes.',
] as const;

export default function ResetPasswordPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
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
    <AuthLayout
      heading={confirmSuccess ? 'Password updated' : 'Reset your password'}
      subheading={
        confirmSuccess
          ? 'Your password has been reset successfully.'
          : "Enter your account email and we'll send you a secure link to set a new password."
      }
      panelTitle="Back into your command center in two quick steps."
      panelPoints={PANEL_POINTS}
    >
      {confirmSuccess ? (
        <div className="pt-2">
          <Link
            href="/login"
            className="inline-flex w-full items-center justify-center rounded-xl bg-[#0ea5e9] px-6 py-3 text-base font-bold text-white shadow-[0_8px_20px_rgba(14,165,233,0.3)] transition-all hover:bg-[#0c8fcc]"
          >
            Log in
          </Link>
        </div>
      ) : (
        <>
          <form onSubmit={handleRequest} className="flex flex-col gap-5" noValidate>
            <AuthField
              label="Email"
              name="email"
              type="email"
              inputMode="email"
              value={email}
              onChange={setEmail}
              autoComplete="email"
              required
              placeholder="you@company.com"
            />
            <div aria-live="polite" role="status">
              {requestError ? <p className="text-sm text-rose-600">{requestError}</p> : null}
            </div>
            <AuthSubmit busy={requestBusy}>
              {requestBusy ? 'Sending…' : requestSent ? 'Reset link sent' : 'Send reset link'}
            </AuthSubmit>
          </form>

          {requestSent ? (
            <form onSubmit={handleConfirm} className="mt-8 flex flex-col gap-5 border-t border-[#dbe6ee] pt-8" noValidate>
              <p className="text-sm text-[#55677c]">Check your inbox — enter the token and your new password below.</p>
              <AuthField
                label="Reset token"
                name="token"
                value={token}
                onChange={setToken}
                required
                placeholder="Paste the token from your email"
              />
              <AuthField
                label="New password"
                name="newPassword"
                type="password"
                value={newPassword}
                onChange={setNewPassword}
                autoComplete="new-password"
                required
                placeholder="Min. 10 characters"
              />
              <AuthField
                label="Confirm new password"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={setConfirmPassword}
                autoComplete="new-password"
                required
                placeholder="Re-enter new password"
              />
              <div aria-live="polite" role="status">
                {confirmError ? <p className="text-sm text-rose-600">{confirmError}</p> : null}
              </div>
              <AuthSubmit busy={confirmBusy}>{confirmBusy ? 'Updating…' : 'Set new password'}</AuthSubmit>
            </form>
          ) : null}

          <AuthAltLinks>
            <Link href="/login" className={authLink}>
              ← Back to login
            </Link>
          </AuthAltLinks>
        </>
      )}
    </AuthLayout>
  );
}
