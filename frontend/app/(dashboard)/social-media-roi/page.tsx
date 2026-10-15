'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiGet, apiSend } from '@/app/lib/platform-api';
import { Badge, Button, Card, CardTitle, Field, FieldSelect, Page, PageHeader, Stat, StatGrid, TableWrap, tableClass } from '../_ui/kit';
import {
  buildCalculatorPayload,
  buildSpendPayload,
  buildTrackedLinkPayload,
  formatCurrencyAmount,
  parseCalculatorResult,
  parseRoiSummary,
  parseSpendList,
  parseSpendWriteResult,
  parseTrackedLinkResult,
  type CalculatorDraft,
  type CalculatorResult,
  type PersistenceMode,
  type RoiSummary,
  type SpendEntry,
} from './social-roi-model';
import styles from './social-media-roi.module.css';

type Resource<T> = {
  status: 'loading' | 'refreshing' | 'ready' | 'error' | 'stale';
  data: T | null;
  error: string;
};

type CalculatorReceipt = {
  currency: string;
  metrics: CalculatorResult;
};

const WINDOWS = [30, 90, 365];
const CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD'];
const EMPTY_CALCULATOR: CalculatorDraft = {
  revenue: '', paidSpend: '', teamCost: '', toolsCost: '', agencyCost: '',
};

function initialResource<T>(): Resource<T> {
  return { status: 'loading', data: null, error: '' };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message.trim() ? error.message : fallback;
}

function money(value: number | null, currency: string): string {
  return value === null ? '—' : formatCurrencyAmount(value, currency);
}

