# ToolHive API Documentation

## Overview

ToolHive is a platform that makes deploying Model Context Protocol (MCP) servers easy, secure, and fun. It provides a comprehensive API for managing MCP servers through REST endpoints, CLI commands, and an MCP server interface.

Based on the [official ToolHive repository](https://github.com/stacklok/toolhive), this documentation covers:
- REST API endpoints (v1beta)
- CLI commands 
- MCP Server interface
- Configuration and deployment options

## Table of Contents

1. [REST API Endpoints](#rest-api-endpoints)
2. [CLI Commands](#cli-commands)
3. [MCP Server Interface](#mcp-server-interface)
4. [Configuration](#configuration)
5. [Authentication & Security](#authentication--security)
6. [Examples](#examples)

---

## REST API Endpoints

### Base URL
```
http://localhost:8080/api/v1beta
```

### System Endpoints

#### Health Check
```http
GET /health
```
**Description:** Check the health status of the ToolHive API server.

**Response:**
- `204 No Content` - API is healthy and running

#### Get OpenAPI Specification
```http
GET /api/openapi.json
```
**Description:** Retrieve the complete OpenAPI specification for the API.

**Response:**
- `200 OK` - Returns OpenAPI specification in JSON format

#### Get Version
```http
GET /api/v1beta/version
```
**Description:** Get the current version of ToolHive.

**Response:**
```json
{
  "version": "0.2.5"
}
```

---

### Server Management Endpoints

#### List All Servers
```http
GET /api/v1beta/servers
```
**Description:** List all MCP servers managed by ToolHive.

**Response:**
```json
{
  "servers": [
    {
      "Name": "github-server",
      "State": "running",
      "Image": "mcp/github:latest",
      "Created": "2025-01-03T10:30:00Z",
      "Ports": ["8080:8080"],
      "Environment": ["GITHUB_TOKEN=***"]
    }
  ]
}
```

#### Stop a Server
```http
POST /api/v1beta/servers/{server_name}/stop
```
**Description:** Stop a running MCP server.

**Parameters:**
- `server_name` (path) - Name of the server to stop

**Response:**
- `204 No Content` - Server stopped successfully
- `404 Not Found` - Server not found

---

### Registry Endpoints

#### List Registries
```http
GET /api/v1beta/registry
```
**Description:** Get a list of all available registries.

**Response:**
```json
{
  "registries": [
    {
      "name": "default",
      "version": "v1.0",
      "server_count": 25,
      "last_updated": "2025-01-03T10:00:00Z"
    }
  ]
}
```

#### Get Registry Details
```http
GET /api/v1beta/registry/{name}
```
**Description:** Get detailed information about a specific registry.

**Parameters:**
- `name` (path) - Name of the registry

**Response:**
```json
{
  "name": "default",
  "servers": [
    {
      "name": "github",
      "description": "GitHub MCP server for repository operations",
      "image": "mcp/github:latest",
      "env_vars": [
        {
          "name": "GITHUB_TOKEN",
          "required": true,
          "description": "GitHub personal access token"
        }
      ]
    }
  ]
}
```

#### Add Registry
```http
POST /api/v1beta/registry
```
**Description:** Add a new registry.

**Request Body:**
```json
{
  "name": "custom-registry",
  "url": "https://example.com/registry",
  "type": "git"
}
```

**Response:**
- `501 Not Implemented` - Feature not yet implemented

#### Remove Registry
```http
DELETE /api/v1beta/registry/{name}
```
**Description:** Remove a registry by name.

**Parameters:**
- `name` (path) - Name of the registry to remove

**Response:**
- `204 No Content` - Registry removed successfully
- `404 Not Found` - Registry not found

---

### Discovery Endpoints

#### List Client Status
```http
GET /api/v1beta/discovery/clients
```
**Description:** List all MCP clients compatible with ToolHive and their status.

**Response:**
```json
{
  "clients": [
    {
      "name": "cursor",
      "type": "editor",
      "installed": true,
      "configured": true,
      "version": "1.5.0"
    },
    {
      "name": "github-copilot",
      "type": "ai-assistant", 
      "installed": false,
      "configured": false
    }
  ]
}
```

---

## CLI Commands

### Installation
```bash
# Install ToolHive CLI
curl -sSfL https://toolhive.sh/install.sh | sh

# Or download from GitHub releases
# https://github.com/stacklok/toolhive/releases
```

### Core Commands

#### Start API Server
```bash
thv serve [OPTIONS]
```
**Description:** Start the ToolHive API server.

**Options:**
- `--port, -p` - Port to listen on (default: 8080)
- `--host` - Host to bind to (default: 127.0.0.1)
- `--config` - Path to configuration file

**Example:**
```bash
thv serve --port 8080
```

#### Run MCP Server
```bash
thv run [OPTIONS] <SERVER_NAME_OR_IMAGE>
```
**Description:** Run an MCP server from registry, container image, or protocol scheme.

**Options:**
- `--name` - Custom name for the server instance
- `--transport` - Transport mode (stdio, sse)
- `--port` - Port for HTTP proxy (host port)
- `--host` - Host for HTTP proxy (default: 127.0.0.1)
- `--target-port` - Port for container to expose (SSE only)
- `--target-host` - Host to forward traffic to (SSE only)
- `--permission-profile` - Permission profile (none, network, or JSON file path)
- `--foreground` - Run in foreground mode
- `-e, --env` - Environment variables (KEY=VALUE)
- `-v, --volume` - Volume mounts (host-path:container-path[:ro])
- `--secret` - Secrets (NAME,target=TARGET)

**Examples:**
```bash
# Run from registry
thv run github -e GITHUB_TOKEN=ghp_xxx

# Run custom image
thv run mcp/custom:latest --port 8081

# Run with protocol
thv run npx://mcp-package --transport sse
```

#### Remove Server
```bash
thv rm [OPTIONS] <SERVER_NAME>
```
**Description:** Remove an MCP server.

**Options:**
- `--force` - Force removal of running container

**Example:**
```bash
thv rm github-server --force
```

### Registry Commands

#### List Available Servers
```bash
thv registry list [OPTIONS]
```
**Description:** List all available MCP servers in registries.

**Options:**
- `--format` - Output format (json, table, yaml)

**Example:**
```bash
thv registry list --format json
```

#### Search Registry
```bash
thv search <QUERY> [OPTIONS]
```
**Description:** Search for MCP servers in registries.

**Options:**
- `--format` - Output format (json, table)

**Example:**
```bash
thv search github --format json
```

#### Get Server Info
```bash
thv registry info <SERVER_NAME> [OPTIONS]
```
**Description:** Get detailed information about a specific server.

**Options:**
- `--format` - Output format (json, yaml)

**Example:**
```bash
thv registry info github --format json
```

---

## MCP Server Interface

The ToolHive MCP server provides a natural language interface to control ToolHive through MCP-compatible applications like Cursor.

### Available Tools

#### 1. list_running_servers
**Description:** List all currently running MCP servers.

**Input Schema:** No parameters required.

**Response:**
```json
{
  "running_servers": [
    {
      "Name": "github-server",
      "State": "running",
      "Image": "mcp/github:latest"
    }
  ],
  "count": 1,
  "timestamp": "2025-01-03T10:30:00Z"
}
```

#### 2. run_mcp_server
**Description:** Start an MCP server from registry, container image, or protocol scheme.

**Input Schema:**
```json
{
  "server_name": "string (required)",
  "name": "string (optional)",
  "transport": "stdio|sse (optional)",
  "port": "integer (optional)",
  "host": "string (optional)",
  "target_port": "integer (optional)",
  "target_host": "string (optional)",
  "permission_profile": "string (optional)",
  "env_vars": ["string array (optional)"],
  "volumes": ["string array (optional)"],
  "secrets": ["string array (optional)"],
  "foreground": "boolean (optional)",
  "args": ["string array (optional)"]
}
```

#### 3. stop_mcp_server
**Description:** Stop a running MCP server.

**Input Schema:**
```json
{
  "server_name": "string (required)"
}
```

#### 4. get_toolhive_status
**Description:** Get ToolHive system status.

**Response:**
```json
{
  "api_healthy": true,
  "api_base_url": "http://localhost:8080",
  "version": "0.2.5",
  "auto_start_enabled": true,
  "total_servers": 3,
  "running_servers": 1,
  "timestamp": "2025-01-03T10:30:00Z"
}
```

#### 5. list_registry_servers
**Description:** List available MCP servers from registries.

#### 6. search_registry_servers
**Description:** Search for MCP servers by name, description, or tags.

**Input Schema:**
```json
{
  "query": "string (required)",
  "format": "json|text (optional)"
}
```

#### 7. get_server_requirements
**Description:** Get setup requirements for an MCP server before running it.

**Input Schema:**
```json
{
  "server_name": "string (required)"
}
```

#### 8. remove_mcp_server
**Description:** Remove an MCP server managed by ToolHive.

**Input Schema:**
```json
{
  "server_name": "string (required)",
  "force": "boolean (optional)"
}
```

### Available Resources

#### 1. toolhive://status
**Description:** Current ToolHive system status
**MIME Type:** application/json

#### 2. toolhive://servers
**Description:** List of all MCP servers managed by ToolHive
**MIME Type:** application/json

#### 3. toolhive://registry
**Description:** List of available MCP servers from registries
**MIME Type:** application/json

#### 4. toolhive://search
**Description:** Search interface for finding MCP servers
**MIME Type:** application/json

---

## Configuration

### Environment Variables

#### ToolHive API Configuration
- `TOOLHIVE_API_BASE` - Base URL for ToolHive API (default: http://localhost:8080)
- `TOOLHIVE_CLI_PATH` - Path to ToolHive CLI binary (default: thv)
- `TOOLHIVE_AUTO_START_API` - Auto-start API server (default: true)
- `LOG_LEVEL` - Logging level (default: ERROR)

#### MCP Server Configuration
Create a `toolhive.env` file:
```env
TOOLHIVE_API_BASE=http://localhost:8080
TOOLHIVE_CLI_PATH=thv
TOOLHIVE_AUTO_START_API=true
LOG_LEVEL=ERROR
```

### Cursor Integration
Add to your Cursor MCP configuration:
```json
{
  "mcpServers": {
    "toolhive-controller": {
      "command": "npx",
      "args": ["-y", "toolhive-mcp"],
      "env": {
        "TOOLHIVE_API_BASE": "http://localhost:8080",
        "TOOLHIVE_CLI_PATH": "thv",
        "TOOLHIVE_AUTO_START_API": "true",
        "LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

---

## Authentication & Security

### Permission Profiles
ToolHive uses JSON-based permission profiles to control container access:

#### Example Permission Profile
```json
{
  "read": ["/var/run/mcp.sock"],
  "write": ["/var/run/mcp.sock"],
  "network": {
    "outbound": {
      "insecure_allow_all": false,
      "allow_transport": ["tcp", "udp"],
      "allow_host": ["localhost", "api.github.com"],
      "allow_port": [80, 443]
    }
  }
}
```

### Security Features
- **Containerized Execution:** All MCP servers run in isolated containers
- **Permission Profiles:** Fine-grained access control
- **Secret Management:** Secure handling of sensitive environment variables
- **Network Policies:** Controlled network access
- **RBAC Support:** Role-based access control for Kubernetes deployments

---

## Examples

### Basic Usage

#### 1. Start ToolHive API Server
```bash
# Start the API server
thv serve --port 8080

# Check health
curl http://localhost:8080/health
```

#### 2. Run GitHub MCP Server
```bash
# Run with environment variable
thv run github -e GITHUB_TOKEN=ghp_your_token_here

# Run with custom name and port
thv run github --name my-github --port 8081 -e GITHUB_TOKEN=ghp_xxx
```

#### 3. List and Manage Servers
```bash
# List running servers
curl http://localhost:8080/api/v1beta/servers

# Stop a server
curl -X POST http://localhost:8080/api/v1beta/servers/github/stop
```

### Advanced Usage

#### 1. Custom Permission Profile
```bash
# Create permission profile
cat > github-perms.json << EOF
{
  "network": {
    "outbound": {
      "allow_host": ["api.github.com", "github.com"],
      "allow_port": [443]
    }
  }
}
EOF

# Run with custom permissions
thv run github --permission-profile github-perms.json -e GITHUB_TOKEN=ghp_xxx
```

#### 2. Volume Mounting
```bash
# Mount local directory
thv run file-server -v $(pwd):/workspace:ro
```

#### 3. Using with Docker Image
```bash
# Run custom Docker image
thv run docker.io/myorg/custom-mcp:latest --port 8082
```

### MCP Client Usage

#### Using the Python Client
```python
#!/usr/bin/env python3
import asyncio
from client import MCPClient

async def main():
    client = MCPClient()
    await client.connect_to_server("toolhive_server.py")
    
    # List available tools
    print("Available tools:")
    tools = await client.session.list_tools()
    for tool in tools.tools:
        print(f"- {tool.name}: {tool.description}")
    
    # Run a server
    result = await client.call_tool("run_mcp_server", {
        "server_name": "github",
        "env_vars": ["GITHUB_TOKEN=ghp_xxx"]
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Error Handling

### Common HTTP Status Codes
- `200 OK` - Successful request
- `204 No Content` - Successful request with no response body
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `501 Not Implemented` - Feature not yet implemented

### Error Response Format
```json
{
  "error": "Description of the error",
  "code": "ERROR_CODE",
  "details": {
    "additional": "context"
  }
}
```

---

## Support and Resources

- **Official Documentation:** [https://docs.stacklok.com/toolhive](https://docs.stacklok.com/toolhive)
- **GitHub Repository:** [https://github.com/stacklok/toolhive](https://github.com/stacklok/toolhive)
- **Discord Community:** Join the ToolHive Discord for support
- **Issues:** Report bugs and feature requests on GitHub

---

*This documentation is based on ToolHive v0.2.5 and the MCP server implementation. For the most up-to-date information, please refer to the official ToolHive documentation.*
