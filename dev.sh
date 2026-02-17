#!/usr/bin/env bash
set -e

# 42 Bank - Local Development Startup Script with MCP
# Starts MCP server (tools) + A2A server (agents)

USER="${1:-alice}"
MODEL="${2:-qwen2.5-14b-instruct-generic-gpu:4}"

echo "🏦 42 Bank - Local Development Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "User: $USER"
echo "Model: $MODEL"
echo ""

# 1. Check Foundry Local
echo "1️⃣  Checking Foundry Local..."
# Discover Foundry Local dynamically
FOUNDRY_URL=$(foundry service status 2>/dev/null | grep -oE 'http://[^/]+' | head -1)

if [ -z "$FOUNDRY_URL" ] || ! curl -s "$FOUNDRY_URL/v1/models" >/dev/null 2>&1; then
    echo "❌ Foundry Local is not running!"
    echo ""
    echo "Start it with:"
    echo "  foundry model run $MODEL"
    exit 1
fi
echo "✅ Foundry Local is running on $FOUNDRY_URL"

# 2. Bootstrap database if needed
if [ ! -f "data/bank.db" ]; then
    echo ""
    echo "2️⃣  Initializing database..."
    uv run python bootstrap.py >/dev/null
    echo "✅ Database initialized"
else
    echo ""
    echo "2️⃣  Database already exists"
fi

# 3. Check MCP server
echo ""
echo "3️⃣  Checking MCP server (port 8001)..."
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "⚠️  MCP server already running"
    read -p "Restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "mcp_server.py" || true
        sleep 2
    fi
fi

# 4. Check A2A server
echo ""
echo "4️⃣  Checking A2A server (port 8000)..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "⚠️  A2A server already running"
    read -p "Restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "a2a_server.py" || true
        sleep 2
    else
        echo ""
        echo "✅ All systems ready!"
        echo ""
        echo "Start CLI:"
        echo "  uv run main.py --user $USER"
        exit 0
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting servers..."
echo ""

# Start MCP server in background
echo "Starting MCP server (banking tools) on port 8001..."
env FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:61574/v1 \
    uv run python mcp_server.py --http --user $USER --port 8001 >/tmp/42bank-mcp.log 2>&1 &
MCP_PID=$!

# Wait for MCP server
for i in {1..30}; do
    if curl -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ MCP server ready (PID: $MCP_PID)"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "❌ MCP server failed to start"
        echo "Check logs: tail -f /tmp/42bank-mcp.log"
        kill $MCP_PID 2>/dev/null || true
        exit 1
    fi
done

echo ""
echo "Starting A2A server (agents) on port 8000..."
echo "Press Ctrl+C to stop both servers"
echo ""

# Start A2A server in foreground (blocks here)
exec env FOUNDRY_LOCAL_ENDPOINT="$FOUNDRY_URL/v1" \
     MODEL_NAME=$MODEL \
     uv run python a2a_server.py --user $USER
