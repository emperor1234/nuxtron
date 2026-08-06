import { describe, expect, it } from 'vitest';

import { FINAL_HYBRID_SUMMARY, OPEN_SOURCE_HYBRID_STACKS } from './hybrid-stacks';

describe('hybrid stack architecture definitions', () => {
  it('keeps all configured 100/100 stack categories', () => {
    expect(OPEN_SOURCE_HYBRID_STACKS).toHaveLength(50);

    const ids = OPEN_SOURCE_HYBRID_STACKS.map((stack) => stack.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        'seo-ai',
        'geo',
        'aio-2',
        'llmo',
        'sageo',
        'vso',
        'sxo',
        'gxo',
        'entity-first-seo',
        'peao',
        'msvo',
        'daeo',
        'cxao',
        'eeat-suite',
        'autonomous-agent-engine',
        'programmatic-seo-engine',
        'seo-ab-testing',
        'ecommerce-seo-suite',
        'autonomous-link-building-system',
        'international-multilingual-seo',
        'site-migration-seo-manager',
        'video-seo-module',
        'local-seo-suite',
        'news-seo-google-discover',
        'analytics-reporting-intelligence',
        'agency-multi-tenant-platform',
        'integrations-automation-layer',
        'revenue-attribution-intelligence',
        'growth-playbooks-automation',
        'trust-risk-governance',
        'multi-channel-activation-loop',
        'realtime-search-ai-monitoring',
        'ai-technical-seo-engine',
        'content-quality-hallucination-auditor',
        'knowledge-graph-management',
        'ai-internal-linking-engine',
        'crawl-budget-optimizer',
        'ai-schema-engine',
        'ux-conversion-optimizer',
        'rag-site-search-engine',
        'competitor-intelligence-engine',
        'topical-map-silo-builder',
        'log-file-analysis-engine',
        'review-reputation-engine',
        'brand-voice-style-engine',
        'accessibility-optimizer',
        'image-media-seo-engine',
        'social-seo-distribution',
        'landing-page-builder',
        'security-seo-health-monitor',
      ])
    );

    for (const stack of OPEN_SOURCE_HYBRID_STACKS) {
      expect(stack.hybridScore).toBe('100/100 (100%)');
      // Some modules are purely open-source and have no freeTools — openSourceTools covers them
      expect(stack.freeTools.length + stack.openSourceTools.length).toBeGreaterThan(0);
      expect(stack.openSourceTools.length).toBeGreaterThan(0);
      expect(stack.outcomes.length).toBeGreaterThan(0);
    }
  });

  it('enforces valid score ranges for all listed tools', () => {
    for (const stack of OPEN_SOURCE_HYBRID_STACKS) {
      for (const tool of [...stack.freeTools, ...stack.openSourceTools]) {
        expect(tool.score).toBeGreaterThan(0);
        expect(tool.score).toBeLessThanOrEqual(100);
      }
    }
  });

  it('includes required tools in each hybrid stack', () => {
    const seoAi = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'seo-ai');
    const geo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'geo');
    const aio2 = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'aio-2');
    const llmo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'llmo');
    const sageo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'sageo');
    const vso = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'vso');
    const sxo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'sxo');
    const gxo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'gxo');
    const entityFirstSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'entity-first-seo');
    const peao = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'peao');
    const msvo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'msvo');
    const daeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'daeo');
    const cxao = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'cxao');
    const eeat = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'eeat-suite');
    const autonomousAgent = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'autonomous-agent-engine');
    const programmaticSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'programmatic-seo-engine');
    const seoAbTesting = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'seo-ab-testing');
    const ecommerceSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'ecommerce-seo-suite');
    const autonomousLinkBuilding = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'autonomous-link-building-system');
    const internationalMultilingualSeo = OPEN_SOURCE_HYBRID_STACKS.find(
      (s) => s.id === 'international-multilingual-seo'
    );
    const siteMigrationSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'site-migration-seo-manager');
    const videoSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'video-seo-module');
    const localSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'local-seo-suite');
    const newsSeo = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'news-seo-google-discover');
    const analyticsReporting = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'analytics-reporting-intelligence');
    const agencyMultiTenant = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'agency-multi-tenant-platform');
    const integrationsAutomation = OPEN_SOURCE_HYBRID_STACKS.find((s) => s.id === 'integrations-automation-layer');

    expect(seoAi?.hybridStack).toContain('SerpBear');
    expect(seoAi?.hybridStack).toContain('SEO Panel');

    expect(geo?.hybridStack).toContain('OpenLens');
    expect(geo?.hybridStack).toContain('LlamaIndex');

    expect(aio2?.hybridStack).toContain('AutoGen');
    expect(aio2?.hybridStack).toContain('CrewAI');

    expect(llmo?.hybridStack).toContain('AutoGen');
    expect(llmo?.hybridStack).toContain('LangChain');

    expect(sageo?.hybridStack).toContain('SerpBear');
    expect(sageo?.hybridStack).toContain('BERTopic');

    expect(vso?.hybridStack).toContain('JSON-LD');
    expect(vso?.hybridStack).toContain('Haystack');

    expect(sxo?.hybridStack).toContain('Lighthouse');
    expect(sxo?.hybridStack).toContain('PostHog');

    expect(gxo?.hybridStack).toContain('AutoGen');
    expect(gxo?.hybridStack).toContain('PostgreSQL/pgvector');

    expect(entityFirstSeo?.hybridStack).toContain('Neo4j');
    expect(entityFirstSeo?.hybridStack).toContain('JSON-LD');

    expect(peao?.hybridStack).toContain('Prophet/scikit-learn');
    expect(peao?.hybridStack).toContain('Grafana');

    expect(msvo?.hybridStack).toContain('OpenLens');
    expect(msvo?.hybridStack).toContain('PostgreSQL');

    expect(daeo?.hybridStack).toContain('YaCy/OpenSearch');
    expect(daeo?.hybridStack).toContain('IPFS/MinIO');

    expect(cxao?.hybridStack).toContain('Rasa/Botpress');
    expect(cxao?.hybridStack).toContain('LangChain');

    expect(eeat?.hybridStack).toContain('Haystack');
    expect(eeat?.hybridStack).toContain('OpenSearch');

    expect(autonomousAgent?.hybridStack).toContain('AutoGen');
    expect(autonomousAgent?.hybridStack).toContain('Celery');

    expect(programmaticSeo?.hybridStack).toContain('Next.js/Astro');
    expect(programmaticSeo?.hybridStack).toContain('OpenSearch');

    expect(seoAbTesting?.hybridStack).toContain('SciPy');
    expect(seoAbTesting?.hybridStack).toContain('Unleash');

    expect(ecommerceSeo?.hybridStack).toContain('OpenSearch');
    expect(ecommerceSeo?.hybridStack).toContain('LlamaIndex');

    expect(autonomousLinkBuilding?.hybridStack).toContain('Scrapy');
    expect(autonomousLinkBuilding?.hybridStack).toContain('SEO Panel');

    expect(internationalMultilingualSeo?.hybridStack).toContain('langdetect');
    expect(internationalMultilingualSeo?.hybridStack).toContain('GSC/Bing');

    expect(siteMigrationSeo?.hybridStack).toContain('ScreamingFrog/SiteCrawler');
    expect(siteMigrationSeo?.hybridStack).toContain('Python scripts');

    expect(videoSeo?.hybridStack).toContain('FFmpeg');
    expect(videoSeo?.hybridStack).toContain('Whisper');

    expect(localSeo?.hybridStack).toContain('OpenStreetMap');
    expect(localSeo?.hybridStack).toContain('LlamaIndex');

    expect(newsSeo?.hybridStack).toContain('RSS/Atom');
    expect(newsSeo?.hybridStack).toContain('BERTopic');

    expect(analyticsReporting?.hybridStack).toContain('PostgreSQL');
    expect(analyticsReporting?.hybridStack).toContain('Prophet');

    expect(agencyMultiTenant?.hybridStack).toContain('tenant_id + RLS');
    expect(agencyMultiTenant?.hybridStack).toContain('Keycloak/Ory');

    expect(integrationsAutomation?.hybridStack).toContain('Prefect/Airflow');
    expect(integrationsAutomation?.hybridStack).toContain('Prometheus');
  });

  it('keeps final summary aligned with stack categories', () => {
    expect(FINAL_HYBRID_SUMMARY).toHaveLength(50);

    const summaryCategories = FINAL_HYBRID_SUMMARY.map((row) => row.category);
    expect(summaryCategories).toEqual(
      expect.arrayContaining([
        'SEO-AI',
        'GEO',
        'AIO-2',
        'LLMO',
        'SAGEO',
        'VSO',
        'SXO',
        'GXO',
        'ENTITY-FIRST SEO',
        'PEAO',
        'MSVO',
        'DAEO',
        'CXAO',
        'E-E-A-T',
        'AUTONOMOUS AGENT ENGINE',
        'PROGRAMMATIC SEO',
        'SEO A/B TESTING',
        'ECOMMERCE SEO',
        'AUTONOMOUS LINK BUILDING',
        'INTERNATIONAL & MULTILINGUAL SEO',
        'SITE MIGRATION SEO',
        'VIDEO SEO',
        'LOCAL SEO',
        'NEWS SEO & GOOGLE DISCOVER',
        'ANALYTICS, REPORTING & INTELLIGENCE',
        'AGENCY & MULTI-TENANT PLATFORM',
        'INTEGRATIONS & AUTOMATION LAYER',
      ])
    );

    for (const row of FINAL_HYBRID_SUMMARY) {
      expect(row.score).toBe('100/100');
      expect(row.stack.length).toBeGreaterThan(0);
    }
  });
});
