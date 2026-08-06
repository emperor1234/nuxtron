'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type NotificationItem = {
  id: number;
  title: string;
  message: string;
  category: string;
  // ENHANCED: priority field (info | warning | error | success | critical)
  priority: string;
  read: boolean;
  created_at: string;
};

// ENHANCED: toast state for real-time popup alerts
type ToastItem = {
  id: number;
  title: string;
  message: string;
  priority: string;
  expiresAt: number;
};

type NotificationSnapshot = {
  notifications: NotificationItem[];
  unreadCount: number;
  // ENHANCED (additive): global unread count from backend snapshot.
  unreadTotal?: number;
  total?: number;
};

const proxyBaseUrl = '/api/fastapi';
// Falls back to a dev tenant when NEXT_PUBLIC_DEFAULT_TENANT_ID is unset so the
// app runs locally without crashing; notification fetches simply degrade to the
// offline state if the backend/tenant isn't available.
const defaultTenantId = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || 'default').trim();

function formatAge(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return 'just now';
  }

  const seconds = Math.max(0, Math.round((Date.now() - parsed) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function NotificationCenter() {
  const [panelOpen, setPanelOpen] = useState(false);
  // ENHANCED: keep raw feed state separate so UI filters do not fight SSE snapshots.
  const [allNotifications, setAllNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [connectionState, setConnectionState] = useState<'connecting' | 'live' | 'offline'>('connecting');
  // ENHANCED: category filter — backend supports ?category=X, now exposed in UI
  const [filterCategory, setFilterCategory] = useState<string>('');
  // ENHANCED: toast queue for popup alerts when panel is closed
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const prevNotifIdsRef = useRef<Set<number>>(new Set());
  const prevUnreadCountRef = useRef(0);
  const panelOpenRef = useRef(false);
  const connectionStateRef = useRef<'connecting' | 'live' | 'offline'>('connecting');

  const removeExpiredToasts = useCallback(() => {
    const now = Date.now();
    setToasts((prev) => prev.filter((t) => t.expiresAt > now));
  }, []);

  useEffect(() => {
    panelOpenRef.current = panelOpen;
  }, [panelOpen]);

  useEffect(() => {
    connectionStateRef.current = connectionState;
  }, [connectionState]);

  // ENHANCED: dismiss expired toasts every second
  useEffect(() => {
    const interval = setInterval(() => {
      removeExpiredToasts();
    }, 1000);
    return () => clearInterval(interval);
  }, [removeExpiredToasts]);

  // ENHANCED: helper to add a toast for newly arrived notifications
  const addToast = useCallback((item: NotificationItem) => {
    setToasts((prev) => {
      // Don't duplicate toasts for the same notification
      if (prev.some((t) => t.id === item.id)) return prev;
      return [
        ...prev,
        {
          id: item.id,
          title: item.title,
          message: item.message,
          priority: item.priority || 'info',
          expiresAt: Date.now() + 5000,
        },
      ];
    });
  }, []);

  const dismissToast = useCallback((toastId: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }, []);

  const authHeaders = useMemo(
    () => ({
      'Content-Type': 'application/json',
      'X-Tenant-Id': defaultTenantId,
    }),
    []
  );

  const notifications = useMemo(
    () => (filterCategory ? allNotifications.filter((n) => n.category === filterCategory) : allNotifications),
    [allNotifications, filterCategory]
  );

  useEffect(() => {
    let cancelled = false;

    async function loadInitialSnapshot() {
      try {
        // ENHANCED: apply category filter if set
        const url = new URL(`${proxyBaseUrl}/notifications`, globalThis.location.origin);
        if (filterCategory) url.searchParams.set('category', filterCategory);
        const response = await fetch(url.toString(), {
          headers: authHeaders,
          cache: 'no-store',
        });
        if (!response.ok) {
          throw new Error(`Notification bootstrap failed: ${response.status}`);
        }

        const payload = (await response.json()) as NotificationSnapshot;
        if (cancelled) return;
        const incoming = payload.notifications || [];
        const unread = Number(payload.unreadTotal ?? payload.unreadCount ?? 0);
        setAllNotifications(incoming);
        setUnreadCount(unread);
        // Seed known IDs to avoid stale toasts
        prevNotifIdsRef.current = new Set(incoming.map((n) => n.id));
        prevUnreadCountRef.current = unread;
      } catch {
        if (!cancelled) {
          setConnectionState('offline');
        }
      }
    }

    loadInitialSnapshot();
    return () => {
      cancelled = true;
    };
  }, [authHeaders, filterCategory]);

  useEffect(() => {
    const streamUrl = new URL(`${proxyBaseUrl}/notifications/stream`, globalThis.location.origin);
    streamUrl.searchParams.set('tenant_id', defaultTenantId);

    const eventSource = new EventSource(streamUrl);

    const handleSnapshot = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as NotificationSnapshot;
        const incoming = payload.notifications || [];
        const unread = Number(payload.unreadTotal ?? payload.unreadCount ?? 0);
        setAllNotifications(incoming);
        setUnreadCount(unread);
        setConnectionState('live');

        // ENHANCED: detect new unread notifications and show toast when panel is closed
        const newItems = incoming.filter((n) => !n.read && !prevNotifIdsRef.current.has(n.id));
        const unreadIncreased = unread > prevUnreadCountRef.current;
        const newestCreatedAt = incoming[0]?.created_at ? Date.parse(incoming[0].created_at) : Number.NaN;
        const hasVeryRecentItem = Number.isFinite(newestCreatedAt) && Date.now() - newestCreatedAt < 7000;
        if (!panelOpenRef.current && (newItems.length > 0 || unreadIncreased || hasVeryRecentItem)) {
          const candidate = newItems[0] || incoming.find((n) => !n.read) || incoming[0];
          if (candidate) addToast(candidate);
        }
        // Update known IDs
        prevNotifIdsRef.current = new Set(incoming.map((n) => n.id));
        prevUnreadCountRef.current = unread;
      } catch {
        setConnectionState('offline');
      }
    };

    eventSource.addEventListener('notifications.snapshot', handleSnapshot as EventListener);
    eventSource.addEventListener('notifications.updated', handleSnapshot as EventListener);
    eventSource.onerror = () => {
      setConnectionState('offline');
    };

    return () => {
      eventSource.close();
    };
  }, [addToast, filterCategory]);

  // Fallback polling keeps notification state fresh if SSE connects late.
  useEffect(() => {
    let cancelled = false;

    async function pollSnapshot() {
      try {
        const url = new URL(`${proxyBaseUrl}/notifications`, globalThis.location.origin);
        if (filterCategory) url.searchParams.set('category', filterCategory);
        const response = await fetch(url.toString(), {
          headers: authHeaders,
          cache: 'no-store',
        });
        if (!response.ok || cancelled) return;

        const payload = (await response.json()) as NotificationSnapshot;
        const incoming = payload.notifications || [];
        const unread = Number(payload.unreadTotal ?? payload.unreadCount ?? 0);
        const unreadIncreased = unread > prevUnreadCountRef.current;
        const newItems = incoming.filter((n) => !n.read && !prevNotifIdsRef.current.has(n.id));
        const newestCreatedAt = incoming[0]?.created_at ? Date.parse(incoming[0].created_at) : Number.NaN;
        const hasVeryRecentItem = Number.isFinite(newestCreatedAt) && Date.now() - newestCreatedAt < 7000;

        setAllNotifications(incoming);
        setUnreadCount(unread);

        if (!panelOpenRef.current && (unreadIncreased || newItems.length > 0 || hasVeryRecentItem)) {
          const candidate = newItems[0] || incoming.find((n) => !n.read) || incoming[0];
          if (candidate) addToast(candidate);
        }

        prevNotifIdsRef.current = new Set(incoming.map((n) => n.id));
        prevUnreadCountRef.current = unread;
      } catch {
        // Ignore polling failures; SSE remains the primary channel.
      }
    }

    const interval = setInterval(() => {
      // Keep SSE as the primary sync path; poll only while recovering/offline.
      if (connectionStateRef.current === 'live') {
        return;
      }
      void pollSnapshot();
    }, 2500);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [addToast, authHeaders, filterCategory]);

  async function markAllRead() {
    const response = await fetch(`${proxyBaseUrl}/notifications/read-all`, {
      method: 'POST',
      headers: authHeaders,
    });
    if (!response.ok) {
      return;
    }
  }

  async function markOneRead(notificationId: number) {
    const response = await fetch(`${proxyBaseUrl}/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: authHeaders,
    });
    if (!response.ok) {
      return;
    }
  }

  async function dismissOne(notificationId: number) {
    const response = await fetch(`${proxyBaseUrl}/notifications/${notificationId}`, {
      method: 'DELETE',
      headers: authHeaders,
    });
    if (!response.ok) {
      return;
    }
  }

  // ENHANCED: auto-mark-read when user clicks to open a notification item
  async function handleItemClick(notification: NotificationItem) {
    if (!notification.read) {
      await markOneRead(notification.id);
    }
  }

  function handleItemKeyDown(event: React.KeyboardEvent<HTMLButtonElement>, notification: NotificationItem) {
    if (notification.read) {
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      void handleItemClick(notification);
    }
  }

  const triggerLabel = unreadCount > 0 ? `Notifications (${unreadCount} unread)` : 'Notifications';
  let connectionStatusText = 'Realtime sync reconnecting';
  if (connectionState === 'live') {
    connectionStatusText = 'Realtime sync active';
  } else if (connectionState === 'connecting') {
    connectionStatusText = 'Connecting...';
  }

  return (
    <div className="notification-shell">
      {/* Newly added shared shell component avoids duplicating notification UI per page. */}

      {/* ENHANCED: toast popup area for realtime alerts when panel is closed */}
      {toasts.length > 0 ? (
        <div className="notification-toast-tray" aria-live="polite" aria-atomic="false">
          {toasts.map((toast) => (
            <div key={toast.id} className={`notification-toast notification-toast--${toast.priority}`} role="alert">
              <strong className="notification-toast-title">{toast.title}</strong>
              <p className="notification-toast-msg">{toast.message}</p>
              <button
                type="button"
                className="notification-toast-close"
                aria-label="Dismiss toast"
                onClick={() => dismissToast(toast.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        id="notificationTrigger"
        className="notification-trigger"
        aria-label={triggerLabel}
        aria-controls="notificationPanel"
        aria-expanded={panelOpen}
        onClick={() => setPanelOpen((value) => !value)}
      >
        <span className="notification-trigger-label">Alerts</span>
        {unreadCount > 0 ? (
          <span id="notificationBadge" className="notification-badge">
            {unreadCount}
          </span>
        ) : null}
      </button>

      <aside id="notificationPanel" className={`notification-panel${panelOpen ? ' open' : ''}`} aria-live="polite">
        <div className="notification-panel-head">
          <div>
            <h3>Notification Center</h3>
            <p className="muted">{connectionStatusText}</p>
          </div>
          <button type="button" id="markAllReadBtn" onClick={markAllRead} disabled={unreadCount === 0}>
            Mark all read
          </button>
        </div>

        {/* ENHANCED: category filter dropdown — maps to ?category=X on the list endpoint */}
        <div className="notification-filter-row">
          <label htmlFor="notifCategoryFilter" className="sr-only">
            Filter by category
          </label>
          <select
            id="notifCategoryFilter"
            className="notification-filter-select"
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {/* Collect unique categories from current list for dynamic options */}
            {[...new Set(allNotifications.map((n) => n.category))]
              .sort((a, b) => a.localeCompare(b))
              .map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
          </select>
        </div>

        <div id="notificationList" className="notification-list">
          {notifications.length === 0 ? (
            <article className="notification-item notification-empty">
              <strong>No notifications yet</strong>
              <p className="muted">Realtime alerts will appear here as backend events arrive.</p>
            </article>
          ) : (
            notifications.map((notification) => (
              /* ENHANCED: click anywhere on item auto-marks it as read */
              <article
                key={notification.id}
                className={`notification-item notification-item--${notification.priority || 'info'}${notification.read ? ' is-read' : ''}`}
              >
                <button
                  type="button"
                  className="notification-copy"
                  onClick={() => {
                    void handleItemClick(notification);
                  }}
                  onKeyDown={(e) => handleItemKeyDown(e, notification)}
                  style={{ cursor: notification.read ? 'default' : 'pointer' }}
                  disabled={notification.read}
                >
                  <div className="notification-meta-row">
                    <strong>{notification.title}</strong>
                    <span className="notification-age">{formatAge(notification.created_at)}</span>
                  </div>
                  <p>{notification.message}</p>
                  <div className="notification-meta-tags">
                    <span className="notification-category">{notification.category}</span>
                    {/* ENHANCED: priority badge for non-info notifications */}
                    {notification.priority && notification.priority !== 'info' ? (
                      <span className={`notification-priority notification-priority--${notification.priority}`}>
                        {notification.priority}
                      </span>
                    ) : null}
                  </div>
                </button>
                <div className="notification-actions">
                  {notification.read ? null : (
                    <button
                      type="button"
                      className="notification-read"
                      onClick={(e) => {
                        e.stopPropagation();
                        markOneRead(notification.id);
                      }}
                    >
                      Read
                    </button>
                  )}
                  <button
                    type="button"
                    className="notification-dismiss"
                    onClick={(e) => {
                      e.stopPropagation();
                      dismissOne(notification.id);
                    }}
                  >
                    Dismiss
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
