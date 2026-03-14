"""Test script to check if agent properly handles MCP tools."""
import asyncio
import sys

async def test_agent_with_mcp():
    from agent_framework.openai import OpenAIChatClient
    from openai import AsyncOpenAI
    from mcp_client import get_banking_mcp_tools
    from bank_agents import inquiry
    
    # Create a mock client
    async_client = AsyncOpenAI(
        api_key="test",
        base_url="http://localhost:8000/v1"
    )
    client = OpenAIChatClient(model_id="test", async_client=async_client)
    
    # Get MCP tools
    mcp_tools = get_banking_mcp_tools("http://localhost:8001")
    
    # Create agent
    agent = inquiry.get_agent(client, mcp_tools)
    
    # Test 1: Without context manager
    print("Test 1: Running agent WITHOUT context manager...")
    try:
        response = await agent.run("What is my balance?")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error (expected): {e}")
    
    # Test 2: With context manager
    print("\nTest 2: Running agent WITH context manager...")
    try:
        async with agent:
            response = await agent.run("What is my balance?")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_with_mcp())
