#!/usr/bin/env python3
"""
ToolHive MCP Server Setup
One-command setup for the ToolHive MCP server
"""

import os
import sys
import subprocess
import json
import shutil
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

def create_virtual_env():
    """Create virtual environment"""
    venv_path = Path(".venv")
    if venv_path.exists():
        print_status("Virtual environment already exists ✓", "success")
        return True
    
    print_status("Creating virtual environment...", "info")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_status("Virtual environment created ✓", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to create virtual environment: {e}", "error")
        return False

def install_dependencies():
    """Install dependencies in virtual environment"""
    print_status("Installing dependencies...", "info")
    
    # Determine the correct pip path
    if os.name == 'nt':  # Windows
        pip_path = Path(".venv/Scripts/pip")
    else:  # Unix-like
        pip_path = Path(".venv/bin/pip")
    
    try:
        # Upgrade pip first
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True, capture_output=True)
        
        # Install requirements
        subprocess.run([str(pip_path), "install", "-e", "."], check=True, capture_output=True)
        
        print_status("Dependencies installed ✓", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install dependencies: {e}", "error")
        return False

def setup_environment():
    """Setup environment variables"""
    env_file = Path("toolhive.env")
    if env_file.exists():
        print_status("Environment file already exists ✓", "success")
        return True
    
    print_status("Creating environment file...", "info")
    
    # Create a basic toolhive.env file
    with open(env_file, 'w') as f:
        f.write("""# ToolHive MCP Server Configuration

# ToolHive API Configuration
TOOLHIVE_API_BASE=http://localhost:8080
TOOLHIVE_CLI_PATH=thv
TOOLHIVE_AUTO_START_API=true
TOOLHIVE_TIMEOUT=30

# Logging Configuration
LOG_LEVEL=ERROR
LOG_FILE=toolhive_mcp.log

# MCP Server Configuration
MCP_SERVER_PORT=8081
MCP_SERVER_HOST=localhost
DEBUG=false
""")
    
    print_status("Environment file created ✓", "success")
    return True

def setup_cursor_config():
    """Setup Cursor MCP configuration"""
    print_status("Setting up Cursor configuration...", "info")
    
    # Get current directory
    current_dir = Path.cwd()
    
    # Determine the correct python path
    if os.name == 'nt':  # Windows
        python_path = current_dir / ".venv" / "Scripts" / "python.exe"
    else:  # Unix-like
        python_path = current_dir / ".venv" / "bin" / "python3"
    
    # Create Cursor config directory
    if os.name == 'nt':  # Windows
        cursor_config_dir = Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage"
    else:  # macOS/Linux
        cursor_config_dir = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage"
    
    cursor_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create MCP configuration
    mcp_config = {
        "mcpServers": {
            "toolhive-controller": {
                "command": str(python_path),
                "args": [str(current_dir / "toolhive_server.py")],
                "env": {
                    "TOOLHIVE_API_BASE": "http://localhost:8080",
                    "TOOLHIVE_CLI_PATH": "thv",
                    "TOOLHIVE_AUTO_START_API": "true",
                    "LOG_LEVEL": "ERROR"
                }
            }
        }
    }
    
    config_file = cursor_config_dir / "mcp_servers.json"
    with open(config_file, 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    # Also save a local copy
    with open("cursor_mcp_config.json", 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    print_status("Cursor configuration created ✓", "success")
    print_status(f"Config saved to: {config_file}", "info")
    return True

def make_executable():
    """Make scripts executable on Unix-like systems"""
    if os.name != 'nt':  # Not Windows
        scripts = ["run.py", "setup.py", "toolhive_server.py"]
        for script in scripts:
            script_path = Path(script)
            if script_path.exists():
                os.chmod(script_path, 0o755)
        print_status("Scripts made executable ✓", "success")

def main():
    """Main setup function"""
    print_status("🚀 ToolHive MCP Server Setup", "info")
    print_status("This will set up everything you need to run the server", "info")
    print("")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print_status("Python 3.8 or higher is required", "error")
        sys.exit(1)
    print_status(f"Python {sys.version.split()[0]} ✓", "success")
    
    # Create virtual environment
    if not create_virtual_env():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Setup Cursor configuration
    if not setup_cursor_config():
        sys.exit(1)
    
    # Make scripts executable
    make_executable()
    
    print("")
    print_status("🎉 Setup complete!", "success")
    print("")
    print_status("Next steps:", "info")
    print_status("1. Activate the virtual environment:", "info")
    if os.name == 'nt':  # Windows
        print_status("   .venv\\Scripts\\activate", "info")
    else:  # Unix-like
        print_status("   source .venv/bin/activate", "info")
    print("")
    print_status("2. Run the server:", "info")
    print_status("   python run.py", "info")
    print("")
    print_status("3. Or run directly:", "info")
    print_status("   python toolhive_server.py", "info")
    print("")
    print_status("4. For Cursor integration:", "info")
    print_status("   - Restart Cursor completely", "info")
    print_status("   - Start a new chat", "info")
    print_status("   - Try: 'What's the ToolHive system status?'", "info")
    print("")

if __name__ == "__main__":
    main() 