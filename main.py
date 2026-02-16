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
from agents import create_banking_workflow, discover_foundry_local_endpoint
from bootstrap import bootstrap
from agent_framework import WorkflowEvent, AgentResponse
from agent_framework.orchestrations import HandoffAgentUserRequest
from agent_framework._workflows._workflow import Workflow
from agent_framework._workflows._agent import WorkflowAgent


def parse_txt(content: Any) -> str:
    """Recursively extracts clean text from complex nested AI outputs."""
    if content is None:
        return ""

    if isinstance(content, str):
        content = content.strip()
        content = re.sub(r"```json\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL)

        if content.startswith("[") or content.startswith("{"):
            try:
                sanitized = content.replace("\\n", "\n").replace('\\"', '"')
                data = json.loads(sanitized)
                return parse_txt(data)
            except:
                text_match = re.search(
                    r"['\"]text['\"]:\s*['\"](.*?)['\"]", content, flags=re.DOTALL
                )
                if text_match:
                    return text_match.group(1)
        return content

    if isinstance(content, dict):
        if "text" in content:
            return parse_txt(content["text"])
        if content.get("type") == "text":
            return parse_txt(content.get("text", ""))
        return ""

    if isinstance(content, list):
        return " ".join(parse_txt(item) for item in content if item)

    return str(content)


def handle_events(
    events: List[WorkflowEvent[Any]],
) -> List[WorkflowEvent[HandoffAgentUserRequest]]:
    hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []
    for e in events:
        if e.type == "handoff_sent":
            print(f"\n[Handoff: {e.data.source} -> {e.data.target}]")
        elif e.type == "output" and isinstance(e.data, AgentResponse):
            for msg in e.data.messages:
                sender = msg.author_name or msg.role
                for c in msg.contents:
                    if c.type == "text_reasoning":
                        print(f"[{sender} Thinking: {c.text}]")
                    elif c.type == "text":
                        txt = parse_txt(c.text).strip()
                        txt = re.sub(
                            r"\[?\{'type': 'text', 'text': ['\"](.*?)['\"]\}\]?",
                            r"\1",
                            txt,
                        )
                        if (
                            txt.strip()
                            and not txt.startswith("[{")
                            and not "Continue assisting" in txt
                        ):
                            print(f"\n{sender}: {txt.strip()}\n")
                    elif c.type == "function_call":
                        print(f"[System: {sender} called {c.name}({c.arguments})]")
        elif e.type == "request_info" and isinstance(e.data, HandoffAgentUserRequest):
            for msg in e.data.agent_response.messages:
                for c in msg.contents:
                    if c.type == "text":
                        txt = parse_txt(c.text).strip()
                        if txt:
                            print(f"\n{msg.author_name or msg.role}: {txt}\n")
            hil.append(e)
    return hil


async def chat(agent: WorkflowAgent, mode: str, endpoint: str = None):
    thread = agent.get_new_thread()
    display_id = thread.service_thread_id or uuid.uuid4().hex[:8]
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {display_id}")
    if endpoint:
        print(f"LLM Endpoint: {endpoint}")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")

    pending_hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []

    while True:
        try:
            label = "You (reply): " if pending_hil else "You: "
            try:
                prompt = input(label).strip()
            except EOFError, KeyboardInterrupt:
                print("\nExiting...")
                break

            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                break

            print("[Processing...]")
            if not pending_hil:
                response = await agent.run(prompt, thread=thread)
                events = [
                    WorkflowEvent(
                        type="output", data=response, source_executor_id=agent.id
                    )
                ]
            else:
                resps = {
                    req.request_id: HandoffAgentUserRequest.create_response(prompt)
                    for req in pending_hil
                }
                response = await agent.run(prompt, thread=thread)
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
            endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
            if not endpoint:
                endpoint = discover_foundry_local_endpoint()
            if not endpoint:
                print(
                    "Error: Foundry Local not found. Run 'foundry model run <model>' first."
                )
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
    except EOFError, KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
