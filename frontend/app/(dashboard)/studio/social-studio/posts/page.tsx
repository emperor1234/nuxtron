'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type SocialPost, type SocialNetwork } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const NETWORKS: SocialNetwork[] = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'youtube'];

export default function PostsPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [content, setContent] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialNetwork[]>([]);
  const [scheduledAt, setScheduledAt] = useState('');
  const [mediaUrls, setMediaUrls] = useState<string[]>([]);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    loadPosts();
  }, []);

  async function loadPosts() {
    setError(null);
    try {
      const result = await socialApi.listScheduledPosts();
      setPosts(result || []);
    } catch (err) {
      console.error('Failed to load posts:', err);
      setPosts([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Posts backend unavailable in strict no-mock mode.'
          : 'Posts backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!content.trim() || selectedPlatforms.length === 0) {
      alert('Please enter content and select at least one platform');
      return;
    }

    setPublishing(true);
    try {
      if (scheduledAt) {
        const post = await socialApi.schedulePost('temp_id', scheduledAt, selectedPlatforms);
        setPosts([...posts, post]);
      } else {
        const post = await socialApi.createPost(selectedPlatforms, content, mediaUrls);
        setPosts([...posts, post]);
      }

      // Reset form
      setContent('');
      setSelectedPlatforms([]);
      setScheduledAt('');
      setMediaUrls([]);
      setShowForm(false);
    } catch (err) {
      console.error('Post creation failed:', err);
      alert('Failed to create post. Please try again.');
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Social Posts</h1>
          <p style={styles.subtitle}>Create, schedule, and manage posts across all platforms</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            ...styles.createBtn,
            backgroundColor: showForm ? '#e7e9ef' : '#6366f1',
          }}
        >
          {showForm ? 'Cancel' : '+ New Post'}
        </button>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {/* Create Form */}
      {showForm && (
        <div style={styles.formCard}>
          <h2 style={styles.formTitle}>Create New Post</h2>

          <div style={styles.formGroup}>
            <label style={styles.label}>Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What's on your mind?"
              style={styles.textarea}
              maxLength={2800}
            />
            <small style={styles.charCount}>{content.length} / 2800</small>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Platforms</label>
            <div style={styles.platformGrid}>
              {NETWORKS.map((network) => (
                <button
                  key={network}
                  onClick={() =>
                    setSelectedPlatforms(
                      selectedPlatforms.includes(network)
                        ? selectedPlatforms.filter((p) => p !== network)
                        : [...selectedPlatforms, network]
                    )
                  }
                  style={{
                    ...styles.platformBtn,
                    backgroundColor: selectedPlatforms.includes(network) ? '#6366f1' : '#eef0f4',
                    borderColor: selectedPlatforms.includes(network) ? '#6366f1' : '#e7e9ef',
                  }}
                >
                  {network.charAt(0).toUpperCase() + network.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Schedule For (Optional)</label>
              <input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                style={styles.input}
              />
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Preview</label>
            <div style={styles.preview}>
              <p>{content || 'Your post content will appear here...'}</p>
              {mediaUrls.length > 0 && (
                <div style={styles.previewMedia}>
                  {mediaUrls.map((url, idx) => (
                    <img key={idx} src={url} alt="preview" style={styles.previewImg} />
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={styles.formActions}>
            <button
              onClick={handleCreate}
              disabled={publishing}
              style={{
                ...styles.publishBtn,
                opacity: publishing ? 0.6 : 1,
                cursor: publishing ? 'not-allowed' : 'pointer',
              }}
            >
              {publishing ? 'Creating...' : scheduledAt ? 'Schedule Post' : 'Post Now'}
            </button>
          </div>
        </div>
      )}

      {/* Posts List */}
      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonCard} />
          <div style={styles.skeletonCard} />
        </div>
      ) : (
        <>
          {posts.length > 0 ? (
            <div style={styles.postsList}>
              {posts.map((post) => (
                <div key={post.id} style={styles.postCard}>
                  <div style={styles.postHeader}>
                    <div>
                      <span style={styles.statusBadge(post.status)}>{post.status.toUpperCase()}</span>
                      {post.scheduledAt && (
                        <small style={styles.scheduledTime}>
                          Scheduled for {new Date(post.scheduledAt).toLocaleString()}
                        </small>
                      )}
                    </div>
                    <div style={styles.platforms}>
                      {post.platforms.map((p) => (
                        <span key={p} style={styles.platformBadge}>
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>

                  <p style={styles.postContent}>{post.content}</p>

                  {post.mediaUrls && post.mediaUrls.length > 0 && (
                    <div style={styles.postMedia}>
                      {post.mediaUrls.map((url, idx) => (
                        <img key={idx} src={url} alt="post" style={styles.postImg} />
                      ))}
                    </div>
                  )}

                  {post.metrics && (
                    <div style={styles.postMetrics}>
                      <div style={styles.metric}>
                        <span>❤️ {post.metrics.likes}</span>
                      </div>
                      <div style={styles.metric}>
                        <span>💬 {post.metrics.comments}</span>
                      </div>
                      <div style={styles.metric}>
                        <span>🔄 {post.metrics.shares}</span>
                      </div>
                      <div style={styles.metric}>
                        <span>👁️ {post.metrics.impressions}</span>
                      </div>
                      <div style={styles.metric}>
                        <span>🎯 {post.metrics.reach}</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>✍️</div>
              <h2>No Posts Yet</h2>
              <p>Create your first social media post</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, any> = {
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
  createBtn: {
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
  textarea: {
    width: '100%',
    minHeight: '120px',
    padding: '12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical' as const,
  },
  charCount: {
    display: 'block',
    marginTop: '4px',
    fontSize: '12px',
    color: 'var(--muted)',
  },
  platformGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 100px), 1fr))',
    gap: '8px',
  },
  platformBtn: {
    padding: '8px 12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))',
    gap: '16px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
  },
  preview: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    padding: '12px',
    fontSize: '13px',
    color: 'var(--text)',
  },
  previewMedia: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 80px), 1fr))',
    gap: '8px',
    marginTop: '12px',
  },
  previewImg: {
    width: '100%',
    height: '80px',
    objectFit: 'cover' as const,
    borderRadius: '4px',
  },
  formActions: {
    display: 'flex',
    gap: '12px',
    marginTop: '24px',
  },
  publishBtn: {
    padding: '10px 20px',
    backgroundColor: '#10B981',
    color: 'var(--text)',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  postsList: {
    display: 'grid',
    gap: '16px',
  },
  postCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '20px',
  },
  postHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  statusBadge: (status: string) => ({
    display: 'inline-block',
    padding: '4px 8px',
    backgroundColor: status === 'published' ? '#10B98126' : status === 'scheduled' ? '#F5901426' : '#6B728026',
    color: status === 'published' ? '#10B981' : status === 'scheduled' ? '#F59014' : 'var(--muted)',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
  }),
  scheduledTime: {
    display: 'block',
    marginTop: '6px',
    fontSize: '12px',
    color: 'var(--muted)',
  },
  platforms: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap' as const,
  },
  platformBadge: {
    display: 'inline-block',
    padding: '3px 8px',
    backgroundColor: '#e7e9ef',
    color: 'var(--text)',
    borderRadius: '3px',
    fontSize: '11px',
  },
  postContent: {
    margin: '0 0 12px',
    lineHeight: '1.5',
    color: 'var(--text)',
  },
  postMedia: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 150px), 1fr))',
    gap: '8px',
    marginBottom: '12px',
  },
  postImg: {
    width: '100%',
    height: '150px',
    objectFit: 'cover' as const,
    borderRadius: '6px',
  },
  postMetrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))',
    gap: '12px',
    paddingTop: '12px',
    borderTop: '1px solid var(--line)',
  },
  metric: {
    textAlign: 'center' as const,
    fontSize: '12px',
    color: 'var(--muted)',
  },
  skeleton: {
    display: 'grid',
    gap: '16px',
  },
  skeletonCard: {
    height: '200px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
  emptyState: {
    textAlign: 'center' as const,
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
