import { describe, expect, it } from 'vitest';
import { requireStripeUrl } from './stripe-url';

describe('requireStripeUrl', () => {
  it('accepts the exact Stripe checkout host for payments', () => {
    expect(requireStripeUrl('https://checkout.stripe.com/c/pay/cs_test', 'checkout.stripe.com'))
      .toBe('https://checkout.stripe.com/c/pay/cs_test');
  });

  it('accepts the exact Stripe billing portal host for subscription management', () => {
    expect(requireStripeUrl('https://billing.stripe.com/p/session_test', 'billing.stripe.com'))
      .toBe('https://billing.stripe.com/p/session_test');
  });

  it.each([
    'http://checkout.stripe.com/pay',
    'https://checkout.stripe.com.attacker.invalid/pay',
    'https://checkout.stripe.com@attacker.invalid/pay',
    'https://user:password@checkout.stripe.com/pay',
    '/billing/checkout',
    'not a URL',
  ])('rejects unsafe destination %s', (value) => {
    expect(() => requireStripeUrl(value, 'checkout.stripe.com')).toThrow(/destination/);
  });

  it('does not allow a checkout host where the portal host is required', () => {
    expect(() => requireStripeUrl('https://checkout.stripe.com/pay', 'billing.stripe.com')).toThrow(/unsafe/);
  });
});
