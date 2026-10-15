export type KpiId = 'clicks' | 'impressions' | 'ctr' | 'average-position';
export type KpiInput = {
  source: string;
  previousPeriod: string;
  currentPeriod: string;
  clicksPrevious: string;
  clicksCurrent: string;
  impressionsPrevious: string;
  impressionsCurrent: string;
  ctrPrevious: string;
  ctrCurrent: string;
  positionPrevious: string;
  positionCurrent: string;
};

export type KpiComparisonMetric = {
  id: KpiId;
  label: string;
  unit: 'count' | 'percent' | 'position';
  previous: number | null;
  current: number | null;
  delta: number | null;
  relativeChangePercent: number | null;
  note: string;
};

export type KpiComparisonReport = {
  source: string;
  previousPeriod: string;
  currentPeriod: string;
  metrics: KpiComparisonMetric[];
};

const METRICS: readonly {
  id: KpiId;
  label: string;
  unit: KpiComparisonMetric['unit'];
  previousKey: keyof KpiInput;
  currentKey: keyof KpiInput;
  integer: boolean;
}[] = [
  { id: 'clicks', label: 'Clicks', unit: 'count', previousKey: 'clicksPrevious', currentKey: 'clicksCurrent', integer: true },
  { id: 'impressions', label: 'Impressions', unit: 'count', previousKey: 'impressionsPrevious', currentKey: 'impressionsCurrent', integer: true },
  { id: 'ctr', label: 'Click-through rate', unit: 'percent', previousKey: 'ctrPrevious', currentKey: 'ctrCurrent', integer: false },
  { id: 'average-position', label: 'Average position', unit: 'position', previousKey: 'positionPrevious', currentKey: 'positionCurrent', integer: false },
];

function parseValue(raw: string, label: string, integer: boolean): number | null {
  const text = raw.trim();
  if (!text) return null;
  const value = Number(text);
  if (!Number.isFinite(value) || value < 0 || (integer && !Number.isSafeInteger(value))) {
    throw new Error(`${label} must be a non-negative ${integer ? 'safe whole number' : 'number'}.`);
  }
  return value;
}

function numberText(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

export function calculateKpiComparison(input: KpiInput): KpiComparisonReport {
  const source = input.source.trim();
  const previousPeriod = input.previousPeriod.trim();
  const currentPeriod = input.currentPeriod.trim();
  if (!source) throw new Error('Enter the data source for these values.');
  if (!previousPeriod || !currentPeriod) throw new Error('Enter labels for both comparison periods.');
  if (previousPeriod.toLocaleLowerCase() === currentPeriod.toLocaleLowerCase()) {
    throw new Error('Use different labels for the comparison and current periods.');
  }

  let suppliedCount = 0;
  const metrics = METRICS.map((definition): KpiComparisonMetric => {
    const previous = parseValue(input[definition.previousKey], `${definition.label} (${previousPeriod})`, definition.integer);
    const current = parseValue(input[definition.currentKey], `${definition.label} (${currentPeriod})`, definition.integer);
    if ((previous === null) !== (current === null)) {
      throw new Error(`${definition.label}: enter values for both periods or leave both blank.`);
    }
    if (previous === null || current === null) {
      return { id: definition.id, label: definition.label, unit: definition.unit, previous: null, current: null, delta: null, relativeChangePercent: null, note: 'Not supplied for these periods.' };
    }

    if (definition.unit === 'percent' && (previous > 100 || current > 100)) {
      throw new Error('Click-through rate must be between 0 and 100 percent.');
    }
    if (definition.unit === 'position' && (previous === 0 || current === 0 || previous > 1_000_000 || current > 1_000_000)) {
      throw new Error('Average position must be greater than zero and at most 1,000,000.');
    }

    suppliedCount += 1;
    const delta = current - previous;
    let relativeChangePercent: number | null = null;
    let note: string;
    if (definition.unit === 'count') {
      relativeChangePercent = previous > 0 ? (delta / previous) * 100 : null;
      note = previous === 0
        ? current === 0
          ? 'Both periods are zero; percentage change is undefined.'
          : 'Changed from a zero baseline; percentage change is undefined.'
        : `${relativeChangePercent! >= 0 ? '+' : ''}${numberText(relativeChangePercent!)}% relative change.`;
    } else if (definition.unit === 'percent') {
      note = `${delta >= 0 ? '+' : ''}${numberText(delta)} percentage points.`;
    } else {
      const movement = delta === 0 ? 'unchanged' : `${numberText(Math.abs(delta))} positions ${delta < 0 ? 'lower' : 'higher'}`;
      note = `Average position ${movement}; no cause is inferred. Lower numbers are nearer the top.`;
    }
    return { id: definition.id, label: definition.label, unit: definition.unit, previous, current, delta, relativeChangePercent, note };
  });

  if (suppliedCount === 0) throw new Error('Enter at least one metric for both periods.');
  return { source, previousPeriod, currentPeriod, metrics };
}

export function displayKpiValue(metric: KpiComparisonMetric, value: number | null): string {
  if (value === null) return 'Not supplied';
  const formatted = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
  if (metric.unit === 'percent') return `${formatted}%`;
  return formatted;
}
