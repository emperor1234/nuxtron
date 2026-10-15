import { describe, expect, it } from 'vitest';
import { getFallbackModulesResponse } from './module-registry-fallback';

describe('SEO module registry fallback', () => {
  it('maps Analytics & history metadata to the saved analysis history route', () => {
    const response = getFallbackModulesResponse();
    const history = response.modules.find((module) => module.key === 'analytics-reporting-intelligence');
    expect(history).toMatchObject({
      display_name: 'SEO Analysis History',
      group: 'Analytics & history',
      route_path: '/seo/history',
      implemented: true,
    });
  });

  it('preserves unavailable connector readiness and an accurate implemented count', () => {
    const response = getFallbackModulesResponse();
    const integrations = response.modules.find((module) => module.key === 'integrations-automation-layer');
    expect(integrations).toMatchObject({
      route_path: '/seo/integrations-automation',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
    });
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
    expect(response.implemented).toBeLessThan(response.total);
  });

  it('keeps Keyword Data Review local-only when the module API is unavailable', () => {
    const response = getFallbackModulesResponse();
    const keywordReview = response.modules.find((module) => module.key === 'keyword-research-engine');
    expect(keywordReview).toMatchObject({
      display_name: 'Keyword Data Review',
      group: 'Research & visibility',
      route_path: '/seo/keywords',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
      database_ready: false,
    });
    expect(keywordReview?.description).toMatch(/browser-local review of user-provided keyword exports/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('does not restore unsupported Trust & Risk scoring from fallback metadata', () => {
    const response = getFallbackModulesResponse();
    const governance = response.modules.find((module) => module.key === 'trust-risk-governance');
    expect(governance).toMatchObject({
      display_name: 'Trust & Risk Governance',
      route_path: '/seo/trust-risk-governance',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
    });
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('keeps Agency Workspace Health unavailable without verified workspace evidence', () => {
    const response = getFallbackModulesResponse();
    const agency = response.modules.find((module) => module.key === 'agency-multi-tenant-platform');
    expect(agency).toMatchObject({
      display_name: 'Agency Workspace Health',
      route_path: '/seo/agency-platform',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
    });
    expect(agency?.description).toMatch(/health scores are unavailable/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('keeps SEO Competitor Research unavailable without verified search evidence', () => {
    const response = getFallbackModulesResponse();
    const competitor = response.modules.find((module) => module.key === 'competitor-intelligence-engine');
    expect(competitor).toMatchObject({
      display_name: 'SEO Competitor Research',
      group: 'Search Intelligence',
      route_path: '/seo/competitor',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
    });
    expect(competitor?.description).toMatch(/competitor metrics are unavailable/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('keeps competitor activity monitoring unavailable without durable sourced collection', () => {
    const response = getFallbackModulesResponse();
    const monitor = response.modules.find((module) => module.key === 'competitor-activity-monitor');
    expect(monitor).toMatchObject({
      display_name: 'Competitor Activity Monitor',
      group: 'Search Intelligence',
      route_path: '/seo/competitor-monitoring',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
      database_ready: false,
    });
    expect(monitor?.description).toMatch(/no sample events or alerts are generated/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('labels corpus search as a local preview while connected semantic retrieval remains unavailable', () => {
    const response = getFallbackModulesResponse();
    const corpus = response.modules.find((module) => module.key === 'rag-site-search-engine');
    expect(corpus).toMatchObject({
      display_name: 'Corpus Search Preview',
      group: 'Search Intelligence',
      route_path: '/seo/rag-search',
      implemented: true,
      backend_ready: false,
      frontend_ready: true,
      database_ready: false,
    });
    expect(corpus?.description).toMatch(/browser-local keyword matching/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('keeps Programmatic SEO local-only until evidence and publishing controls exist', () => {
    const response = getFallbackModulesResponse();
    const programmatic = response.modules.find((module) => module.key === 'programmatic-seo-engine');
    expect(programmatic).toMatchObject({
      display_name: 'Programmatic SEO Draft Preview',
      route_path: '/seo/programmatic',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
      database_ready: false,
    });
    expect(programmatic?.description).toMatch(/search metrics, persistence, and publishing are unavailable/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('keeps International SEO limited to the browser-local hreflang review', () => {
    const response = getFallbackModulesResponse();
    const international = response.modules.find((module) => module.key === 'international-multilingual-seo');
    expect(international).toMatchObject({
      display_name: 'Hreflang & Locale Review',
      group: 'International SEO',
      route_path: '/seo/international-multilingual',
      implemented: false,
      backend_ready: false,
      frontend_ready: true,
      database_ready: false,
    });
    expect(international?.description).toMatch(/reciprocal-link.*canonical verification are unavailable/i);
    expect(response.implemented).toBe(response.modules.filter((module) => module.implemented).length);
  });

  it('does not advertise the retired, non-durable Client Portal', () => {
    const response = getFallbackModulesResponse();
    expect(response.modules.some((module) => module.key === 'client-portal')).toBe(false);
  });

  it('describes Revenue Attribution as a recorded-event report rather than an estimate', () => {
    const response = getFallbackModulesResponse();
    const attribution = response.modules.find((module) => module.key === 'revenue-attribution-intelligence');
    expect(attribution).toMatchObject({
      display_name: 'Revenue Attribution',
      route_path: '/seo/revenue-attribution',
      implemented: true,
    });
    expect(attribution?.description).toMatch(/recorded conversions and tracked touchpoints/i);
    expect(attribution?.description).toMatch(/no causal lift is estimated/i);
  });
});
