'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Review = {
  id: number;
  platform: string;
  reviewer_name: string;
  rating: number;
  text: string;
  sentiment: string;
  responded: boolean;
  created_at: string;
};
type ReviewSummary = {
  total_reviews: number;
  avg_rating: number;
  rating_distribution: Record<string, number>;
  responded_count: number;
  response_rate: number;
  sentiment_breakdown: Record<string, number>;
};

export default function ReviewsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [platform, setPlatform] = useState('google');
  const [reviewerName, setReviewerName] = useState('Customer One');
  const [rating, setRating] = useState('5');
  const [text, setText] = useState('Great experience and onboarding support.');
  const [error, setError] = useState('');

  async function load() {
    try {
      setError('');
      const [summaryRes, reviewsRes] = await Promise.all([
        apiGet<{ summary: ReviewSummary }>('/reviews/summary', tenantId),
        apiGet<{ reviews: Review[] }>('/reviews', tenantId),
      ]);
      setSummary(summaryRes.summary ?? null);
      setReviews(reviewsRes.reviews ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load reviews');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ingest() {
    try {
      await apiSend(
        '/reviews/ingest',
        'POST',
        {
          platform,
          reviewer_name: reviewerName,
          rating: Number.parseInt(rating, 10) || 5,
          text,
        },
        tenantId
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ingest failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Reviews and Reputation</h1>
        <p style={{ color: 'var(--muted)' }}>Ingest customer reviews and monitor rating + sentiment quality.</p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
            gap: 10,
            marginBottom: 10,
          }}
        >
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Total Reviews</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.total_reviews ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Avg Rating</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.avg_rating ?? 0}</div>
          </div>
          <div style={card}>
            <div style={{ color: 'var(--muted)', fontSize: 12 }}>Response Rate</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.response_rate ?? 0}%</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Ingest Review</h3>
            <select style={input} value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="google">google</option>
              <option value="trustpilot">trustpilot</option>
              <option value="g2">g2</option>
              <option value="facebook">facebook</option>
            </select>
            <input
              style={input}
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="reviewer name"
            />
            <input
              style={input}
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              type="number"
              min={1}
              max={5}
              placeholder="rating"
            />
            <textarea style={{ ...input, minHeight: 90 }} value={text} onChange={(e) => setText(e.target.value)} />
            <button
              onClick={() => void ingest()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Ingest
            </button>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Reviews ({reviews.length})</h3>
            {reviews.map((r) => (
              <div key={r.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <div style={{ fontWeight: 700 }}>
                  {r.reviewer_name} · {r.platform} · {r.rating}/5
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  {r.sentiment} · responded: {r.responded ? 'yes' : 'no'} · {new Date(r.created_at).toLocaleString()}
                </div>
                <div style={{ fontSize: 13 }}>{r.text}</div>
              </div>
            ))}
          </section>
        </div>
      </div>
    </main>
  );
}
