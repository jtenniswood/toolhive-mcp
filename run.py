#!/usr/bin/env python3
"""
ToolHive MCP Server Launcher
Simple script to run the ToolHive MCP server with automatic setup
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "reset": "\033[0m"       # Reset
    }
    
    symbols = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = colors.get(status, colors["info"])
    symbol = symbols.get(status, "")
    reset = colors["reset"]
    
    print(f"{color}{symbol} {message}{reset}")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print_status("Python 3.8 or higher is required", "error")
        sys.exit(1)
    print_status(f"Python {sys.version.split()[0]} ✓", "success")

def check_virtual_env():
    """Check if we're in a virtual environment, create one if not"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_status("Virtual environment detected ✓", "success")
        return True
    
    venv_path = Path(".venv")
    if venv_path.exists():
        print_status("Virtual environment found, please activate it:", "warning")
        print_status("  source .venv/bin/activate  # Linux/Mac", "info")
        print_status("  .venv\\Scripts\\activate     # Windows", "info")
        return False
    
    print_status("Creating virtual environment...", "info")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_status("Virtual environment created! Please activate it and run again:", "success")
        print_status("  source .venv/bin/activate && python run.py", "info")
        return False
    except subprocess.CalledProcessError:
        print_status("Failed to create virtual environment", "error")
        return False

def install_dependencies():
    """Install required dependencies"""
    try:
        import mcp
        import requests
        print_status("Dependencies already installed ✓", "success")
        return True
    except ImportError:
        print_status("Installing dependencies...", "info")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                         check=True, capture_output=True)
            print_status("Dependencies installed ✓", "success")
            return True
        except subprocess.CalledProcessError as e:
            print_status(f"Failed to install dependencies: {e}", "error")
            return False

def check_toolhive_cli():
    """Check if ToolHive CLI is available"""
    try:
        result = subprocess.run(["thv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status("ToolHive CLI found ✓", "success")
            return True
    except FileNotFoundError:
        pass
    
    print_status("ToolHive CLI not found", "warning")
    print_status("Install with: curl -sSL https://install.toolhive.ai | bash", "info")
    print_status("Or: brew tap stacklok/tap && brew install thv", "info")
    return False

def check_toolhive_api():
    """Check if ToolHive API is running"""
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code == 204:
            print_status("ToolHive API is running ✓", "success")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print_status("ToolHive API not running", "warning")
    print_status("The server will try to start it automatically", "info")
    return False

def run_server():
    """Run the ToolHive MCP server"""
    print_status("Starting ToolHive MCP Server...", "info")
    print_status("Press Ctrl+C to stop", "info")
    print("")
    
    try:
        # Run the server
        subprocess.run([sys.executable, "toolhive_server.py"], check=True)
    except KeyboardInterrupt:
        print_status("\nServer stopped by user", "info")
    except subprocess.CalledProcessError as e:
        print_status(f"Server failed to start: {e}", "error")
        return False
    except FileNotFoundError:
        print_status("toolhive_server.py not found", "error")
        return False
    
    return True

def main():
    """Main launcher function"""
    print_status("🚀 ToolHive MCP Server Launcher", "info")
    print("")
    
    # Check Python version
    check_python_version()
    
    # Check virtual environment
    if not check_virtual_env():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Check ToolHive CLI (optional)
    has_cli = check_toolhive_cli()
    
    # Check ToolHive API (optional)
    has_api = check_toolhive_api()
    
    if not has_cli:
        print_status("Note: Some features may be limited without ToolHive CLI", "warning")
    
    print("")
    print_status("All checks complete! Starting server...", "success")
    print("")
    
    # Run the server
    run_server()

if __name__ == "__main__":
    main() 