#!/usr/bin/env node
/**
 * normalize-design.mjs
 * One-off codemod to enforce design-system consistency across route pages:
 *   1. Brand/accent color unification  -> single brand indigo (#6366f1)
 *   2. Card/panel border-radius snapping -> {12, 16, 22} scale
 *   3. rem font-sizes -> nearest step on the canonical px type scale
 *
 * Inline styles can't be media-queried or themed, so we normalize their raw
 * values directly. Run from the `frontend` directory:
 *   node scripts/normalize-design.mjs "app/(dashboard)"
 */
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2] || 'app/(dashboard)';

// 1) Brand / accent blues + violets that should all read as the one brand.
const BRAND = '#6366f1';
const BRAND_VARIANTS = [
  '2563eb', // blue-600
  '3b82f6', // blue-500
  '1d4ed8', // blue-700
  '1e40af', // blue-800
  '4f46e5', // indigo-600
  '4338ca', // indigo-700
  '7c3aed', // violet-600
];

// Type scale (px) — every font-size snaps to the nearest step.
const TYPE_SCALE = [11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 32, 36, 40, 44, 48];
const snap = (n, scale) => scale.reduce((a, b) => (Math.abs(b - n) < Math.abs(a - n) ? b : a));

function transform(src) {
  let s = src;

  // --- Colors: collapse brand variants (with optional 2-digit alpha) to brand.
  for (const hex of BRAND_VARIANTS) {
    const re = new RegExp(`#${hex}([0-9a-fA-F]{2})?\\b`, 'gi');
    s = s.replace(re, (_m, alpha) => `${BRAND}${alpha || ''}`);
  }
  // Case-normalize green so it isn't read as two different tokens.
  s = s.replace(/#22C55E\b/g, '#22c55e');

  // --- Radius: snap mid/large panel radii to 16 (keeps 12, 22, pills, small).
  s = s.replace(/borderRadius:\s*'(14|18|20)px'/g, "borderRadius: '16px'");
  s = s.replace(/borderRadius:\s*(14|18|20)\b(?!px)/g, 'borderRadius: 16');

  // --- Font size: rem -> nearest px scale step (unifies the unit system).
  s = s.replace(/fontSize:\s*'([\d.]+)rem'/g, (_m, rem) => {
    const px = snap(Math.round(parseFloat(rem) * 16), TYPE_SCALE);
    return `fontSize: '${px}px'`;
  });
  // Bare px font sizes -> snap to scale too (e.g. 17px, 19px, 23px -> nearest).
  s = s.replace(/fontSize:\s*'(\d+)px'/g, (_m, px) => {
    const v = snap(parseInt(px, 10), TYPE_SCALE);
    return `fontSize: '${v}px'`;
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
