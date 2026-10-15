import { MENUS, type FlyoutItem } from '../_shell/nav';

export const SEO_SHORTCUT_LABELS = [
  'Rank Position Review',
  'Traffic Analytics',
  'AI Visibility Dashboard',
  'Domain Overview',
] as const;

export function getSeoShortcuts(): FlyoutItem[] {
  const items = new Map((MENUS.seo?.groups ?? []).flatMap((group) => group.items.map((item) => [item.label, item] as const)));
  const shortcuts = SEO_SHORTCUT_LABELS.map((label) => {
    const item = items.get(label);
    if (!item) throw new Error(`SEO start shortcut does not match a menu item: ${label}`);
    return item;
  });
  if (new Set(shortcuts.map((item) => item.href)).size !== shortcuts.length) {
    throw new Error('SEO start shortcuts must point to unique destinations.');
  }
  return shortcuts;
}
