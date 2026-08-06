const fs = require('node:fs');

const fp = 'app/seo/performance/page.tsx';
let content = fs.readFileSync(fp, 'utf8');

// 1. Prefix standalone unused functions
content = content.replace('function confidenceColor(', 'function _confidenceColor(');
content = content.replace('function cspScoreColor(', 'function _cspScoreColor(');

// 2. Fix AreaChart - labels prop (it's in the interface)
// { points, width = 380, height = 72, color = '#3b82f6', labels }
// Change to: labels: _labels
content = content.replace("color = '#3b82f6', labels }", "color = '#3b82f6', labels: _labels }");

// 3. For all PerfTabProps function signatures, alias unused props
// Pattern: function XxxTab({ result, card, isOfflinePreview, ... }: PerfTabProps)
// Replace simple { result, card, isOfflinePreview } with aliased versions
const tabFixes = [
  // Functions that don't use any of these props at all
  ['FilmstripTab', ['result', 'card', 'isOfflinePreview']],
];

// Instead of per-function, do a global replacement for typed interface destructuring
// Replace patterns like: { result, card, isOfflinePreview }: PerfTabProps
// with: { result: _result, card: _card, isOfflinePreview: _isOfflinePreview }: PerfTabProps

// Find all function signatures with PerfTabProps
const lines = content.split('\n');
const newLines = lines.map((line, idx) => {
  if (!line.includes('}: PerfTabProps')) return line;

  // For each prop that might be unused, check if it appears in the next 200 lines
  // We'll take a different approach - identify which props are unused and alias them
  const unusedInThisFunc = getUnusedProps(lines, idx);

  let updated = line;
  for (const prop of unusedInThisFunc) {
    // Replace `prop` in destructuring (but not `prop: something`)
    const re = new RegExp(String.raw`\b${prop}(?!\s*:)`, 'g');
    updated = updated.replace(re, `${prop}: _${prop}`);
  }
  return updated;
});

function getUnusedProps(lines, sigLineIdx) {
  // Read the JSON results to get which props are unused at that line
  const json = require('./eslint-results-fixed.json');
  const perf = json.find((f) => f.filePath.includes('performance'));
  if (!perf) return [];

  const lineNum = sigLineIdx + 1;
  const issues = perf.messages.filter((m) => m.ruleId === '@typescript-eslint/no-unused-vars' && m.line === lineNum);

  return issues
    .map((m) => {
      const match = m.message.match(/'([^']+)' is (defined|assigned)/);
      return match ? match[1] : null;
    })
    .filter(Boolean);
}

content = newLines.join('\n');
fs.writeFileSync(fp, content, 'utf8');
console.log('Done');
