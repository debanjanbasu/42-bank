"""
Cosmos DB MCP Client for 42-Bank.
Provides a client to interact with the Azure Cosmos DB MCP Toolkit.

This client wraps the official Microsoft Cosmos DB MCP Toolkit,
providing a clean Python interface for banking operations.

Usage:
    from cosmos_mcp_client import CosmosMCPClient
    
    client = CosmosMCPClient(
        base_url="https://cosmos-mcp.azurecontainerapps.io/mcp",
        database_id="banking"
    )
    
    user = await client.find_document("users", "alice_token")
"""

import os
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime


class CosmosMCPError(Exception):
    """Exception raised for Cosmos MCP errors."""
    pass


class CosmosMCPClient:
    """
    Client for Azure Cosmos DB MCP Toolkit.
    
    The toolkit provides these tools:
    - find_document_by_id: Find a document by ID
    - get_recent_documents: Get N most recent documents
    - text_search: Search documents where property contains text
    - get_approximate_schema: Sample documents to infer schema
    - list_databases: List all databases
    - list_collections: List all containers in a database
    - vector_search: Semantic search using embeddings
    
    Environment Variables:
        COSMOS_MCP_URL: Base URL of the MCP server
        COSMOS_DATABASE: Default database name
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        database_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Cosmos MCP client.
        
        Args:
            base_url: MCP server URL (default: from COSMOS_MCP_URL env)
            database_id: Database name (default: from COSMOS_DATABASE env)
            api_key: Optional API key for authentication
        """
        self.base_url = base_url or os.getenv("COSMOS_MCP_URL", "")
        self.database_id = database_id or os.getenv("COSMOS_DATABASE", "banking")
        self.api_key = api_key or os.getenv("COSMOS_MCP_API_KEY")
        
        if not self.base_url:
            raise CosmosMCPError(
                "COSMOS_MCP_URL not set. Set it or pass base_url parameter."
            )
    
    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        database_id: Optional[str] = None,
        container_id: Optional[str] = None,
    ) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            database_id: Override default database
            container_id: Container name
            
        Returns:
            Tool result (parsed from JSON if applicable)
        """
        db = database_id or self.database_id
        
        # Build request payload for MCP protocol
        payload = {
            "databaseId": db,
            **arguments
        }
        
        if container_id:
            payload["containerId"] = container_id
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        url = f"{self.base_url}/tools/{tool_name}"
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract content from MCP response format
                if isinstance(data, dict) and "content" in data:
                    content = data["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get("text", "{}")
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return text
                return data
                
            except httpx.HTTPStatusError as e:
                raise CosmosMCPError(f"HTTP error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                raise CosmosMCPError(f"Request error: {e}")
    
    # ============ Document Operations ============
    
    async def find_document(
        self,
        container_id: str,
        document_id: str,
        database_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a document by its ID.
        
        Args:
            container_id: Container name
            document_id: Document ID
            database_id: Override default database
            
        Returns:
            Document dict or None if not found
        """
        try:
            result = await self._call_tool(
                "find_document_by_id",
                {"id": document_id},
                database_id=database_id,
                container_id=container_id,
            )
            return result if isinstance(result, dict) else None
        except CosmosMCPError:
            return None
    
    async def get_recent_documents(
        self,
        container_id: str,
        count: int = 10,
        database_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent documents from a container.
        
        Args:
            container_id: Container name
            count: Number of documents to retrieve
            database_id: Override default database
            
        Returns:
            List of documents
        """
        result = await self._call_tool(
            "get_recent_documents",
            {"count": count},
            database_id=database_id,
            container_id=container_id,
        )
        return result if isinstance(result, list) else []
    
    async def text_search(
        self,
        container_id: str,
        property_name: str,
        search_phrase: str,
        database_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents where a property contains text.
        
        Args:
            container_id: Container name
            property_name: Property to search
            search_phrase: Text to search for
            database_id: Override default database
            
        Returns:
            List of matching documents
        """
        result = await self._call_tool(
            "text_search",
            {
                "propertyName": property_name,
                "searchPhrase": search_phrase,
            },
            database_id=database_id,
            container_id=container_id,
        )
        return result if isinstance(result, list) else []
    
    async def get_schema(
        self,
        container_id: str,
        database_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the approximate schema of a container.
        
        Args:
            container_id: Container name
            database_id: Override default database
            
        Returns:
            Schema information
        """
        return await self._call_tool(
            "get_approximate_schema",
            {},
            database_id=database_id,
            container_id=container_id,
        )
    
    # ============ Container Operations ============
    
    async def list_containers(
        self,
        database_id: Optional[str] = None,
    ) -> List[str]:
        """
        List all containers in the database.
        
        Args:
            database_id: Override default database
            
        Returns:
            List of container names
        """
        result = await self._call_tool(
            "list_collections",
            {},
            database_id=database_id,
        )
        return result if isinstance(result, list) else []
    
    # ============ Banking-Specific Helpers ============
    
    async def get_user_by_username(
        self,
        username: str,
        database_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a user by username.
        
        Uses text_search on the username field.
        
        Args:
            username: Username to search for
            database_id: Override default database
            
        Returns:
            User document or None
        """
        results = await self.text_search(
            container_id="users",
            property_name="username",
            search_phrase=username,
            database_id=database_id,
        )
        
        # Find exact match
        for user in results:
            if user.get("username") == username:
                return user
        return None
    
    async def get_user_transactions(
        self,
        username: str,
        limit: int = 10,
        database_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a user.
        
        Gets recent transactions and filters by username.
        
        Args:
            username: Username to filter by
            limit: Maximum number of transactions
            database_id: Override default database
            
        Returns:
            List of transactions
        """
        # Get recent transactions
        all_txns = await self.get_recent_documents(
            container_id="transactions",
            count=limit * 3,  # Get more to filter
            database_id=database_id,
        )
        
        # Filter by user
        user_txns = [
            t for t in all_txns
            if t.get("sender") == username or t.get("recipient") == username
        ]
        
        return user_txns[:limit]
    
    async def get_pending_requests_for_user(
        self,
        username: str,
        database_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending payment requests for a user.
        
        Args:
            username: Recipient username
            database_id: Override default database
            
        Returns:
            List of pending requests
        """
        results = await self.text_search(
            container_id="pending_requests",
            property_name="recipient",
            search_phrase=username,
            database_id=database_id,
        )
        
        # Filter for pending status
        return [r for r in results if r.get("status") == "pending"]


# ============ Synchronous Wrapper ============

class CosmosMCPClientSync:
    """
    Synchronous wrapper for CosmosMCPClient.
    
    Use this for non-async code or simple scripts.
    
    Usage:
        from cosmos_mcp_client import CosmosMCPClientSync
        
        client = CosmosMCPClientSync()
        user = client.find_document("users", "alice_token")
    """
    
    def __init__(self, *args, **kwargs):
        self._async_client = CosmosMCPClient(*args, **kwargs)
    
    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def find_document(self, container_id: str, document_id: str, **kwargs) -> Optional[Dict]:
        return self._run_async(
            self._async_client.find_document(container_id, document_id, **kwargs)
        )
    
    def get_recent_documents(self, container_id: str, count: int = 10, **kwargs) -> List[Dict]:
        return self._run_async(
            self._async_client.get_recent_documents(container_id, count, **kwargs)
        )
    
    def text_search(self, container_id: str, property_name: str, search_phrase: str, **kwargs) -> List[Dict]:
        return self._run_async(
            self._async_client.text_search(container_id, property_name, search_phrase, **kwargs)
        )
    
    def get_user_by_username(self, username: str, **kwargs) -> Optional[Dict]:
        return self._run_async(
            self._async_client.get_user_by_username(username, **kwargs)
        )
    
    def get_user_transactions(self, username: str, limit: int = 10, **kwargs) -> List[Dict]:
        return self._run_async(
            self._async_client.get_user_transactions(username, limit, **kwargs)
        )
