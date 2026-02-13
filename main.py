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
from agents import create_banking_workflow
from bootstrap import bootstrap
from agent_framework import WorkflowEvent, AgentResponse
from agent_framework.orchestrations import HandoffAgentUserRequest
from agent_framework._workflows._workflow import Workflow
from agent_framework._workflows._agent import WorkflowAgent


def check_connectivity(endpoint: str) -> bool:
    try:
        r = httpx.get(f"{endpoint.rstrip('/')}/models", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def parse_txt(content: Any) -> str:
    """Recursively extracts clean text from complex nested AI outputs."""
    if content is None:
        return ""

    if isinstance(content, str):
        content = content.strip()
        # 1. Clean markdown code blocks
        content = re.sub(r"```json\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL)

        # 2. Check for stringified JSON artifacts
        if content.startswith("[") or content.startswith("{"):
            try:
                # Handle double-encoded artifacts
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
                        # Aggressive noise reduction
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


async def chat(agent: WorkflowAgent, mode: str):
    thread = agent.get_new_thread()
    # AgentThread identifier handling
    display_id = thread.service_thread_id or uuid.uuid4().hex[:8]
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {display_id}")
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
                # Use the thread's underlying conversation management
                response = await agent.run(prompt, thread=thread)
                # Convert response to events for handle_events consistency
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
                # WorkflowAgent handles responses internally via run() when pending_requests is populated
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


def run():
    p = argparse.ArgumentParser()
    p.add_argument("--user", choices=["alice", "bob"])
    p.add_argument("--bootstrap", action="store_true")
    p.add_argument("--mode", choices=["local", "hosted"], default="local")
    p.add_argument("--devui", action="store_true")
    args = p.parse_args()

    try:
        if args.bootstrap or not os.path.exists("data/bank.db"):
            bootstrap()
            if args.bootstrap:
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

        if args.mode == "local":
            url = os.getenv("FOUNDRY_LOCAL_ENDPOINT", "http://localhost:8080/v1")
            if not check_connectivity(url):
                print(f"Warning: Local LLM unreachable at {url}")

        wf = create_banking_workflow(ledger, ident, user, token, mode=args.mode)
        if args.devui:
            from agent_framework.devui import serve

            serve(entities=[wf], auto_open=True, port=8081)
        else:
            agent = wf.as_agent(name="BankingWorkflowAgent")
            asyncio.run(chat(agent, args.mode))
    except EOFError, KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
