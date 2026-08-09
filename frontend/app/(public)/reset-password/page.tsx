'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Check, KeyRound, Lock, Mail } from 'lucide-react';
import { apiPost, DEFAULT_TENANT_ID } from '@/app/lib/api-client';
import { AuthLayout, AuthSubmit, AuthAltLinks, authLink } from '@/app/components/auth/auth-layout';
import { AuthField } from '@/app/components/auth/auth-field';

const PANEL_POINTS = [
  'Reset links are single-use and expire automatically.',
  'Your session is signed out everywhere once the password changes.',
  'Every account event is written to the audit trail.',
] as const;

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
    <AuthLayout
      heading={confirmSuccess ? 'Password updated' : 'Reset your password'}
      subheading={
        confirmSuccess
          ? 'Your password has been reset successfully.'
          : "Enter your account email and we'll send you a secure reset token."
      }
      panelTitle="Get back into your command center."
      panelPoints={PANEL_POINTS}
    >
      {confirmSuccess ? (
        <div className="py-2">
          <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#466cf314] text-[#466cf3]">
            <Check size={22} strokeWidth={2.5} aria-hidden="true" />
          </div>
          <Link href="/login" className="mk-btn-primary">
            Log in
          </Link>
        </div>
      ) : (
        <>
          <form className="flex flex-col gap-5" onSubmit={handleRequest} noValidate>
            <AuthField
              label="Email"
              name="email"
              type="email"
              inputMode="email"
              value={email}
              onChange={setEmail}
              autoComplete="email"
              required
              icon={<Mail size={17} aria-hidden="true" />}
              placeholder="you@company.com"
            />

            {requestError ? <p className="text-sm text-rose-600">{requestError}</p> : null}

            <AuthSubmit busy={requestBusy || requestSent}>
              {requestBusy ? 'Sending…' : requestSent ? 'Reset link sent' : 'Send reset link'}
            </AuthSubmit>
          </form>

          {requestSent ? (
            <form
              className="mt-8 flex flex-col gap-5 border-t border-[#18181814] pt-8"
              onSubmit={handleConfirm}
              noValidate
            >
              <p className="text-sm text-[#46484d]">
                Check your inbox — enter the token and your new password below.
              </p>
              <AuthField
                label="Reset token"
                name="token"
                value={token}
                onChange={setToken}
                required
                icon={<KeyRound size={17} aria-hidden="true" />}
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
                icon={<Lock size={17} aria-hidden="true" />}
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
                icon={<Lock size={17} aria-hidden="true" />}
                placeholder="Re-enter new password"
              />

              {confirmError ? <p className="text-sm text-rose-600">{confirmError}</p> : null}

              <AuthSubmit busy={confirmBusy}>{confirmBusy ? 'Updating…' : 'Set new password'}</AuthSubmit>
            </form>
          ) : null}
        </>
      )}

      <AuthAltLinks>
        <Link href="/login" className={authLink}>
          ← Back to login
        </Link>
      </AuthAltLinks>
    </AuthLayout>
  );
}
