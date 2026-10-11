#!/usr/bin/env node
// Resolves the design tokens, then reports every style object or CSS rule that
// pairs a foreground and a background whose contrast falls below WCAG AA.
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

import { dirname, resolve as resolvePath } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolvePath(dirname(fileURLToPath(import.meta.url)), '..');

// --- resolve tokens from globals.css + the product/marketing scopes ---
const sources = [
  'app/globals.css',
  'app/(dashboard)/_ui/tokens.css',
  'app/(public)/marketing.css',
];
const raw = new Map();
for (const file of sources) {
  const css = readFileSync(`${ROOT}/${file}`, 'utf8');
  for (const m of css.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;}]+)/gi)) {
    const name = m[1].trim();
    const value = m[2].trim();
    if (!raw.has(name)) raw.set(name, value);
  }
}
function resolve(value, depth = 0) {
  if (depth > 8 || !value) return null;
  const v = value.trim();
  let m = v.match(/^#[0-9a-fA-F]{3,8}$/);
  if (m) return v;
  m = v.match(/^var\((--[a-z0-9-]+)(?:\s*,\s*(.+))?\)$/i);
  if (m) {
    const inner = raw.get(m[1]);
    return resolve(inner ?? m[2], depth + 1);
  }
  // Treat a mix over transparent as the token itself; it sits on a light page.
  m = v.match(/^color-mix\(in oklab,\s*(var\(--[a-z0-9-]+\)|#[0-9a-fA-F]{3,8})\s+([0-9.]+)%,\s*(transparent|var\(--[a-z0-9-]+\)|#[0-9a-fA-F]{3,8})\)$/i);
  if (m) {
    const a = resolve(m[1], depth + 1);
    const pct = parseFloat(m[2]) / 100;
    const b = m[3] === 'transparent' ? '#f8f7f4' : resolve(m[3], depth + 1);
    if (!a || !b) return null;
    return mix(a, b, pct);
  }
  return null;
}
function rgb(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3) h = [...h].map((c) => c + c).join('');
  if (h.length === 8) h = h.slice(0, 6);
  if (h.length !== 6) return null;
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}
function mix(a, b, pct) {
  const A = rgb(a), B = rgb(b);
  if (!A || !B) return null;
  const out = A.map((v, i) => Math.round(v * pct + B[i] * (1 - pct)));
  return '#' + out.map((v) => v.toString(16).padStart(2, '0')).join('');
}
function lum(hex) {
  const c = rgb(hex);
  if (!c) return null;
  const f = c.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
}
function ratio(fg, bg) {
  const a = lum(fg), b = lum(bg);
  if (a === null || b === null) return null;
  const hi = Math.max(a, b), lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}

// --- scan style objects and CSS rules for fg/bg pairs ---
const COLOR = `(?:#[0-9a-fA-F]{3,8}|var\\(--[a-z0-9-]+\\)|color-mix\\([^)]*\\))`;
const files = execSync(
  `grep -rlE "(color|background)" app components --include='*.tsx' --include='*.css'`,
  { cwd: ROOT, encoding: 'utf8' },
).trim().split('\n');

const findings = [];
for (const file of files) {
  const text = readFileSync(`${ROOT}/${file}`, 'utf8');
  const lines = text.split('\n');
  lines.forEach((line, i) => {
    // Only pair declarations on the same line, so the two values provably
    // belong to the same element rather than to a nearby one.
    const fgM = line.match(new RegExp(`(?:^|[^-\\w])color\\s*[:=]\\s*['"\`]?(${COLOR})`, 'i'));
    if (!fgM) return;
    const bgM = line.match(new RegExp(`(?:background|background-color|backgroundColor)\\s*[:=]\\s*['"\`]?(${COLOR})`, 'i'));
    if (!bgM) return;
    const fg = resolve(fgM[1]);
    const bg = resolve(bgM[1]);
    if (!fg || !bg) return;
    const r = ratio(fg, bg);
    if (r === null || r >= 4.5) return;
    findings.push({
      file, line: i + 1, r: r.toFixed(2),
      fg: `${fgM[1]} = ${fg}`, bg: `${bgM[1]} = ${bg}`,
      src: line.trim().slice(0, 90),
    });
  });
}

findings.sort((a, b) => a.r - b.r);
console.log(`${findings.length} foreground/background pairs below 4.5:1\n`);
for (const f of findings.slice(0, 40)) {
  console.log(`${f.r}:1  ${f.file}:${f.line}`);
  console.log(`        fg ${f.fg}  on  bg ${f.bg}`);
}

if (findings.length) process.exitCode = 1;
