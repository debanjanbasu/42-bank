import asyncio
import argparse
import os
import httpx
import re
import json
import sys
import uuid
import readline
from pathlib import Path
from typing import Dict, Any, Optional
from bootstrap import bootstrap
from identity import IdentityManager
from ledger import LedgerEngine
from utils import get_foundry_local_endpoint

# Configure readline for better input experience
HISTORY_FILE = Path.home() / ".42bank_history"


def setup_readline():
    """Setup readline for command history and arrow key navigation."""
    try:
        # Enable tab completion
        readline.parse_and_bind("tab: complete")
        
        # Enable arrow key navigation
        readline.parse_and_bind("set editing-mode emacs")
        
        # Load history from file
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
        
        # Set history length
        readline.set_history_length(1000)
    except Exception:
        pass  # Readline might not be available on all platforms


def clean_agent_response(text: str) -> str:
    """Clean up agent response text by removing tool call markup."""
    # Remove <tool_call>...</tool_call> blocks
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    # Remove Thai/multilingual prefixes (common in model responses)
    text = re.sub(r'^[\u0E00-\u0E7F\s]+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\n\n+', '\n\n', text.strip())
    return text.strip()


async def chat_async(user: str, a2a_url: str = "http://localhost:8000"):
    """Chat via A2A triage agent (which routes to specialists)."""
    from identity import IdentityManager
    from ledger import LedgerEngine
    import aiohttp
    
    setup_readline()
    session_id = uuid.uuid4().hex[:8]
    
    # Setup
    ident, ledger = IdentityManager(), LedgerEngine()
    token = ident.get_token(user)
    pk = ident.get_public_key(user)
    if pk:
        ledger.register_user(token, user, pk.hex())
    
    print(f"\nConnected to 42 Bank ({user.upper()}). Session: {session_id}")
    print(f"A2A Triage: {a2a_url}/a2a/triage")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")
    print("Use ↑/↓ arrow keys to navigate command history.\n")

    # Call triage agent - it routes to specialists internally
    triage_url = f"{a2a_url}/a2a/triage/v1/message"
    
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    prompt = input("You: ").strip()
                    if not prompt or prompt.lower() in ["exit", "quit"]:
                        break

                    print("[Processing...]")
                    
                    payload = {
                        "message": {
                            "parts": [{"kind": "text", "text": prompt}]
                        }
                    }
                    
                    async with session.post(triage_url, json=payload) as resp:
                        if resp.status != 200:
                            print(f"\n❌ Error: HTTP {resp.status}")
                            continue
                        
                        result = await resp.json()
                        # Extract text from A2A response
                        if "result" in result and "parts" in result["result"]:
                            for part in result["result"]["parts"]:
                                if part.get("kind") == "text":
                                    text = part.get("text", "")
                                    cleaned = clean_agent_response(text)
                                    if cleaned:
                                        print(f"\n{cleaned}\n")
                        else:
                            print(f"\n{result}\n")

                except KeyboardInterrupt:
                    print("\n")
                    break
                except EOFError:
                    break
                except Exception as err:
                    print(f"\n❌ Error: {err}\n")
    finally:
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except:
            pass


