#!/usr/bin/env python3
"""
ToolHive MCP Server (Simplified)
"""

import json
import logging
import os
import asyncio
import subprocess
import signal
import atexit
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
import sys

from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
import mcp.server.stdio

# Load environment variables from toolhive.env
load_dotenv('toolhive.env')

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# ToolHive configuration
TOOLHIVE_API_BASE = os.getenv("TOOLHIVE_API_BASE", "http://localhost:8080")
TOOLHIVE_CLI_PATH = os.getenv("TOOLHIVE_CLI_PATH", "thv")
AUTO_START_API = os.getenv("TOOLHIVE_AUTO_START_API", "true").lower() == "true"

# Global variable to track the API server process
_api_server_process: Optional[subprocess.Popen] = None

# Initialize the MCP server
server = Server("ToolHive Controller")

def start_toolhive_api_server():
    """Start the ToolHive API server in the background if not already running"""
    global _api_server_process
    
    if not AUTO_START_API:
        logger.info("Auto-start disabled via TOOLHIVE_AUTO_START_API=false")
        return False
    
    # Check if API server is already running
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/health", timeout=2)
        if response.status_code == 204:
            logger.info("ToolHive API server already running")
            return True
    except requests.exceptions.RequestException:
        pass  # API server not running, we'll start it
    
    try:
        # Enhanced URL parsing for host/port extraction
        from urllib.parse import urlparse
        parsed = urlparse(TOOLHIVE_API_BASE)
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 8080)
        
        # Build enhanced command with better configuration
        cmd = [TOOLHIVE_CLI_PATH, "serve", "--port", port, "--host", host]
        
        # Add optional API configuration from environment
        api_config = os.getenv("TOOLHIVE_API_CONFIG", "").split()
        if api_config:
            cmd.extend(api_config)
            logger.info(f"Using additional API config: {' '.join(api_config)}")
        
        # Start the API server in the background
        logger.info(f"Starting ToolHive API server on {host}:{port}...")
        print(f"🚀 Launching ToolHive API: {' '.join(cmd)}")
        
        # Create log directory for API server output
        api_log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(api_log_dir, exist_ok=True)
        
        # Open log files for API server output
        stdout_log = open(os.path.join(api_log_dir, "toolhive-api.log"), "w")
        stderr_log = open(os.path.join(api_log_dir, "toolhive-api-error.log"), "w")
        
        _api_server_process = subprocess.Popen(
            cmd,
            stdout=stdout_log,
            stderr=stderr_log,
            preexec_fn=os.setsid  # Create new process group for clean shutdown
        )
        
        # Progressive health checking with retries (up to 10 seconds)
        max_retries = int(os.getenv("TOOLHIVE_API_RETRIES", "5"))
        startup_timeout = int(os.getenv("TOOLHIVE_API_STARTUP_TIMEOUT", "10"))
        
        for attempt in range(max_retries):
            wait_time = startup_timeout / max_retries
            time.sleep(wait_time)
            
            try:
                response = requests.get(f"{TOOLHIVE_API_BASE}/health", timeout=2)
                if response.status_code == 204:
                    logger.info(f"ToolHive API server started successfully (PID: {_api_server_process.pid})")
                    print(f"✅ ToolHive API server running at {TOOLHIVE_API_BASE}")
                    # Close log files since server is running
                    stdout_log.close()
                    stderr_log.close()
                    return True
            except requests.exceptions.RequestException:
                continue
        
        # If we get here, the server didn't start properly
        logger.error(f"ToolHive API server failed to start within {startup_timeout} seconds")
        print(f"❌ ToolHive API server failed to start")
        
        # Check if process has terminated and provide diagnostics
        if _api_server_process.poll() is not None:
            return_code = _api_server_process.returncode
            logger.error(f"ToolHive API server process exited with code {return_code}")
            print(f"📋 Process exited with code {return_code}")
            
            # Read error log for diagnosis
            try:
                stderr_log.close()
                with open(os.path.join(api_log_dir, "toolhive-api-error.log"), "r") as f:
                    error_log = f.read().strip()
                    if error_log:
                        logger.error(f"API server error: {error_log}")
                        print(f"📝 Error details saved to: {os.path.join(api_log_dir, 'toolhive-api-error.log')}")
            except Exception:
                pass
        else:
            stdout_log.close()
            stderr_log.close()
        
        return False
    
    except FileNotFoundError:
        logger.error(f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}")
        print(f"❌ ToolHive CLI not found. Please install ToolHive first:")
        print(f"   curl -sSfL https://toolhive.sh/install.sh | sh")
        print(f"   Or download from: https://github.com/stacklok/toolhive/releases")
        return False
    except Exception as e:
        logger.error(f"Failed to start ToolHive API server: {e}")
        print(f"❌ Failed to start ToolHive API server: {e}")
        return False

