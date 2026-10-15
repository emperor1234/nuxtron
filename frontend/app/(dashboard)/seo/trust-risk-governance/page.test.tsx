import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TrustRiskGovernancePage from './page';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Trust & Risk Governance page', () => {
  it('does not invent risk posture or collect sensitive data while evidence is unavailable', () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    render(<TrustRiskGovernancePage />);

    expect(screen.getByRole('heading', { name: 'No evidence-backed assessment' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toMatch(/assessment unavailable/i);
    expect(screen.getByText(/does not produce governance scores, compliance percentages, risk ratings/i)).toBeTruthy();
    expect(screen.getByText(/does not collect domain, control, incident, or note inputs/i)).toBeTruthy();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});
