'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { socialApi, type SocialNetwork } from '@/app/lib/social-api';

export default function SocialOAuthCallbackPage() {
  const params = useParams<{ network: string }>();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Completing OAuth callback...');

  useEffect(() => {
    let active = true;

    async function run() {
      const network = (params?.network || '').trim();
      const code = (searchParams.get('code') || '').trim();
      const state = (searchParams.get('state') || '').trim();
      const oauthError = (searchParams.get('error') || '').trim();

      if (!network) {
        if (!active) return;
        setStatus('error');
        setMessage('Missing OAuth network in callback URL.');
        return;
      }

      if (oauthError) {
        if (!active) return;
        setStatus('error');
        setMessage(`OAuth provider returned an error: ${oauthError}`);
        return;
      }

      if (!code || !state) {
        if (!active) return;
        setStatus('error');
        setMessage('Missing OAuth code/state from provider callback.');
        return;
      }

      try {
        await socialApi.completeOAuth(network as SocialNetwork, code, state);
        if (!active) return;
        setStatus('success');
        setMessage('Account connected successfully. Redirecting to social accounts...');
        setTimeout(() => {
          globalThis.location.href = '/studio/social-accounts?oauth=success';
        }, 850);
      } catch (error) {
        if (!active) return;
        const detail = error instanceof Error ? error.message : 'OAuth callback failed.';
        setStatus('error');
        setMessage(detail);
      }
    }

    void run();
    return () => {
      active = false;
    };
  }, [params?.network, searchParams]);

  return (
    <main style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Social OAuth Callback</h1>
        <p style={{ ...styles.message, color: status === 'error' ? '#dc2626' : '#C7D2FE' }}>{message}</p>
        <div style={styles.actions}>
          <Link href="/studio/social-accounts" style={styles.link}>
            Back to Social Accounts
          </Link>
        </div>
      </div>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'grid',
    placeItems: 'center',
    padding: '24px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
  },
  card: {
    width: '100%',
    maxWidth: '560px',
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '16px',
    padding: '24px',
  },
  title: {
    margin: '0 0 10px',
    fontSize: '22px',
    fontWeight: 700,
    color: 'var(--text)',
  },
  message: {
    margin: '0 0 16px',
    fontSize: '14px',
    lineHeight: '1.5',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-start',
  },
  link: {
    color: 'var(--brand)',
    textDecoration: 'none',
    fontSize: '14px',
  },
};
