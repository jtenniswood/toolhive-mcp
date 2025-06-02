#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs-extra');
const path = require('path');
const chalk = require('chalk');

// Get the directory where this package is installed
const packageDir = path.dirname(__dirname);

function printStatus(message, type = 'info') {
  const symbols = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };
  
  const colors = {
    info: chalk.blue,
    success: chalk.green,
    warning: chalk.yellow,
    error: chalk.red
  };
  
  const color = colors[type] || colors.info;
  const symbol = symbols[type] || '';
  
  console.log(color(`${symbol} ${message}`));
}

function checkPython() {
  return new Promise((resolve) => {
    const pythonCommands = ['python3', 'python'];
    let pythonCmd = null;
    
    const checkNext = (index) => {
      if (index >= pythonCommands.length) {
        resolve(null);
        return;
      }
      
      const cmd = pythonCommands[index];
      const child = spawn(cmd, ['--version'], { stdio: 'pipe' });
      
      child.on('close', (code) => {
        if (code === 0) {
          pythonCmd = cmd;
          resolve(cmd);
        } else {
          checkNext(index + 1);
        }
      });
      
      child.on('error', () => {
        checkNext(index + 1);
      });
    };
    
    checkNext(0);
  });
}

async function createVirtualEnv(pythonCmd) {
  const venvPath = path.join(packageDir, '.venv');
  
  if (fs.existsSync(venvPath)) {
    printStatus('Virtual environment already exists', 'success');
    return true;
  }
  
  printStatus('Creating virtual environment...', 'info');
  
  try {
    const venvProcess = spawn(pythonCmd, ['-m', 'venv', '.venv'], {
      cwd: packageDir,
      stdio: 'pipe'
    });
    
    await new Promise((resolve, reject) => {
      venvProcess.on('close', (code) => {
        if (code === 0) {
          printStatus('Virtual environment created successfully!', 'success');
          resolve();
        } else {
          reject(new Error(`Failed to create virtual environment: ${code}`));
        }
      });
      
      venvProcess.on('error', (err) => {
        reject(err);
      });
    });
    
    return true;
  } catch (error) {
    printStatus(`Failed to create virtual environment: ${error.message}`, 'error');
    return false;
  }
}

