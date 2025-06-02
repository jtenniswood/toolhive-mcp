#!/usr/bin/env python3
"""
MCP Demo Client

A simple client to interact with MCP servers using the Python SDK.
This client demonstrates how to connect to servers and use their tools and resources.
"""

import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables from toolhive.env
load_dotenv('toolhive.env')

class MCPClient:
    def __init__(self):
        """Initialize the MCP client"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available capabilities
        print("\n🔗 Connected to MCP server!")
        
        # List tools
        try:
            response = await self.session.list_tools()
            tools = response.tools
            if tools:
                print(f"\n🛠️  Available tools ({len(tools)}):")
                for tool in tools:
                    print(f"  • {tool.name}: {tool.description}")
            else:
                print("\n🛠️  No tools available")
        except Exception as e:
            print(f"Error listing tools: {e}")

        # List resources
        try:
            response = await self.session.list_resources()
            resources = response.resources
            if resources:
                print(f"\n📚 Available resources ({len(resources)}):")
                for resource in resources:
                    print(f"  • {resource.uri}: {resource.description}")
            else:
                print("\n📚 No resources available")
        except Exception as e:
            print(f"Error listing resources: {e}")

        # List prompts
        try:
            response = await self.session.list_prompts()
            prompts = response.prompts
            if prompts:
                print(f"\n💬 Available prompts ({len(prompts)}):")
                for prompt in prompts:
                    print(f"  • {prompt.name}: {prompt.description}")
            else:
                print("\n💬 No prompts available")
        except Exception as e:
            print(f"Error listing prompts: {e}")

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a tool on the server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            return result.content
        except Exception as e:
            return f"Error calling tool '{tool_name}': {e}"

    async def read_resource(self, uri: str):
        """Read a resource from the server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        try:
            content, mime_type = await self.session.read_resource(uri)
            return content, mime_type
        except Exception as e:
            return f"Error reading resource '{uri}': {e}", None

    async def get_prompt(self, name: str, arguments: dict = None):
        """Get a prompt from the server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        try:
            result = await self.session.get_prompt(name, arguments or {})
            return result
        except Exception as e:
            return f"Error getting prompt '{name}': {e}"

    async def interactive_session(self):
        """Run an interactive session with the server"""
        print("\n" + "="*60)
        print("🚀 MCP Interactive Client")
        print("="*60)
        print("Commands:")
        print("  tool <name> [args...]     - Call a tool")
        print("  resource <uri>            - Read a resource")
        print("  prompt <name> [args...]   - Get a prompt")
        print("  help                      - Show this help")
        print("  quit                      - Exit")
        print("="*60)

        while True:
            try:
                command = input("\n> ").strip()
                
                if not command:
                    continue
                    
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if command.lower() == 'help':
                    await self._show_help()
                    continue

                parts = command.split()
                cmd_type = parts[0].lower()

                if cmd_type == 'tool':
                    await self._handle_tool_command(parts[1:])
                elif cmd_type == 'resource':
                    await self._handle_resource_command(parts[1:])
                elif cmd_type == 'prompt':
                    await self._handle_prompt_command(parts[1:])
                else:
                    print(f"❌ Unknown command: {cmd_type}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def _show_help(self):
        """Show detailed help information"""
        if not self.session:
            return
            
        print("\n📖 Detailed Help:")
        
        # Show tools with examples
        try:
            response = await self.session.list_tools()
            tools = response.tools
            if tools:
                print("\n🛠️  Tools:")
                for tool in tools:
                    print(f"  • {tool.name}")
                    print(f"    Description: {tool.description}")
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        schema = tool.inputSchema
                        if hasattr(schema, 'properties') and schema.properties:
                            print(f"    Parameters: {', '.join(schema.properties.keys())}")
                    print(f"    Usage: tool {tool.name} [arguments]")
                    print()
        except Exception as e:
            print(f"Error getting tools: {e}")

        # Show resources with examples
        try:
            response = await self.session.list_resources()
            resources = response.resources
            if resources:
                print("📚 Resources:")
                for resource in resources:
                    print(f"  • {resource.uri}")
                    print(f"    Description: {resource.description}")
                    print(f"    Usage: resource {resource.uri}")
                    print()
        except Exception as e:
            print(f"Error getting resources: {e}")

    async def _handle_tool_command(self, args):
        """Handle tool command"""
        if not args:
            print("❌ Usage: tool <name> [key=value ...]")
            return

        tool_name = args[0]
        
        # Parse arguments (simple key=value format)
        tool_args = {}
        for arg in args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                # Try to parse as number, otherwise keep as string
                try:
                    if '.' in value:
                        tool_args[key] = float(value)
                    else:
                        tool_args[key] = int(value)
                except ValueError:
                    tool_args[key] = value
            else:
                # Positional argument - we'll need to know the parameter name
                # For simplicity, assume first positional arg maps to common names
                if not tool_args:
                    common_names = ['message', 'text', 'query', 'expression', 'title']
                    for name in common_names:
                        tool_args[name] = arg
                        break

        print(f"🔧 Calling tool '{tool_name}' with args: {tool_args}")
        result = await self.call_tool(tool_name, tool_args)
        print(f"✅ Result: {result}")

    async def _handle_resource_command(self, args):
        """Handle resource command"""
        if not args:
            print("❌ Usage: resource <uri>")
            return

        uri = args[0]
        print(f"📖 Reading resource '{uri}'...")
        content, mime_type = await self.read_resource(uri)
        print(f"✅ Content ({mime_type or 'unknown type'}):")
        print(content)

    async def _handle_prompt_command(self, args):
        """Handle prompt command"""
        if not args:
            print("❌ Usage: prompt <name> [key=value ...]")
            return

        prompt_name = args[0]
        
        # Parse arguments
        prompt_args = {}
        for arg in args[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                prompt_args[key] = value

        print(f"💬 Getting prompt '{prompt_name}' with args: {prompt_args}")
        result = await self.get_prompt(prompt_name, prompt_args)
        print(f"✅ Prompt: {result}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        print("Example: python client.py server.py")
        sys.exit(1)

    server_path = sys.argv[1]
    client = MCPClient()
    
    try:
        print("🔌 Connecting to MCP server...")
        await client.connect_to_server(server_path)
        await client.interactive_session()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 