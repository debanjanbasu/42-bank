import asyncio
import argparse
import os
import httpx
import re
import json
import sys
import uuid
from typing import List, Dict, Union, Any, Optional
from identity import IdentityManager
from ledger import LedgerEngine
from agents import create_banking_workflow, get_foundry_local_endpoint
from bootstrap import bootstrap
from agent_framework import WorkflowEvent, AgentResponse
from agent_framework.orchestrations import HandoffAgentUserRequest
from agent_framework._workflows._workflow import Workflow
from agent_framework._workflows._agent import WorkflowAgent


def parse_txt(content: Any) -> str:
    """Extract clean text from agent outputs."""
    if content is None:
        return ""
    
    if isinstance(content, str):
        content = content.strip()
        # Filter out JSON-like structures
        if content.startswith("[{") or content.startswith("{"):
            return ""
        return content
    
    if isinstance(content, dict):
        # Skip handoff and function call dicts
        if content.get("type") in ["handoff", "function_call"]:
            return ""
        return content.get("text", "")
    
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(t for t in texts if t and not t.startswith("[{"))
    
    return str(content)


def handle_events(
    events: List[WorkflowEvent[Any]],
) -> List[WorkflowEvent[HandoffAgentUserRequest]]:
    hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []
    for e in events:
        if e.type == "handoff_sent":
            source = e.data.source if hasattr(e.data, 'source') else 'Agent'
            target = e.data.target if hasattr(e.data, 'target') else 'Agent'
            print(f"[Handoff: {source} → {target}]")
        elif e.type == "output" and isinstance(e.data, AgentResponse):
            for msg in e.data.messages:
                sender = msg.author_name or msg.role
                for c in msg.contents:
                    if c.type == "text_reasoning":
                        # Skip reasoning output for cleaner UI
                        pass
                    elif c.type == "text":
                        txt = parse_txt(c.text).strip()
                        if txt and "Continue assisting" not in txt and "handoff" not in txt.lower():
                            print(f"\n{sender}: {txt}\n")
                    elif c.type == "function_call":
                        # Only show important function calls
                        if c.name not in ["request_info"]:
                            print(f"[Calling: {c.name}]")
        elif e.type == "request_info" and isinstance(e.data, HandoffAgentUserRequest):
            # Human in loop request - show the agent's message
            for msg in e.data.agent_response.messages:
                for c in msg.contents:
                    if c.type == "text":
                        txt = parse_txt(c.text).strip()
                        if txt and not txt.startswith("[{"):
                            print(f"\n{msg.author_name or msg.role}: {txt}\n")
            hil.append(e)
    return hil


async def chat(agent: Any, mode: str, endpoint: Optional[str] = None):
    session_id = uuid.uuid4().hex[:8]
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {session_id}")
    if endpoint:
        print(f"LLM Endpoint: {endpoint}")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")

    pending_hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []

    while True:
        try:
            label = "You (reply): " if pending_hil else "You: "
            try:
                prompt = input(label).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                break

            print("[Processing...]")
            response = await agent.run(prompt)
            events = [
                WorkflowEvent(
                    type="output", data=response, source_executor_id=agent.id
                )
            ]
            pending_hil = handle_events(events)

        except Exception as err:
            print(f"Error: {err}")
            pending_hil = []


def run_a2a(args):
    """Run the A2A server."""
    from a2a_server import run_a2a_server

    asyncio.run(
        run_a2a_server(
            host=args.host,
            port=args.port,
            username=args.user,
            mode=args.mode,
            model_name=args.model,
        )
    )


def run_mcp(args):
    """Run the MCP server."""
    from mcp_server import run_http, run_stdio

    if args.stdio:
        run_stdio(username=args.user)
    else:
        run_http(host=args.host, port=args.port, username=args.user)


def run():
    p = argparse.ArgumentParser(description="42-Bank: A2A/MCP Compliant Banking Agents")
    p.add_argument("--user", choices=["alice", "bob"], default="alice")
    p.add_argument("--bootstrap", action="store_true")
    p.add_argument("--mode", choices=["local", "hosted"], default="local")
    p.add_argument("--devui", action="store_true")
    p.add_argument("--model", default=None, help="Model name/deployment")

    server_group = p.add_mutually_exclusive_group()
    server_group.add_argument("--a2a", action="store_true", help="Run as A2A server")
    server_group.add_argument("--mcp", action="store_true", help="Run as MCP server")

    p.add_argument("--host", default="0.0.0.0", help="Server host")
    p.add_argument(
        "--port", type=int, default=8000, help="Server port (A2A: 8000, MCP: 8001)"
    )
    p.add_argument("--stdio", action="store_true", help="Run MCP in stdio mode")

    args = p.parse_args()

    try:
        if args.bootstrap or not os.path.exists("data/bank.db"):
            bootstrap()
        if args.bootstrap:
            return

        if args.a2a:
            run_a2a(args)
            return

        if args.mcp:
            if args.port == 8000:
                args.port = 8001
            run_mcp(args)
            return

        user = args.user or input("User (alice/bob): ").strip().lower()
        ident, ledger = IdentityManager(), LedgerEngine()
        token = ident.get_token(user)
        if not token:
            print(f"User {user} not found.")
            return

        pk = ident.get_public_key(user)
        if pk:
            ledger.register_user(token, user, pk.hex())

        endpoint = None
        if args.mode == "local":
            try:
                endpoint = get_foundry_local_endpoint()
            except RuntimeError as e:
                print(f"\n{e}")
                print("\nTo start Foundry Local:")
                print("  foundry model run Phi-4-mini-instruct-generic-gpu:5")
                return

        wf = create_banking_workflow(
            ledger, ident, user, token, mode=args.mode, model_name=args.model
        )
        if args.devui:
            from agent_framework.devui import serve

            serve(entities=[wf], auto_open=True, port=8081)
        else:
            agent = wf.as_agent(name="BankingWorkflowAgent")
            asyncio.run(chat(agent, args.mode, endpoint))
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
