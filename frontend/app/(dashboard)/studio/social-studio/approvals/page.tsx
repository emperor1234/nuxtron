'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type ApprovalRequest } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

export default function ApprovalsPage() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedApprovers, setSelectedApprovers] = useState<string[]>([]);
  const [autoPublish, setAutoPublish] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadApprovals();
  }, []);

  async function loadApprovals() {
    setError(null);
    try {
      const result = await socialApi.listPendingApprovals();
      setRequests(result || []);
    } catch (err) {
      console.error('Failed to load approvals:', err);
      setRequests([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Approvals backend unavailable in strict no-mock mode.'
          : 'Approvals backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(requestId: string) {
    try {
      await socialApi.approveRequest(requestId);
      setRequests(requests.map((r) => (r.id === requestId ? { ...r, status: 'approved' } : r)));
    } catch (err) {
      console.error('Approve failed:', err);
      alert('Failed to approve request');
    }
  }

  async function handleReject(requestId: string, reason: string) {
    try {
      await socialApi.rejectRequest(requestId, reason);
      setRequests(requests.map((r) => (r.id === requestId ? { ...r, status: 'rejected' } : r)));
    } catch (err) {
      console.error('Reject failed:', err);
      alert('Failed to reject request');
    }
  }

  const pending = requests.filter((r) => r.status === 'pending');
  const approved = requests.filter((r) => r.status === 'approved');
  const rejected = requests.filter((r) => r.status === 'rejected');

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Content Approvals</h1>
          <p style={styles.subtitle}>Manage content review workflows and approvals across your team</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            ...styles.requestBtn,
            backgroundColor: showForm ? '#e7e9ef' : '#6366f1',
          }}
        >
          {showForm ? 'Cancel' : '+ Request Approval'}
        </button>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {/* Request Form */}
      {showForm && (
        <div style={styles.formCard}>
          <h2 style={styles.formTitle}>Request Content Approval</h2>

          <div style={styles.formGroup}>
            <label style={styles.label}>Select Content</label>
            <select style={styles.select}>
              <option>Choose a post...</option>
              <option>Announcing new features 🚀</option>
              <option>Behind-the-scenes studio tour</option>
            </select>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Approvers (Email)</label>
            <div style={styles.approversGrid}>
              {['manager@company.com', 'legal@company.com', 'brand@company.com'].map((email) => (
                <button
                  key={email}
                  onClick={() =>
                    setSelectedApprovers(
                      selectedApprovers.includes(email)
                        ? selectedApprovers.filter((e) => e !== email)
                        : [...selectedApprovers, email]
                    )
                  }
                  style={{
                    ...styles.approverChip,
                    backgroundColor: selectedApprovers.includes(email) ? '#6366f1' : '#eef0f4',
                    borderColor: selectedApprovers.includes(email) ? '#6366f1' : '#e7e9ef',
                  }}
                >
                  {email}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.checkboxLabel}>
              <input type="checkbox" checked={autoPublish} onChange={(e) => setAutoPublish(e.target.checked)} />
              Auto-publish when all approvals received
            </label>
          </div>

          <div style={styles.formActions}>
            <button style={styles.submitBtn}>Send for Approval</button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
        </div>
      ) : (
        <>
          {/* Pending Approvals */}
          {pending.length > 0 && (
            <section style={styles.section}>
              <h2 style={{ ...styles.sectionTitle, color: '#F59014' }}>⏳ Pending Approvals ({pending.length})</h2>
              <div style={styles.requestsList}>
                {pending.map((req) => (
                  <div key={req.id} style={styles.requestCard}>
                    <div style={styles.requestHeader}>
                      <div>
                        <h3 style={styles.contentPreview}>{req.contentPreview}</h3>
                        <div style={styles.requestMeta}>
                          <span>📅 Requested {new Date(req.requestedAt).toLocaleString()}</span>
                          <span>👤 {req.requestedBy}</span>
                        </div>
                      </div>
                      <div style={styles.platformBadges}>
                        {req.platforms.map((p) => (
                          <span key={p} style={styles.platformBadge}>
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div style={styles.approversSection}>
                      <span style={styles.approversLabel}>Approvers:</span>
                      <div style={styles.approversList}>
                        {req.approvers.map((approver) => (
                          <span key={approver} style={styles.approverItem}>
                            ✓ {approver}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div style={styles.actions}>
                      <button onClick={() => handleApprove(req.id)} style={styles.approveBtn}>
                        ✓ Approve
                      </button>
                      <button
                        onClick={() => {
                          const reason = prompt('Enter rejection reason:');
                          if (reason) handleReject(req.id, reason);
                        }}
                        style={styles.rejectBtn}
                      >
                        ✗ Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Approved */}
          {approved.length > 0 && (
            <section style={styles.section}>
              <h2 style={{ ...styles.sectionTitle, color: '#10B981' }}>✓ Approved ({approved.length})</h2>
              <div style={styles.requestsList}>
                {approved.map((req) => (
                  <div
                    key={req.id}
                    style={{
                      ...styles.requestCard,
                      borderLeftColor: '#10B981',
                      opacity: 0.8,
                    }}
                  >
                    <div style={styles.requestHeader}>
                      <div>
                        <h3 style={styles.contentPreview}>{req.contentPreview}</h3>
                        <div style={styles.requestMeta}>
                          <span>✓ Approved for publication</span>
                          <span>{req.autoPublishOnApprove ? '🤖 Auto-publish enabled' : '👤 Manual publish'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Rejected */}
          {rejected.length > 0 && (
            <section style={styles.section}>
              <h2 style={{ ...styles.sectionTitle, color: '#EF4444' }}>✗ Rejected ({rejected.length})</h2>
              <div style={styles.requestsList}>
                {rejected.map((req) => (
                  <div
                    key={req.id}
                    style={{
                      ...styles.requestCard,
                      borderLeftColor: '#EF4444',
                      opacity: 0.6,
                    }}
                  >
                    <div style={styles.requestHeader}>
                      <div>
                        <h3 style={styles.contentPreview}>{req.contentPreview}</h3>
                        <small style={styles.rejectedLabel}>Rejected</small>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {pending.length === 0 && approved.length === 0 && rejected.length === 0 && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>✅</div>
              <h2>No Approval Requests</h2>
              <p>All your content is ready to go!</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    padding: '32px 24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--muted)',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--muted)',
    margin: 0,
  },
  requestBtn: {
    padding: '10px 20px',
    backgroundColor: '#6366f1',
    color: 'var(--text)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  errorBanner: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '12px 14px',
    borderRadius: '10px',
    marginBottom: '16px',
  },
  formCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '32px',
  },
  formTitle: {
    fontSize: '18px',
    fontWeight: 600,
    margin: '0 0 20px',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
    color: 'var(--text)',
  },
  select: {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
  },
  approversGrid: {
    display: 'grid',
    gap: '8px',
  },
  approverChip: {
    padding: '8px 12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
    textAlign: 'left',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: 'var(--text)',
    cursor: 'pointer',
  },
  formActions: {
    display: 'flex',
    gap: '12px',
    marginTop: '24px',
  },
  submitBtn: {
    padding: '10px 20px',
    backgroundColor: '#10B981',
    color: 'var(--text)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  section: {
    marginBottom: '32px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '16px',
  },
  requestsList: {
    display: 'grid',
    gap: '12px',
  },
  requestCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderLeft: '4px solid #F59014',
    borderRadius: '8px',
    padding: '16px',
  },
  requestHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
    gap: '12px',
  },
  contentPreview: {
    margin: '0 0 6px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text)',
  },
  requestMeta: {
    display: 'flex',
    gap: '12px',
    fontSize: '12px',
    color: 'var(--muted)',
  },
  platformBadges: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  platformBadge: {
    display: 'inline-block',
    padding: '3px 8px',
    backgroundColor: '#e7e9ef',
    color: 'var(--text)',
    borderRadius: '3px',
    fontSize: '11px',
  },
  approversSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '12px',
    paddingBottom: '12px',
    borderBottom: '1px solid var(--line)',
    fontSize: '12px',
  },
  approversLabel: {
    fontWeight: 600,
    color: 'var(--muted)',
  },
  approversList: {
    display: 'flex',
    gap: '8px',
    flex: 1,
    flexWrap: 'wrap',
  },
  approverItem: {
    display: 'inline-block',
    padding: '2px 6px',
    backgroundColor: '#1119274D',
    color: 'var(--muted)',
    borderRadius: '3px',
    fontSize: '11px',
  },
  actions: {
    display: 'flex',
    gap: '12px',
  },
  approveBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: '#10B98126',
    color: '#15803d',
    border: '1px solid #10B98126',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  rejectBtn: {
    flex: 1,
    padding: '8px',
    backgroundColor: '#EF444426',
    color: '#dc2626',
    border: '1px solid #EF444426',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  rejectedLabel: {
    display: 'block',
    marginTop: '6px',
    fontSize: '11px',
    color: '#EF4444',
    fontWeight: 600,
  },
  skeleton: {
    display: 'grid',
    gap: '16px',
  },
  skeletonCard: {
    height: '150px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 24px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    border: '1px dashed #e7e9ef',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
};
