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
from agent_framework import AgentResponse, AgentThread, Message, Content
from agent_framework._workflows._agent import WorkflowAgent


def check_connectivity(endpoint: str) -> bool:
    try:
        r = httpx.get(f"{endpoint.rstrip('/')}/models", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def parse_txt(content: Any) -> str:
    if isinstance(content, str):
        # Clean JSON artifacts often seen in small model outputs
        content = re.sub(r"^\[?\{'type': 'text', 'text': ['\"]", "", content)
        content = re.sub(r"['\"]\}\]?$", "", content)
        return content.strip()
    if isinstance(content, dict):
        return parse_txt(content.get("text", ""))
    if isinstance(content, list):
        return " ".join(parse_txt(i) for i in content)
    return str(content)


async def chat(agent: WorkflowAgent, mode: str):
    thread = agent.get_new_thread()
    # AgentThread doesn't have a public .id attribute in all versions,
    # use a local identifier for display if service_thread_id is missing.
    display_id = thread.service_thread_id or uuid.uuid4().hex[:8]
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {display_id}")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")

    while True:
        try:
            prompt = input("You: ").strip()
            if not prompt or prompt.lower() in ["exit", "quit"]:
                break

            print("[Thinking...]")
            # WorkflowAgent.run() maintains state via the thread and internal workflow session
            response = await agent.run(prompt, thread=thread)

            for msg in response.messages:
                sender = msg.author_name or msg.role
                for c in msg.contents:
                    if c.type == "text":
                        txt = parse_txt(c.text)
                        if txt and len(txt) > 2 and "Continue" not in txt:
                            print(f"\n{sender}: {txt}\n")
                    elif c.type == "function_call":
                        if c.name == WorkflowAgent.REQUEST_INFO_FUNCTION_NAME:
                            # This is a HIL request from the workflow
                            pass
                        else:
                            print(f"[System: {sender} called {c.name}({c.arguments})]")

        except EOFError, KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as err:
            print(f"Error: {err}")


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

        user = args.user
        if not user:
            try:
                user = input("User (alice/bob): ").strip().lower()
            except EOFError, KeyboardInterrupt:
                print("\nExiting...")
                return

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

            print(f"\nLaunching DevUI for {user.capitalize()} on port 8081...")
            serve(entities=[wf], auto_open=True, port=8081)
        else:
            # Use WorkflowAgent for persistent memory within a session
            agent = wf.as_agent(name="BankingWorkflowAgent")
            asyncio.run(chat(agent, args.mode))

    except EOFError, KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
