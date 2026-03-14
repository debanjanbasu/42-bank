#!/usr/bin/env bash
set -e

USER="${1:-alice}"
MODEL="${2:-qwen2.5-1.5b}"

echo "🏦 42 Bank - Local Development"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "User: $USER | Model: $MODEL"
echo ""

# 1. Foundry Local
echo "1️⃣ Checking Foundry Local..."
FOUNDRY_URL=$(foundry service status 2>/dev/null | grep -oE 'http://[^/]+' | head -1)
if [ -z "$FOUNDRY_URL" ] || ! curl -s "$FOUNDRY_URL/v1/models" >/dev/null 2>&1; then
	echo "⚠️ Foundry Local not responding. Starting model: $MODEL"
	foundry model run "$MODEL" &
	FOUNDRY_PID=$!
	for i in $(seq 1 90); do
		FOUNDRY_URL=$(foundry service status 2>/dev/null | grep -oE 'http://[^/]+' | head -1)
		if [ -n "$FOUNDRY_URL" ] && curl -s "$FOUNDRY_URL/v1/models" >/dev/null 2>&1; then
			break
		fi
		sleep 1
	done
	if [ -z "$FOUNDRY_URL" ]; then
		echo "❌ Foundry Local failed to start"
		exit 1
	fi
	echo "✅ Foundry Local: $FOUNDRY_URL"
else
	echo "✅ Foundry Local: $FOUNDRY_URL"
fi

# 2. Cosmos DB
echo ""
echo "2️⃣ Checking Cosmos DB Emulator..."
if ! docker info >/dev/null 2>&1; then
	echo "❌ Docker not running"
	exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -q "42bank-cosmos"; then
	docker-compose up -d cosmos-emulator
	for i in $(seq 1 60); do
		if curl -s http://localhost:1234 >/dev/null 2>&1; then break; fi
		sleep 1
	done
fi
if ! curl -s http://localhost:1234 >/dev/null 2>&1; then
	echo "❌ Cosmos emulator not responding"
	exit 1
fi
echo "✅ Cosmos DB ready"

# 3. Bootstrap
echo ""
echo "3️⃣ Seeding database..."
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
export COSMOS_DATABASE="banking"
uv run python bootstrap.py
echo "✅ Database ready"

# 4. MCP Server
echo ""
echo "4️⃣ Starting MCP server (port 8001)..."
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
	echo "⚠️ MCP server already running"
else
	uv run python mcp_server.py --http --user "$USER" --port 8001 >/tmp/42bank-mcp.log 2>&1 &
	for i in $(seq 1 30); do
		if curl -s http://localhost:8001/health >/dev/null 2>&1; then break; fi
		sleep 1
	done
	echo "✅ MCP server ready"
fi

# 5. Mobile API
echo ""
echo "5️⃣ Starting Mobile API (port 8000)..."
if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
	echo "⚠️ Mobile API already running"
else
	uv run uvicorn api:app --host 0.0.0.0 --port 8000 >/tmp/42bank-api.log 2>&1 &
	for i in $(seq 1 30); do
		if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then break; fi
		sleep 1
	done
	echo "✅ Mobile API ready"
fi

# 6. A2A Server
echo ""
echo "6️⃣ Starting A2A server (port 8002)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Cosmos Explorer: http://localhost:1234/"
echo "Mobile API: http://localhost:8000"
echo "A2A Server: http://localhost:8002"
echo ""
export FOUNDRY_LOCAL_ENDPOINT="$FOUNDRY_URL/v1"
export MODEL_NAME="$MODEL"
echo "Running A2A server..."
echo ""

uv run python a2a_server.py --user "$USER" --port 8002
