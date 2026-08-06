const { execSync } = require('node:child_process');
const fs = require('node:fs');

const json = JSON.parse(
  execSync('npx eslint app --format=json', {
    encoding: 'utf8',
    maxBuffer: 50 * 1024 * 1024,
    stdio: ['pipe', 'pipe', 'ignore'],
  }).trim()
);

// Group by rule and collect samples
const issuesByRule = {};
json.forEach((file) => {
  file.messages.forEach((msg) => {
    if (!issuesByRule[msg.ruleId]) {
      issuesByRule[msg.ruleId] = { count: 0, samples: [] };
    }
    issuesByRule[msg.ruleId].count++;
    if (issuesByRule[msg.ruleId].samples.length < 3) {
      issuesByRule[msg.ruleId].samples.push({
        file: file.filePath.split('\\').pop(),
        line: msg.line,
        message: msg.message.split('\n')[0],
      });
    }
  });
});

console.log('\n📋 DETAILED ESLINT ISSUE ANALYSIS\n');
console.log('='.repeat(80));

// Sort by count
Object.entries(issuesByRule)
  .sort((a, b) => b[1].count - a[1].count)
  .forEach(([rule, data], idx) => {
    console.log(`\n${idx + 1}. ${rule} — ${data.count} issues`);
    console.log('-'.repeat(60));
    data.samples.forEach((sample) => {
      console.log(`  📁 ${sample.file}:${sample.line}`);
      console.log(`     ${sample.message.substring(0, 70)}...`);
    });
  });

console.log('\n' + '='.repeat(80));
console.log('\n📊 SUMMARY BY CATEGORY\n');

const categories = {
  'React Hooks': ['react-hooks/set-state-in-effect', 'react-hooks/exhaustive-deps', 'react-hooks/immutability'],
  'Type Safety': ['no-undef'],
  'Code Quality': ['no-unused-vars', 'no-console', '@typescript-eslint/no-unused-vars'],
  Other: [],
};

const categoryCounts = {};
Object.entries(issuesByRule).forEach(([rule, data]) => {
  let categorized = false;
  for (const [cat, rules] of Object.entries(categories)) {
    if (cat !== 'Other' && rules.includes(rule)) {
      categoryCounts[cat] = (categoryCounts[cat] || 0) + data.count;
      categorized = true;
      break;
    }
  }
  if (!categorized) {
    categoryCounts['Other'] = (categoryCounts['Other'] || 0) + data.count;
  }
});

Object.entries(categoryCounts)
  .sort((a, b) => b[1] - a[1])
  .forEach(([cat, count]) => {
    const pct = ((count / Object.values(issuesByRule).reduce((s, d) => s + d.count, 0)) * 100).toFixed(0);
    console.log(`  ${count.toString().padStart(3)} issues (${pct}%) — ${cat}`);
  });

console.log('\n');
