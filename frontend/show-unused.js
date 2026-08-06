const j = require('./eslint-results-fixed.json');
const all = [];
j.forEach((f) => {
  f.messages
    .filter((m) => m.ruleId === '@typescript-eslint/no-unused-vars')
    .forEach((m) => {
      all.push({
        file: f.filePath.replace(/.*\\app\\/, 'app\\'),
        line: m.line,
        col: m.column,
        msg: m.message,
      });
    });
});
all.sort((a, b) => {
  if (a.file < b.file) return -1;
  if (a.file > b.file) return 1;
  return a.line - b.line;
});
all.forEach((e) => console.log(`${e.file}:${e.line} - ${e.msg.substring(0, 80)}`));
console.log('\nTotal:', all.length);
