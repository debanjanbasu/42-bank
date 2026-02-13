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


def check_connectivity(endpoint: str) -> bool:
    try:
        r = httpx.get(f"{endpoint.rstrip('/')}/models", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def clean_output(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL)
    text = re.sub(r"\[?\{'type': 'text'.*?\}\]?", "", text, flags=re.DOTALL)
    text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
    return text.strip()


def parse_txt(content: Any) -> str:
    if isinstance(content, str):
        # Strip stringified JSON artifacts
        content = re.sub(r"^\[?\{'type': 'text', 'text': ['\"]", "", content)
        content = re.sub(r"['\"]\}\]?$", "", content)
        return content.strip()
    if isinstance(content, dict):
        return parse_txt(content.get("text", ""))
    if isinstance(content, list):
        return " ".join(parse_txt(i) for i in content)
    return str(content)


def handle_events(
    events: List[WorkflowEvent[Any]],
) -> List[WorkflowEvent[HandoffAgentUserRequest]]:
    hil = []
    for e in events:
        if e.type == "handoff_sent":
            print(f"\n[Handoff: {e.data.source} -> {e.data.target}]")
        elif e.type == "output" and isinstance(e.data, AgentResponse):
            for msg in e.data.messages:
                sender = msg.author_name or msg.role
                for c in msg.contents:
                    if c.type == "text":
                        txt = parse_txt(c.text)
                        if txt and len(txt) > 5 and "Continue" not in txt:
                            print(f"\n{sender}: {txt}\n")
                    elif c.type == "function_call":
                        print(f"[System: {sender} called {c.name}({c.arguments})]")
        elif e.type == "request_info":
            hil.append(e)
    return hil


async def chat(wf: Workflow, mode: str):
    conv_id = str(uuid.uuid4())
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {conv_id[:8]}")
    print("Type 'exit' or Ctrl+C to quit.")

    pending_hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []

    while True:
        try:
            label = "You (reply): " if pending_hil else "You: "
            prompt = input(label).strip()
            if not prompt or prompt.lower() in ["exit", "quit"]:
                break

            print("[Thinking...]")
            if not pending_hil:
                # Use a consistent conversation_id for memory
                events = [
                    ev
                    async for ev in wf.run(prompt, conversation_id=conv_id, stream=True)
                ]
            else:
                resps = {
                    req.request_id: HandoffAgentUserRequest.create_response(prompt)
                    for req in pending_hil
                }
                events = await wf.run(responses=resps, conversation_id=conv_id)

            pending_hil = handle_events(events)

        except EOFError, KeyboardInterrupt:
            print("\nExiting...")
            break
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

        wf = create_banking_workflow(ledger, ident, user, token, mode=args.mode)
        if args.devui:
            from agent_framework.devui import serve

            serve(entities=[wf], auto_open=True, port=8081)
        else:
            asyncio.run(chat(wf, args.mode))
    except EOFError, KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
