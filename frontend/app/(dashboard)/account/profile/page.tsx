'use client';

import AccountNav from '@/app/components/account-nav';
import { useEffect, useState } from 'react';
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
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const session = readSessionUser();
    if (session?.email) setEmail(session.email);
    if (session?.name) {
      const parts = session.name.split(/\s+/);
      if (parts[0]) setFirstName(parts[0]);
      if (parts.length > 1) setLastName(parts.slice(1).join(' '));
    }

    let active = true;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const query = session?.email ? `?q=${encodeURIComponent(session.email)}&limit=20` : '?limit=40';
        const data = await apiGet(`/crm/contacts${query}`, tenantId);
        if (!active) return;
        const contacts = Array.isArray(data.contacts) ? (data.contacts as Contact[]) : [];
        const tagged = contacts.find((item) => Array.isArray(item.tags) && item.tags.includes('account-profile'));
        const matched =
          tagged ||
          contacts.find((item) => session?.email && item.email?.toLowerCase() === session.email.toLowerCase());
        if (!matched) return;

        setTitle(asString(matched.title));
        if (matched.first_name) setFirstName(asString(matched.first_name));
        if (matched.last_name) setLastName(asString(matched.last_name));
        setEmail(asString(matched.email) || session?.email || '');
        setMobile(asString(matched.phone));
        const props = matched.properties || {};
        setAddressLine1(asString(props.address_line_1));
        setAddressLine2(asString(props.address_line_2));
        setCity(asString(props.city));
        setPostcode(asString(props.postcode));
      } catch (ex) {
        if (active) setError(ex instanceof Error ? ex.message : 'Could not load profile.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [tenantId]);

  async function saveProfile() {
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      await apiPost(
        '/crm/contacts',
        {
          email,
          title,
          first_name: firstName,
          last_name: lastName,
          phone: mobile,
          tags: ['account-profile'],
          properties: {
            source: 'account_profile',
            address_line_1: addressLine1,
            address_line_2: addressLine2,
            city,
            postcode,
          },
        },
        tenantId
      );
      setSaved(true);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to save profile.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="account-shell">
      <AccountNav />
      <section className="card">
        <h1>Personal Details</h1>
        <p className="muted">Keep your profile information current for billing and compliance.</p>
        {loading ? <p className="muted">Loading profile…</p> : null}
        <form className="auth-form">
          <label>
            <span>Tenant ID</span>
            <input value={tenantId} readOnly />
          </label>
          <div className="auth-grid auth-grid-2">
            <label>
              <span>Title</span>
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label>
              <span>First Name</span>
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </label>
            <label>
              <span>Last Name</span>
              <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </label>
            <label>
              <span>Email</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
            </label>
            <label>
              <span>Mobile</span>
              <input value={mobile} onChange={(e) => setMobile(e.target.value)} />
            </label>
            <label>
              <span>Address Line 1</span>
              <input value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} />
            </label>
            <label>
              <span>Address Line 2</span>
              <input value={addressLine2} onChange={(e) => setAddressLine2(e.target.value)} />
            </label>
            <label>
              <span>City</span>
              <input value={city} onChange={(e) => setCity(e.target.value)} />
            </label>
            <label>
              <span>Postcode</span>
              <input value={postcode} onChange={(e) => setPostcode(e.target.value)} />
            </label>
          </div>
          {error ? <p className="auth-errors">{error}</p> : null}
          {saved ? <p className="muted">Profile saved.</p> : null}
          <button type="button" onClick={() => void saveProfile()} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </section>
    </main>
  );
}
