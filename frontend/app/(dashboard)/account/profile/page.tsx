'use client';

import AccountNav from '@/app/components/account-nav';
import { useState } from 'react';
import { apiPost, resolveSessionTenant } from '@/app/lib/api-client';

export default function AccountProfilePage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [title, setTitle] = useState('Director');
  const [firstName, setFirstName] = useState('Alex');
  const [lastName, setLastName] = useState('Morgan');
  const [email, setEmail] = useState('alex@company.com');
  const [mobile, setMobile] = useState('+44 7700 900000');
  const [addressLine1, setAddressLine1] = useState('221B Baker Street');
  const [addressLine2, setAddressLine2] = useState('Marylebone');
  const [city, setCity] = useState('London');
  const [postcode, setPostcode] = useState('NW1 6XE');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

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
          <button type="button" onClick={saveProfile} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </section>
    </main>
  );
}
