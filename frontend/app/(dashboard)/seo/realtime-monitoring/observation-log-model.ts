export const SEARCH_SOURCES = ['Google', 'Bing', 'Other'] as const;
export const AI_SURFACES = ['not-checked', 'none-observed', 'google-ai-overview', 'chatgpt', 'perplexity', 'other-ai-surface'] as const;

export type SearchSource = (typeof SEARCH_SOURCES)[number];
export type AiSurface = (typeof AI_SURFACES)[number];

export type SearchObservation = {
  id: string;
  query: string;
  source: SearchSource;
  observedAt: string;
  position: number | null;
  aiSurface: AiSurface;
};

export type SearchObservationInput = {
  query: string;
  source: string;
  observedAtLocal: string;
  position: string;
  aiSurface: string;
};

export type ObservationTrend = {
  key: string;
  query: string;
  source: SearchSource;
  observationCount: number;
  latest: SearchObservation;
  previous: SearchObservation | null;
  positionsImprovedBy: number | null;
};

export function createSearchObservation(input: SearchObservationInput, id: string): SearchObservation {
  const query = input.query.trim();
  if (!query) throw new Error('Enter the search query that was observed.');
  if (query.length > 300) throw new Error('Search queries must be 300 characters or fewer.');
  if (!(SEARCH_SOURCES as readonly string[]).includes(input.source)) throw new Error('Choose the search source for this observation.');
  if (!input.observedAtLocal || !Number.isFinite(new Date(input.observedAtLocal).getTime())) {
    throw new Error('Enter a valid date and time for the observation.');
  }
  if (!(AI_SURFACES as readonly string[]).includes(input.aiSurface)) throw new Error('Choose an AI-surface observation status, including “Not checked” if unknown.');
  const positionText = input.position.trim();
  const position = positionText === '' ? null : Number(positionText);
  if (position !== null && (!Number.isFinite(position) || position < 1 || position > 1000)) {
    throw new Error('Rank position must be a number from 1 to 1000, or left blank.');
  }
  return {
    id,
    query,
    source: input.source as SearchSource,
    observedAt: new Date(input.observedAtLocal).toISOString(),
    position,
    aiSurface: input.aiSurface as AiSurface,
  };
}

export function summarizeObservationTrends(observations: SearchObservation[]): ObservationTrend[] {
  const groups = new Map<string, SearchObservation[]>();
  for (const observation of observations) {
    const key = `${observation.source.toLowerCase()}|${observation.query.trim().toLowerCase()}`;
    const current = groups.get(key) ?? [];
    current.push(observation);
    groups.set(key, current);
  }
  return Array.from(groups, ([key, entries]) => {
    const sorted = [...entries].sort((left, right) => Date.parse(left.observedAt) - Date.parse(right.observedAt));
    const latest = sorted[sorted.length - 1];
    const previous = sorted.length > 1 ? sorted[sorted.length - 2] : null;
    return {
      key,
      query: latest.query,
      source: latest.source,
      observationCount: sorted.length,
      latest,
      previous,
      positionsImprovedBy: previous && latest.position !== null && previous.position !== null
        ? previous.position - latest.position
        : null,
    };
  }).sort((left, right) => Date.parse(right.latest.observedAt) - Date.parse(left.latest.observedAt));
}

export function aiSurfaceLabel(surface: AiSurface): string {
  switch (surface) {
    case 'not-checked': return 'Not checked';
    case 'none-observed': return 'No AI answer observed';
    case 'google-ai-overview': return 'Google AI Overview observed';
    case 'chatgpt': return 'ChatGPT answer observed';
    case 'perplexity': return 'Perplexity answer observed';
    case 'other-ai-surface': return 'Other AI surface observed';
  }
}

function csvCell(value: string): string {
  const safe = /^[\s]*[=+@-]/.test(value) ? `'${value}` : value;
  return `"${safe.replaceAll('"', '""')}"`;
}

export function searchObservationsCsv(observations: SearchObservation[]): string {
  const rows = [
    ['Query', 'Search source', 'Observed at (UTC)', 'Rank position', 'AI surface status'],
    ...observations.map((observation) => [
      observation.query,
      observation.source,
      observation.observedAt,
      observation.position === null ? '' : String(observation.position),
      aiSurfaceLabel(observation.aiSurface),
    ]),
  ];
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}
