#!/usr/bin/env bash
set -e

# 42 Bank - Local Development Startup Script
# 
# Supports two database modes:
#   - sqlite (default): Fast, no Docker required
#   - cosmos: Production parity using Cosmos DB emulator
#
# Usage:
#   ./dev.sh alice                    # SQLite (default)
#   DB_MODE=cosmos ./dev.sh alice     # Cosmos DB emulator
#
# Prerequisites for Cosmos mode:
#   - Docker Desktop installed and running
#   - Run: docker-compose up -d cosmos-emulator

USER="${1:-alice}"
MODEL="${2:-qwen2.5-14b-instruct-generic-gpu:4}"
DB_MODE="${DB_MODE:-sqlite}"  # sqlite or cosmos

echo "🏦 42 Bank - Local Development Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "User: $USER"
echo "Model: $MODEL"
echo "Database: $DB_MODE"
echo ""

# 1. Check Foundry Local
echo "1️⃣ Checking Foundry Local..."
FOUNDRY_URL=$(foundry service status 2>/dev/null | grep -oE 'http://[^/]+' | head -1)

if [ -z "$FOUNDRY_URL" ] || ! curl -s "$FOUNDRY_URL/v1/models" >/dev/null 2>&1; then
    echo "❌ Foundry Local is not running!"
    echo ""
    echo "Start it with:"
    echo "  foundry model run $MODEL"
    exit 1
fi
echo "✅ Foundry Local: $FOUNDRY_URL"

# 2. Database setup
echo ""
echo "2️⃣ Checking database..."

if [ "$DB_MODE" = "cosmos" ]; then
    # Cosmos DB Emulator mode
    echo "Using Cosmos DB Emulator..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo "❌ Docker is not running!"
        echo "Start Docker Desktop and try again."
        echo ""
        echo "Or use SQLite mode: ./dev.sh $USER"
        exit 1
    fi
    
    # Check if emulator is running
    if ! docker ps | grep -q "42bank-cosmos"; then
        echo "Starting Cosmos DB Emulator..."
        docker-compose up -d cosmos-emulator 2>/dev/null || {
            echo "❌ Failed to start Cosmos emulator"
            echo "Try: docker-compose up -d cosmos-emulator"
            exit 1
        }
        echo "Waiting for emulator to start (30 seconds)..."
        sleep 30
    fi
    
    # Health check
    if curl -sk https://localhost:8081/_explorer/index.html >/dev/null 2>&1; then
        echo "✅ Cosmos DB Emulator ready"
    else
        echo "❌ Cosmos DB Emulator not responding"
        echo "Check: docker-compose logs cosmos-emulator"
        exit 1
    fi
    
    # Set environment variables for Cosmos
    export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
    export COSMOS_DATABASE="banking"
    
    # Check if database is initialized
    echo ""
    echo "Initializing Cosmos DB (if needed)..."
    uv run python scripts/init-cosmos-local.py 2>/dev/null || true
    echo "✅ Cosmos DB ready"
    
else
    # SQLite mode (default)
    if [ ! -f "data/bank.db" ]; then
        echo "Initializing SQLite database..."
        uv run python bootstrap.py >/dev/null 2>&1
        echo "✅ SQLite database initialized"
    else
        echo "✅ SQLite database ready"
    fi
fi

# 3. Check MCP server
echo ""
echo "3️⃣ Checking MCP server (port 8001)..."
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
echo "4️⃣ Checking A2A server (port 8000)..."
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
        echo ""
        echo "Data Explorer (Cosmos mode):"
        echo "  https://localhost:1234/_explorer/index.html"
        exit 0
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting servers..."
echo ""

# Start MCP server in background
echo "Starting MCP server (banking tools) on port 8001..."
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

# Set environment for servers
export FOUNDRY_LOCAL_ENDPOINT="$FOUNDRY_URL/v1"
export MODEL_NAME="$MODEL"

# Show useful links
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Links:"
echo "  CLI: uv run main.py --user $USER"
if [ "$DB_MODE" = "cosmos" ]; then
    echo "  Cosmos Explorer: https://localhost:1234/_explorer/index.html"
fi
echo ""

# Start A2A server in foreground (blocks here)
exec uv run python a2a_server.py --user $USER
