'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import AccountNav from '@/app/components/account-nav';
import { Button, TableWrap } from '@/app/(dashboard)/_ui/kit';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

type OrderItem = {
  id: string | number;
  created_at?: string;
  product_name?: string;
  total_usd?: number | string;
  order_status?: string;
};

function isPreviewResponse(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  const source = String(payload.data_source ?? payload.source ?? payload.mode ?? '').toLowerCase();
  return payload.is_mock === true || payload.mock === true || payload.preview === true || payload.is_demo === true ||
    ['mock', 'demo', 'sample', 'preview', 'fallback', 'seeded'].includes(source);
}

function parseOrders(value: unknown): OrderItem[] {
  if (!value || typeof value !== 'object' || isPreviewResponse(value)) {
    throw new Error('Live order data is unavailable.');
  }
  const raw = (value as Record<string, unknown>).orders;
  if (!Array.isArray(raw)) throw new Error('Order data is incomplete.');
  return raw.slice(0, 50).map((item) => {
    if (!item || typeof item !== 'object') throw new Error('Order data contains an invalid record.');
    const row = item as Record<string, unknown>;
    if (typeof row.id !== 'string' && typeof row.id !== 'number') {
      throw new Error('Order data contains a record without a stable identifier.');
    }
    return {
      id: row.id,
      created_at: typeof row.created_at === 'string' ? row.created_at : undefined,
      product_name: typeof row.product_name === 'string' ? row.product_name : undefined,
      total_usd: typeof row.total_usd === 'string' || typeof row.total_usd === 'number' ? row.total_usd : undefined,
      order_status: typeof row.order_status === 'string' ? row.order_status : undefined,
    };
  });
}

function formatDate(value?: string): string {
  if (!value) return 'Date unavailable';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(parsed);
}

function formatMoney(value?: number | string): string {
  const amount = typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : Number.NaN;
  return Number.isFinite(amount)
    ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(amount)
    : '—';
}

export default function AccountOrdersPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await apiGet('/money-printers/commerce-pro/orders', tenantId);
        if (!active) return;
        setOrders(parseOrders(response));
        setError('');
      } catch (ex) {
        if (!active) return;
        setError(ex instanceof Error ? ex.message : 'Failed to load orders.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [refresh, tenantId]);

  function retry() {
    setLoading(true);
    setError('');
    setRefresh((value) => value + 1);
  }

  return (
    <div className="account-shell">
      <AccountNav />
      <section className="card" aria-labelledby="account-orders-title">
        <header>
          <h1 id="account-orders-title">Order Details</h1>
          <p className="muted">Review recent purchases and their current status.</p>
          <p className="muted">Showing up to 50 recent order records.</p>
        </header>

        {loading ? <p role="status" aria-live="polite">Loading orders…</p> : null}
        {error ? (
          <div role="alert" className="auth-errors">
            <p>{error}</p>
            <Button onClick={retry}>Retry orders</Button>
          </div>
        ) : null}
        {!loading && !error && orders.length === 0 ? (
          <div className="account-empty-state" role="status">
            <h2>No orders yet</h2>
            <p>Your completed purchases will appear here.</p>
            <Link href="/billing">Review plans and billing</Link>
          </div>
        ) : null}
        {!error && orders.length > 0 ? (
          <TableWrap>
            <table>
              <caption className="sr-only">Up to 50 recent purchase records</caption>
              <thead>
                <tr>
                  <th scope="col">Order</th>
                  <th scope="col">Date</th>
                  <th scope="col">Product</th>
                  <th scope="col">Total</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order, index) => (
                  <tr key={`${order.id}-${index}`}>
                    <td>{`ORD-${order.id}`}</td>
                    <td>{formatDate(order.created_at)}</td>
                    <td>{order.product_name?.trim() || '—'}</td>
                    <td>{formatMoney(order.total_usd)}</td>
                    <td>{order.order_status?.trim() || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        ) : null}
      </section>
    </div>
  );
}
