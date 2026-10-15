export type RevenuePersistence = 'postgres' | 'process-memory';
export type RevenueCurrencyStatus = 'none' | 'single' | 'mixed' | 'unsupported';

export type RevenueCurrencyTotal = {
  currency: string | null;
  currency_supported: boolean;
  conversions: number;
  tracked_conversions: number;
  revenue: number | null;
  attributed_revenue: number | null;
  unattributed_revenue: number | null;
};

export type RevenueChannel = {
  channel: string;
  currency: string | null;
  currency_supported: boolean;
  attributed_revenue: number | null;
};

export type RevenueReport = {
  window_days: number;
  persistence_mode: RevenuePersistence;
  currency_status: RevenueCurrencyStatus;
  currency_codes: string[];
  currency_totals: RevenueCurrencyTotal[];
  totals: {
    conversions: number;
    tracked_conversions: number;
    currency: string | null;
    revenue: number | null;
    attributed_revenue: number | null;
    unattributed_revenue: number | null;
  };
  channels: RevenueChannel[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function count(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`Invalid revenue report ${label}`);
  }
  return value;
}

function amount(value: unknown, label: string): number | null {
  if (value === null) return null;
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    throw new Error(`Invalid revenue report ${label}`);
  }
  return value;
}

function nullableCurrency(value: unknown, label: string): string | null {
  if (value === null) return null;
  if (typeof value !== 'string' || value.length > 12) {
    throw new Error(`Invalid revenue report ${label}`);
  }
  return value;
}

function supportedMoney(
  supported: boolean,
  currency: string | null,
  values: Array<number | null>,
  label: string
): void {
  if (supported && (!currency || !/^[A-Z]{3}$/.test(currency) || values.some((value) => value === null))) {
    throw new Error(`Invalid supported currency totals in ${label}`);
  }
  if (!supported && values.some((value) => value !== null)) {
    throw new Error(`Unsupported currency amount must be withheld in ${label}`);
  }
}