function percent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(2)}%`;
}

function ratio(value: number | null): string {
  return value === null ? '—' : value.toFixed(2);
}

function isLoading<T>(resource: Resource<T>): boolean {
  return resource.status === 'loading' || resource.status === 'refreshing';
}

function destinationUrlProblem(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if ((url.protocol !== 'https:' && url.protocol !== 'http:') || !url.hostname || url.username || url.password) {
      return 'Use an HTTP or HTTPS URL without embedded credentials.';
    }
    return null;
  } catch {
    return 'Enter a valid destination URL beginning with http:// or https://.';
  }
}

function MetricTable({
  title,
  nameLabel,
  rows,
  currency,
  windowDays,
}: {
  title: string;
  nameLabel: string;
  rows: Array<{ name: string; revenue: number | null; spend: number | null; netProfit: number | null; roas: number | null; roiPct: number | null }>;
  currency: string;
  windowDays: number;
}) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      {rows.length === 0 ? (
        <p className={styles.muted}>No {nameLabel.toLowerCase()} performance has been recorded in this period.</p>
      ) : (
        <TableWrap>
          <table className={tableClass}>
            <caption className={styles.srOnly}>{title} for the last {windowDays} days, shown in {currency}</caption>
            <thead>
              <tr>
                <th scope="col">{nameLabel}</th>
                <th scope="col">Attributed revenue ({currency})</th>
                <th scope="col">Spend ({currency})</th>
                <th scope="col">Net ({currency})</th>
                <th scope="col">ROAS</th>
                <th scope="col">ROI</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.name}>
                  <th scope="row">{row.name}</th>
                  <td>{money(row.revenue, currency)}</td>
                  <td>{money(row.spend, currency)}</td>
                  <td>{money(row.netProfit, currency)}</td>
                  <td>{ratio(row.roas)}</td>
                  <td>{percent(row.roiPct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
    </Card>
  );
}

export default function SocialMediaRoiPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [windowDays, setWindowDays] = useState(90);
  const [summary, setSummary] = useState<Resource<RoiSummary>>(initialResource);
  const [spendHistory, setSpendHistory] = useState<Resource<SpendEntry[]>>(initialResource);
  const [spendPersistenceMode, setSpendPersistenceMode] = useState<PersistenceMode | null>(null);
  const [actionError, setActionError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [creatingLink, setCreatingLink] = useState(false);
  const [recordingSpend, setRecordingSpend] = useState(false);
  const [calculating, setCalculating] = useState(false);

  const [campaign, setCampaign] = useState('');
  const [channel, setChannel] = useState('');
  const [postId, setPostId] = useState('');
  const [destinationUrl, setDestinationUrl] = useState('');
  const [destinationUrlError, setDestinationUrlError] = useState('');
  const [trackedUrl, setTrackedUrl] = useState('');
  const [spendAmount, setSpendAmount] = useState('');
  const [spendCurrency, setSpendCurrency] = useState('');
  const [calculatorDraft, setCalculatorDraft] = useState<CalculatorDraft>(EMPTY_CALCULATOR);
  const [calculatorCurrency, setCalculatorCurrency] = useState('');
  const [calculatorReceipt, setCalculatorReceipt] = useState<CalculatorReceipt | null>(null);

  const loadSummary = useCallback(async () => {
    if (!tenantId) {
      setSummary({ status: 'error', data: null, error: 'Sign in to a workspace before loading ROI data.' });
      return;
    }
    setSummary((current) => ({ status: current.data ? 'refreshing' : 'loading', data: current.data, error: '' }));
    try {
      const result = parseRoiSummary(await apiGet<unknown>(`/analytics/social-roi/summary?window_days=${windowDays}`, tenantId));
      if (!result) throw new Error('The ROI service returned an incomplete or unsupported summary.');
      setSummary({ status: 'ready', data: result, error: '' });
    } catch (error) {
      const message = errorMessage(error, 'ROI summary could not be loaded.');
      setSummary((current) => current.data
        ? { status: 'stale', data: current.data, error: message }
        : { status: 'error', data: null, error: message });
    }
  }, [tenantId, windowDays]);

  const loadSpendHistory = useCallback(async () => {
    if (!tenantId) {
      setSpendHistory({ status: 'error', data: null, error: 'Sign in to a workspace before loading spend history.' });
      return;
    }
    setSpendHistory((current) => ({ status: current.data ? 'refreshing' : 'loading', data: current.data, error: '' }));
    try {
      const result = parseSpendList(await apiGet<unknown>('/analytics/social-roi/spend?limit=20&offset=0', tenantId));
      if (!result) throw new Error('The spend service returned an incomplete or unsupported list.');
      setSpendPersistenceMode(result.persistenceMode);
      setSpendHistory({ status: 'ready', data: result.items, error: '' });
    } catch (error) {
      const message = errorMessage(error, 'Recent spend entries could not be loaded.');
      setSpendHistory((current) => current.data
        ? { status: 'stale', data: current.data, error: message }
        : { status: 'error', data: null, error: message });
    }
  }, [tenantId]);

  const refreshData = useCallback(async () => {
    await Promise.all([loadSummary(), loadSpendHistory()]);
  }, [loadSpendHistory, loadSummary]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshData(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshData]);

  const campaignSuggestions = useMemo(() => summary.data?.campaigns.map((item) => item.name) ?? [], [summary.data]);
  const channelSuggestions = useMemo(() => summary.data?.channels.map((item) => item.name) ?? [], [summary.data]);
  const currencyCodes = summary.data?.currencyCodes ?? [];
  const currencyChoices = [...new Set([...CURRENCIES, ...currencyCodes])].sort();
  const currencyStatus = summary.data?.currencyStatus ?? 'none';
  const currency = currencyStatus === 'single' ? (currencyCodes[0] ?? '') : '';
  const persistenceMode = summary.data?.persistenceMode ?? spendPersistenceMode;
  const currencyHint = currencyStatus === 'single'
    ? currency
    : currencyStatus === 'mixed'
      ? 'Mixed currencies — totals hidden'
      : currencyStatus === 'unsupported'
        ? 'Unsupported currency records'
        : 'No currency-coded records';
  const refreshing = isLoading(summary) || isLoading(spendHistory);
  const totals = summary.data?.totals;

  async function createTrackedLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError('');
    setActionMessage('');
    setTrackedUrl('');
    if (!tenantId) {
      setActionError('Sign in to a workspace before creating a tracked URL.');
      return;
    }
    const urlProblem = destinationUrlProblem(destinationUrl);
    if (urlProblem) {
      setDestinationUrlError(urlProblem);
      setActionError('Review the destination URL field before creating a tracked link.');
      return;
    }
    setDestinationUrlError('');
    const payload = buildTrackedLinkPayload({ postId, platform: channel, campaign, destinationUrl });
    if (!payload) {
      setActionError('Enter a post ID, channel, campaign, and a valid HTTP(S) destination URL.');
      return;
    }
    setCreatingLink(true);
    try {
      const result = parseTrackedLinkResult(await apiSend<unknown>('/analytics/revenue-attribution/touchpoints', 'POST', payload, tenantId));
      if (!result) throw new Error('The tracking service did not return a valid tracked URL and storage receipt.');
      setTrackedUrl(result.trackedUrl);
      setActionMessage(result.persistenceMode === 'postgres'
        ? 'Tracked URL created and saved in the workspace database.'
        : 'Tracked URL created in temporary process memory; it may be lost when the service restarts.');
      await refreshData();
    } catch (error) {
      setActionError(errorMessage(error, 'Tracked URL could not be created.'));
    } finally {
      setCreatingLink(false);
    }
  }

  async function recordSpend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError('');
    setActionMessage('');
    if (!tenantId) {
      setActionError('Sign in to a workspace before recording spend.');
      return;
    }
    const payload = buildSpendPayload({ channel, campaign, amount: spendAmount, currency: spendCurrency });
    if (!payload) {
      setActionError('Enter a positive spend amount, complete the shared campaign context, and select a currency.');
      return;
    }
    setRecordingSpend(true);
    try {
      const result = parseSpendWriteResult(await apiSend<unknown>('/analytics/social-roi/spend', 'POST', payload, tenantId));
      if (!result) throw new Error('The spend service did not return a valid saved-record receipt.');
      setActionMessage(result.persistenceMode === 'postgres'
        ? 'Spend entry saved in the workspace database.'
        : 'Spend entry recorded in temporary process memory; it may be lost when the service restarts.');
      setSpendAmount('');
      await refreshData();
    } catch (error) {
      setActionError(errorMessage(error, 'Spend entry could not be recorded.'));
    } finally {
      setRecordingSpend(false);
    }
  }

  async function runCalculator(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError('');
    setActionMessage('');
    setCalculatorReceipt(null);
    if (!tenantId) {
      setActionError('Sign in to a workspace before running the calculator.');
      return;
    }
    const payload = buildCalculatorPayload(calculatorDraft);
    if (!payload || !/^[A-Z]{3}$/.test(calculatorCurrency)) {
      setActionError('Enter every non-negative assumption explicitly and select one currency for the scenario.');
      return;
    }
    setCalculating(true);
    try {
      const result = parseCalculatorResult(await apiSend<unknown>('/analytics/social-roi/calculator', 'POST', payload, tenantId));
      if (!result) throw new Error('The calculator returned an incomplete scenario.');
      setCalculatorReceipt({ currency: calculatorCurrency, metrics: result });
      setActionMessage('Scenario calculated from the assumptions entered below; these results are not stored.');
    } catch (error) {
      setActionError(errorMessage(error, 'The ROI scenario could not be calculated.'));
    } finally {
      setCalculating(false);
    }
  }

  const changeCalculatorField = (field: keyof CalculatorDraft, value: string) => {
    setCalculatorDraft((current) => ({ ...current, [field]: value }));
  };

  const summaryStateText = summary.status === 'loading'
    ? 'Loading ROI summary…'
    : summary.status === 'refreshing'
      ? 'Refreshing ROI summary…'
      : '';
  const spendStateText = spendHistory.status === 'loading'
    ? 'Loading recent spend entries…'
    : spendHistory.status === 'refreshing'
      ? 'Refreshing recent spend entries…'
      : '';

  return (
    <Page>
      <PageHeader
        title="Social Media ROI"
        subtitle="Review attributed conversions and recorded social spend for this workspace."
        actions={<Button variant="ghost" onClick={() => void refreshData()} disabled={!tenantId || refreshing}>{refreshing ? 'Refreshing…' : 'Refresh data'}</Button>}
      />

      {!tenantId ? <p className={styles.error} role="alert">Sign in to a workspace before using Social Media ROI.</p> : null}
      {actionMessage ? <p className={styles.status} role="status">{actionMessage}</p> : null}
      {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}

      {persistenceMode === 'process-memory' ? (
        <div className={styles.warning} role="note">
          <strong>Temporary storage is active.</strong> Social ROI records are currently held in process memory and may be lost when the service restarts. Do not treat these entries as durable financial records.
        </div>
      ) : persistenceMode === 'postgres' ? (
        <p className={styles.status}><Badge tone="success">PostgreSQL-backed workspace data</Badge></p>
      ) : null}

      <Card className={styles.reportControls}>
        <div>
          <CardTitle>Reporting context</CardTitle>
          <p className={styles.muted}>Values are attributed by the service from conversion touchpoints and recorded spend. Financial totals are withheld when currency units cannot be compared safely.</p>
        </div>
        <FieldSelect
          id="roi-reporting-window"
          label="Reporting period"
          value={windowDays}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (!WINDOWS.includes(next)) return;
            setWindowDays(next);
            setSummary({ status: 'loading', data: null, error: '' });
          }}
        >
          {WINDOWS.map((days) => <option key={days} value={days}>Last {days} days</option>)}
        </FieldSelect>
      </Card>

      <section aria-label="Social Media ROI summary">
        <StatGrid>
          <Stat label="Attributed revenue" value={summary.status === 'loading' && !summary.data ? '…' : money(totals?.revenue ?? null, currency)} hint={currencyHint} />
          <Stat label="Recorded spend" value={summary.status === 'loading' && !summary.data ? '…' : money(totals?.spend ?? null, currency)} hint={currencyHint} />
          <Stat label="Net attributed" value={summary.status === 'loading' && !summary.data ? '…' : money(totals?.netProfit ?? null, currency)} hint={currencyHint} />
          <Stat label="ROAS" value={summary.status === 'loading' && !summary.data ? '…' : ratio(totals?.roas ?? null)} hint={currencyStatus !== 'single' ? 'Requires one supported currency' : totals?.spend === 0 ? 'Requires recorded spend' : 'Attributed revenue ÷ spend'} />
          <Stat label="ROI" value={summary.status === 'loading' && !summary.data ? '…' : percent(totals?.roiPct ?? null)} hint={currencyStatus !== 'single' ? 'Requires one supported currency' : totals?.spend === 0 ? 'Requires recorded spend' : 'Net attributed ÷ spend'} />
          <Stat label="Tracking coverage" value={summary.status === 'loading' && !summary.data ? '…' : totals?.conversions === 0 ? '—' : percent(totals?.trackingCoveragePct ?? null)} hint={totals?.conversions === 0 ? 'No conversions in this period' : `${totals?.trackedConversions ?? '—'} of ${totals?.conversions ?? '—'} conversions tracked`} />
        </StatGrid>
      </section>

      {summaryStateText ? <p className={styles.status} role="status">{summaryStateText}</p> : null}
      {summary.error ? <p className={styles.error} role={summary.status === 'error' ? 'alert' : 'status'}>{summary.status === 'stale' ? 'Refresh failed; showing the last loaded summary. ' : ''}{summary.error}</p> : null}
      {summary.data?.currencyStatus === 'mixed' ? (
        <div className={styles.warning} role="note"><strong>Mixed currencies are not normalized.</strong> Combined money metrics and campaign/channel comparisons are hidden. Reported currencies: {summary.data.currencyCodes.join(', ')}.</div>
      ) : null}
      {summary.data?.currencyStatus === 'unsupported' ? (
        <div className={styles.warning} role="note"><strong>Some records use an unsupported currency code.</strong> Combined financial metrics are hidden until currency records are corrected.</div>
      ) : null}
      {summary.data?.currencyStatus === 'none' ? <p className={styles.muted}>No currency-coded conversions or spend entries are available in this period yet.</p> : null}

      <div className={styles.panelGrid}>
        <Card>
          <CardTitle>Campaign context</CardTitle>
          <p className={styles.muted}>Enter the campaign and channel once. Both a tracked link and its spend entry will use the same values.</p>
          <div className={styles.formGrid}>
            <Field
              id="roi-campaign-context"
              label="Campaign name"
              value={campaign}
              onChange={(event) => setCampaign(event.target.value)}
              maxLength={160}
              list="roi-campaign-suggestions"
              autoComplete="off"
              placeholder="Enter campaign name"
            />
            <datalist id="roi-campaign-suggestions">{campaignSuggestions.map((name) => <option key={name} value={name} />)}</datalist>
            <Field
              id="roi-channel-context"
              label="Social channel"
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              maxLength={80}
              list="roi-channel-suggestions"
              autoComplete="off"
              placeholder="Enter channel, e.g. LinkedIn"
            />
            <datalist id="roi-channel-suggestions">{channelSuggestions.map((name) => <option key={name} value={name} />)}</datalist>
          </div>
        </Card>

        <Card>
          <CardTitle>Generate a tracked post URL</CardTitle>
          <p className={styles.muted}>Creates an attribution touchpoint for a post and destination. Use the generated URL in the post you publish.</p>
          <form className={styles.formGrid} onSubmit={(event) => void createTrackedLink(event)}>
            <Field id="roi-post-id" label="Post ID or internal reference" value={postId} onChange={(event) => setPostId(event.target.value)} maxLength={160} required placeholder="Post or content reference" />
            <Field id="roi-destination-url" label="Destination URL" type="url" value={destinationUrl} onChange={(event) => { setDestinationUrl(event.target.value); setDestinationUrlError(''); }} maxLength={2000} required placeholder="https://example.com/page" autoComplete="url" aria-invalid={Boolean(destinationUrlError)} aria-describedby={destinationUrlError ? 'roi-destination-url-help roi-destination-url-error' : 'roi-destination-url-help'} />
            <p id="roi-destination-url-help" className={`${styles.muted} ${styles.fullWidth}`}>Use HTTP or HTTPS; URLs containing embedded credentials are not accepted.</p>
            {destinationUrlError ? <p id="roi-destination-url-error" className={`${styles.error} ${styles.fullWidth}`} role="alert">{destinationUrlError}</p> : null}
            <div className={`${styles.actions} ${styles.fullWidth}`}>
              <Button variant="primary" type="submit" disabled={!tenantId || !campaign.trim() || !channel.trim() || creatingLink}>{creatingLink ? 'Creating tracked URL…' : 'Create tracked URL'}</Button>
              {!campaign.trim() || !channel.trim() ? <span className={styles.muted}>Set the shared campaign context first.</span> : null}
            </div>
          </form>
          {trackedUrl ? <div className={styles.trackedLink}><span>Generated tracked URL</span><code>{trackedUrl}</code></div> : null}
        </Card>

        <Card>
          <CardTitle>Record social spend</CardTitle>
          <p className={styles.muted}>This entry uses the shared campaign and channel above; the amount must be positive and its currency explicit.</p>
          <form className={styles.formGrid} onSubmit={(event) => void recordSpend(event)}>
            <Field id="roi-spend-amount" label="Spend amount" type="number" min="0.01" step="0.01" inputMode="decimal" value={spendAmount} onChange={(event) => setSpendAmount(event.target.value)} required placeholder="0.00" />
            <FieldSelect id="roi-spend-currency" label="Spend currency" value={spendCurrency} onChange={(event) => setSpendCurrency(event.target.value)} required>
              <option value="">Select currency</option>
              {currencyChoices.map((code) => <option key={code} value={code}>{code}</option>)}
            </FieldSelect>
            <p className={`${styles.muted} ${styles.fullWidth}`}>Current context: <strong>{channel || 'No channel selected'}</strong> · <strong>{campaign || 'No campaign entered'}</strong></p>
            <div className={`${styles.actions} ${styles.fullWidth}`}>
              <Button variant="primary" type="submit" disabled={!tenantId || !campaign.trim() || !channel.trim() || recordingSpend}>{recordingSpend ? 'Saving spend…' : 'Record spend'}</Button>
            </div>
          </form>
        </Card>

        <Card>
          <CardTitle>Recent spend entries</CardTitle>
          {spendStateText ? <p className={styles.status} role="status">{spendStateText}</p> : null}
          {spendHistory.error ? <p className={styles.error} role={spendHistory.status === 'error' ? 'alert' : 'status'}>{spendHistory.status === 'stale' ? 'Refresh failed; showing the last loaded spend entries. ' : ''}{spendHistory.error}</p> : null}
          {spendHistory.status === 'loading' && !spendHistory.data ? null : spendHistory.status === 'error' && !spendHistory.data ? null : spendHistory.data?.length ? (
            <TableWrap>
              <table className={tableClass}>
                <caption className={styles.srOnly}>Most recent recorded social spend entries</caption>
                <thead><tr><th scope="col">Date</th><th scope="col">Channel</th><th scope="col">Campaign</th><th scope="col">Spend</th></tr></thead>
                <tbody>
                  {spendHistory.data.map((item) => (
                    <tr key={item.id}>
                      <td>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(item.spentAt))}</td>
                      <td>{item.channel}</td>
                      <td>{item.campaign || 'Unassigned'}</td>
                      <td>{formatCurrencyAmount(item.amount, item.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : spendHistory.status === 'ready' ? <p className={styles.muted}>No spend entries are recorded for this workspace yet.</p> : null}
        </Card>
      </div>

      <section className={styles.panelGrid} aria-label="Campaign and channel performance">
        {summary.status === 'loading' && !summary.data ? <p className={styles.status} role="status">Loading campaign and channel breakdowns…</p> : null}
        {summary.status === 'error' && !summary.data ? <p className={styles.error} role="alert">Campaign and channel comparisons are unavailable because the summary request failed.</p> : null}
        {summary.data?.currencyStatus === 'single' ? (
          <>
            <MetricTable title="Campaign performance" nameLabel="Campaign" rows={summary.data.campaigns} currency={currency} windowDays={windowDays} />
            <MetricTable title="Channel performance" nameLabel="Channel" rows={summary.data.channels} currency={currency} windowDays={windowDays} />
          </>
        ) : summary.data ? (
          <Card><p className={styles.muted}>Campaign and channel financial comparisons are unavailable until all included records share one supported currency.</p></Card>
        ) : null}
      </section>

      <Card>
        <CardTitle>One-off ROI scenario</CardTitle>
        <p className={styles.muted}>A what-if calculation only. Enter every cost and revenue assumption explicitly; this does not change recorded workspace data.</p>
        <form className={styles.formGrid} onSubmit={(event) => void runCalculator(event)}>
          <FieldSelect id="roi-calculator-currency" label="Scenario currency" value={calculatorCurrency} onChange={(event) => setCalculatorCurrency(event.target.value)} required>
            <option value="">Select currency</option>
            {currencyChoices.map((code) => <option key={code} value={code}>{code}</option>)}
          </FieldSelect>
          <Field id="roi-calculator-revenue" label="Attributed revenue" type="number" min="0" step="0.01" inputMode="decimal" value={calculatorDraft.revenue} onChange={(event) => changeCalculatorField('revenue', event.target.value)} required placeholder="0.00" />
          <Field id="roi-calculator-paid-spend" label="Paid social spend" type="number" min="0" step="0.01" inputMode="decimal" value={calculatorDraft.paidSpend} onChange={(event) => changeCalculatorField('paidSpend', event.target.value)} required placeholder="0.00" />
          <Field id="roi-calculator-team-cost" label="Team cost" type="number" min="0" step="0.01" inputMode="decimal" value={calculatorDraft.teamCost} onChange={(event) => changeCalculatorField('teamCost', event.target.value)} required placeholder="0.00" />
          <Field id="roi-calculator-tools-cost" label="Tools cost" type="number" min="0" step="0.01" inputMode="decimal" value={calculatorDraft.toolsCost} onChange={(event) => changeCalculatorField('toolsCost', event.target.value)} required placeholder="0.00" />
          <Field id="roi-calculator-agency-cost" label="Agency cost" type="number" min="0" step="0.01" inputMode="decimal" value={calculatorDraft.agencyCost} onChange={(event) => changeCalculatorField('agencyCost', event.target.value)} required placeholder="0.00" />
          <div className={`${styles.actions} ${styles.fullWidth}`}><Button variant="primary" type="submit" disabled={!tenantId || calculating}>{calculating ? 'Calculating…' : 'Calculate scenario'}</Button></div>
        </form>
        {calculatorReceipt ? (
          <div className={styles.scenarioResult} role="status">
            <h3>Scenario result · {calculatorReceipt.currency}</h3>
            <dl className={styles.resultGrid}>
              <div><dt>Revenue</dt><dd>{money(calculatorReceipt.metrics.revenue, calculatorReceipt.currency)}</dd></div>
              <div><dt>Total cost</dt><dd>{money(calculatorReceipt.metrics.spend, calculatorReceipt.currency)}</dd></div>
              <div><dt>Net</dt><dd>{money(calculatorReceipt.metrics.netProfit, calculatorReceipt.currency)}</dd></div>
              <div><dt>ROAS</dt><dd>{ratio(calculatorReceipt.metrics.roas)}</dd></div>
              <div><dt>ROI</dt><dd>{percent(calculatorReceipt.metrics.roiPct)}</dd></div>
            </dl>
            {calculatorReceipt.metrics.spend === 0 ? <p className={styles.muted}>ROAS and ROI are undefined with zero total cost.</p> : null}
          </div>
        ) : null}
      </Card>
    </Page>
  );
}