def chat_sync(a2a_url: str, user: str):
    """Synchronous chat interface that calls triage agent via A2A HTTP."""
    import requests
    
    setup_readline()
    session_id = uuid.uuid4().hex[:8]
    context_id = str(uuid.uuid4())
    
    print(f"\nConnected to 42 Bank ({user.upper()}). Session: {session_id}")
    print(f"A2A Endpoint: {a2a_url}")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")
    print("Use ↑/↓ arrow keys to navigate command history.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input:
                continue

            print("[Processing...]")
            
            # Call triage agent via A2A HTTP with streaming support
            # Use streaming endpoint for real-time responses
            use_streaming = True  # Enable streaming for better UX
            
            if use_streaming:
                endpoint = f"{a2a_url}/a2a/triage/v1/message:stream"
                
                # Stream response with SSE
                response = requests.post(
                    endpoint,
                    json={
                        "message": {
                            "parts": [{"kind": "text", "text": user_input}],
                            "contextId": context_id
                        }
                    },
                    stream=True,
                    timeout=None  # No timeout for streaming
                )
                
                if response.status_code == 200:
                    print()  # New line before streaming output
                    full_text = ""
                    
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]  # Remove 'data: ' prefix
                                
                                if data_str == '[DONE]':
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    if 'result' in data:
                                        for part in data['result'].get('parts', []):
                                            if part.get('kind') == 'text':
                                                text = part.get('text', '')
                                                full_text += text
                                    elif 'error' in data:
                                        print(f"❌ Error: {data['error'].get('message', 'Unknown error')}")
                                        break
                                except json.JSONDecodeError:
                                    pass
                    
                    # Filter tool calls and Thai text from final response
                    import re
                    clean_text = re.sub(r'<tool_call>.*?</tool_call>', '', full_text, flags=re.DOTALL)
                    clean_text = re.sub(r'\{[^}]*"name"[^}]*"send_money"[^}]*\}', '', clean_text)
                    clean_text = re.sub(r'\{[^}]*"name"[^}]*"arguments"[^}]*\}', '', clean_text)
                    # Remove Thai text (Unicode range 0e00-0e7f)
                    clean_text = re.sub(r'[\u0e00-\u0e7f]+', '', clean_text)
                    clean_text = clean_text.strip()
                    
                    if clean_text:
                        print(clean_text)
                    
                    print()  # Final newline
                else:
                    print(f"❌ Error: HTTP {response.status_code}")
            else:
                # Non-streaming fallback
                response = requests.post(
                    f"{a2a_url}/a2a/triage/v1/message",
                    json={
                        "message": {
                            "parts": [{"kind": "text", "text": user_input}],
                            "contextId": context_id
                        }
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract text from response parts
                    text = ""
                    for part in data.get("parts", []):
                        if part.get("kind") == "text":
                            text += part.get("text", "")
                    
                    # Clean up tool call markup and formatting
                    cleaned_text = clean_agent_response(text)
                    
                    if cleaned_text:
                        print(f"\n{cleaned_text}\n")
                    else:
                        print("\nNo response received. Please try again.\n")
                else:
                    print(f"❌ Error: HTTP {response.status_code}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nExiting...")
    try:
        readline.write_history_file(str(HISTORY_FILE))
    except:
        pass


async def chat(agent: Any, mode: str, endpoint: Optional[str] = None):
    """Interactive chat with command history support."""
    setup_readline()
    
    session_id = uuid.uuid4().hex[:8]
    print(f"\nConnected to 42 Bank ({mode.upper()}). Session: {session_id}")
    if endpoint:
        print(f"LLM Endpoint: {endpoint}")
    print("Type 'exit', 'quit' or use Ctrl+C to quit.")
    print("Use ↑/↓ arrow keys to navigate command history.\n")

    pending_hil: List[WorkflowEvent[HandoffAgentUserRequest]] = []

    try:
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
                
                # Handle pending human-in-the-loop requests
                if pending_hil:
                    # Respond to the pending request
                    hil_event = pending_hil[0]
                    response = await agent.run(
                        prompt,
                        request_info_response={
                            "request_id": hil_event.data.request_id,
                            "response": prompt
                        }
                    )
                    pending_hil = []
                else:
                    # Normal message
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
    finally:
        # Save history on exit
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except Exception:
            pass


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
                print("  foundry model run qwen2.5-1.5b-instruct-generic-gpu:4")
                return

        # Verify A2A server is running
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code != 200:
                print("\n⚠ A2A server health check failed")
                print("\nStart the A2A server:")
                print(f"  uv run a2a_server.py --user {user}")
                return
        except Exception as e:
            print(f"\n⚠ Cannot connect to A2A server at http://localhost:8000")
            print("\nStart the A2A server in another terminal:")
            print(f"  uv run a2a_server.py --user {user}")
            return

        # Use A2A protocol for all agent communication
        a2a_url = "http://localhost:8000"
        
        if args.devui:
            print("\nDevUI not supported in A2A mode.")
        else:
            asyncio.run(chat_async(user, a2a_url))
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    run()