export function parseRevenueAttributionReport(value: unknown): RevenueReport {
  if (!isRecord(value) || value.status !== 'ok') {
    throw new Error('Invalid Revenue Attribution response');
  }

  const windowDays = count(value.window_days, 'window');
  if (windowDays < 1 || windowDays > 365) throw new Error('Invalid Revenue Attribution window');

  const persistenceMode = value.persistence_mode;
  if (persistenceMode !== 'postgres' && persistenceMode !== 'process-memory') {
    throw new Error('Invalid Revenue Attribution persistence mode');
  }

  const currencyStatus = value.currency_status;
  if (!['none', 'single', 'mixed', 'unsupported'].includes(String(currencyStatus))) {
    throw new Error('Invalid Revenue Attribution currency status');
  }

  if (!Array.isArray(value.currency_codes) || !value.currency_codes.every(
    (item) => typeof item === 'string' && /^[A-Z]{3}$/.test(item)
  )) {
    throw new Error('Invalid Revenue Attribution currency codes');
  }
  const currencyCodes = value.currency_codes as string[];
  if (new Set(currencyCodes).size !== currencyCodes.length) {
    throw new Error('Duplicate Revenue Attribution currency codes');
  }

  if (!Array.isArray(value.currency_totals)) throw new Error('Invalid Revenue Attribution currency totals');
  const currencyTotals: RevenueCurrencyTotal[] = value.currency_totals.map((item, index) => {
    if (!isRecord(item) || typeof item.currency_supported !== 'boolean') {
      throw new Error(`Invalid Revenue Attribution currency row ${index}`);
    }
    const currency = nullableCurrency(item.currency, `currency row ${index}`);
    const conversions = count(item.conversions, `currency row ${index} conversions`);
    const trackedConversions = count(item.tracked_conversions, `currency row ${index} tracked conversions`);
    if (trackedConversions > conversions) throw new Error(`Invalid Revenue Attribution tracked count in row ${index}`);
    const revenue = amount(item.revenue, `currency row ${index} revenue`);
    const attributedRevenue = amount(item.attributed_revenue, `currency row ${index} attributed revenue`);
    const unattributedRevenue = amount(item.unattributed_revenue, `currency row ${index} unattributed revenue`);
    supportedMoney(item.currency_supported, currency, [revenue, attributedRevenue, unattributedRevenue], `currency row ${index}`);
    return {
      currency,
      currency_supported: item.currency_supported,
      conversions,
      tracked_conversions: trackedConversions,
      revenue,
      attributed_revenue: attributedRevenue,
      unattributed_revenue: unattributedRevenue,
    };
  });

  if (!isRecord(value.totals)) throw new Error('Invalid Revenue Attribution totals');
  const conversions = count(value.totals.conversions, 'conversions');
  const trackedConversions = count(value.totals.tracked_conversions, 'tracked conversions');
  if (trackedConversions > conversions) throw new Error('Tracked conversions exceed total conversions');
  const currency = nullableCurrency(value.totals.currency, 'currency');
  const revenue = amount(value.totals.revenue, 'revenue');
  const attributedRevenue = amount(value.totals.attributed_revenue, 'attributed revenue');
  const unattributedRevenue = amount(value.totals.unattributed_revenue, 'unattributed revenue');

  const expectedConversions = currencyTotals.reduce((sum, item) => sum + item.conversions, 0);
  const expectedTracked = currencyTotals.reduce((sum, item) => sum + item.tracked_conversions, 0);
  if (conversions !== expectedConversions || trackedConversions !== expectedTracked) {
    throw new Error('Revenue Attribution currency counts do not match totals');
  }

  const status = currencyStatus as RevenueCurrencyStatus;
  if (status === 'none') {
    if (currencyTotals.length !== 0 || conversions !== 0 || currency !== null || revenue !== 0 || attributedRevenue !== 0 || unattributedRevenue !== 0) {
      throw new Error('Invalid empty Revenue Attribution totals');
    }
  } else if (status === 'single') {
    if (currencyTotals.length !== 1 || !currencyTotals[0].currency_supported || currency !== currencyTotals[0].currency) {
      throw new Error('Invalid single-currency Revenue Attribution totals');
    }
  } else {
    if (status === 'mixed' && currencyTotals.length < 2) throw new Error('Invalid mixed-currency Revenue Attribution totals');
    if (status === 'unsupported' && (currencyTotals.length !== 1 || currencyTotals[0].currency_supported)) {
      throw new Error('Invalid unsupported-currency Revenue Attribution totals');
    }
    if (currency !== null || revenue !== null || attributedRevenue !== null || unattributedRevenue !== null) {
      throw new Error('Combined Revenue Attribution totals must be withheld');
    }
  }

  const expectedCurrencyCodes = currencyTotals
    .filter((item) => item.currency_supported && item.currency !== null)
    .map((item) => item.currency as string)
    .sort();
  if (expectedCurrencyCodes.join(',') !== [...currencyCodes].sort().join(',')) {
    throw new Error('Revenue Attribution currency codes do not match report buckets');
  }

  if (!Array.isArray(value.channels)) throw new Error('Invalid Revenue Attribution channels');
  const channels: RevenueChannel[] = value.channels.map((item, index) => {
    if (!isRecord(item) || typeof item.channel !== 'string' || typeof item.currency_supported !== 'boolean') {
      throw new Error(`Invalid Revenue Attribution channel ${index}`);
    }
    const channelCurrency = nullableCurrency(item.currency, `channel ${index} currency`);
    const attributed = amount(item.attributed_revenue, `channel ${index} attributed revenue`);
    supportedMoney(item.currency_supported, channelCurrency, [attributed], `channel ${index}`);
    return {
      channel: item.channel,
      currency: channelCurrency,
      currency_supported: item.currency_supported,
      attributed_revenue: attributed,
    };
  });

  return {
    window_days: windowDays,
    persistence_mode: persistenceMode,
    currency_status: status,
    currency_codes: [...currencyCodes],
    currency_totals: currencyTotals,
    totals: {
      conversions,
      tracked_conversions: trackedConversions,
      currency,
      revenue,
      attributed_revenue: attributedRevenue,
      unattributed_revenue: unattributedRevenue,
    },
    channels,
  };
}
