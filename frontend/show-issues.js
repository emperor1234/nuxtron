const json = require('./eslint-results-fixed.json');

// Group issues by rule and file
const issues = {};

json.forEach((file) => {
  file.messages.forEach((msg) => {
    if (!issues[msg.ruleId]) issues[msg.ruleId] = [];
    issues[msg.ruleId].push({
      file: file.filePath,
      line: msg.line,
      message: msg.message.split('\n')[0],
      ruleId: msg.ruleId,
    });
  });
});

// Show top issues
console.log('\n📋 ISSUES REQUIRING MANUAL FIXES\n');

const priority = [
  'react/no-unescaped-entities',
  'react-hooks/set-state-in-effect',
  'react-hooks/exhaustive-deps',
  '@typescript-eslint/no-unused-vars',
  'no-undef',
];

priority.forEach((ruleId) => {
  if (issues[ruleId]) {
    const issueList = issues[ruleId];
    console.log(`\n${ruleId}: ${issueList.length} issues`);
    console.log('-'.repeat(70));

    issueList.slice(0, 3).forEach((issue) => {
      const fileName = issue.file.split('\\').pop();
      console.log(`  ${fileName}:${issue.line}`);
      console.log(`    ${issue.message.substring(0, 65)}...`);
    });

    if (issueList.length > 3) {
      console.log(`  ... and ${issueList.length - 3} more`);
    }
  }
});

console.log('\n');
