import type { CSSProperties } from 'react';

type TierTone = {
  bg: string;
  color: string;
  border: string;
};

type PillSize = 'xs' | 'sm';

type PillTone = {
  bg: string;
  color: string;
  border: string;
};

type PillOptions = {
  uppercase?: boolean;
};

export function getTierTone(tier: string | undefined): TierTone {
  if (tier === 'Core') return { bg: 'rgba(34,197,94,0.12)', color: '#15803d', border: 'rgba(34,197,94,0.35)' };
  if (tier === 'AI') return { bg: 'rgba(56,189,248,0.14)', color: '#0369a1', border: 'rgba(56,189,248,0.35)' };
  if (tier === 'New') return { bg: 'rgba(245,158,11,0.14)', color: '#b45309', border: 'rgba(245,158,11,0.35)' };
  if (tier === 'Experiment') return { bg: 'rgba(13,148,136,0.12)', color: '#0f766e', border: 'rgba(13,148,136,0.35)' };
  if (tier === 'SaaS') return { bg: 'rgba(236,72,153,0.12)', color: '#be185d', border: 'rgba(236,72,153,0.35)' };
  return { bg: 'rgba(148,163,184,0.14)', color: '#475569', border: 'rgba(148,163,184,0.4)' };
}

export function getTierBadgeStyle(tier: string | undefined): CSSProperties {
  const tone = getTierTone(tier);
  return getPillStyle(tone, 'xs', { uppercase: true });
}

export function getPillStyle(tone: PillTone, size: PillSize = 'xs', options: PillOptions = {}): CSSProperties {
  const isSmall = size === 'xs';
  return {
    fontSize: isSmall ? 10 : 11,
    fontWeight: 800,
    borderRadius: 999,
    padding: isSmall ? '2px 8px' : '6px 10px',
    background: tone.bg,
    color: tone.color,
    border: `1px solid ${tone.border}`,
    textTransform: options.uppercase ? 'uppercase' : 'none',
    letterSpacing: isSmall ? '0.08em' : '0.06em',
  };
}
