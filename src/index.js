#!/usr/bin/env node

/**
 * ToolHive MCP Server
 * 
 * This module provides programmatic access to the ToolHive MCP server.
 * For CLI usage, use the bin/toolhive-mcp.js script.
 */

const path = require('path');
const { spawn } = require('child_process');

/**
 * Start the ToolHive MCP server
 * @param {Object} options - Configuration options
 * @param {boolean} options.setupOnly - Only run setup, don't start server
 * @param {string} options.pythonCmd - Python command to use
 * @returns {Promise<ChildProcess>} The server process
 */
function startServer(options = {}) {
  const binPath = path.join(__dirname, '..', 'bin', 'toolhive-mcp.js');
  const args = [];
  
  if (options.setupOnly) {
    args.push('--setup-only');
  }
  
  return new Promise((resolve, reject) => {
    const process = spawn('node', [binPath, ...args], {
      stdio: 'inherit'
    });
    
    process.on('error', reject);
    process.on('spawn', () => resolve(process));
  });
}

module.exports = {
  startServer
};

// If called directly, run the CLI
if (require.main === module) {
  require('../bin/toolhive-mcp.js');
} 