async function installPythonDependencies(pythonCmd) {
  printStatus('Installing Python dependencies...', 'info');
  
  const requirementsPath = path.join(packageDir, 'requirements.txt');
  
  if (!fs.existsSync(requirementsPath)) {
    printStatus('No requirements.txt found, skipping dependency installation', 'warning');
    return;
  }
  
  // Try to create and use a virtual environment first
  const venvCreated = await createVirtualEnv(pythonCmd);
  
  let finalPythonCmd = pythonCmd;
  if (venvCreated) {
    // Use virtual environment python
    const venvPythonPath = process.platform === 'win32' 
      ? path.join(packageDir, '.venv', 'Scripts', 'python.exe')
      : path.join(packageDir, '.venv', 'bin', 'python3');
    
    if (fs.existsSync(venvPythonPath)) {
      finalPythonCmd = venvPythonPath;
      printStatus('Using virtual environment for dependency installation', 'info');
    }
  }
  
  const installMethods = [
    // Method 1: Virtual environment (if available)
    {
      name: 'virtual environment',
      cmd: finalPythonCmd,
      args: ['-m', 'pip', 'install', '-r', requirementsPath]
    },
    // Method 2: User install with break-system-packages
    {
      name: 'user install with break-system-packages',
      cmd: pythonCmd,
      args: ['-m', 'pip', 'install', '--user', '--break-system-packages', '-r', requirementsPath]
    },
    // Method 3: User install (traditional)
    {
      name: 'user install',
      cmd: pythonCmd,
      args: ['-m', 'pip', 'install', '--user', '-r', requirementsPath]
    },
    // Method 4: System install with break-system-packages
    {
      name: 'system install with break-system-packages',
      cmd: pythonCmd,
      args: ['-m', 'pip', 'install', '--break-system-packages', '-r', requirementsPath]
    }
  ];
  
  for (const method of installMethods) {
    try {
      printStatus(`Trying ${method.name}...`, 'info');
      
      const installProcess = spawn(method.cmd, method.args, {
        cwd: packageDir,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      
      let stdout = '';
      let stderr = '';
      
      installProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      installProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      await new Promise((resolve, reject) => {
        installProcess.on('close', (code) => {
          if (code === 0 || stderr.includes('already satisfied') || stderr.includes('Requirement already satisfied')) {
            printStatus(`Dependencies installed successfully using ${method.name}!`, 'success');
            resolve();
          } else {
            reject(new Error(`${method.name} failed: ${stderr}`));
          }
        });
        
        installProcess.on('error', (err) => {
          reject(err);
        });
      });
      
      // If we get here, installation was successful
      return;
      
    } catch (error) {
      printStatus(`${method.name} failed: ${error.message}`, 'warning');
      continue;
    }
  }
  
  // If all methods failed
  printStatus('Could not install dependencies automatically.', 'error');
  printStatus('Please install manually with one of these commands:', 'info');
  printStatus('  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt', 'info');
  printStatus('  pip3 install --user --break-system-packages -r requirements.txt', 'info');
  printStatus('Continuing anyway - some features may not work.', 'warning');
}

async function setupPython() {
  printStatus('Setting up ToolHive MCP Server...', 'info');
  
  // Check if Python is available
  const pythonCmd = await checkPython();
  if (!pythonCmd) {
    printStatus('Python 3.8+ is required but not found', 'error');
    printStatus('Please install Python 3.8 or higher and try again', 'error');
    process.exit(1);
  }
  
  printStatus(`Found Python: ${pythonCmd}`, 'success');
  
  // Install Python dependencies
  await installPythonDependencies(pythonCmd);
  
  // Check if we have the traditional setup files and run them if available
  const setupPyPath = path.join(packageDir, 'setup.py');
  const venvPath = path.join(packageDir, '.venv');
  
  if (fs.existsSync(setupPyPath) && !fs.existsSync(venvPath)) {
    printStatus('Running additional setup...', 'info');
    
    try {
      await new Promise((resolve, reject) => {
        const setupProcess = spawn(pythonCmd, [setupPyPath], {
          cwd: packageDir,
          stdio: 'inherit'
        });
        
        setupProcess.on('close', (code) => {
          if (code === 0) {
            printStatus('Additional setup completed successfully!', 'success');
            resolve();
          } else {
            printStatus('Additional setup had issues, but continuing...', 'warning');
            resolve(); // Don't fail, just warn
          }
        });
        
        setupProcess.on('error', (err) => {
          printStatus(`Setup warning: ${err.message}`, 'warning');
          resolve(); // Don't fail, just warn
        });
      });
    } catch (error) {
      printStatus('Setup had issues but continuing...', 'warning');
    }
  }
}

async function runServer() {
  const pythonCmd = await checkPython();
  if (!pythonCmd) {
    printStatus('Python not found', 'error');
    process.exit(1);
  }
  
  // Try to use virtual environment python if available, otherwise use system python
  const venvPythonPath = process.platform === 'win32' 
    ? path.join(packageDir, '.venv', 'Scripts', 'python.exe')
    : path.join(packageDir, '.venv', 'bin', 'python3');
  
  const finalPythonCmd = fs.existsSync(venvPythonPath) ? venvPythonPath : pythonCmd;
  const serverPath = path.join(packageDir, 'toolhive_server.py');
  
  printStatus('Starting ToolHive MCP Server...', 'info');
  
  // Set up environment variables for the Python process
  const env = {
    ...process.env,
    PYTHONPATH: packageDir,
    // Add user site-packages to Python path for --user installed packages
    PYTHONUSERBASE: process.env.PYTHONUSERBASE || path.join(require('os').homedir(), '.local')
  };
  
  const serverProcess = spawn(finalPythonCmd, [serverPath], {
    cwd: packageDir,
    stdio: 'inherit',
    env: env
  });
  
  serverProcess.on('close', (code) => {
    if (code !== 0) {
      printStatus(`Server exited with code ${code}`, 'error');
    }
  });
  
  serverProcess.on('error', (err) => {
    printStatus(`Server error: ${err.message}`, 'error');
  });
  
  // Handle graceful shutdown
  process.on('SIGINT', () => {
    printStatus('Shutting down server...', 'info');
    serverProcess.kill('SIGINT');
  });
  
  process.on('SIGTERM', () => {
    printStatus('Shutting down server...', 'info');
    serverProcess.kill('SIGTERM');
  });
}

async function main() {
  const args = process.argv.slice(2);
  
  try {
    // Always run setup first if needed
    await setupPython();
    
    if (args.includes('--setup-only')) {
      printStatus('Setup completed. Run without --setup-only to start the server.', 'success');
      return;
    }
    
    // Start the server
    await runServer();
    
  } catch (error) {
    printStatus(`Error: ${error.message}`, 'error');
    process.exit(1);
  }
}

if (require.main === module) {
  main();
} 