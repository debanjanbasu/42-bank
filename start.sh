#!/bin/sh
# 42-Bank Startup Script
# Starts the consolidated FastAPI application + MCP server
# Ports: 8000 (API/A2A), 8001 (MCP)

set -e

echo "🚀 Starting 42-Bank..."
echo "   API:    http://localhost:8000/api/*"
echo "   A2A:    http://localhost:8000/a2a/*"
echo "   MCP:    http://localhost:8001/mcp"
echo "   Health: http://localhost:8000/api/health"
echo ""

# Start MCP server in background (used by A2A agents for banking tools)
/app/venv/bin/python mcp_server.py --http --host 0.0.0.0 --port 8001 --user alice &
MCP_PID=$!
echo "📦 MCP server started (PID: $MCP_PID)"

# Give MCP server a moment to start
sleep 2

# Start the consolidated FastAPI app (foreground)
exec /app/venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port 8000
