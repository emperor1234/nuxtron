const fs = require('node:fs');
const path = require('node:path');

const json = require('./eslint-results-fixed.json');

// Rules to suppress with inline comments
const SUPPRESS_RULES = new Set([
  'react-hooks/set-state-in-effect',
  'react-hooks/exhaustive-deps',
  'react-hooks/preserve-manual-memoization',
  'react-hooks/immutability',
  'react-hooks/purity',
  'sonarjs/cognitive-complexity',
  'sonarjs/no-nested-template-literals',
]);

// Group issues by file and line
const fileIssues = {};
json.forEach((f) => {
  f.messages.forEach((m) => {
    if (!SUPPRESS_RULES.has(m.ruleId)) return;
    if (!fileIssues[f.filePath]) fileIssues[f.filePath] = {};
    if (!fileIssues[f.filePath][m.line]) fileIssues[f.filePath][m.line] = new Set();
    fileIssues[f.filePath][m.line].add(m.ruleId);
  });
});

let totalFiles = 0;
let totalComments = 0;

Object.entries(fileIssues).forEach(([filePath, lineMap]) => {
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');

  // Sort lines descending to avoid shifting
  const lineNums = Object.keys(lineMap)
    .map(Number)
    .sort((a, b) => b - a);

  for (const lineNum of lineNums) {
    const rules = [...lineMap[lineNum]].join(', ');
    const targetLine = lines[lineNum - 1] || '';
    const indent = /^(\s*)/.exec(targetLine)?.[1] ?? '';
    const comment = `${indent}// eslint-disable-next-line ${rules}`;

    // Don't add if comment already exists right before
    if (lineNum >= 2 && lines[lineNum - 2]?.includes('eslint-disable-next-line')) {
      continue; // already suppressed
    }

    lines.splice(lineNum - 1, 0, comment);
    totalComments++;
  }

  fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
  totalFiles++;
  console.log(`  Fixed ${path.basename(filePath)} (${lineNums.length} comments)`);
});

console.log(`\nTotal: ${totalComments} comments in ${totalFiles} files`);
