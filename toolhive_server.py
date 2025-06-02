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
        # Extract port from TOOLHIVE_API_BASE
        port = "8080"  # default
        if ":" in TOOLHIVE_API_BASE:
            port = TOOLHIVE_API_BASE.split(":")[-1]
        
        # Start the API server in the background
        logger.info(f"Starting ToolHive API server on port {port}...")
        _api_server_process = subprocess.Popen(
            [TOOLHIVE_CLI_PATH, "serve", "--port", port],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group for clean shutdown
        )
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        # Verify it started successfully
        try:
            response = requests.get(f"{TOOLHIVE_API_BASE}/health", timeout=5)
            if response.status_code == 204:
                logger.info(f"ToolHive API server started successfully (PID: {_api_server_process.pid})")
                return True
            else:
                logger.error("ToolHive API server started but health check failed")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"ToolHive API server health check failed: {e}")
            return False
    
    except FileNotFoundError:
        logger.error(f"ToolHive CLI not found at: {TOOLHIVE_CLI_PATH}")
        return False
    except Exception as e:
        logger.error(f"Failed to start ToolHive API server: {e}")
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

def validate_server_requirements(server_name: str, provided_env_vars: list = None) -> dict:
    """Validate if all required parameters are provided for a server"""
    provided_env_vars = provided_env_vars or []
    
    # Get registry info to check requirements
    registry_info = get_registry_server_info(server_name)
    
    if "error" in registry_info:
        # If not in registry, assume it's a custom image/protocol - no validation needed
        return {"valid": True, "info": f"Custom server/image: {server_name}"}
    
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

def run_mcp_server(server_name: str, **kwargs) -> dict:
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
            name="get_toolhive_status",
            description="Get ToolHive system status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
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
                result = run_mcp_server(server_name, **arguments)
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
            
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
            
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": f"Tool execution failed: {str(e)}"}))]

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="toolhive://status",
            name="ToolHive Status",
            description="Current ToolHive system status",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://servers",
            name="All Servers",
            description="List of all MCP servers managed by ToolHive",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://registry",
            name="Registry Servers",
            description="List of available MCP servers from ToolHive registry",
            mimeType="application/json"
        ),
        Resource(
            uri="toolhive://search",
            name="Search Registry",
            description="Search interface for finding MCP servers in the registry",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reads"""
    try:
        if uri == "toolhive://status":
            status = get_toolhive_status()
            return json.dumps(status, indent=2)
            
        elif uri == "toolhive://servers":
            servers = get_toolhive_servers()
            result = {
                "servers": servers,
                "count": len(servers),
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result, indent=2)
            
        elif uri == "toolhive://registry":
            registry_data = get_registry_servers()
            result = {
                "registry_servers": registry_data,
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result, indent=2)
            
        elif uri == "toolhive://search":
            # Return search interface information
            search_info = {
                "description": "Search for MCP servers in the ToolHive registry",
                "usage": "Use the 'search_registry_servers' tool with a query parameter",
                "examples": [
                    {"query": "github", "description": "Find GitHub-related servers"},
                    {"query": "api", "description": "Find API-related servers"},
                    {"query": "memory", "description": "Find memory/storage servers"},
                    {"query": "database", "description": "Find database servers"}
                ],
                "note": "Search queries match against server names, descriptions, and tags",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(search_info, indent=2)
            
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