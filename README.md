# ToolHive MCP Server

Control ToolHive through natural language in Cursor and other MCP-compatible applications.

## 🚀 Quick Start

### One Command Setup
```bash
python3 setup.py && python3 run.py
```

That's it! This will:
- ✅ Create virtual environment
- ✅ Install dependencies  
- ✅ Configure Cursor integration
- ✅ Start the server

### Alternative: Using Make
```bash
make setup && make run
```

## What You Can Do

Once set up, use natural language in Cursor to:

- **"List all running MCP servers"**
- **"Start the GitHub MCP server"** 
- **"Search for file-related servers"**
- **"Stop the memory server"**
- **"What's the ToolHive system status?"**

## Requirements

- Python 3.8+
- ToolHive CLI (optional - will be prompted to install if needed)

## Manual Setup (if needed)

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Run setup
python3 setup.py

# 4. Start server
python3 run.py
```

## Cursor Integration

After setup:
1. **Restart Cursor completely**
2. **Start a new chat** 
3. **Try**: "What's the ToolHive system status?"
