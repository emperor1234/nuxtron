'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

export default function BillingSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    async function activate() {
      if (!sessionId) {
        setStatus('error');
        setMessage('No session found. Please return to pricing and try again.');
        return;
      }
      try {
        // Activate subscription in our system after successful Stripe checkout
        await apiSend('/billing/stripe/activate', 'POST', { session_id: sessionId }, DEFAULT_TENANT_ID);
        setStatus('success');
      } catch {
        // Even if activation call fails, Stripe payment succeeded — webhook will retry
        setStatus('success');
        setMessage('Payment received! Your plan will be activated shortly.');
      }
    }
    void activate();
  }, [sessionId]);

  return (
    <main style={{ textAlign: 'center', padding: '80px 24px' }}>
      {status === 'loading' && (
        <>
          <h1>Activating your plan…</h1>
          <p>Please wait while we set up your subscription.</p>
        </>
      )}
      {status === 'success' && (
        <>
          <h1 style={{ color: '#26d78e' }}>You&apos;re all set! 🎉</h1>
          <p>{message || 'Your subscription is now active. Welcome aboard!'}</p>
          <a
            href="/dashboard"
            style={{
              display: 'inline-block',
              marginTop: 24,
              padding: '12px 32px',
              background: '#1bc7ff',
              borderRadius: 8,
              color: '#000',
              fontWeight: 700,
              textDecoration: 'none',
            }}
          >
            Go to Dashboard
          </a>
        </>
      )}
      {status === 'error' && (
        <>
          <h1 style={{ color: '#f87171' }}>Something went wrong</h1>
          <p>{message}</p>
          <a
            href="/pricing"
            style={{
              display: 'inline-block',
              marginTop: 24,
              padding: '12px 32px',
              background: '#374151',
              borderRadius: 8,
              color: '#fff',
              textDecoration: 'none',
            }}
          >
            Back to Pricing
          </a>
        </>
      )}
    </main>
  );
}
