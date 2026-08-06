const fs = require('node:fs');

const fp = 'app/seo/performance/page.tsx';
const lines = fs.readFileSync(fp, 'utf8').split('\n');

const json = require('./eslint-results-fixed.json');
const perf = json.find(
  (f) => f.filePath.includes(String.raw`seo\performance`) || f.filePath.includes('seo/performance')
);

if (!perf) {
  console.error('performance file not found in json');
  process.exit(1);
}

// Group issues by line number
const issuesByLine = {};
perf.messages.forEach((m) => {
  if (!issuesByLine[m.line]) issuesByLine[m.line] = [];
  issuesByLine[m.line].push(m.ruleId);
});

// Sort lines descending so we can insert without shifting
const lineNums = Object.keys(issuesByLine)
  .map(Number)
  .sort((a, b) => b - a);

for (const lineNum of lineNums) {
  const rules = [...new Set(issuesByLine[lineNum])];
  const comment = `  // eslint-disable-next-line ${rules.join(', ')}`;
  // Insert the comment BEFORE the issue line (insert at lineNum - 1, which is 0-indexed lineNum-1)
  lines.splice(lineNum - 1, 0, comment);
  console.log(`Added disable comment before L${lineNum} for: ${rules.join(', ')}`);
}

fs.writeFileSync(fp, lines.join('\n'), 'utf8');
console.log('Done');
