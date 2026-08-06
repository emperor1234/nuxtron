self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  if (!url.pathname.startsWith('/api/')) return;

  event.respondWith(
    fetch(event.request).catch(
      () =>
        new Response(
          JSON.stringify({
            status: 'offline',
            detail: 'Network unavailable. Request should be retried by offline sync queue.',
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          }
        )
    )
  );
});
