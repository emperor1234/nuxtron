import { describe, expect, it } from 'vitest';
import { calculateKpiComparison, type KpiInput } from './traffic-comparison-model';

const blank: KpiInput = {
  source: 'Search Console export',
  previousPeriod: 'Aug 1–31',
  currentPeriod: 'Sep 1–30',
  clicksPrevious: '',
  clicksCurrent: '',
  impressionsPrevious: '',
  impressionsCurrent: '',
  ctrPrevious: '',
  ctrCurrent: '',
  positionPrevious: '',
  positionCurrent: '',
};

describe('calculateKpiComparison', () => {
  it('distinguishes recorded zero values from metrics that were not supplied', () => {
    const report = calculateKpiComparison({
      ...blank,
      clicksPrevious: '0',
      clicksCurrent: '0',
      impressionsPrevious: '0',
      impressionsCurrent: '12',
      ctrPrevious: '0',
      ctrCurrent: '0',
      positionPrevious: '9.5',
      positionCurrent: '7.25',
    });
    expect(report.metrics.find((metric) => metric.id === 'clicks')).toMatchObject({ previous: 0, current: 0, relativeChangePercent: null });
    expect(report.metrics.find((metric) => metric.id === 'impressions')?.note).toMatch(/zero baseline/i);
    expect(report.metrics.find((metric) => metric.id === 'ctr')?.delta).toBe(0);
    expect(report.metrics.find((metric) => metric.id === 'average-position')?.current).toBe(7.25);
    expect(report.metrics.find((metric) => metric.id === 'average-position')?.note).toMatch(/no cause is inferred/i);
  });

  it('keeps an entirely absent metric unavailable and requires at least one complete pair', () => {
    expect(() => calculateKpiComparison(blank)).toThrow(/at least one metric/i);
    const report = calculateKpiComparison({ ...blank, clicksPrevious: '10', clicksCurrent: '12' });
    expect(report.metrics.find((metric) => metric.id === 'impressions')).toMatchObject({ previous: null, current: null, note: 'Not supplied for these periods.' });
    expect(report.metrics.find((metric) => metric.id === 'clicks')?.relativeChangePercent).toBe(20);
  });

  it('rejects incomplete pairs, invalid counts, out-of-range CTR, and zero search position', () => {
    expect(() => calculateKpiComparison({ ...blank, clicksCurrent: '2' })).toThrow(/both periods or leave both blank/i);
    expect(() => calculateKpiComparison({ ...blank, clicksPrevious: '1.5', clicksCurrent: '2' })).toThrow(/whole number/i);
    expect(() => calculateKpiComparison({ ...blank, ctrPrevious: '101', ctrCurrent: '50' })).toThrow(/between 0 and 100/i);
    expect(() => calculateKpiComparison({ ...blank, positionPrevious: '0', positionCurrent: '1' })).toThrow(/greater than zero/i);
  });

  it('requires explicit source and distinct periods', () => {
    expect(() => calculateKpiComparison({ ...blank, source: '' })).toThrow(/data source/i);
    expect(() => calculateKpiComparison({ ...blank, previousPeriod: 'Same', currentPeriod: 'same', clicksPrevious: '1', clicksCurrent: '2' })).toThrow(/different labels/i);
  });
});
