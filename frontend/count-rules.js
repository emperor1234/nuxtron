const json = require('./eslint-results-fixed.json');
const rules = {};
json.forEach((f) =>
  f.messages.forEach((m) => {
    rules[m.ruleId] = (rules[m.ruleId] || 0) + 1;
  })
);

console.log('\nTop 20 ESLint Issues by Rule:\n');
Object.entries(rules)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 20)
  .forEach(([rule, count]) => {
    console.log(`  ${count.toString().padStart(3)} - ${rule}`);
  });

// Category analysis
const hookIssues = Object.entries(rules)
  .filter(([r]) => r.includes('react-hooks'))
  .reduce((sum, [, c]) => sum + c, 0);

const typeIssues = Object.entries(rules)
  .filter(([r]) => r.includes('@typescript-eslint') || r === 'no-undef')
  .reduce((sum, [, c]) => sum + c, 0);

console.log(`\nCategory Summary:`);
console.log(`  React Hooks: ${hookIssues} issues`);
console.log(`  Type Safety: ${typeIssues} issues`);
console.log(`  Total: ${Object.values(rules).reduce((a, b) => a + b, 0)} issues\n`);
