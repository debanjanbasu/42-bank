"""Shared utilities for banking agents."""
import json
import os
import re
import subprocess
import urllib.request
from typing import Any, Optional

from dotenv import load_dotenv
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncOpenAI

from azure_projects_compat import patch_azure_projects_models

patch_azure_projects_models()

from agent_framework.azure import AzureAIClient

load_dotenv()

_foundry_endpoint_cache: Optional[str] = None


def _is_valid_foundry_endpoint(endpoint: str, timeout: float = 2.0) -> bool:
    """Validate that endpoint is an OpenAI-compatible Foundry server with at least one model."""
    try:
        req = urllib.request.Request(f"{endpoint}/models", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return False

            payload = json.loads(response.read().decode("utf-8") or "{}")
            data = payload.get("data") if isinstance(payload, dict) else None
            return isinstance(data, list) and len(data) > 0
    except Exception:  # noqa: BLE001 — broad catch intentional for probe function
        return False


async def _is_valid_foundry_endpoint_async(endpoint: str, timeout: float = 2.0) -> bool:
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


async def get_foundry_local_endpoint_async() -> str:
    """
    Async version of get_foundry_local_endpoint.
    Caches the discovered endpoint in a module-level variable.
    """
    import asyncio

    global _foundry_endpoint_cache

    if _foundry_endpoint_cache and await _is_valid_foundry_endpoint_async(_foundry_endpoint_cache):
        return _foundry_endpoint_cache

    env_endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
    if env_endpoint and await _is_valid_foundry_endpoint_async(env_endpoint):
        _foundry_endpoint_cache = env_endpoint
        return env_endpoint

    # Run lsof async
    try:
        proc = await asyncio.create_subprocess_exec(
            "lsof", "-nP", "-iTCP", "-sTCP:LISTEN",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        output = stdout.decode()
        for line in output.split('\n'):
            lower_line = line.lower()
            if 'inference' in lower_line or ('foundry' in lower_line and 'python' not in lower_line):
                match = re.search(r'127\.0\.0\.1:(\d+)\s+\(LISTEN\)', line)
                if not match:
                    match = re.search(r'\*:(\d+)\s+\(LISTEN\)', line)
                if match:
                    port = match.group(1)
                    endpoint = f"http://127.0.0.1:{port}/v1"
                    if await _is_valid_foundry_endpoint_async(endpoint):
                        _foundry_endpoint_cache = endpoint
                        return endpoint
    except (asyncio.TimeoutError, OSError, FileNotFoundError):
        pass

    # Run foundry service status async
    try:
        proc = await asyncio.create_subprocess_exec(
            "foundry", "service", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        output = stdout.decode()
        if "running" in output.lower():
            match = re.search(r'http://([^/:\s]+):(\d+)', output)
            if match:
                host, port = match.groups()
                endpoint = f"http://{host}:{port}/v1"
                if await _is_valid_foundry_endpoint_async(endpoint):
                    _foundry_endpoint_cache = endpoint
                    return endpoint
    except (asyncio.TimeoutError, OSError, FileNotFoundError):
        pass

    raise RuntimeError(
        "Foundry Local not running or not responding.\n"
        "Start with: foundry model run qwen2.5-14b\n"
        "Or set FOUNDRY_LOCAL_ENDPOINT environment variable to the endpoint.\n"
        "Check status: foundry service status"
    )


async def _patched_request(self, *args, **kwargs):
    """Patched request method that adds system_fingerprint to responses."""
    # Call original httpx request
    response = await self._client.request(*args, **kwargs)
    
    # Patch JSON responses to add system_fingerprint if missing
    original_json = response.json
    
    def patched_json():
        data = original_json()
        if isinstance(data, dict) and "system_fingerprint" not in data:
            data["system_fingerprint"] = "foundry-local"
        return data
    
    response.json = patched_json
    return response


def create_chat_client(mode: str = "local", model_name: Optional[str] = None):
    """Create chat client for local (Foundry) or hosted (Azure) deployment."""
    if mode == "local":
        endpoint = get_foundry_local_endpoint()
        model_id = model_name or os.getenv("MODEL_NAME", "qwen2.5-14b")
        
        # Create custom AsyncOpenAI client
        async_client = AsyncOpenAI(
            api_key="local-dev-key",
            base_url=endpoint
        )
        
        # Monkey-patch the _request method to add system_fingerprint
        async_client._client.request = _patched_request.__get__(async_client._client, type(async_client._client))
        
        client = OpenAIChatClient(
            model_id=model_id,
            async_client=async_client
        )
        return client
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


async def create_chat_client_async(mode: str = "local", model_name: Optional[str] = None):
    """Async version of create_chat_client — uses async Foundry endpoint discovery."""
    if mode == "local":
        endpoint = await get_foundry_local_endpoint_async()
        model_id = model_name or os.getenv("MODEL_NAME", "qwen2.5-14b")

        async_client = AsyncOpenAI(
            api_key="local-dev-key",
            base_url=endpoint
        )
        async_client._client.request = _patched_request.__get__(async_client._client, type(async_client._client))
        return OpenAIChatClient(model_id=model_id, async_client=async_client)
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
    Foundry runs on a random port each time - scan for it or use environment variable.
    Checks the async cache first if it was already discovered.
    """
    global _foundry_endpoint_cache

    # Return cached endpoint if valid
    if _foundry_endpoint_cache and _is_valid_foundry_endpoint(_foundry_endpoint_cache):
        return _foundry_endpoint_cache

    # Try environment variable first (but validate it's still working)
    env_endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
    if env_endpoint:
        if _is_valid_foundry_endpoint(env_endpoint):
            _foundry_endpoint_cache = env_endpoint
            return env_endpoint
    
    # Try to find foundry process and extract port from its output/listening ports
    try:
        # Check for listening ports used by foundry process
        result = subprocess.run(
            ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Look for foundry process listening ports
            for line in result.stdout.split('\n'):
                lower_line = line.lower()
                # Look specifically for Inference.Service.Agent (Foundry), not just any Python process
                if 'inference' in lower_line or ('foundry' in lower_line and 'python' not in lower_line):
                    # Extract port from line like: "Inference 46045 ... 127.0.0.1:55028 (LISTEN)"
                    match = re.search(r'127\.0\.0\.1:(\d+)\s+\(LISTEN\)', line)
                    if not match:
                        # Try format: "*:PORT (LISTEN)"
                        match = re.search(r'\*:(\d+)\s+\(LISTEN\)', line)
                    if match:
                        port = match.group(1)
                        endpoint = f"http://127.0.0.1:{port}/v1"
                        if _is_valid_foundry_endpoint(endpoint):
                            return endpoint
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
    
    # Get from foundry service status
    try:
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and "running" in result.stdout.lower():
            # Output: "🟢 Model management service is running on http://127.0.0.1:57069/openai/status"
            # Extract: http://127.0.0.1:57069
            match = re.search(r'http://([^/:\s]+):(\d+)', result.stdout)
            if match:
                host, port = match.groups()
                endpoint = f"http://{host}:{port}/v1"
                if _is_valid_foundry_endpoint(endpoint):
                    return endpoint
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
    
    # Fallback: Scan common ports range where foundry typically runs
    # Foundry uses random high ports, so scan 49152-65535 (ephemeral port range)
    # But limit to a reasonable subset to avoid slow scans
    import random
    sample_ports = [8000, 8080, 8888, 9000] + random.sample(range(49152, 65535), 50)
    
    for port in sample_ports:
        endpoint = f"http://127.0.0.1:{port}/v1"
        if _is_valid_foundry_endpoint(endpoint, timeout=0.5):
            return endpoint
    
    raise RuntimeError(
        "Foundry Local not running or not responding.\n"
        "Start with: foundry model run qwen2.5-14b\n"
        "Or set FOUNDRY_LOCAL_ENDPOINT environment variable to the endpoint.\n"
        "Check status: foundry service status"
    )
