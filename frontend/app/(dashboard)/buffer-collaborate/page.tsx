'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type TeamMember = {
  id: string;
  email: string;
  name?: string;
  role: string;
  status: string;
  channel_ids?: number[];
  invited_at?: string;
  joined_at?: string | null;
};

type ApprovalRequest = {
  id: number;
  status: string;
  platform?: string;
  content_preview?: string;
  requested_by?: string;
  approval_levels?: string[];
  approvals_received?: string[];
};

const panel = {
  background: 'var(--bg-soft, #f8fafc)',
  border: '1px solid var(--line, #e2e8f0)',
  borderRadius: 12,
  padding: 16,
} as const;

function memberTimeLabel(member: TeamMember): string {
  if (member.joined_at) return `joined ${new Date(member.joined_at).toLocaleDateString()}`;
  if (member.invited_at) return `invited ${new Date(member.invited_at).toLocaleDateString()}`;
  return 'no timestamp';
}

function approvalBadgeTone(status: string): { background: string; color: string } {
  if (status === 'pending') return { background: '#fef3c7', color: '#92400e' };
  if (status === 'approved') return { background: '#dcfce7', color: '#166534' };
  return { background: '#fee2e2', color: '#b91c1c' };
}

export default function BufferCollaboratePage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID || 'tenant-demo');
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('editor');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [memberRes, approvalRes] = await Promise.all([
        apiGet<{ members?: TeamMember[] }>('/social/team/members', tenantId),
        apiGet<{ requests?: ApprovalRequest[] }>('/content/approval/requests', tenantId),
      ]);
      setMembers(memberRes.members ?? []);
      setApprovals(approvalRes.requests ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load collaboration data');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function inviteMember() {
    if (!email.trim()) return;
    try {
      await apiSend(
        '/social/team/members/invite',
        'POST',
        {
          email,
          role,
          channel_ids: [],
        },
        tenantId
      );
      setEmail('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invite failed');
    }
  }

  async function updateRole(memberId: string, nextRole: string) {
    try {
      await apiSend(
        `/social/team/members/${memberId}`,
        'PUT',
        {
          role: nextRole,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Role update failed');
    }
  }

  async function removeMember(memberId: string) {
    try {
      await apiSend(`/social/team/members/${memberId}`, 'DELETE', undefined, tenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Remove failed');
    }
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg, #f8fafc)', color: 'var(--text, #0f172a)', padding: 24 }}>
      <div style={{ maxWidth: 1240, margin: '0 auto' }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ margin: 0, fontSize: 28 }}>Collaborate</h1>
          <p style={{ margin: '6px 0 0', color: '#64748b' }}>
            Manage roles, invites, and pending approval queues across your social team.
          </p>
        </div>

        {error ? <div style={{ ...panel, color: '#b91c1c', marginBottom: 14 }}>{error}</div> : null}
        {loading ? (
          <div style={{ color: '#64748b', padding: 30, textAlign: 'center' }}>Loading collaboration data…</div>
        ) : null}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
          <section>
            <div style={{ ...panel, marginBottom: 16 }}>
              <h2 style={{ marginTop: 0 }}>Invite team member</h2>
              <div style={{ display: 'grid', gap: 10 }}>
                <input
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="name@company.com"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    borderRadius: 8,
                    border: '1px solid #cbd5e1',
                  }}
                />
                <select
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
                >
                  {['admin', 'editor', 'approver', 'analyst', 'viewer'].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => void inviteMember()}
                  style={{
                    border: 'none',
                    borderRadius: 10,
                    padding: '10px 12px',
                    background: '#6366f1',
                    color: '#fff',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Send invite
                </button>
              </div>
            </div>

            <div style={panel}>
              <h2 style={{ marginTop: 0 }}>Team members</h2>
              <div style={{ display: 'grid', gap: 12 }}>
                {members.map((member) => (
                  <div key={member.id} style={{ padding: 14, borderRadius: 10, background: '#fff' }}>
                    <div
                      style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}
                    >
                      <div>
                        <div style={{ fontWeight: 700 }}>{member.name || member.email}</div>
                        <div style={{ fontSize: 12, color: '#64748b' }}>{member.email}</div>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                          {member.status} · {memberTimeLabel(member)}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          value={member.role}
                          onChange={(event) => void updateRole(member.id, event.target.value)}
                          style={{ padding: '7px 10px', borderRadius: 8, border: '1px solid #cbd5e1' }}
                        >
                          {['admin', 'editor', 'approver', 'analyst', 'viewer'].map((value) => (
                            <option key={value} value={value}>
                              {value}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={() => void removeMember(member.id)}
                          style={{
                            border: 'none',
                            borderRadius: 8,
                            padding: '8px 10px',
                            background: '#fee2e2',
                            color: '#b91c1c',
                            cursor: 'pointer',
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {members.length === 0 ? <div>No team members found.</div> : null}
              </div>
            </div>
          </section>

          <aside style={panel}>
            <h2 style={{ marginTop: 0 }}>Approval queue</h2>
            <div style={{ display: 'grid', gap: 12 }}>
              {approvals.map((request) => (
                <div key={request.id} style={{ padding: 14, borderRadius: 10, background: '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                    <strong>{request.content_preview || 'Approval request'}</strong>
                    <span
                      style={{
                        fontSize: 11,
                        borderRadius: 999,
                        padding: '4px 8px',
                        ...approvalBadgeTone(request.status),
                      }}
                    >
                      {request.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>
                    {request.platform || 'unknown'} · requested by {request.requested_by || 'unknown'}
                  </div>
                  <div style={{ fontSize: 12, color: '#475569', marginTop: 8 }}>
                    Received: {(request.approvals_received || []).join(', ') || 'none yet'}
                  </div>
                  <div style={{ fontSize: 12, color: '#475569' }}>
                    Needed: {(request.approval_levels || []).join(', ') || 'none configured'}
                  </div>
                </div>
              ))}
              {approvals.length === 0 ? <div>No approval requests found.</div> : null}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
