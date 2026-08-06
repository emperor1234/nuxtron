'use client';

import AccountNav from '@/app/components/account-nav';
import { useState } from 'react';
import { apiPost, resolveSessionTenant } from '@/app/lib/api-client';

export default function AccountSettingsPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [timezone, setTimezone] = useState('Europe/London');
  const [language, setLanguage] = useState('English');
  const [digestEnabled, setDigestEnabled] = useState(true);
  const [mfaEnabled, setMfaEnabled] = useState(true);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  async function saveSettings() {
    setSaving(true);
    setSaved(false);
    setError('');
    if (newPassword && newPassword !== confirmPassword) {
      setError('Password confirmation does not match.');
      setSaving(false);
      return;
    }
    try {
      let passwordHashPreview = '';
      if (newPassword.trim()) {
        const hashResponse = await apiPost(
          '/security/hash-password',
          {
            password: newPassword,
            algorithm: 'bcrypt',
          },
          tenantId
        );
        const hashed = typeof hashResponse.hash === 'string' ? hashResponse.hash : '';
        passwordHashPreview = hashed.slice(0, 14);
      }

      await apiPost(
        '/white-label/checkpoint',
        {
          action: 'account_settings_saved',
          points: 8,
          note: `timezone=${timezone}; language=${language}; digest=${digestEnabled}; mfa=${mfaEnabled}; password_updated=${Boolean(newPassword.trim())}; password_hash_preview=${passwordHashPreview}`,
        },
        tenantId
      );
      setNewPassword('');
      setConfirmPassword('');
      setSaved(true);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="account-shell">
      <AccountNav />
      <section className="card">
        <h1>Settings</h1>
        <form className="auth-form">
          <label>
            <span>Tenant ID</span>
            <input value={tenantId} readOnly />
          </label>
          <label>
            <span>Timezone</span>
            <select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
              <option>Europe/London</option>
              <option>America/New_York</option>
              <option>Asia/Dubai</option>
            </select>
          </label>
          <label>
            <span>Language</span>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option>English</option>
              <option>Spanish</option>
              <option>French</option>
            </select>
          </label>
          <label>
            <input type="checkbox" checked={digestEnabled} onChange={(e) => setDigestEnabled(e.target.checked)} />{' '}
            Enable weekly performance digest
          </label>
          <label>
            <input type="checkbox" checked={mfaEnabled} onChange={(e) => setMfaEnabled(e.target.checked)} /> Enable
            multi-factor authentication
          </label>
          <div className="auth-grid auth-grid-2">
            <label>
              <span>New Password</span>
              <input
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                type="password"
                minLength={8}
                placeholder="Leave blank to keep current password"
              />
            </label>
            <label>
              <span>Confirm Password</span>
              <input
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                type="password"
                minLength={8}
                placeholder="Re-enter new password"
              />
            </label>
          </div>
          {error ? <p className="auth-errors">{error}</p> : null}
          {saved ? <p className="muted">Preferences saved.</p> : null}
          <button type="button" onClick={saveSettings} disabled={saving}>
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </form>
      </section>
    </main>
  );
}
