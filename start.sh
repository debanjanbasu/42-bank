#!/bin/sh
# 42-Bank Startup Script
# Starts the consolidated FastAPI application
# Port: 8000

set -e

echo "🚀 Starting 42-Bank..."
echo "   API:    http://localhost:8000/api/*"
echo "   A2A:    http://localhost:8000/a2a/*"
echo "   Health: http://localhost:8000/api/health"
echo ""

# Start the consolidated FastAPI app
exec uvicorn api:app --host 0.0.0.0 --port 8000
