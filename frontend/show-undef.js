const json = require('./eslint-results-fixed.json');

const issues = {};
json.forEach((file) => {
  file.messages.forEach((msg) => {
    if (!issues[msg.ruleId]) issues[msg.ruleId] = [];
    issues[msg.ruleId].push({ file: file.filePath, line: msg.line, message: msg.message.split('\n')[0] });
  });
});

// Show unique no-undef symbols
const undefIssues = issues['no-undef'] || [];
const syms = [
  ...new Set(undefIssues.map((i) => i.message.replace(/'.+' is not defined/, (m) => m.match(/'(.+)'/)[1]))),
];
// Actually extract symbol names
const symbolsSet = new Set();
undefIssues.forEach((i) => {
  const m = i.message.match(/'([^']+)' is not defined/);
  if (m) symbolsSet.add(m[1]);
});
console.log('\nMissing globals (no-undef):', [...symbolsSet].sort((a, b) => a.localeCompare(b)).join(', '));
console.log('\nno-undef details:');
undefIssues.forEach((i) => {
  const m = i.message.match(/'([^']+)' is not defined/);
  console.log(`  ${i.file.split('\\').pop()}:${i.line} - ${m ? m[1] : i.message}`);
});
