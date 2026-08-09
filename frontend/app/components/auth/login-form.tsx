'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Building2, Lock, Mail } from 'lucide-react';
import { apiPost, DEFAULT_TENANT_ID, setAuthSession, syncServerSession } from '@/app/lib/api-client';
import { loginSchema } from '@/app/lib/auth/schemas';
import { AuthField } from './auth-field';
import { AuthSubmit, AuthAltLinks, authLink } from './auth-layout';

const SAFE_REDIRECT_PATTERN = /^\/[a-z0-9/_-]*$/i;

/** Reads `?next=` from the URL directly (no useSearchParams/Suspense needed)
 * and only accepts a same-origin relative path, never an absolute/external
 * URL (open-redirect guard). */
function resolvePostLoginPath(): string {
  if (!globalThis.window) return '/dashboard';
  const next = new URLSearchParams(globalThis.window.location.search).get('next') || '';
  return SAFE_REDIRECT_PATTERN.test(next) ? next : '/dashboard';
}

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [showWorkspace, setShowWorkspace] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  const parsed = useMemo(
    () => loginSchema.safeParse({ tenantId, email, password }),
    [tenantId, email, password]
  );
  const fieldError = useMemo(() => {
    if (parsed.success) return {} as Record<string, string>;
    const byField: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const key = String(issue.path[0] ?? '');
      if (key && !byField[key]) byField[key] = issue.message;
    }
    return byField;
  }, [parsed]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    setError('');
    setResult('');
    if (!parsed.success) return;

    setBusy(true);
    try {
      const response = await apiPost('/auth/login', { email: parsed.data.email, password: parsed.data.password }, parsed.data.tenantId);
      const payload = response.result as Record<string, unknown> | undefined;
      const rawToken = payload?.token;
      const token = typeof rawToken === 'string' ? rawToken : '';
      if (token) {
        setAuthSession(token, parsed.data.tenantId);
        await syncServerSession(token);
        window.location.href = resolvePostLoginPath();
      }
      setResult('Login successful. Redirecting…');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Login failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form className="flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
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
          error={submitted ? fieldError.email : undefined}
        />
        <AuthField
          label="Password"
          name="password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
          icon={<Lock size={17} aria-hidden="true" />}
          placeholder="••••••••"
          error={submitted ? fieldError.password : undefined}
        />

        {showWorkspace ? (
          <AuthField
            label="Workspace ID"
            name="tenant"
            value={tenantId}
            onChange={setTenantId}
            autoComplete="organization"
            required
            icon={<Building2 size={17} aria-hidden="true" />}
            placeholder="acme"
            error={submitted ? fieldError.tenantId : undefined}
          />
        ) : (
          <button
            type="button"
            onClick={() => setShowWorkspace(true)}
            className="-mt-2 self-start text-xs font-medium text-[#8a8d93] underline-offset-4 transition-colors hover:text-[#46484d] hover:underline"
          >
            Signing into a specific workspace? <span className="text-[#46484d]">Add workspace ID</span>
          </button>
        )}

        <AuthSubmit busy={busy}>
          {busy ? (
            'Signing in…'
          ) : (
            <span className="inline-flex items-center gap-2">
              Sign in <ArrowRight size={16} aria-hidden="true" />
            </span>
          )}
        </AuthSubmit>

        <div aria-live="polite" role="status">
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          {result ? <p className="text-sm text-[#46484d]">{result}</p> : null}
        </div>
      </form>

      <AuthAltLinks>
        <Link href="/reset-password" className={authLink}>
          Reset password
        </Link>
        <span aria-hidden="true"> · </span>
        <Link href="/register" className={authLink}>
          Create account
        </Link>
      </AuthAltLinks>
    </>
  );
}
