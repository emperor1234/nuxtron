import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { SocialStudioHeader } from './social-studio-header';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('SocialStudioHeader', () => {
  it('shows unavailable markers instead of reporting unknown balances as zero', () => {
    const { container } = render(
      <SocialStudioHeader
        credits={null}
        pendingTopups={null}
        walletUsd={null}
        generatedCount={0}
      />,
    );

    expect(Array.from(container.querySelectorAll('dd'), (item) => item.textContent)).toEqual([
      '—',
      '—',
      '—',
      '0',
    ]);
  });

  it('preserves real zero balances returned by the service', () => {
    const { container } = render(
      <SocialStudioHeader
        credits={0}
        pendingTopups={0}
        walletUsd={0}
        generatedCount={0}
      />,
    );

    expect(Array.from(container.querySelectorAll('dd'), (item) => item.textContent)).toEqual([
      '0',
      '0',
      '$0.00',
      '0',
    ]);
  });
});
