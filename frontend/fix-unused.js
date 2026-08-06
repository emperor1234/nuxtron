const fs = require('node:fs');
const path = require('node:path');
const json = require('./eslint-results-fixed.json');

// Group unused vars by file and line
const fileIssues = {};
json.forEach((f) => {
  f.messages
    .filter((m) => m.ruleId === '@typescript-eslint/no-unused-vars')
    .forEach((m) => {
      // Extract var name from message like "'foo' is defined but never used"
      const match = m.message.match(/'([^']+)' is (defined|assigned a value) but never used/);
      if (!match) return;
      const varName = match[1];
      if (!fileIssues[f.filePath]) fileIssues[f.filePath] = {};
      if (!fileIssues[f.filePath][m.line]) fileIssues[f.filePath][m.line] = [];
      fileIssues[f.filePath][m.line].push(varName);
    });
});

let totalFixed = 0;

Object.entries(fileIssues).forEach(([filePath, lineMap]) => {
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  let changed = false;

  Object.entries(lineMap).forEach(([lineNum, varNames]) => {
    const idx = Number.parseInt(lineNum, 10) - 1;
    const original = lines[idx];
    let updated = original;

    varNames.forEach((varName) => {
      if (varName.startsWith('_')) return; // already prefixed

      // Match in destructuring: { varName, ... } or { varName: ... }
      // Pattern: word boundary match of the exact variable name
      // Replace in destructuring patterns
      const destructureRe = new RegExp(String.raw`(\{[^}]*?)\b${varName}\b(?!\s*:)([^}]*\})`, 'g');
      const newLine = updated.replace(destructureRe, (m, before, after) => {
        return `${before}_${varName}${after}`;
      });

      if (newLine === updated) {
        // Try simple assignment: const varName = ...
        const assignRe = new RegExp(String.raw`\bconst\s+${varName}\b`);
        if (assignRe.test(updated)) {
          updated = updated.replace(assignRe, `const _${varName}`);
        }
        // Try function declaration: function varName(
        const funcRe = new RegExp(String.raw`\bfunction\s+${varName}\b`);
        if (funcRe.test(updated)) {
          updated = updated.replace(funcRe, `function _${varName}`);
        }
      } else {
        updated = newLine;
      }
    });

    if (updated !== original) {
      lines[idx] = updated;
      changed = true;
      totalFixed += varNames.length;
      console.log(`Fixed L${lineNum} in ${path.basename(filePath)}: ${varNames.join(', ')}`);
    }
  });

  if (changed) {
    fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
    console.log(`  -> Saved ${path.basename(filePath)}`);
  }
});

console.log(`\nTotal fixed: ${totalFixed}`);
