const fs = require('node:fs');

const fp = 'app/seo/performance/page.tsx';
let content = fs.readFileSync(fp, 'utf8');
const originalLength = content.length;

// Replace all destructured PerfTabProps props that are unused
// Pattern: { result, card, isOfflinePreview }: PerfTabProps
// We need to alias unused props like: { result: _result, isOfflinePreview: _isOfflinePreview }

// The issue: these lines in ESLint 3.x report unused destructured object props
// Solution: use ESLint `destructuredArrayIgnorePattern` or alias in interface
// Simplest approach: add /* eslint-disable-next-line */ only for the specific functions
// OR update the config to use caughtErrorsIgnorePattern

// Actually the cleanest fix: update eslint config to also ignore destructured props
// Add `destructuredArrayIgnorePattern: '^_'` -- but that's for arrays
// For objects, need to actually alias them

// Let's look at lines that still have isOfflinePreview not aliased
const lines = content.split('\n');
let count = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (line.includes('}: PerfTabProps') && line.includes('isOfflinePreview') && !line.includes('isOfflinePreview: _')) {
    // Replace each problematic prop with aliased version
    let updated = line;

    // Replace isOfflinePreview (not already aliased)
    updated = updated.replaceAll(/\bisOfflinePreview\b(?!\s*:)/g, 'isOfflinePreview: _isOfflinePreview');
    // Replace card (not already aliased)
    updated = updated.replaceAll(/\bcard\b(?!\s*:)/g, 'card: _card');
    // Replace result (not already aliased) - but be careful it may be used
    // Don't replace result since some tabs use it

    // Also replace other potentially unused props in HistoryTab
    updated = updated.replaceAll(/\bautoFixing\b(?!\s*:)/g, 'autoFixing: _autoFixing');
    updated = updated.replaceAll(/\bautoFixResult\b(?!\s*:)/g, 'autoFixResult: _autoFixResult');
    updated = updated.replaceAll(/\bautoFixError\b(?!\s*:)/g, 'autoFixError: _autoFixError');
    updated = updated.replaceAll(/\bfixingItem\b(?!\s*:)/g, 'fixingItem: _fixingItem');
    updated = updated.replaceAll(/\bfixedItems\b(?!\s*:)/g, 'fixedItems: _fixedItems');
    updated = updated.replaceAll(/\bfixSingleItem\b(?!\s*:)/g, 'fixSingleItem: _fixSingleItem');
    updated = updated.replaceAll(/\boptimizeSite\b(?!\s*:)/g, 'optimizeSite: _optimizeSite');
    updated = updated.replaceAll(/\bresult\b(?!\s*:)/g, 'result: _result');

    if (updated !== line) {
      lines[i] = updated;
      count++;
      console.log(`Fixed L${i + 1}`);
    }
  }
}

content = lines.join('\n');
fs.writeFileSync(fp, content, 'utf8');
console.log(`Fixed ${count} function signatures`);
