'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, FieldSelect, Page, PageHeader } from '../../_ui/kit';
import { parseRevenueAttributionReport, type RevenueReport } from './report-model';
import styles from './revenue-attribution.module.css';

const WINDOW_OPTIONS = [30, 90, 180, 365] as const;

function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

function formatAmount(value: number | null, currency: string | null, supported: boolean): string {
  if (!supported || !currency || value === null) return 'Amount withheld';
  return `${new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)} ${currency}`;
}

function currencyLabel(currency: string | null, supported: boolean): string {
  if (!currency) return 'Unspecified currency';
  return supported ? currency : `Unrecognized code: ${currency}`;
}

export default function RevenueAttributionPage() {
  const [windowDays, setWindowDays] = useState<number>(30);
  const [report, setReport] = useState<RevenueReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const activeRequest = useRef(0);
  const workspaceRef = useRef('');

  const loadReport = useCallback(async () => {
    const requestId = ++activeRequest.current;
    const workspaceId = resolveSessionTenant();
    if (!workspaceId) {
      workspaceRef.current = '';
      setReport(null);
      setRefreshedAt(null);
      setError('Workspace context is required. Sign in or select a workspace to view recorded revenue events.');
      setLoading(false);
      return;
    }

    if (workspaceRef.current && workspaceRef.current !== workspaceId) {
      setReport(null);
      setRefreshedAt(null);
    }
    workspaceRef.current = workspaceId;
    setLoading(true);
    setError('');

    try {
      const raw = await apiGet<unknown>(
        `/analytics/revenue-attribution/report?window_days=${windowDays}`,
        workspaceId,
        { cache: false }
      );
      const nextReport = parseRevenueAttributionReport(raw);
      if (requestId !== activeRequest.current) return;
      setReport(nextReport);
      setRefreshedAt(new Date().toISOString());
    } catch {
      if (requestId !== activeRequest.current) return;
      setError('Could not load the recorded revenue report. Retry the request; no generated or sample totals are shown.');
    } finally {
      if (requestId === activeRequest.current) setLoading(false);
    }
  }, [windowDays]);

  useEffect(() => {
    let active = true;
    window.queueMicrotask(() => {
      if (active) void loadReport();
    });
    return () => {
      active = false;
      activeRequest.current += 1;
    };
  }, [loadReport]);

  const persistenceIsTemporary = report?.persistence_mode === 'process-memory';

  return (
    <Page>
      <PageHeader
        title="Revenue Attribution"
        subtitle="Recorded conversions linked to tracked Nuxtron touchpoints; no modeled or causal lift estimate."
        actions={(
          <Button variant="ghost" onClick={() => void loadReport()} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh report'}
          </Button>
        )}
      />

      <Card className={styles.controls}>
        <FieldSelect
          id="revenue-attribution-window"
          label="Reporting window"
          value={windowDays}
          onChange={(event) => setWindowDays(Number(event.currentTarget.value))}
        >
          {WINDOW_OPTIONS.map((days) => <option key={days} value={days}>Last {days} days</option>)}
        </FieldSelect>
        <p className={styles.sourceNote}>
          Source: authenticated workspace conversion records and tracked touchpoints. Provider webhooks are paused until signed per-workspace routing is available.
        </p>
      </Card>

      {loading && !report ? <p className={styles.status} role="status">Loading recorded conversion activity…</p> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}

      {report ? (
        <>
          <div className={styles.provenance} role="status">
            <Badge tone={persistenceIsTemporary ? 'neutral' : 'success'}>
              {persistenceIsTemporary ? 'Temporary process-memory data' : 'PostgreSQL-backed data'}
            </Badge>
            <span>{refreshedAt ? `Updated ${new Date(refreshedAt).toLocaleTimeString()}` : 'Update time unavailable'}</span>
            {error ? <span className={styles.staleNotice}>Showing the last successful report; refresh failed.</span> : null}
          </div>

          {persistenceIsTemporary ? (
            <p className={styles.persistenceWarning}>
              These records are held in process memory and may be lost when the service restarts; they are not confirmed as durable.
            </p>
          ) : null}

          {report.totals.conversions === 0 ? (
            <Card className={styles.emptyState}>
              <CardTitle sub={`No authenticated conversion records were returned for the last ${report.window_days} days.`}>
                No recorded conversion activity
              </CardTitle>
              <p className={styles.secondaryText}>
                Revenue is not estimated from domain names, channel labels, or notes. This report will populate only when conversion events and tracked touchpoints are recorded for this workspace.
              </p>
            </Card>
          ) : (
            <>
              <section className={styles.countGrid} aria-label="Recorded conversion counts">
                <Card className={styles.metricCard}>
                  <span className={styles.metricLabel}>Recorded conversions</span>
                  <strong className={styles.metricValue}>{formatCount(report.totals.conversions)}</strong>
                  <span className={styles.metricHint}>In the last {report.window_days} days</span>
                </Card>
                <Card className={styles.metricCard}>
                  <span className={styles.metricLabel}>With tracked touchpoints</span>
                  <strong className={styles.metricValue}>{formatCount(report.totals.tracked_conversions)}</strong>
                  <span className={styles.metricHint}>Linked to one or more stored Nuxtron touchpoints</span>
                </Card>
              </section>

              <section className={styles.reportSection} aria-labelledby="revenue-by-currency-title">
                <CardTitle sub="Currency buckets are kept separate. No exchange-rate conversion or cross-currency total is applied.">
                  <span id="revenue-by-currency-title">Revenue by currency</span>
                </CardTitle>
                <div className={styles.currencyGrid}>
                  {report.currency_totals.map((item) => (
                    <Card className={styles.currencyCard} key={item.currency ?? 'unspecified-currency'}>
                      <div className={styles.currencyHeading}>
                        <strong>{currencyLabel(item.currency, item.currency_supported)}</strong>
                        <span>{formatCount(item.conversions)} conversions</span>
                      </div>
                      {item.currency_supported && item.currency ? (
                        <dl className={styles.moneyList}>
                          <div><dt>Recorded revenue</dt><dd>{formatAmount(item.revenue, item.currency, true)}</dd></div>
                          <div><dt>Attributed to tracked touchpoints</dt><dd>{formatAmount(item.attributed_revenue, item.currency, true)}</dd></div>
                          <div><dt>Not linked to tracked touchpoints</dt><dd>{formatAmount(item.unattributed_revenue, item.currency, true)}</dd></div>
                        </dl>
                      ) : (
                        <p className={styles.secondaryText}>Amounts are hidden because this record group has no supported three-letter currency code.</p>
                      )}
                    </Card>
                  ))}
                </div>
              </section>

              <Card className={styles.reportSection}>
                <CardTitle sub="Only recorded touchpoint-source labels are shown; detailed order identifiers and customer references are omitted.">
                  Channel attribution
                </CardTitle>
                {report.channels.length > 0 ? (
                  <ul className={styles.channelList}>
                    {report.channels.map((item, index) => (
                      <li key={`${item.currency ?? 'unspecified'}-${item.channel}-${index}`}>
                        <span className={styles.channelName}>{item.channel}</span>
                        <span className={styles.channelCurrency}>{currencyLabel(item.currency, item.currency_supported)}</span>
                        <strong>{formatAmount(item.attributed_revenue, item.currency, item.currency_supported)}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.secondaryText}>No tracked touchpoints are associated with the recorded conversions in this window.</p>
                )}
              </Card>

              <p className={styles.methodNote}>
                Attribution is an even allocation across each conversion’s distinct recorded touchpoints. It describes the event ledger; it does not establish incremental lift or prove that a channel caused a conversion.
              </p>
            </>
          )}
        </>
      ) : null}
    </Page>
  );
}
