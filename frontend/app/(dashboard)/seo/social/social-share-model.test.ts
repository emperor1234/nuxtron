import { describe, expect, it } from 'vitest';
import { buildSocialShareReport, type SocialShareInput } from './social-share-model';

const valid: SocialShareInput = {
  channels: ['x', 'linkedin'],
  openGraphTitle: 'Product overview',
  openGraphDescription: 'A description written by the customer.',
  canonicalUrl: 'https://example.com/product',
  openGraphUrl: 'https://example.com/product',
  openGraphImage: '',
  twitterTitle: 'X title override',
  twitterDescription: '',
  twitterImage: '',
  twitterCardType: 'summary_large_image',
};

describe('buildSocialShareReport', () => {
  it('requires a selected channel and complete HTTP(S) metadata', () => {
    expect(() => buildSocialShareReport({ ...valid, channels: [] })).toThrow(/select at least one channel/i);
    expect(() => buildSocialShareReport({ ...valid, canonicalUrl: '' })).toThrow(/canonical url is required/i);
    expect(() => buildSocialShareReport({ ...valid, openGraphUrl: 'javascript:alert(1)' })).toThrow(/HTTP or HTTPS/i);
    expect(() => buildSocialShareReport({ ...valid, openGraphImage: 'https://user:secret@example.com/a.png' })).toThrow(/credentials/i);
    expect(() => buildSocialShareReport({ ...valid, channels: ['x'], twitterCardType: '' })).toThrow(/card type/i);
  });

  it('builds channel-specific previews only from entered metadata and compares supplied URLs', () => {
    const report = buildSocialShareReport(valid);
    expect(report.canonicalAlignment).toBe('match');
    expect(report.previews[0]).toMatchObject({
      channel: 'x',
      title: 'X title override',
      description: 'A description written by the customer.',
      imageUrl: null,
      titleSource: 'Twitter title override',
      imageSource: 'No image URL supplied',
      cardType: 'summary_large_image',
    });
    expect(report.previews[1]).toMatchObject({
      channel: 'linkedin',
      title: 'Product overview',
      pageUrl: 'https://example.com/product',
      titleSource: 'Open Graph title',
      cardType: null,
    });
  });

  it('labels missing or mismatched Open Graph URLs without asserting a page was inspected', () => {
    expect(buildSocialShareReport({ ...valid, channels: ['facebook'], openGraphUrl: '' }).canonicalAlignment).toBe('not-provided');
    expect(buildSocialShareReport({ ...valid, channels: ['facebook'], openGraphUrl: 'https://example.com/other' }).canonicalAlignment).toBe('mismatch');
  });
});
