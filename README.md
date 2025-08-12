# ToolHive MCP Server

**Control ToolHive through natural language in Cursor and other MCP-compatible applications.**

The ToolHive MCP Server provides comprehensive control over ToolHive's MCP server management capabilities through a natural language interface. With 17 tools and 10 resources, you can manage servers, registries, and system information using conversational commands.

## ✨ Features

- **🚀 Complete Server Management** - Start, stop, restart, and monitor MCP servers
- **📚 Registry Operations** - Search, manage, and discover MCP servers from registries
- **🔍 System Information** - Access status, version, and client compatibility data
- **📊 Resource Access** - Rich data resources for servers, registries, and help
- **🤖 Natural Language** - Intuitive commands like "run github server with token"
- **🔒 Enhanced Security** - Permission profiles and secure container execution
- **📝 Comprehensive Logging** - Access server logs and system diagnostics

## Quick Start

### 1. Install ToolHive
See details at https://github.com/stacklok/toolhive

### 2. Install ToolHive MCP Server
```bash
npm install -g toolhive-mcp
```

### 3. Add to Cursor Configuration
Add this to your Cursor MCP configuration:
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

### 4. Start Using Natural Language Commands

Once configured, you can control ToolHive through natural language:

- **"Run a GitHub server with my token"**
- **"Show me all running servers"**
- **"Search for database servers in the registry"**
- **"Get the logs for my github-server"**
- **"What's the current ToolHive status?"**

## Project Structure

```
toolhive-mcp/
├── src/                      # Source code
│   ├── toolhive_server.py   # Main MCP server
│   └── index.js             # Node.js entry point
├── bin/                     # Executable scripts
├── examples/                # Example implementations
│   └── client.py           # MCP client example
├── docs/                    # Documentation
│   ├── TOOLHIVE_API_DOCUMENTATION.md
│   └── Makefile            # Build commands
├── package.json            # npm configuration
├── pyproject.toml          # Python configuration
├── requirements.txt        # Python dependencies
└── toolhive.env           # Environment configuration
```

## 🛠️ Available Tools (17)

### Server Management
- **`list_running_servers`** - List all currently running MCP servers
- **`run_mcp_server`** - Start an MCP server with full configuration options
- **`stop_mcp_server`** - Stop a running MCP server
- **`restart_mcp_server`** - Restart an existing MCP server
- **`remove_mcp_server`** - Remove/delete an MCP server
- **`get_server_logs`** - Get logs from an MCP server (configurable line count)

### Registry Management
- **`list_registry_servers`** - List available MCP servers from registries
- **`search_registry_servers`** - Search for servers by name, description, or tags
- **`get_server_requirements`** - Get setup requirements for a server
- **`list_registries`** - List all configured registries
- **`get_registry_details`** - Get detailed information about a registry
- **`add_registry`** - Add a new registry to ToolHive
- **`remove_registry`** - Remove a registry from ToolHive

### System Information
- **`get_toolhive_status`** - Get comprehensive system status
- **`get_toolhive_version`** - Get version and build information
- **`get_client_discovery`** - Get MCP client compatibility information
- **`get_openapi_spec`** - Get complete OpenAPI specification

## 📚 Available Resources (10)

### Core System
- **`toolhive://status`** - Current system status and health
- **`toolhive://version`** - Version and build information
- **`toolhive://openapi`** - Complete OpenAPI specification

### Server Management
- **`toolhive://servers`** - All managed servers with detailed status
- **`toolhive://servers/running`** - Currently running servers only

### Registry & Discovery
- **`toolhive://registry`** - Available servers from all registries
- **`toolhive://registries`** - All configured registries
- **`toolhive://search`** - Search examples and interface
- **`toolhive://clients`** - MCP client compatibility data

### Help & Documentation
- **`toolhive://help`** - Comprehensive usage guide and examples

## 🎯 Example Usage

