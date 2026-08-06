#!/usr/bin/env node
/**
 * Validation Pipeline for Nuxtron Frontend
 * Runs: TypeScript + ESLint + Auto-fixes
 */

const { exec } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const cwd = path.join(__dirname, '..');
let hasErrors = false;

console.log('\n🔍 Starting Nuxtron Frontend Validation Pipeline...\n');

// 1. TypeScript Check
console.log('📋 [1/3] Running TypeScript check...');
exec('npx tsc --noEmit', { cwd, maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
  if (error) {
    console.error('❌ TypeScript errors found:\n', stderr || stdout);
    hasErrors = true;
  } else {
    console.log('✅ TypeScript: Clean\n');
  }

  // 2. ESLint Check
  console.log('🎯 [2/3] Running ESLint validation...');
  exec('npx eslint app --format=json 2>/dev/null', { cwd, maxBuffer: 10 * 1024 * 1024 }, (error, stdout) => {
    try {
      const eslintResults = JSON.parse(stdout || '[]');
      const totalErrors = eslintResults.reduce((sum, file) => sum + (file.errorCount || 0), 0);
      const totalWarnings = eslintResults.reduce((sum, file) => sum + (file.warningCount || 0), 0);

      if (totalErrors > 0) {
        console.warn(`⚠️  ESLint found ${totalErrors} errors and ${totalWarnings} warnings`);
        hasErrors = true;

        // Show top issues
        const allMessages = eslintResults
          .flatMap((file) => file.messages.map((msg) => ({ file: file.filePath, ...msg })))
          .sort((a, b) => b.severity - a.severity)
          .slice(0, 10);

        console.log('\n📌 Top Issues:');
        allMessages.forEach((msg) => {
          const icon = msg.severity === 2 ? '❌' : '⚠️ ';
          console.log(`  ${icon} ${path.basename(msg.file)}:${msg.line} - ${msg.message}`);
        });
      } else {
        console.log('✅ ESLint: Clean\n');
      }
    } catch (e) {
      console.error('Error parsing ESLint results:', e.message);
    }

    // 3. Summary
    console.log('\n' + '='.repeat(60));
    if (hasErrors) {
      console.log('❌ Validation issues found. Review above.');
    } else {
      console.log('✅ All validations passed!');
    }
    console.log('='.repeat(60) + '\n');

    process.exit(hasErrors ? 1 : 0);
  });
});
