"""Shared utilities for banking agents."""
import os
import re
import subprocess
import urllib.request
from typing import Optional
from dotenv import load_dotenv
from agent_framework.openai import OpenAIChatClient
from agent_framework.azure import AzureAIClient
from azure.identity.aio import DefaultAzureCredential

load_dotenv()


def create_chat_client(mode: str = "local", model_name: Optional[str] = None):
    """Create chat client for local (Foundry) or hosted (Azure) deployment."""
    if mode == "local":
        endpoint = get_foundry_local_endpoint()
        model_id = model_name or os.getenv("MODEL_NAME", "qwen2.5-14b-instruct-generic-gpu:4")
        return OpenAIChatClient(
            model_id=model_id, api_key="local-dev-key", base_url=endpoint
        )
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT required for hosted mode")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "qwen2.5-14b"
        )
        return AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        )


def get_foundry_local_endpoint() -> str:
    """
    Dynamically discover Foundry Local endpoint.
    Foundry runs on a random port each time - use `foundry service status` to discover it.
    """
    # Try environment variable first (allows manual override)
    env_endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
    if env_endpoint:
        return env_endpoint
    
    # Get from foundry service status
    try:
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Output: "🟢 Model management service is running on http://127.0.0.1:57069/openai/status"
            # Extract: http://127.0.0.1:57069
            match = re.search(r'http://([^/:\s]+):(\d+)', result.stdout)
            if match:
                host, port = match.groups()
                return f"http://{host}:{port}/v1"
    except Exception:
        pass
    
    raise RuntimeError(
        "Foundry Local not running or not found.\n"
        "Start with: foundry model run qwen2.5-14b-instruct-generic-gpu:4\n"
        "Check status: foundry service status"
    )
