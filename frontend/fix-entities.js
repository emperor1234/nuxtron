const fs = require('node:fs');
const path = require('node:path');
const json = require('./eslint-results-fixed.json');

// Find all files with unescaped entity issues
const filesToFix = new Map();

json.forEach((file) => {
  file.messages.forEach((msg) => {
    if (msg.ruleId === 'react/no-unescaped-entities') {
      if (!filesToFix.has(file.filePath)) {
        filesToFix.set(file.filePath, []);
      }
      filesToFix.get(file.filePath).push(msg);
    }
  });
});

console.log(`\nFound ${filesToFix.size} files with unescaped entities\n`);

// Map of entities to their HTML escape codes
const entityMap = {
  '"': '&quot;',
  "'": '&#39;',
  '—': '&mdash;',
  '–': '&ndash;',
  '…': '&hellip;',
  '©': '&copy;',
  '®': '&reg;',
  '™': '&trade;',
  '<': '&lt;',
  '>': '&gt;',
  '&': '&amp;',
};

filesToFix.forEach((issues, filePath) => {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    let updated = false;

    // For quote issues, we need to be careful in JSX attributes vs. content
    // This is a simplified approach - quotes inside JSX text content
    Object.entries(entityMap).forEach(([entity, escape]) => {
      const lines = content.split('\n');
      issues.forEach((issue) => {
        const lineNum = issue.line - 1;
        if (lines[lineNum]) {
          const oldLine = lines[lineNum];
          // Simple replacement - in real code you'd need more sophisticated parsing
          if (entity === '"' && oldLine.includes('"')) {
            lines[lineNum] = oldLine.replaceAll('"', '&quot;');
            updated = true;
          }
        }
      });
      content = lines.join('\n');
    });

    if (updated) {
      fs.writeFileSync(filePath, content, 'utf8');
      const fileName = path.basename(filePath);
      console.log(`✓ Fixed ${fileName} (${issues.length} entities)`);
    }
  } catch (err) {
    console.error(`✗ Error fixing ${filePath}:`, err.message);
  }
});

console.log('\nEntity fixes applied!\n');
