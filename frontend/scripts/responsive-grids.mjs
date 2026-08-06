#!/usr/bin/env node
/**
 * Make inline CSS grids intrinsically responsive (no media query needed).
 *
 * Route pages use inline styles, which media queries cannot reach. These
 * transforms make every grid collapse gracefully on small viewports:
 *
 *  1. minmax(Npx, 1fr)            -> minmax(min(100%, Npx), 1fr)
 *     (a column can never be wider than its container -> auto-fill/fit grids
 *      collapse to 1 column on mobile instead of overflowing)
 *  2. repeat(K, minmax(Npx,1fr))  -> repeat(auto-fit, minmax(min(100%, Npx), 1fr))
 *  3. repeat(K, 1fr)              -> repeat(auto-fit, minmax(min(100%, Wpx), 1fr))
 *  4. '1fr 1fr[ 1fr...]'          -> repeat(auto-fit, minmax(min(100%, Wpx), 1fr))
 *
 * W is chosen per column count so the desktop layout keeps ~K columns at the
 * ~1180px content width while stacking on tablet/mobile.
 *
 * Usage: node scripts/responsive-grids.mjs "app/(dashboard)"
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const dirs = process.argv.slice(2);
if (!dirs.length) { console.error('Provide a directory.'); process.exit(1); }

// Min column width per intended column count (keeps ~K cols at ~1180px).
const W = { 1: 100, 2: 420, 3: 300, 4: 260, 5: 210, 6: 180 };
const widthFor = (k) => W[k] ?? 150;

function transform(src) {
  let s = src;

  // 0) Content + fixed-width-sidebar 2-pane layouts -> stack on mobile.
  //    minmax(0, Xfr) minmax(Ypx, Z)  /  minmax(Ypx, Z) minmax(0, Xfr)
  s = s.replace(/minmax\(\s*0\s*,\s*[\d.]+fr\s*\)\s+minmax\(\s*\d+px\s*,\s*[^)]+\)/g,
    'repeat(auto-fit, minmax(min(100%, 320px), 1fr))');
  s = s.replace(/minmax\(\s*\d+px\s*,\s*[^)]+\)\s+minmax\(\s*0\s*,\s*[\d.]+fr\s*\)/g,
    'repeat(auto-fit, minmax(min(100%, 320px), 1fr))');

  // 0b) '<bigpx>px 1fr' / '1fr <bigpx>px' sidebars (>=200px) -> stack on mobile.
  s = s.replace(/(gridTemplateColumns:\s*)(['"`])(?:[2-9]\d\d|\d{4})px 1fr\2/g,
    (_m, head, q) => `${head}${q}repeat(auto-fit, minmax(min(100%, 300px), 1fr))${q}`);
  s = s.replace(/(gridTemplateColumns:\s*)(['"`])1fr (?:[2-9]\d\d|\d{4})px\2/g,
    (_m, head, q) => `${head}${q}repeat(auto-fit, minmax(min(100%, 300px), 1fr))${q}`);

  // 2) repeat(K, minmax(Npx, 1fr)) -> auto-fit + clamp
  s = s.replace(/repeat\(\s*\d+\s*,\s*minmax\(\s*(\d+)px\s*,\s*1fr\s*\)\s*\)/g,
    (_m, n) => `repeat(auto-fit, minmax(min(100%, ${n}px), 1fr))`);

  // 1) bare minmax(Npx, 1fr) -> clamp to viewport (skip if already min())
  s = s.replace(/minmax\(\s*(\d+)px\s*,\s*1fr\s*\)/g,
    (_m, n) => `minmax(min(100%, ${n}px), 1fr)`);

  // 3) repeat(K, 1fr) -> auto-fit responsive
  s = s.replace(/repeat\(\s*(\d+)\s*,\s*1fr\s*\)/g,
    (_m, k) => `repeat(auto-fit, minmax(min(100%, ${widthFor(Number(k))}px), 1fr))`);

  // 4) gridTemplateColumns: '<fr> <fr> ...' (all fr, equal OR asymmetric ratios,
  //    2-4 columns) -> auto-fit responsive. Leaves px/auto/minmax tracks alone,
  //    so compact row grids like '72px 1fr 26px' or '90px 1fr 90px' are untouched.
  s = s.replace(/(gridTemplateColumns:\s*)(['"`])(\d*\.?\d+fr(?:\s+\d*\.?\d+fr){1,3})\2/g,
    (_m, head, q, body) => {
      const k = body.trim().split(/\s+/).length;
      return `${head}${q}repeat(auto-fit, minmax(min(100%, ${widthFor(k)}px), 1fr))${q}`;
    });

  return s;
}

function walk(dir, out) {
  for (const name of readdirSync(dir)) {
    if (name === '_shell') continue; // never touch the sidebar/shell
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (extname(p) === '.tsx') out.push(p);
  }
}

const files = [];
for (const d of dirs) walk(d, files);

let changed = 0;
for (const f of files) {
  const src = readFileSync(f, 'utf8');
  const next = transform(src);
  if (next !== src) { writeFileSync(f, next); changed++; console.log('updated', f); }
}
console.log(`\nDone. ${changed}/${files.length} files changed.`);
