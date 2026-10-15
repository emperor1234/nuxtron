'use client';

import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader } from '../../_ui/kit';
import styles from './traffic-comparison.module.css';
import { calculateKpiComparison, displayKpiValue, type KpiComparisonReport, type KpiInput } from './traffic-comparison-model';

const INITIAL_INPUT: KpiInput = {
  source: '',
  previousPeriod: '',
  currentPeriod: '',
  clicksPrevious: '',
  clicksCurrent: '',
  impressionsPrevious: '',
  impressionsCurrent: '',
  ctrPrevious: '',
  ctrCurrent: '',
  positionPrevious: '',
  positionCurrent: '',
};

const METRIC_FIELDS = [
  { id: 'clicks', label: 'Clicks', previous: 'clicksPrevious', current: 'clicksCurrent', step: '1', hint: 'Whole-number totals' },
  { id: 'impressions', label: 'Impressions', previous: 'impressionsPrevious', current: 'impressionsCurrent', step: '1', hint: 'Whole-number totals' },
  { id: 'ctr', label: 'Click-through rate (%)', previous: 'ctrPrevious', current: 'ctrCurrent', step: 'any', hint: 'Enter a percentage from 0 to 100; change is shown in percentage points' },
  { id: 'position', label: 'Average position', previous: 'positionPrevious', current: 'positionCurrent', step: 'any', hint: 'Positive values only; a lower number is nearer the top' },
] as const;

type InputKey = keyof KpiInput;

export default function TrafficAnalyticsPage() {
  const [input, setInput] = useState<KpiInput>(INITIAL_INPUT);
  const [report, setReport] = useState<KpiComparisonReport | null>(null);
  const [error, setError] = useState('');

  function updateField(key: InputKey, value: string) {
    setInput((current) => ({ ...current, [key]: value }));
    setReport(null);
    setError('');
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setReport(null);
    try {
      setReport(calculateKpiComparison(input));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not compare these values.');
    }
  }

  return (
    <Page>
      <PageHeader title="Traffic Analytics" subtitle="Compare search KPIs from two periods using values you provide; this page is not connected to an analytics provider." />
      <Card>
        <Badge tone="neutral">Manual comparison · no provider connection</Badge>
        <p className={styles.scopeNotice}>Enter values from a source you trust, such as an exported search report. Nuxtron calculates only the differences shown below. It does not fetch traffic, assign a performance score, infer causes, or recommend that a change was caused by SEO work.</p>
        <form className={styles.form} onSubmit={submit}>
          <div className={styles.metaGrid}>
            <label className={styles.field} htmlFor="traffic-source"><span>Data source</span><input id="traffic-source" value={input.source} onChange={(event) => updateField('source', event.target.value)} required /></label>
            <label className={styles.field} htmlFor="traffic-previous-period"><span>Comparison period label</span><input id="traffic-previous-period" value={input.previousPeriod} onChange={(event) => updateField('previousPeriod', event.target.value)} required /></label>
            <label className={styles.field} htmlFor="traffic-current-period"><span>Current period label</span><input id="traffic-current-period" value={input.currentPeriod} onChange={(event) => updateField('currentPeriod', event.target.value)} required /></label>
          </div>

          {METRIC_FIELDS.map((metric) => (
            <fieldset className={styles.group} key={metric.id}>
              <legend>{metric.label}</legend>
              <p className={styles.groupHint}>{metric.hint}. Leave both values blank if this metric is not available.</p>
              <div className={styles.valueGrid}>
                <label className={styles.field} htmlFor={`${metric.id}-previous`}>
                  <span>{metric.label} — comparison period</span>
                  <input id={`${metric.id}-previous`} type="number" min={metric.id === 'position' ? '0.0001' : '0'} step={metric.step} value={input[metric.previous]} onChange={(event) => updateField(metric.previous as InputKey, event.target.value)} />
                </label>
                <label className={styles.field} htmlFor={`${metric.id}-current`}>
                  <span>{metric.label} — current period</span>
                  <input id={`${metric.id}-current`} type="number" min={metric.id === 'position' ? '0.0001' : '0'} step={metric.step} value={input[metric.current]} onChange={(event) => updateField(metric.current as InputKey, event.target.value)} />
                </label>
              </div>
            </fieldset>
          ))}
          {error && <p className={styles.error} role="alert">{error}</p>}
          <Button type="submit" variant="primary">Compare supplied values</Button>
        </form>
      </Card>

      {report && (
        <section aria-label="Manual SEO comparison result">
          <Card>
            <CardTitle sub="Differences are arithmetic on the values entered above; missing inputs remain unavailable.">Period comparison</CardTitle>
            <Badge tone="neutral">Source supplied by you: {report.source}</Badge>
            <p className={styles.comparisonContext}>{report.previousPeriod} → {report.currentPeriod}</p>
            <div className={styles.metricGrid}>
              {report.metrics.map((metric) => (
                <article className={styles.metric} key={metric.id}>
                  <h3>{metric.label}</h3>
                  {metric.previous === null || metric.current === null ? (
                    <p className={styles.values}>Not supplied</p>
                  ) : (
                    <p className={styles.values}>{displayKpiValue(metric, metric.previous)} → {displayKpiValue(metric, metric.current)}</p>
                  )}
                  <p className={styles.metricNote}>{metric.note}</p>
                </article>
              ))}
            </div>
          </Card>
        </section>
      )}
    </Page>
  );
}
