# ToolHive MCP Server Makefile
# Simple commands for common tasks

.PHONY: help setup run clean install test status

# Default target
help:
	@echo "🚀 ToolHive MCP Server Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - One-time setup (creates venv, installs deps, configures Cursor)"
	@echo "  make run      - Run the server with automatic checks"
	@echo "  make install  - Install dependencies only"
	@echo "  make clean    - Clean up virtual environment and cache files"
	@echo "  make test     - Test the server connection"
	@echo "  make status   - Check system status"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup && make run"

# One-time setup
setup:
	@echo "🔧 Setting up ToolHive MCP Server..."
	python3 setup.py

# Run the server
run:
	@echo "🚀 Starting ToolHive MCP Server..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python run.py; \
	else \
		python run.py; \
	fi

# Install dependencies only
install:
	@echo "📦 Installing dependencies..."
	@if [ ! -d .venv ]; then python3 -m venv .venv; fi
	@. .venv/bin/activate && pip install --upgrade pip && pip install -e .
	@echo "✅ Dependencies installed"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .venv
	rm -rf __pycache__
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".DS_Store" -delete
	@echo "✅ Cleanup complete"

# Test server connection
test:
	@echo "🧪 Testing server..."
	@if [ -f .venv/bin/activate ]; then \
		. .venv/bin/activate && python -c "import requests; print('✅ Server reachable' if requests.get('http://localhost:8080/health', timeout=2).status_code == 204 else '❌ Server not running')"; \
	else \
		python -c "import requests; print('✅ Server reachable' if requests.get('http://localhost:8080/health', timeout=2).status_code == 204 else '❌ Server not running')"; \
	fi

# Check system status
status:
	@echo "📊 System Status:"
	@echo "Python: $(shell python3 --version)"
	@echo "Virtual env: $(shell [ -d .venv ] && echo '✅ Exists' || echo '❌ Missing')"
	@echo "Dependencies: $(shell [ -f .venv/bin/python ] && .venv/bin/python -c 'import mcp; print("✅ Installed")' 2>/dev/null || echo '❌ Missing')"
	@echo "ToolHive CLI: $(shell command -v thv >/dev/null 2>&1 && echo '✅ Available' || echo '❌ Missing')"
	@echo "Config file: $(shell [ -f cursor_mcp_config.json ] && echo '✅ Exists' || echo '❌ Missing')" 