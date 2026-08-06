'use client';

import AccountNav from '@/app/components/account-nav';
import { useEffect, useState } from 'react';
import { apiGet, resolveSessionTenant } from '@/app/lib/api-client';

type OrderItem = {
  id: number;
  created_at: string;
  product_name: string;
  total_usd: number;
  order_status: string;
};

export default function AccountOrdersPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      setError('');
      try {
        const response = await apiGet('/money-printers/commerce-pro/orders', tenantId);
        if (!active) return;
        setOrders(((response.orders as OrderItem[] | undefined) || []).slice(0, 50));
      } catch (ex) {
        if (!active) return;
        setError(ex instanceof Error ? ex.message : 'Failed to load orders.');
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [tenantId]);

  return (
    <main className="account-shell">
      <AccountNav />
      <section className="card">
        <h1>Order Details</h1>
        <label className="auth-form" style={{ maxWidth: 360 }}>
          <span>Tenant ID</span>
          <input value={tenantId} readOnly />
        </label>
        {error ? <p className="auth-errors">{error}</p> : null}
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Order</th>
                <th>Date</th>
                <th>Plan</th>
                <th>Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{`ORD-${order.id}`}</td>
                  <td>{new Date(order.created_at).toISOString().slice(0, 10)}</td>
                  <td>{order.product_name}</td>
                  <td>{`$${Number(order.total_usd || 0).toFixed(2)}`}</td>
                  <td>{order.order_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
