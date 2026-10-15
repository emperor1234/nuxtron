export type StripeHost = 'checkout.stripe.com' | 'billing.stripe.com';

export function requireStripeUrl(value: string, hostname: StripeHost): string {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error('The billing provider returned an invalid destination.');
  }

  if (
    url.protocol !== 'https:' ||
    url.hostname !== hostname ||
    url.username ||
    url.password
  ) {
    throw new Error('The billing provider returned an unsafe destination.');
  }

  return url.toString();
}