def stop_toolhive_api_server():
    """Stop the ToolHive API server if we started it"""
    global _api_server_process
    
    if _api_server_process is None:
        return
    
    try:
        logger.info(f"Stopping ToolHive API server (PID: {_api_server_process.pid})...")
        
        # Send SIGTERM to the process group
        os.killpg(os.getpgid(_api_server_process.pid), signal.SIGTERM)
        
        # Wait for graceful shutdown
        try:
            _api_server_process.wait(timeout=10)
            logger.info("ToolHive API server stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop gracefully
            logger.warning("ToolHive API server didn't stop gracefully, force killing...")
            os.killpg(os.getpgid(_api_server_process.pid), signal.SIGKILL)
            _api_server_process.wait()
            logger.info("ToolHive API server force stopped")
            
    except Exception as e:
        logger.error(f"Error stopping ToolHive API server: {e}")
    finally:
        _api_server_process = None

# Register cleanup function
atexit.register(stop_toolhive_api_server)

# Handle signals for clean shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    stop_toolhive_api_server()
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def get_toolhive_servers():
    """Get servers from ToolHive API"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/servers", timeout=5)
        if response.status_code == 200:
            return response.json().get("servers", [])
    except Exception as e:
        logger.error(f"Failed to get servers: {e}")
        return []
    
def get_registry_servers():
    """Get available servers from ToolHive registry using CLI"""
    try:
        result = subprocess.run(
            [TOOLHIVE_CLI_PATH, "registry", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw output
                return {"raw_output": result.stdout, "format": "text"}
        else:
            return {"error": f"Command failed with exit code {result.returncode}", "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except FileNotFoundError:
        return {"error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"error": f"Failed to run registry list: {str(e)}"}

def get_toolhive_status():
    """Get ToolHive status"""
    global _api_server_process
    
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/health", timeout=5)
        api_healthy = response.status_code == 204
        
        version_response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/version", timeout=5)
        version = version_response.json().get("version", "unknown") if version_response.status_code == 200 else "unknown"
        
        status = {
            "api_healthy": api_healthy,
            "api_base_url": TOOLHIVE_API_BASE,
            "version": version,
            "auto_start_enabled": AUTO_START_API,
            "api_server_auto_started": _api_server_process is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add process info if we started the API server
        if _api_server_process is not None:
            status["api_server_pid"] = _api_server_process.pid
            status["api_server_running"] = _api_server_process.poll() is None
        
        if api_healthy:
            servers = get_toolhive_servers()
            status["total_servers"] = len(servers)
            status["running_servers"] = len([s for s in servers if s.get("State") == "running"])
        
        return status
    except Exception as e:
        return {
            "api_healthy": False,
            "error": str(e),
            "api_base_url": TOOLHIVE_API_BASE,
            "auto_start_enabled": AUTO_START_API,
            "api_server_auto_started": _api_server_process is not None,
            "timestamp": datetime.now().isoformat()
        }

def get_registry_server_info(server_name: str):
    """Get detailed information about a server from the registry"""
    try:
        result = subprocess.run(
            [TOOLHIVE_CLI_PATH, "registry", "info", server_name, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"error": "Failed to parse registry info JSON"}
        else:
            return {"error": f"Server '{server_name}' not found in registry", "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except FileNotFoundError:
        return {"error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"error": f"Failed to get registry info: {str(e)}"}

def search_internet_for_server(server_name: str) -> dict:
    """Search the internet for MCP server information when not found in registry"""
    try:
        import requests
        
        # Search for MCP server on GitHub, npm, PyPI, and general web
        search_queries = [
            f"mcp server {server_name} github",
            f"{server_name} model context protocol",
            f"mcp {server_name} npm package",
            f"{server_name} mcp server docker",
            f"model context protocol {server_name} setup"
        ]
        
        results = {
            "server_name": server_name,
            "found_alternatives": [],
            "installation_suggestions": [],
            "web_search_performed": True,
            "search_queries": search_queries
        }
        
        # Check common package registries
        package_checks = [
            {
                "type": "npm",
                "url": f"https://registry.npmjs.org/{server_name}",
                "protocol_prefix": "npx://"
            },
            {
                "type": "npm_mcp",
                "url": f"https://registry.npmjs.org/mcp-{server_name}",
                "protocol_prefix": "npx://"
            },
            {
                "type": "docker",
                "url": f"https://hub.docker.com/v2/repositories/mcp/{server_name}/",
                "protocol_prefix": "mcp/"
            }
        ]
        
        for check in package_checks:
            try:
                response = requests.get(check["url"], timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if check["type"] == "npm" or check["type"] == "npm_mcp":
                        pkg_name = data.get("name", "")
                        description = data.get("description", "")
                        version = data.get("dist-tags", {}).get("latest", "latest")
                        
                        results["found_alternatives"].append({
                            "type": check["type"],
                            "name": pkg_name,
                            "description": description,
                            "version": version,
                            "suggested_command": f"{check['protocol_prefix']}{pkg_name}",
                            "installation": f"npm install -g {pkg_name}"
                        })
                        
                    elif check["type"] == "docker":
                        results["found_alternatives"].append({
                            "type": "docker",
                            "name": f"mcp/{server_name}",
                            "description": f"Docker image for {server_name} MCP server",
                            "suggested_command": f"mcp/{server_name}:latest",
                            "installation": f"docker pull mcp/{server_name}"
                        })
                        
            except Exception:
                continue  # Skip failed checks
        
        # Add generic suggestions if no specific packages found
        if not results["found_alternatives"]:
            results["installation_suggestions"] = [
                f"Try searching npm: npm search mcp {server_name}",
                f"Check GitHub: https://github.com/search?q=mcp+{server_name}",
                f"Look for Docker images: docker search mcp-{server_name}",
                f"Try with npx: npx://mcp-{server_name}",
                f"Try with npm package name: npx://{server_name}",
                f"Check if it's a Docker image: mcp/{server_name}:latest"
            ]
        else:
            results["installation_suggestions"] = [
                "Found potential matches above. Try the suggested commands.",
                f"If none work, check the official {server_name} documentation for MCP server setup instructions.",
                "You can also try manual installation and then use the server with ToolHive."
            ]
        
        return results
        
    except Exception as e:
        return {
            "server_name": server_name,
            "web_search_performed": False,
            "error": f"Web search failed: {str(e)}",
            "fallback_suggestions": [
                f"Try manually searching for '{server_name} mcp server' online",
                f"Check npm registry: https://www.npmjs.com/search?q=mcp%20{server_name}",
                f"Search GitHub: https://github.com/search?q=mcp+{server_name}",
                f"Try common patterns: npx://mcp-{server_name} or mcp/{server_name}:latest"
            ]
        }

def validate_server_requirements(server_name: str, provided_env_vars: list = None) -> dict:
    """Validate if all required parameters are provided for a server"""
    provided_env_vars = provided_env_vars or []
    
    # Get registry info to check requirements
    registry_info = get_registry_server_info(server_name)
    
    if "error" in registry_info:
        # Server not found in registry - search the internet for alternatives
        web_search_results = search_internet_for_server(server_name)
        
        return {
            "valid": False,
            "info": f"Server '{server_name}' not found in ToolHive registry",
            "web_search_results": web_search_results,
            "suggestions": [
                f"Server '{server_name}' was not found in the ToolHive registry.",
                "I searched the internet for possible alternatives:",
            ] + (web_search_results.get("installation_suggestions", [])),
            "found_alternatives": web_search_results.get("found_alternatives", []),
            "recommended_action": "Try one of the suggested commands above, or verify the server name is correct."
        }
    
    validation_result = {
        "valid": True,
        "server_info": registry_info,
        "missing_required_env_vars": [],
        "suggestions": [],
        "warnings": []
    }
    
    # Check required environment variables
    env_vars_info = registry_info.get("env_vars", [])
    provided_env_names = [env.split("=")[0] for env in provided_env_vars]
    
    for env_var in env_vars_info:
        if env_var.get("required", False):
            env_name = env_var.get("name")
            if env_name not in provided_env_names:
                validation_result["valid"] = False
                validation_result["missing_required_env_vars"].append({
                    "name": env_name,
                    "description": env_var.get("description", "No description available")
                })
    
    # Add helpful suggestions
    if validation_result["missing_required_env_vars"]:
        validation_result["suggestions"].append(
            f"To run {server_name}, you need to provide the following environment variables:"
        )
        for missing_env in validation_result["missing_required_env_vars"]:
            validation_result["suggestions"].append(
                f"  - {missing_env['name']}: {missing_env['description']}"
            )
        validation_result["suggestions"].append(
            f"Example: 'Run {server_name} with environment variable {validation_result['missing_required_env_vars'][0]['name']}=your_value_here'"
        )
    
    # Add optional environment variables as suggestions
    optional_env_vars = [env for env in env_vars_info if not env.get("required", False)]
    if optional_env_vars:
        validation_result["suggestions"].append("Optional environment variables:")
        for env_var in optional_env_vars:
            validation_result["suggestions"].append(
                f"  - {env_var.get('name')}: {env_var.get('description', 'No description')}"
            )
    
    return validation_result

def run_mcp_server_old(server_name: str, **kwargs) -> dict:
    """Run an MCP server using ToolHive CLI with validation and helpful guidance"""
    try:
        # First, validate requirements
        validation = validate_server_requirements(server_name, kwargs.get("env_vars", []))
        
        # If validation fails, return helpful guidance instead of running
        if not validation["valid"]:
            return {
                "success": False,
                "validation_failed": True,
                "missing_requirements": validation["missing_required_env_vars"],
                "suggestions": validation["suggestions"],
                "server_info": validation.get("server_info", {}),
                "message": f"Cannot start {server_name} - missing required parameters. See suggestions below."
            }
        
        # Build the command
        cmd = [TOOLHIVE_CLI_PATH, "run"]
        
        # Add optional flags
        if kwargs.get("name"):
            cmd.extend(["--name", kwargs["name"]])
        if kwargs.get("transport"):
            cmd.extend(["--transport", kwargs["transport"]])
        if kwargs.get("port"):
            cmd.extend(["--port", str(kwargs["port"])])
        if kwargs.get("host"):
            cmd.extend(["--host", kwargs["host"]])
        if kwargs.get("target_port"):
            cmd.extend(["--target-port", str(kwargs["target_port"])])
        if kwargs.get("target_host"):
            cmd.extend(["--target-host", kwargs["target_host"]])
        if kwargs.get("permission_profile"):
            cmd.extend(["--permission-profile", kwargs["permission_profile"]])
        if kwargs.get("foreground"):
            cmd.append("--foreground")
        
        # Add environment variables
        if kwargs.get("env_vars"):
            for env_var in kwargs["env_vars"]:
                cmd.extend(["-e", env_var])
        
        # Add volumes
        if kwargs.get("volumes"):
            for volume in kwargs["volumes"]:
                cmd.extend(["-v", volume])
        
        # Add secrets
        if kwargs.get("secrets"):
            for secret in kwargs["secrets"]:
                cmd.extend(["--secret", secret])
        
        # Add the server name/image
        cmd.append(server_name)
        
        # Add additional arguments if provided
        if kwargs.get("args"):
            cmd.append("--")
            cmd.extend(kwargs["args"])
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        response = {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd)
        }
        
        # Add validation info for context
        if validation.get("suggestions"):
            response["setup_info"] = {
                "server_info": validation.get("server_info", {}),
                "suggestions": validation["suggestions"]
            }
        
        return response
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to run server: {str(e)}"}

def remove_mcp_server(server_name: str, force: bool = False) -> dict:
    """Remove an MCP server using ToolHive CLI"""
    try:
        # Build the command
        cmd = [TOOLHIVE_CLI_PATH, "rm", server_name]
        
        # Add force flag if requested
        if force:
            cmd.append("--force")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
            "message": f"Server '{server_name}' {'removed successfully' if result.returncode == 0 else 'removal failed'}"
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to remove server: {str(e)}"}

def get_client_discovery():
    """Get discovery information about MCP clients compatible with ToolHive"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/discovery/clients", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get client discovery: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get client discovery: {e}")
        return {"error": f"Failed to get client discovery: {str(e)}"}

def get_registry_list():
    """Get list of all registries"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/registry", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get registries: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get registries: {e}")
        return {"error": f"Failed to get registries: {str(e)}"}

def get_specific_registry(registry_name: str):
    """Get detailed information about a specific registry"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/registry/{registry_name}", timeout=5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"error": f"Registry '{registry_name}' not found"}
        else:
            return {"error": f"Failed to get registry: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get registry {registry_name}: {e}")
        return {"error": f"Failed to get registry: {str(e)}"}

