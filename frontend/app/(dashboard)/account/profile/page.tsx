'use client';

import { useEffect, useState, type FormEvent } from 'react';
import AccountNav from '@/app/components/account-nav';
import { Button } from '@/app/(dashboard)/_ui/kit';
import { apiGet, apiPost, resolveSessionTenant } from '@/app/lib/api-client';
import { readSessionUser } from '@/app/lib/session-user';

type Contact = {
  email?: string;
  title?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  tags?: string[];
  properties?: Record<string, unknown>;
};

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function isPreviewResponse(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

export default function AccountProfilePage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [title, setTitle] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');
  const [addressLine1, setAddressLine1] = useState('');
  const [addressLine2, setAddressLine2] = useState('');
  const [city, setCity] = useState('');
  const [postcode, setPostcode] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [saved, setSaved] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const session = readSessionUser();
    const sessionName = session?.name?.split(/\s+/) ?? [];
    const sessionFirstName = sessionName[0] ?? '';
    const sessionLastName = sessionName.slice(1).join(' ');

    let active = true;
    async function load() {
      try {
        const query = session?.email ? `?q=${encodeURIComponent(session.email)}&limit=20` : '?limit=40';
        const data = await apiGet(`/crm/contacts${query}`, tenantId);
        if (!active) return;
        if (isPreviewResponse(data) || !Array.isArray(data.contacts)) {
          throw new Error('Live profile data is unavailable or incomplete.');
        }
        const contacts = data.contacts as Contact[];
        const tagged = contacts.find((item) => Array.isArray(item.tags) && item.tags.includes('account-profile'));
        const matched = tagged || contacts.find((item) => session?.email && item.email?.toLowerCase() === session.email.toLowerCase());
        if (!matched) {
          setFirstName(sessionFirstName);
          setLastName(sessionLastName);
          setEmail(session?.email ?? '');
          setNotFound(true);
          setLoadError('');
          return;
        }

        setNotFound(false);
        setTitle(asString(matched.title));
        setFirstName(asString(matched.first_name) || sessionFirstName);
        setLastName(asString(matched.last_name) || sessionLastName);
        setEmail(asString(matched.email) || session?.email || '');
        setMobile(asString(matched.phone));
        const props = matched.properties || {};
        setAddressLine1(asString(props.address_line_1));
        setAddressLine2(asString(props.address_line_2));
        setCity(asString(props.city));
        setPostcode(asString(props.postcode));
        setLoadError('');
      } catch (ex) {
        if (active) setLoadError(ex instanceof Error ? ex.message : 'Could not load profile.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [refresh, tenantId]);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || loadError || !email.trim()) return;
    setSaving(true);
    setSaved(false);
    setSaveError('');
    try {
      await apiPost(
        '/crm/contacts',
        {
          email: email.trim(),
          title: title.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: mobile.trim(),
          tags: ['account-profile'],
          properties: {
            source: 'account_profile',
            address_line_1: addressLine1.trim(),
            address_line_2: addressLine2.trim(),
            city: city.trim(),
            postcode: postcode.trim(),
          },
        },
        tenantId
      );
      setNotFound(false);
      setSaved(true);
    } catch (ex) {
      setSaveError(ex instanceof Error ? ex.message : 'Failed to save profile. Your changes are still available in this form.');
    } finally {
      setSaving(false);
    }
  }

  function retryLoad() {
    setLoading(true);
    setLoadError('');
    setNotFound(false);
    setRefresh((value) => value + 1);
  }

  return (
    <div className="account-shell">
      <AccountNav />
      <section className="card" aria-labelledby="account-profile-title">
        <header>
          <h1 id="account-profile-title">Personal Details</h1>
          <p className="muted">Keep your contact and billing address current.</p>
        </header>
        {loading ? <p className="muted" role="status" aria-live="polite">Loading profile…</p> : null}
        {loadError ? (
          <div className="auth-errors" role="alert">
            <p>{loadError}</p>
            <p>Saving is paused until the current profile can be checked.</p>
            <Button onClick={retryLoad}>Retry profile load</Button>
          </div>
        ) : null}
        {notFound && !loading ? (
          <p className="muted" role="status" aria-live="polite">No saved profile was found for this account. Enter your details to create one.</p>
        ) : null}
        <form className="auth-form" onSubmit={(event) => void saveProfile(event)}>
          <fieldset disabled={loading || Boolean(loadError) || saving} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
            <div className="profile-form-groups">
              <fieldset className="profile-field-group">
                <legend>Personal and contact details</legend>
                <div className="auth-grid auth-grid-2">
                  <label>
                    <span>Title</span>
                    <input value={title} onChange={(event) => setTitle(event.target.value)} autoComplete="honorific-prefix" />
                  </label>
                  <label>
                    <span>First name</span>
                    <input value={firstName} onChange={(event) => setFirstName(event.target.value)} autoComplete="given-name" required />
                  </label>
                  <label>
                    <span>Last name</span>
                    <input value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" required />
                  </label>
                  <label>
                    <span>Email</span>
                    <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required />
                  </label>
                  <label>
                    <span>Mobile</span>
                    <input value={mobile} onChange={(event) => setMobile(event.target.value)} type="tel" autoComplete="tel" />
                  </label>
                </div>
              </fieldset>
              <fieldset className="profile-field-group">
                <legend>Billing address</legend>
                <div className="auth-grid auth-grid-2">
                  <label>
                    <span>Address line 1</span>
                    <input value={addressLine1} onChange={(event) => setAddressLine1(event.target.value)} autoComplete="address-line1" />
                  </label>
                  <label>
                    <span>Address line 2</span>
                    <input value={addressLine2} onChange={(event) => setAddressLine2(event.target.value)} autoComplete="address-line2" />
                  </label>
                  <label>
                    <span>City</span>
                    <input value={city} onChange={(event) => setCity(event.target.value)} autoComplete="address-level2" />
                  </label>
                  <label>
                    <span>Postcode</span>
                    <input value={postcode} onChange={(event) => setPostcode(event.target.value)} autoComplete="postal-code" />
                  </label>
                </div>
              </fieldset>
            </div>
          </fieldset>
          {saveError ? <p className="auth-errors" role="alert" aria-live="assertive">{saveError}</p> : null}
          {saved ? <p className="muted" role="status" aria-live="polite">Profile saved.</p> : null}
          <Button type="submit" variant="primary" disabled={loading || Boolean(loadError) || saving || !email.trim()}>
            {saving ? 'Saving…' : 'Save changes'}
          </Button>
        </form>
      </section>
    </div>
  );
}
