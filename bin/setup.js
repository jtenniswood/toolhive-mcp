#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Get the directory where this package is installed
const packageDir = path.dirname(__dirname);

// Run the main script with setup-only flag
const mainScript = path.join(__dirname, 'toolhive-mcp.js');
const setupProcess = spawn('node', [mainScript, '--setup-only'], {
  cwd: packageDir,
  stdio: 'inherit'
});

setupProcess.on('close', (code) => {
  process.exit(code);
});

setupProcess.on('error', (err) => {
  console.error(`Setup error: ${err.message}`);
  process.exit(1);
}); 