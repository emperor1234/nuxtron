'use client';

import { useMemo, useState } from 'react';
import { ArrowRight, Briefcase, Building2, Lock, Mail, User } from 'lucide-react';
import { apiPost, DEFAULT_TENANT_ID, setAuthSession, syncServerSession } from '@/app/lib/api-client';
import { flattenZodErrors, signupSchema } from '@/app/lib/auth/schemas';
import { AuthField } from './auth-field';
import { AuthSubmit } from './auth-layout';

type FormState = {
  firstName: string;
  lastName: string;
  company: string;
  email: string;
  password: string;
  confirmPassword: string;
};

const INITIAL_STATE: FormState = {
  firstName: '',
  lastName: '',
  company: '',
  email: '',
  password: '',
  confirmPassword: '',
};

export function SignupForm() {
  const [state, setState] = useState<FormState>(INITIAL_STATE);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tenantId, setTenantId] = useState(DEFAULT_TENANT_ID);
  const [showWorkspace, setShowWorkspace] = useState(false);
  const [apiError, setApiError] = useState('');
  const [apiSuccess, setApiSuccess] = useState('');

  const parsed = useMemo(() => signupSchema.safeParse({ ...state, tenantId }), [state, tenantId]);
  const fieldError = useMemo(() => {
    if (parsed.success) return {} as Record<string, string>;
    const byField: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const key = String(issue.path[0] ?? '');
      if (key && !byField[key]) byField[key] = issue.message;
    }
    return byField;
  }, [parsed]);
  const errors = useMemo(() => (parsed.success ? [] : flattenZodErrors(parsed.error)), [parsed]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    setApiError('');
    setApiSuccess('');
    if (errors.length > 0) return;

    setBusy(true);
    try {
      // 1. Create the user account and get an auth token
      const tokenResponse = await apiPost(
        '/auth/register',
        {
          email: state.email.trim(),
          password: state.password,
          first_name: state.firstName,
          last_name: state.lastName,
        },
        tenantId
      );

      const result = tokenResponse.result as Record<string, unknown> | undefined;
      const rawToken = result?.token;
      const token = typeof rawToken === 'string' ? rawToken : '';
      if (token) {
        setAuthSession(token, tenantId);
        await syncServerSession(token);
      }

      // 2. Record CRM contact profile — just what we actually collected.
      // The rest of the profile (address, phone, etc.) is filled in later
      // from account settings, not gated on registration.
      await apiPost(
        '/crm/contacts',
        {
          email: state.email.trim(),
          first_name: state.firstName,
          last_name: state.lastName,
          company: state.company || undefined,
          tags: ['registration'],
        },
        tenantId
      );

      // Plan activation is a separate, explicit step on the billing page —
      // it must never be chained into registration with a placeholder
      // payment method, since that activates a paid plan the user never
      // reviewed or confirmed.
      setApiSuccess('Account created successfully. Redirecting to plan selection…');
      setState(INITIAL_STATE);
      setSubmitted(false);
      window.location.href = '/billing?onboarding=1';
    } catch (ex) {
      setApiError(ex instanceof Error ? ex.message : 'Could not create account.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <AuthField
          label="First name"
          name="firstName"
          value={state.firstName}
          onChange={(v) => update('firstName', v)}
          autoComplete="given-name"
          required
          icon={<User size={17} aria-hidden="true" />}
          placeholder="Jordan"
          error={submitted ? fieldError.firstName : undefined}
        />
        <AuthField
          label="Last name"
          name="lastName"
          value={state.lastName}
          onChange={(v) => update('lastName', v)}
          autoComplete="family-name"
          required
          icon={<User size={17} aria-hidden="true" />}
          placeholder="Rivera"
          error={submitted ? fieldError.lastName : undefined}
        />
      </div>

      <AuthField
        label="Work email"
        name="email"
        type="email"
        inputMode="email"
        value={state.email}
        onChange={(v) => update('email', v)}
        autoComplete="email"
        required
        icon={<Mail size={17} aria-hidden="true" />}
        placeholder="you@company.com"
        error={submitted ? fieldError.email : undefined}
      />

      <AuthField
        label="Company (optional)"
        name="company"
        value={state.company}
        onChange={(v) => update('company', v)}
        autoComplete="organization"
        icon={<Briefcase size={17} aria-hidden="true" />}
        placeholder="Acme Inc."
      />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <AuthField
          label="Password"
          name="password"
          type="password"
          value={state.password}
          onChange={(v) => update('password', v)}
          autoComplete="new-password"
          required
          icon={<Lock size={17} aria-hidden="true" />}
          placeholder="At least 10 characters"
          error={submitted ? fieldError.password : undefined}
        />
        <AuthField
          label="Confirm password"
          name="confirmPassword"
          type="password"
          value={state.confirmPassword}
          onChange={(v) => update('confirmPassword', v)}
          autoComplete="new-password"
          required
          icon={<Lock size={17} aria-hidden="true" />}
          placeholder="Re-enter password"
          error={submitted ? fieldError.confirmPassword : undefined}
        />
      </div>

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
          Joining an existing workspace? <span className="text-[#46484d]">Add workspace ID</span>
        </button>
      )}

      {submitted && errors.length > 0 ? (
        <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-700">
          <p className="font-semibold">Please fix the following:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div aria-live="polite" role="status">
        {apiError ? <p className="text-sm text-rose-600">{apiError}</p> : null}
        {apiSuccess ? <p className="text-sm text-emerald-600">{apiSuccess}</p> : null}
      </div>

      <AuthSubmit busy={busy}>
        {busy ? (
          'Creating account…'
        ) : (
          <span className="inline-flex items-center gap-2">
            Create account <ArrowRight size={16} aria-hidden="true" />
          </span>
        )}
      </AuthSubmit>
    </form>
  );
}
