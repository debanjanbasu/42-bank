# ADR-0004: Agent-to-Agent (A2A) Protocol

**Status:** Accepted  
**Date:** 2024-01-15

## Context
Mobile app needs to communicate with multiple specialized banking agents. Options: direct REST calls, WebSocket, A2A protocol.

## Decision
Use **A2A (Agent-to-Agent) Protocol** for agent communication with SSE streaming.

## Rationale
- **Streaming:** SSE (Server-Sent Events) enables real-time token streaming for better UX
- **Agent cards:** `/a2a` endpoint allows discovery of agent capabilities
- **Standardized:** Emerging standard from Google and partners
- **Multi-agent:** Triage agent routes to specialist agents (transaction, inquiry, advisor)

## Consequences
- SSE requires keep-alive connection management
- Error handling more complex than REST request/response
- Client needs EventSource/polyfill support
