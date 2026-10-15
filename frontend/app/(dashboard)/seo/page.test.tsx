import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { MENUS } from '../_shell/nav';
import SeoHomePage from './page';
import { getSeoShortcuts, SEO_SHORTCUT_LABELS } from './seo-home-model';

afterEach(cleanup);

describe('SEO workflow hub', () => {
  it('exposes every SEO sidebar destination exactly once', () => {
    render(<SeoHomePage />);
    const actual = screen.getAllByTestId('seo-tool-link').map((link) => link.getAttribute('href'));
    const expected = (MENUS.seo?.groups ?? []).flatMap((group) => group.items.map((item) => item.href));
    expect(actual).toEqual(expected);
    expect(new Set(actual).size).toBe(actual.length);
  });

  it('keeps all start shortcuts matched to the SEO menu and unique', () => {
    render(<SeoHomePage />);
    const shortcuts = getSeoShortcuts();
    expect(shortcuts.map((item) => item.label)).toEqual([...SEO_SHORTCUT_LABELS]);
    expect(shortcuts.map((item) => item.href)).toEqual(
      screen.getAllByTestId('seo-shortcut').map((link) => link.getAttribute('href')),
    );
    expect(new Set(shortcuts.map((item) => item.href)).size).toBe(4);
    expect(shortcuts.some((item) => item.label === 'Rank Position Review')).toBe(true);
    expect(shortcuts.some((item) => item.label === 'Performance Audit')).toBe(false);
    expect(shortcuts.some((item) => item.label === 'Site Audit')).toBe(false);
  });
});