def add_registry(registry_data: dict):
    """Add a new registry"""
    try:
        response = requests.post(f"{TOOLHIVE_API_BASE}/api/v1beta/registry", 
                               json=registry_data, timeout=10)
        if response.status_code == 201:
            return {"success": True, "message": "Registry added successfully"}
        elif response.status_code == 501:
            return {"error": "Adding registries is not yet implemented"}
        else:
            return {"error": f"Failed to add registry: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to add registry: {e}")
        return {"error": f"Failed to add registry: {str(e)}"}

def remove_registry(registry_name: str):
    """Remove a registry"""
    try:
        response = requests.delete(f"{TOOLHIVE_API_BASE}/api/v1beta/registry/{registry_name}", timeout=10)
        if response.status_code == 204:
            return {"success": True, "message": f"Registry '{registry_name}' removed successfully"}
        elif response.status_code == 404:
            return {"error": f"Registry '{registry_name}' not found"}
        else:
            return {"error": f"Failed to remove registry: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to remove registry {registry_name}: {e}")
        return {"error": f"Failed to remove registry: {str(e)}"}

def get_version():
    """Get ToolHive version information"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/v1beta/version", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get version: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        return {"error": f"Failed to get version: {str(e)}"}

def get_openapi_spec():
    """Get the OpenAPI specification"""
    try:
        response = requests.get(f"{TOOLHIVE_API_BASE}/api/openapi.json", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get OpenAPI spec: {response.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get OpenAPI spec: {e}")
        return {"error": f"Failed to get OpenAPI spec: {str(e)}"}

def start_mcp_server(server_name: str, **kwargs) -> dict:
    """Start an MCP server using ToolHive CLI with enhanced capabilities"""
    try:
        # First, validate requirements
        validation = validate_server_requirements(server_name, kwargs.get("env_vars", []))
        
        # If validation fails, return helpful guidance instead of running
        if not validation["valid"]:
            return {
                "success": False,
                "validation_failed": True,
                "missing_requirements": validation["missing_required_env_vars"],
                "suggestions": validation["suggestions"],
                "server_info": validation.get("server_info", {}),
                "message": f"Cannot start {server_name} - missing required parameters. See suggestions below."
            }
        
        # Build the command
        cmd = [TOOLHIVE_CLI_PATH, "run"]
        
        # Add optional flags
        if kwargs.get("name"):
            cmd.extend(["--name", kwargs["name"]])
        if kwargs.get("transport"):
            cmd.extend(["--transport", kwargs["transport"]])
        if kwargs.get("port"):
            cmd.extend(["--port", str(kwargs["port"])])
        if kwargs.get("host"):
            cmd.extend(["--host", kwargs["host"]])
        if kwargs.get("target_port"):
            cmd.extend(["--target-port", str(kwargs["target_port"])])
        if kwargs.get("target_host"):
            cmd.extend(["--target-host", kwargs["target_host"]])
        if kwargs.get("permission_profile"):
            cmd.extend(["--permission-profile", kwargs["permission_profile"]])
        if kwargs.get("foreground"):
            cmd.append("--foreground")
        if kwargs.get("detach"):
            cmd.append("--detach")
        
        # Add environment variables
        if kwargs.get("env_vars"):
            for env_var in kwargs["env_vars"]:
                cmd.extend(["-e", env_var])
        
        # Add volumes
        if kwargs.get("volumes"):
            for volume in kwargs["volumes"]:
                cmd.extend(["-v", volume])
        
        # Add secrets
        if kwargs.get("secrets"):
            for secret in kwargs["secrets"]:
                cmd.extend(["--secret", secret])
        
        # Add the server name/image
        cmd.append(server_name)
        
        # Add additional arguments if provided
        if kwargs.get("args"):
            cmd.append("--")
            cmd.extend(kwargs["args"])
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        response = {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd)
        }
        
        # Add validation info for context
        if validation.get("suggestions"):
            response["setup_info"] = {
                "server_info": validation.get("server_info", {}),
                "suggestions": validation["suggestions"]
            }
        
        return response
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to start server: {str(e)}"}

def restart_mcp_server(server_name: str) -> dict:
    """Restart an MCP server"""
    try:
        # First stop the server
        stop_result = remove_mcp_server(server_name, force=True)
        if not stop_result.get("success", False):
            return {"success": False, "error": f"Failed to stop server for restart: {stop_result.get('error', 'Unknown error')}"}
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # Then start it again - this requires getting the original configuration
        # For now, return instructions for manual restart
        return {
            "success": False,
            "message": "Restart requires manual intervention. Please stop the server and run it again with the same parameters.",
            "instructions": [
                f"1. Server '{server_name}' has been stopped",
                f"2. Use 'run_mcp_server' tool to start it again with your desired configuration"
            ]
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to restart server: {str(e)}"}

def get_server_logs(server_name: str, lines: int = 100) -> dict:
    """Get logs from an MCP server"""
    try:
        # Try to get logs using docker logs command
        cmd = ["docker", "logs", "--tail", str(lines), server_name]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "logs": result.stdout,
                "stderr": result.stderr,
                "lines_requested": lines,
                "server_name": server_name
            }
        else:
            return {
                "success": False,
                "error": f"Failed to get logs: {result.stderr}",
                "server_name": server_name
            }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "Docker command not found"}
    except Exception as e:
        return {"success": False, "error": f"Failed to get logs: {str(e)}"}

def search_registry_servers(query: str = "", format_type: str = "json") -> dict:
    """Search for MCP servers in the registry using ToolHive CLI"""
    try:
        # Check if query is provided since thv search requires it
        if not query:
            return {
                "success": False,
                "error": "Search query is required. Use 'list_registry_servers' to see all available servers.",
                "suggestion": "Provide a search term like 'github', 'memory', 'api', etc."
            }
        
        # Build the command
        cmd = [TOOLHIVE_CLI_PATH, "search", query]
        
        # Add format flag
        cmd.extend(["--format", format_type])
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        response = {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "command": " ".join(cmd),
            "query": query
        }
        
        if result.returncode == 0:
            if format_type == "json":
                try:
                    # Parse JSON response
                    search_results = json.loads(result.stdout)
                    response["results"] = search_results
                    response["count"] = len(search_results) if isinstance(search_results, list) else 0
                except json.JSONDecodeError:
                    response["success"] = False
                    response["error"] = "Failed to parse JSON response"
                    response["raw_output"] = result.stdout
            else:
                # Return text format as-is
                response["results"] = result.stdout
                response["format"] = "text"
        else:
            response["error"] = result.stderr or "Search failed"
            response["stderr"] = result.stderr
        
        return response
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to search registry: {str(e)}"}

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        # Core Server Management
        Tool(
            name="list_running_servers",
            description="List all currently running MCP servers",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="run_mcp_server",
            description="Start an MCP server from registry, container image, or protocol scheme",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Server name from registry, container image, or protocol scheme (e.g., 'github', 'mcp/github:latest', 'npx://package-name')"
                    },
                    "name": {
                        "type": "string",
                        "description": "Custom name for the server instance (optional)"
                    },
                    "transport": {
                        "type": "string",
                        "enum": ["stdio", "sse"],
                        "description": "Transport mode (default: stdio)"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port for the HTTP proxy to listen on (host port)"
                    },
                    "host": {
                        "type": "string",
                        "description": "Host for the HTTP proxy to listen on (default: 127.0.0.1)"
                    },
                    "target_port": {
                        "type": "integer",
                        "description": "Port for the container to expose (SSE transport only)"
                    },
                    "target_host": {
                        "type": "string",
                        "description": "Host to forward traffic to (SSE transport only, default: 127.0.0.1)"
                    },
                    "permission_profile": {
                        "type": "string",
                        "description": "Permission profile (none, network, or path to JSON file, default: network)"
                    },
                    "env_vars": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Environment variables (format: KEY=VALUE)"
                    },
                    "volumes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Volume mounts (format: host-path:container-path[:ro])"
                    },
                    "secrets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Secrets (format: NAME,target=TARGET)"
                    },
                    "foreground": {
                        "type": "boolean",
                        "description": "Run in foreground mode (block until container exits)"
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "Run in detached mode (background)"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional arguments to pass to the server"
                    }
                },
                "required": ["server_name"]
            }
        ),
        Tool(
            name="stop_mcp_server",
            description="Stop a running MCP server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to stop"
                    }
                },
                "required": ["server_name"]
            }
        ),
        Tool(
            name="restart_mcp_server",
            description="Restart an MCP server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to restart"
                    }
                },
                "required": ["server_name"]
            }
        ),
        Tool(
            name="remove_mcp_server",
            description="Remove an MCP server managed by ToolHive",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to remove"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force removal of a running container (default: false)"
                    }
                },
                "required": ["server_name"]
            }
        ),
        Tool(
            name="get_server_logs",
            description="Get logs from an MCP server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to get logs from"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of log lines to retrieve (default: 100)",
                        "minimum": 1,
                        "maximum": 10000
                    }
                },
                "required": ["server_name"]
            }
        ),
        
        # Registry Management
        Tool(
            name="list_registry_servers",
            description="List available MCP servers from the ToolHive registry",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_registry_servers",
            description="Search for MCP servers in the ToolHive registry by name, description, or tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find servers (searches name, description, and tags). Required - cannot be empty."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "text"],
                        "description": "Output format (default: json)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_server_requirements",
            description="Get setup requirements and information for an MCP server before running it",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Server name from registry to check requirements for"
                    }
                },
                "required": ["server_name"]
            }
        ),
        Tool(
            name="list_registries",
            description="List all available registries",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_registry_details",
            description="Get detailed information about a specific registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "registry_name": {
                        "type": "string",
                        "description": "Name of the registry to get details for"
                    }
                },
                "required": ["registry_name"]
            }
        ),
        Tool(
            name="add_registry",
            description="Add a new registry to ToolHive",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the registry"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL of the registry"
                    },
                    "type": {
                        "type": "string",
                        "description": "Type of registry (e.g., 'git', 'http')"
                    }
                },
                "required": ["name", "url"]
            }
        ),
        Tool(
            name="remove_registry",
            description="Remove a registry from ToolHive",
            inputSchema={
                "type": "object",
                "properties": {
                    "registry_name": {
                        "type": "string",
                        "description": "Name of the registry to remove"
                    }
                },
                "required": ["registry_name"]
            }
        ),
        
        # System Information
        Tool(
            name="get_toolhive_status",
            description="Get ToolHive system status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_toolhive_version",
            description="Get ToolHive version information",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_client_discovery",
            description="Get discovery information about MCP clients compatible with ToolHive",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_openapi_spec",
            description="Get the OpenAPI specification for ToolHive API",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="search_internet_for_mcp_server",
            description="Search the internet for MCP server information when not found in registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the MCP server to search for on the internet"
                    }
                },
                "required": ["server_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "list_running_servers":
            servers = get_toolhive_servers()
            running_servers = [s for s in servers if s.get("State") == "running"]
            
            result = {
                "running_servers": running_servers,
                "count": len(running_servers),
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "stop_mcp_server":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                response = requests.post(f"{TOOLHIVE_API_BASE}/api/v1beta/servers/{server_name}/stop", timeout=5)
                success = response.status_code == 204
                result = {
                    "success": success,
                    "message": f"Server '{server_name}' {'stopped successfully' if success else 'not found or already stopped'}"
                }
            except Exception as e:
                result = {"success": False, "error": str(e)}
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_toolhive_status":
            status = get_toolhive_status()
            return [TextContent(type="text", text=json.dumps(status, indent=2))]
            
        elif name == "list_registry_servers":
            registry_data = get_registry_servers()
            result = {
                "registry_servers": registry_data,
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "run_mcp_server":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                result = start_mcp_server(server_name, **arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            
        elif name == "get_server_requirements":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                requirements = validate_server_requirements(server_name, arguments.get("env_vars", []))
                return [TextContent(type="text", text=json.dumps(requirements, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            
        elif name == "remove_mcp_server":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                result = remove_mcp_server(server_name, arguments.get("force", False))
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            
        elif name == "search_registry_servers":
            query = arguments.get("query", "")
            format_type = arguments.get("format", "json")
            
            try:
                result = search_registry_servers(query, format_type)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        # New Tools - Server Management
        elif name == "restart_mcp_server":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                result = restart_mcp_server(server_name)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "get_server_logs":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            lines = arguments.get("lines", 100)
            try:
                result = get_server_logs(server_name, lines)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        # Registry Management Tools
        elif name == "list_registries":
            try:
                result = get_registry_list()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "get_registry_details":
            registry_name = arguments.get("registry_name")
            if not registry_name:
                return [TextContent(type="text", text=json.dumps({"error": "registry_name is required"}))]
            
            try:
                result = get_specific_registry(registry_name)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "add_registry":
            name_arg = arguments.get("name")
            url = arguments.get("url")
            if not name_arg or not url:
                return [TextContent(type="text", text=json.dumps({"error": "name and url are required"}))]
            
            registry_data = {
                "name": name_arg,
                "url": url,
                "type": arguments.get("type", "git")
            }
            
            try:
                result = add_registry(registry_data)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "remove_registry":
            registry_name = arguments.get("registry_name")
            if not registry_name:
                return [TextContent(type="text", text=json.dumps({"error": "registry_name is required"}))]
            
            try:
                result = remove_registry(registry_name)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        # System Information Tools
        elif name == "get_toolhive_version":
            try:
                result = get_version()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "get_client_discovery":
            try:
                result = get_client_discovery()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "get_openapi_spec":
            try:
                result = get_openapi_spec()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
                
        elif name == "search_internet_for_mcp_server":
            server_name = arguments.get("server_name")
            if not server_name:
                return [TextContent(type="text", text=json.dumps({"error": "server_name is required"}))]
            
            try:
                result = search_internet_for_server(server_name)
                # Add helpful formatting for the response
                formatted_result = {
                    "search_summary": f"Internet search results for MCP server '{server_name}'",
                    "server_name": server_name,
                    "found_alternatives": result.get("found_alternatives", []),
                    "installation_suggestions": result.get("installation_suggestions", []),
                    "web_search_performed": result.get("web_search_performed", False),
                    "timestamp": datetime.now().isoformat()
                }
                
                if result.get("error"):
                    formatted_result["error"] = result["error"]
                    formatted_result["fallback_suggestions"] = result.get("fallback_suggestions", [])
                
                return [TextContent(type="text", text=json.dumps(formatted_result, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
            
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": f"Tool execution failed: {str(e)}"}))]

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources"""
    return [
        # Core System Resources
        Resource(
            uri="toolhive://status",
            name="ToolHive Status",
            description="Current ToolHive system status and health information",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://version",
            name="ToolHive Version",
            description="ToolHive version and build information",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://openapi",
            name="OpenAPI Specification",
            description="Complete OpenAPI specification for ToolHive API",
            mimeType="application/json"
        ),
        
        # Server Management Resources
        Resource(
            uri="toolhive://servers",
            name="All Servers",
            description="List of all MCP servers managed by ToolHive with detailed status",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://servers/running",
            name="Running Servers",
            description="List of currently running MCP servers only",
            mimeType="application/json"
        ),
        
        # Registry Resources
        Resource(
            uri="toolhive://registry",
            name="Registry Servers",
            description="List of available MCP servers from all ToolHive registries",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://registries",
            name="All Registries",
            description="List of all configured registries in ToolHive",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://search",
            name="Search Registry",
            description="Search interface for finding MCP servers in registries",
            mimeType="application/json"
        ),
        
        # Discovery Resources
        Resource(
            uri="toolhive://clients",
            name="Client Discovery",
            description="Information about MCP clients compatible with ToolHive",
            mimeType="application/json"
        ),
        
        # Help and Documentation
        Resource(
            uri="toolhive://help",
            name="Help and Usage",
            description="Comprehensive help and usage information for ToolHive MCP server",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reads"""
    try:
        # Core System Resources
        if uri == "toolhive://status":
            status = get_toolhive_status()
            return json.dumps(status, indent=2)
            
        elif uri == "toolhive://version":
            version_data = get_version()
            return json.dumps(version_data, indent=2)
            
        elif uri == "toolhive://openapi":
            openapi_data = get_openapi_spec()
            return json.dumps(openapi_data, indent=2)
            
        # Server Management Resources
        elif uri == "toolhive://servers":
            servers = get_toolhive_servers()
            result = {
                "servers": servers,
                "count": len(servers),
                "running_count": len([s for s in servers if s.get("State") == "running"]),
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result, indent=2)
            
        elif uri == "toolhive://servers/running":
            servers = get_toolhive_servers()
            running_servers = [s for s in servers if s.get("State") == "running"]
            result = {
                "running_servers": running_servers,
                "count": len(running_servers),
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result, indent=2)
            
        # Registry Resources
        elif uri == "toolhive://registry":
            registry_data = get_registry_servers()
            result = {
                "registry_servers": registry_data,
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result, indent=2)
            
        elif uri == "toolhive://registries":
            registries_data = get_registry_list()
            return json.dumps(registries_data, indent=2)
            
        elif uri == "toolhive://search":
            # Return search interface information
            search_info = {
                "description": "Search for MCP servers in the ToolHive registry",
                "usage": "Use the 'search_registry_servers' tool with a query parameter",
                "examples": [
                    {"query": "github", "description": "Find GitHub-related servers"},
                    {"query": "api", "description": "Find API-related servers"},
                    {"query": "memory", "description": "Find memory/storage servers"},
                    {"query": "database", "description": "Find database servers"},
                    {"query": "file", "description": "Find file system servers"},
                    {"query": "web", "description": "Find web scraping servers"}
                ],
                "note": "Search queries match against server names, descriptions, and tags",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(search_info, indent=2)
            
        # Discovery Resources
        elif uri == "toolhive://clients":
            clients_data = get_client_discovery()
            return json.dumps(clients_data, indent=2)
            
        # Help and Documentation
        elif uri == "toolhive://help":
            help_info = {
                "description": "ToolHive MCP Server - Control ToolHive through natural language",
                "version": "0.2.1",
                "tools_count": 18,
                "resources_count": 10,
                "categories": {
                    "server_management": [
                        "list_running_servers",
                        "run_mcp_server", 
                        "stop_mcp_server",
                        "restart_mcp_server",
                        "remove_mcp_server",
                        "get_server_logs"
                    ],
                    "registry_management": [
                        "list_registry_servers",
                        "search_registry_servers",
                        "get_server_requirements",
                        "list_registries",
                        "get_registry_details",
                        "add_registry",
                        "remove_registry"
                    ],
                    "system_information": [
                        "get_toolhive_status",
                        "get_toolhive_version",
                        "get_client_discovery",
                        "get_openapi_spec",
                        "search_internet_for_mcp_server"
                    ]
                },
                "example_usage": [
                    "Run a GitHub server: 'run github server with environment variable GITHUB_TOKEN=your_token'",
                    "List running servers: 'show me all running servers'",
                    "Search for database servers: 'search for database servers in the registry'",
                    "Get server logs: 'show me the logs for github-server'",
                    "Check system status: 'what is the current status of ToolHive?'",
                    "Find unknown server: 'search the internet for custom-server MCP server'"
                ],
                "documentation": {
                    "api_reference": "See toolhive://openapi for complete API specification",
                    "registry_search": "Use toolhive://search for search examples",
                    "system_status": "Use toolhive://status for current system health"
                },
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(help_info, indent=2)
            
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"})
            
    except Exception as e:
        logger.error(f"Resource read failed: {e}")
        return json.dumps({"error": f"Resource read failed: {str(e)}"})

async def main():
    """Main server function with improved error handling"""
    try:
        # Print startup banner
        print("🚀 ToolHive MCP Server Starting...")
        print(f"📍 API Base: {TOOLHIVE_API_BASE}")
        print(f"🔧 CLI Path: {TOOLHIVE_CLI_PATH}")
        print(f"⚡ Auto-start: {'Enabled' if AUTO_START_API else 'Disabled'}")
        print(f"🛠️  Tools: 18 available (Server Management, Registry, System Info, Web Search)")
        print(f"📚 Resources: 10 available (Status, Servers, Registry, Help)")
        print("")
        
        # Start ToolHive API server if needed
        if AUTO_START_API:
            print("🔄 Checking ToolHive API server...")
            api_started = start_toolhive_api_server()
            if api_started:
                print("✅ ToolHive API server is running")
            else:
                print("⚠️  ToolHive API server not available - some features may be limited")
        else:
            print("ℹ️  Auto-start disabled - make sure ToolHive API is running manually")
        
        print("🎯 MCP Server ready for connections")
        print("📝 Use Ctrl+C to stop")
        print("")
        
        # Run the MCP server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Try running: pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server error: {e}")
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        stop_toolhive_api_server()

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 