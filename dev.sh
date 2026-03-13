#!/usr/bin/env bash
set -e

USER="${1:-alice}"
MODEL="${2:-qwen2.5-14b}"

echo "🏦 42 Bank - Local Development"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "User: $USER | Model: $MODEL"
echo ""

# 1. Foundry Local
echo "1️⃣  Checking Foundry Local..."
FOUNDRY_URL=$(foundry service status 2>/dev/null | grep -oE 'http://[^/]+' | head -1)
if [ -z "$FOUNDRY_URL" ] || ! curl -s "$FOUNDRY_URL/v1/models" >/dev/null 2>&1; then
    echo "❌ Foundry Local is not running. Start it with:"
    echo "   foundry model run $MODEL"
    exit 1
fi
echo "✅ Foundry Local: $FOUNDRY_URL"

# 2. Cosmos DB Emulator (required)
echo ""
echo "2️⃣  Checking Cosmos DB Emulator..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Start Docker Desktop and retry."
    exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -q "42bank-cosmos"; then
    echo "Starting Cosmos DB Emulator..."
    docker-compose up -d cosmos-emulator
    echo "Waiting for emulator (up to 60s)..."
	for i in $(seq 1 60); do
		if curl -s http://localhost:1234 >/dev/null 2>&1; then break; fi
		sleep 1
	done
fi
if ! curl -s http://localhost:1234 >/dev/null 2>&1; then
    echo "❌ Cosmos emulator not responding. Check: docker-compose logs cosmos-emulator"
    exit 1
fi
echo "✅ Cosmos DB Emulator ready"

# 3. Seed database
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
export COSMOS_DATABASE="banking"
echo ""
echo "3️⃣  Seeding database..."
uv run python bootstrap.py
echo "✅ Database ready"

# 4. Start MCP server
echo ""
echo "4️⃣  Starting MCP server (port 8001)..."
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "⚠️  MCP server already running (skipping restart)"
else
    uv run python mcp_server.py --http --user "$USER" --port 8001 >/tmp/42bank-mcp.log 2>&1 &
    MCP_PID=$!
    for i in $(seq 1 30); do
        if curl -s http://localhost:8001/health >/dev/null 2>&1; then break; fi
        sleep 1
    done
    echo "✅ MCP server ready (PID: $MCP_PID)"
fi

# 5. Start A2A server
echo ""
echo "5️⃣  Starting A2A server (port 8000)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Cosmos Explorer: http://localhost:1234/"
echo ""
export FOUNDRY_LOCAL_ENDPOINT="$FOUNDRY_URL/v1"
export MODEL_NAME="$MODEL"
exec uv run python a2a_server.py --user "$USER"
