'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type TeamMember = {
  id: string;
  email: string;
  role: string;
  status: string;
  invited_at?: string;
};

export default function TeamPage() {
  const tenantId = DEFAULT_TENANT_ID || 'tenant-demo';
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newMember, setNewMember] = useState('');
  const [newRole, setNewRole] = useState('editor');

  async function loadTeam() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<{ members?: TeamMember[] }>('/social/team/members', tenantId);
      setTeam(data.members ?? []);
    } catch {
      setError('Failed to load team members.');
      setTeam([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTeam();
  }, []);

  async function addMember() {
    if (!newMember.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiSend('/social/team/invite', 'POST', { email: newMember.trim(), role: newRole }, tenantId);
      setNewMember('');
      await loadTeam();
    } catch {
      setError('Failed to invite member. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Team & Governance</p>
        <h1>Roles, Approvals & Workspace Controls</h1>
        <p>Professional team management with granular permissions and audit trails.</p>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20, marginTop: 20 }}>
        <section className="card" style={{ height: 'fit-content', padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Invite Member</h3>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Email</label>
            <input
              value={newMember}
              onChange={(event) => setNewMember(event.target.value)}
              placeholder="member@company.com"
              type="email"
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 600 }}>Role</label>
            <select
              value={newRole}
              onChange={(event) => setNewRole(event.target.value)}
              style={{
                width: '100%',
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--text)',
              }}
            >
              <option value="viewer">Viewer (read-only)</option>
              <option value="editor">Editor (create & edit)</option>
              <option value="approver">Approver (review & publish)</option>
              <option value="admin">Admin (full access)</option>
            </select>
          </div>

          {error && <p style={{ color: '#f44', fontSize: 12, marginBottom: 8 }}>{error}</p>}

          <button
            onClick={() => void addMember()}
            disabled={submitting || !newMember.trim()}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: 8,
              border: 'none',
              background: submitting || !newMember.trim() ? 'var(--muted)' : 'var(--brand)',
              color: '#00101e',
              fontWeight: 700,
              cursor: submitting || !newMember.trim() ? 'not-allowed' : 'pointer',
              marginBottom: 12,
            }}
          >
            {submitting ? 'Sending...' : 'Send Invite'}
          </button>

          <div style={{ padding: 10, background: 'rgba(27, 199, 255, 0.1)', borderRadius: 8, fontSize: 12 }}>
            <strong>Permissions:</strong>
            <ul style={{ margin: '8px 0 0', paddingLeft: 16 }}>
              <li>
                <strong>Viewer:</strong> View reports
              </li>
              <li>
                <strong>Editor:</strong> Create content
              </li>
              <li>
                <strong>Approver:</strong> Review & publish
              </li>
              <li>
                <strong>Admin:</strong> Manage team
              </li>
            </ul>
          </div>
        </section>

        <section className="card" style={{ padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Team Members ({loading ? '...' : team.length})</h3>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>Loading...</p>
            </div>
          ) : team.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted)' }}>
              <p>No team members yet. Invite someone to get started!</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {team.map((member) => (
                <div
                  key={member.id}
                  style={{
                    border: '1px solid var(--line)',
                    borderRadius: 10,
                    padding: 12,
                    background: 'rgba(255, 255, 255, 0.03)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <strong>{member.email}</strong>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                      {member.role} · {member.status}
                    </p>
                  </div>
                  <button
                    style={{
                      padding: '6px 10px',
                      borderRadius: 6,
                      border: '1px solid var(--line)',
                      background: 'transparent',
                      color: member.status === 'pending' ? 'var(--brand)' : 'var(--text)',
                      cursor: 'pointer',
                      fontSize: 12,
                    }}
                  >
                    {member.status === 'pending' ? 'Pending' : 'Revoke'}
                  </button>
                </div>
              ))}
            </div>
          )}

          <div
            style={{
              marginTop: 16,
              padding: 12,
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: 10,
              fontSize: 12,
            }}
          >
            <strong>Audit Trail</strong>
            <p style={{ margin: '6px 0 0', color: 'var(--muted)' }}>All member actions logged for compliance.</p>
          </div>
        </section>
      </div>
    </main>
  );
}
