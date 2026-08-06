#!/usr/bin/env node
/**
 * lighten-tailwind.mjs
 * Enforce the light design system on Tailwind-classed route pages:
 *   1. Off-brand accent utilities (blue/indigo/cyan/sky/violet/purple/slate-700)
 *      -> single brand token  (bg/text/border/ring + hover).
 *   2. Faint light-gray text (slate/gray-100..400) -> var(--muted).
 *   3. Invisible white text (text-white with no background sibling) -> var(--text).
 *      White text that sits on a colored/brand/dark background is preserved.
 *
 * Semantic colors (green/emerald/red/rose/amber/yellow/orange) are left alone.
 * Run from `frontend`:  node scripts/lighten-tailwind.mjs "app/(dashboard)"
 */
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2] || 'app/(dashboard)';
const ACCENT = '(?:blue|indigo|sky|cyan|violet|purple)';

function transform(src) {
  let s = src;

  // --- Brand-ify accent backgrounds (incl. dark slate-700 buttons).
  s = s.replace(new RegExp(`\\bbg-${ACCENT}-(?:400|500|600|700|800)\\b`, 'g'), 'bg-[var(--brand)]');
  s = s.replace(/\bbg-slate-700\b/g, 'bg-[var(--brand)]');
  s = s.replace(new RegExp(`\\bhover:bg-${ACCENT}-(?:500|600|700|800|900)\\b`, 'g'), 'hover:bg-[var(--brand-2)]');
  s = s.replace(/\bhover:bg-slate-700\b/g, 'hover:bg-[var(--brand-2)]');

  // --- Accent text / borders / rings -> brand.
  s = s.replace(new RegExp(`\\btext-${ACCENT}-(?:400|500|600|700)\\b`, 'g'), 'text-[var(--brand)]');
  s = s.replace(new RegExp(`\\bhover:text-${ACCENT}-(?:400|500|600|700)\\b`, 'g'), 'hover:text-[var(--brand)]');
  s = s.replace(new RegExp(`\\bborder-${ACCENT}-(?:300|400|500|600|700)\\b`, 'g'), 'border-[var(--brand)]');
  s = s.replace(new RegExp(`\\bring-${ACCENT}-(?:300|400|500|600|700)\\b`, 'g'), 'ring-[var(--brand)]');
  s = s.replace(new RegExp(`\\bfocus:ring-${ACCENT}-(?:300|400|500|600|700)\\b`, 'g'), 'focus:ring-[var(--brand)]');

  // --- Faint light-gray text (designed for dark bg) -> muted.
  s = s.replace(/\btext-(?:slate|gray|zinc|neutral)-(?:100|200|300|400)\b/g, 'text-[var(--muted)]');
  s = s.replace(/\bhover:text-(?:slate|gray|zinc|neutral)-(?:100|200|300|400)\b/g, 'hover:text-[var(--text)]');

  // --- Invisible white text: only convert when there is no background in the
  //     same quoted class string (a button/badge keeps its white-on-color text).
  s = s.replace(/(['"`])([^'"`]*\btext-white\b[^'"`]*)\1/g, (m, q, body) => {
    const hasBg = /\bbg-(?:\[|black|white|[a-z]+-\d)/.test(body) || /\bbg-\[var/.test(body);
    if (hasBg) return m;
    return `${q}${body.replace(/\btext-white\b/g, 'text-[var(--text)]')}${q}`;
  });

  return s;
}

let changed = 0;
let scanned = 0;
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) {
      if (name === 'node_modules' || name === '.next') continue;
      walk(p);
    } else if (p.endsWith('.tsx') && !p.endsWith('.test.tsx')) {
      scanned++;
      const src = readFileSync(p, 'utf8');
      const out = transform(src);
      if (out !== src) {
        writeFileSync(p, out);
        changed++;
        console.log('updated', p);
      }
    }
  }
}

walk(root);
console.log(`\nDone. ${changed}/${scanned} files changed.`);
