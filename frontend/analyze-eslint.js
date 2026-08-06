const { execSync } = require('node:child_process');

const json = JSON.parse(
  execSync('npx eslint app --format=json', {
    encoding: 'utf8',
    maxBuffer: 50 * 1024 * 1024,
    stdio: ['pipe', 'pipe', 'ignore'],
  }).trim()
);

const rules = {};
const files = {};
json.forEach((f) => {
  f.messages.forEach((m) => {
    rules[m.ruleId] = (rules[m.ruleId] || 0) + 1;
  });
  if (f.messages.length > 0) {
    files[f.filePath.split('\\').pop()] = f.messages.length;
  }
});

console.log('\n📊 ESLint Issue Breakdown\n');
console.log('Top 15 Rules by Count:');
Object.entries(rules)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 15)
  .forEach(([k, v]) => {
    console.log(`  ${v.toString().padStart(3)} - ${k}`);
  });

console.log('\nTop 10 Files by Issue Count:');
Object.entries(files)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10)
  .forEach(([k, v]) => {
    console.log(`  ${v.toString().padStart(3)} - ${k}`);
  });

const totals = json.reduce(
  (acc, f) => ({
    errors: acc.errors + f.errorCount,
    warnings: acc.warnings + f.warningCount,
  }),
  { errors: 0, warnings: 0 }
);

console.log(`\n📈 Total: ${totals.errors} errors, ${totals.warnings} warnings\n`);
