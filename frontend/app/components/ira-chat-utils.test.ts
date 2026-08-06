import { describe, expect, it } from 'vitest';

import {
  buildIraChatContext,
  extractIraBackendMeta,
  extractIraBackendReply,
  getBackendErrorMessage,
  resolveIraPreferredProvider,
} from './ira-chat-utils';

describe('ira-chat-utils', () => {
  it('extracts backend reply when payload is valid', () => {
    const reply = extractIraBackendReply({
      ira: {
        response: 'Autonomous plan ready',
      },
    });

    expect(reply).toBe('Autonomous plan ready');
  });

  it('returns null when backend payload is incomplete', () => {
    expect(extractIraBackendReply({})).toBeNull();
    expect(extractIraBackendReply({ ira: {} })).toBeNull();
    expect(extractIraBackendReply({ ira: { response: '' } })).toBeNull();
    expect(extractIraBackendReply({ ira: { response: 42 } })).toBeNull();
  });

  it('extracts backend metadata when payload includes IRA analysis', () => {
    const meta = extractIraBackendMeta({
      ira: {
        confidence: 0.91,
        intent: 'campaign_planning',
        domain: 'marketing',
        risk_assessment: {
          risk_level: 'low',
        },
        action_plan: {
          recommended_actions: [{ label: 'Create IRA autonomous run plan' }],
        },
        knowledge_hits: [{ title: 'Q2 campaign brief' }],
      },
    });

    expect(meta).toEqual({
      confidence: 0.91,
      intent: 'campaign_planning',
      domain: 'marketing',
      riskLevel: 'low',
      actionLabels: ['Create IRA autonomous run plan'],
      knowledgeHits: ['Q2 campaign brief'],
      providerRequested: undefined,
      providerUsed: undefined,
      providerModel: undefined,
      providerStatus: undefined,
    });
  });

  it('extracts provider metadata when backend reports routing outcome', () => {
    const meta = extractIraBackendMeta({
      ira: {
        provider_requested: 'openai',
        provider_used: 'openai',
        provider_model: 'gpt-4.1-mini',
        provider_status: 'external_ok',
      },
    });

    expect(meta).toEqual({
      confidence: undefined,
      intent: undefined,
      domain: undefined,
      riskLevel: undefined,
      actionLabels: [],
      knowledgeHits: [],
      providerRequested: 'openai',
      providerUsed: 'openai',
      providerModel: 'gpt-4.1-mini',
      providerStatus: 'external_ok',
    });
  });

  it('returns null when backend metadata is absent', () => {
    expect(extractIraBackendMeta({})).toBeNull();
    expect(extractIraBackendMeta({ ira: { response: 'plain text only' } })).toBeNull();
  });

  it('resolves custom provider preference without closing future provider names', () => {
    expect(resolveIraPreferredProvider({ providerPreference: 'openai' })).toBe('openai');
    expect(resolveIraPreferredProvider({ providerPreference: 'anthropic' })).toBe('anthropic');
    expect(resolveIraPreferredProvider({ providerPreference: 'custom', customProvider: 'claude-enterprise' })).toBe(
      'claude-enterprise'
    );
  });

  it('builds chat context with provider routing hints', () => {
    const context = buildIraChatContext(
      { source: 'ira-control-center' },
      { providerPreference: 'anthropic', customProvider: '' }
    );

    expect(context).toEqual({
      source: 'ira-control-center',
      llm_routing: {
        preferred_provider: 'anthropic',
        requested_external_provider: true,
        candidate_providers: ['anthropic'],
        custom_provider_label: '',
      },
    });
  });

  it('formats backend error message from error object', () => {
    const text = getBackendErrorMessage(new Error('gateway timeout'));
    expect(text).toContain('IRA backend unavailable');
    expect(text).toContain('gateway timeout');
  });

  it('falls back to generic message when error shape is unknown', () => {
    const text = getBackendErrorMessage({ cause: 'x' });
    expect(text).toContain('(request failed)');
  });
});
