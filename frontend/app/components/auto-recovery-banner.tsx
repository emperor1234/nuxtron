'use client';

import { useEffect, useState } from 'react';

type RecoveryEventDetail = {
  path?: string;
  attempt?: number;
  totalRetries?: number;
};

export default function AutoRecoveryBanner() {
  const [activeRecoveries, setActiveRecoveries] = useState(0);
  const [lastPath, setLastPath] = useState('');
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [totalRetries, setTotalRetries] = useState(0);

  useEffect(() => {
    function handleStart(event: Event) {
      const detail = (event as CustomEvent<RecoveryEventDetail>).detail;
      setLastPath(detail?.path || 'platform data');
      setRetryAttempt(detail?.attempt || 1);
      setTotalRetries(detail?.totalRetries || 0);
      setActiveRecoveries(1);
    }

    function handleEnd() {
      setActiveRecoveries(0);
      setRetryAttempt(0);
      setTotalRetries(0);
    }

    globalThis.window.addEventListener('nuxtron:auto-recovery:start', handleStart as EventListener);
    globalThis.window.addEventListener('nuxtron:auto-recovery:end', handleEnd);

    return () => {
      globalThis.window.removeEventListener('nuxtron:auto-recovery:start', handleStart as EventListener);
      globalThis.window.removeEventListener('nuxtron:auto-recovery:end', handleEnd);
    };
  }, []);

  if (activeRecoveries <= 0) {
    return null;
  }

  return (
    <div className="auto-recovery-banner" role="status" aria-live="polite">
      <span className="auto-recovery-dot" aria-hidden="true" />
      <span>
        Retrying {Math.max(1, retryAttempt)}/{Math.max(1, totalRetries)} for {lastPath || 'platform data'}...
      </span>
    </div>
  );
}