### Server Management
```
"Run a GitHub server with environment variable GITHUB_TOKEN=your_token"
"Stop the github-server"
"Show me the logs for github-server with last 50 lines"
"Restart my database server"
```

### Registry Operations
```
"Search for memory servers in the registry"
"What are the requirements for the github server?"
"List all available registries"
"Add a new registry called my-registry with URL https://example.com/registry"
```

### System Information
```
"What's the current ToolHive status?"
"What version of ToolHive is running?"
"Show me the OpenAPI specification"
"What MCP clients are compatible with ToolHive?"
```

## ⚙️ Configuration

### Environment Variables
- **`TOOLHIVE_API_BASE`** - ToolHive API URL (default: http://localhost:8080)
- **`TOOLHIVE_CLI_PATH`** - Path to ToolHive CLI (default: thv)
- **`TOOLHIVE_AUTO_START_API`** - Auto-start API server (default: true)
- **`LOG_LEVEL`** - Logging level (default: ERROR)

### Advanced Configuration
Create a `toolhive.env` file for custom settings:
```env
TOOLHIVE_API_BASE=http://localhost:8080
TOOLHIVE_CLI_PATH=thv
TOOLHIVE_AUTO_START_API=true
LOG_LEVEL=ERROR
```

## 📖 Documentation

- **[Complete API Documentation](docs/TOOLHIVE_API_DOCUMENTATION.md)** - Comprehensive API reference
- **[Build Commands](docs/Makefile)** - Development and build instructions
- **[Official ToolHive Repository](https://github.com/stacklok/toolhive)** - Main ToolHive project

## 🔒 Security Features

- **Container Isolation** - All servers run in secure containers
- **Permission Profiles** - Fine-grained access control with JSON profiles
- **Secret Management** - Secure handling of environment variables and secrets
- **Network Policies** - Controlled network access and egress rules
- **RBAC Support** - Role-based access control for Kubernetes deployments

## Development

```bash
# Clone the repository
git clone <repository-url>
cd toolhive-mcp

# Install dependencies
npm install
pip install -r requirements.txt

# Run the server directly
python src/toolhive_server.py

# Or use npm
npm start
```

## 🐛 Troubleshooting

### Common Issues

**Server won't start:**
- Ensure ToolHive CLI is installed and accessible via `thv` command
- Check that the ToolHive API is running (default: http://localhost:8080)
- Verify Python dependencies are installed: `pip install -r requirements.txt`

**API connection failures:**
- Check `TOOLHIVE_API_BASE` environment variable
- Ensure ToolHive API server is running: `thv serve`
- Verify network connectivity to the API endpoint

**Missing tools or resources:**
- Update to the latest version: `npm install -g toolhive-mcp@latest`
- Check the help resource: Access `toolhive://help` for current capabilities

### Getting Help

- **Built-in Help**: Use the `toolhive://help` resource for comprehensive usage information
- **API Documentation**: See [docs/TOOLHIVE_API_DOCUMENTATION.md](docs/TOOLHIVE_API_DOCUMENTATION.md)
- **ToolHive Community**: Join the [ToolHive Discord](https://discord.gg/toolhive) for support
- **Issues**: Report bugs on [GitHub Issues](https://github.com/stacklok/toolhive/issues)

## 📋 Version Information

- **Current Version**: 0.2.0
- **MCP Protocol**: 1.9.0+
- **Python Requirement**: 3.8+
- **Node.js Requirement**: 14.0.0+

### Changelog

**v0.2.0** - Major Feature Release
- Added 9 new tools (17 total)
- Added 6 new resources (10 total)
- Complete ToolHive API coverage
- Enhanced error handling and validation
- Added server log access
- Registry management capabilities
- System information and discovery features

**v0.1.2** - Initial Release
- Basic server management tools
- Core registry integration
- Natural language interface

## 🤝 Contributing

We welcome contributions! Please see the [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.