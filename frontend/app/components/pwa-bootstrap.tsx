'use client';

import { useEffect } from 'react';

export default function PwaBootstrap() {
  useEffect(() => {
    if (typeof globalThis.window === 'undefined' || !('serviceWorker' in navigator)) return;
    if (navigator.webdriver) return;

    const register = async () => {
      try {
        await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      } catch (error) {
        console.error('Service worker registration failed', error);
      }
    };

    void register();
  }, []);

  return null;
}
