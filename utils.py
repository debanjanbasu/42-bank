"""Shared utilities for banking agents."""

import json
import os
import re
from typing import Optional

from dotenv import load_dotenv
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI, AsyncAzureOpenAI

from azure_projects_compat import patch_azure_projects_models

patch_azure_projects_models()

load_dotenv()

_foundry_endpoint_cache: Optional[str] = None


async def _is_valid_foundry_endpoint(endpoint: str, timeout: float = 2.0) -> bool:
    """Async validation using httpx."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{endpoint}/models")
            if resp.status_code != 200:
                return False
            data = resp.json()
            return isinstance(data.get("data"), list) and len(data["data"]) > 0
    except Exception:
        return False


async def get_foundry_local_endpoint() -> str:
    """
    Discover Foundry Local endpoint dynamically.
    Foundry runs on a random port each time - scan for it or use environment variable.
    """
    global _foundry_endpoint_cache

    if _foundry_endpoint_cache and await _is_valid_foundry_endpoint(
        _foundry_endpoint_cache
    ):
        return _foundry_endpoint_cache

    env_endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
    if env_endpoint and await _is_valid_foundry_endpoint(env_endpoint):
        _foundry_endpoint_cache = env_endpoint
        return env_endpoint

    import asyncio

    # Scan listening ports via lsof
    try:
        proc = await asyncio.create_subprocess_exec(
            "lsof",
            "-nP",
            "-iTCP",
            "-sTCP:LISTEN",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        output = stdout.decode()
        for line in output.split("\n"):
            lower_line = line.lower()
            if "inference" in lower_line or (
                "foundry" in lower_line and "python" not in lower_line
            ):
                match = re.search(r"127\.0\.0\.1:(\d+)\s+\(LISTEN\)", line)
                if not match:
                    match = re.search(r"\*:(\d+)\s+\(LISTEN\)", line)
                if match:
                    port = match.group(1)
                    endpoint = f"http://127.0.0.1:{port}/v1"
                    if await _is_valid_foundry_endpoint(endpoint):
                        _foundry_endpoint_cache = endpoint
                        return endpoint
    except (asyncio.TimeoutError, OSError, FileNotFoundError):
        pass

    # Get from foundry service status
    try:
        proc = await asyncio.create_subprocess_exec(
            "foundry",
            "service",
            "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        output = stdout.decode()
        if "running" in output.lower():
            match = re.search(r"http://([^/:\s]+):(\d+)", output)
            if match:
                host, port = match.groups()
                endpoint = f"http://{host}:{port}/v1"
                if await _is_valid_foundry_endpoint(endpoint):
                    _foundry_endpoint_cache = endpoint
                    return endpoint
    except (asyncio.TimeoutError, OSError, FileNotFoundError):
        pass

    raise RuntimeError(
        "Foundry Local not running or not responding.\n"
        "Start with: foundry model run qwen2.5-1.5b-instruct-generic-gpu:4\n"
        "Or set FOUNDRY_LOCAL_ENDPOINT environment variable to the endpoint.\n"
        "Check status: foundry service status"
    )


async def create_chat_client(mode: str = "local", model_name: Optional[str] = None):
    """Create chat client for local (Foundry) or hosted (Azure) deployment."""
    if mode == "local":
        endpoint = await get_foundry_local_endpoint()
        model_id = model_name or os.getenv(
            "MODEL_NAME", "qwen2.5-1.5b-instruct-generic-gpu:4"
        )

        async_client = AsyncOpenAI(api_key="local-dev-key", base_url=endpoint)
        return OpenAIChatClient(model_id=model_id, async_client=async_client)
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "model-router"
        )

        if not project_endpoint or not api_key:
            raise ValueError(
                "AZURE_AI_PROJECT_ENDPOINT and AZURE_OPENAI_API_KEY required for hosted mode"
            )

        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

        async_client = AsyncAzureOpenAI(
            azure_endpoint=project_endpoint.rstrip("/"),
            api_key=api_key,
            api_version=api_version,
        )
        client = OpenAIChatClient(
            model_id=model_deployment_name, async_client=async_client
        )
        client.function_invocation_configuration["include_detailed_errors"] = True
        client.function_invocation_configuration["max_iterations"] = 40
        return client
