# ADR-0003: Model Context Protocol (MCP) for Banking Tools

**Status:** Accepted  
**Date:** 2024-01-15

## Context
AI agents need to call banking operations (check balance, transfer funds). Options: gRPC, REST API, MCP, function calling.

## Decision
Use **MCP (Model Context Protocol)** to expose banking tools to agents.

## Rationale
- **Standardized:** Open protocol adopted by Claude, OpenAI, and others
- **Agent-native:** Tools are self-describing with JSON Schema — no prompt engineering needed
- **Composable:** Agents can discover and combine tools dynamically
- **Azure Functions:** MCP Extension allows serverless deployment

## Alternatives Rejected
- **gRPC:** Requires schema compilation, not natively understood by LLMs
- **REST API:** Works but requires manual tool description in system prompts
- **Direct function calling:** Tight coupling between agent and implementation

## Consequences
- MCP is a newer protocol; tooling less mature than REST
- Tool descriptions must be kept accurate for agent to use correctly
- Requires MCP-compatible agent runtime
