"""Shared type definitions for bank agents."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent


class ChatClientProtocol(Protocol):
    """Protocol for chat clients that can create agents."""

    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...
