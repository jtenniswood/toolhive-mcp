# ToolHive MCP Server

Control ToolHive through natural language in Cursor and other MCP-compatible applications.

### Install ToolHive
See details at https://github.com/stacklok/toolhive

### Then add ToolHive MCP
```
{
    "mcpServers": {
        "toolhive-controller": {
            "command": "npx",
            "args": [
                "-y",
                "toolhive-mcp"
            ],
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
