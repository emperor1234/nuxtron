import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AgencyPlatformPage from './page';

describe('Agency Workspace Health page', () => {
  it('clearly reports missing evidence without sample inputs, health scores, or admin controls', () => {
    const { container } = render(<AgencyPlatformPage />);

    expect(screen.getByRole('heading', { name: 'Agency Workspace Health' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/cannot currently verify/i);
    expect(screen.getByText(/no governance or workspace-health scores/i)).toBeTruthy();
    expect(screen.getByRole('list').textContent).toMatch(/authorized workspace inventory/i);
    expect(screen.getByText(/separate service/i)).toBeTruthy();
    expect(container.querySelector('form, input, textarea, button')).toBeNull();
    expect(container.textContent).not.toMatch(/acme|northstar|velocity|platform health|%/i);
  });
});
