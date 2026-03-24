"""Advisor Agent - Assists with bank products and account opening."""

from typing import Any, Optional

from agent_framework import Agent

from bank_agents._types import ChatClientProtocol


def get_agent(client: ChatClientProtocol, tools) -> Agent:
    instructions = (
        "You are a financial advisor. User is authenticated. "
        "LANGUAGE: Always respond in ENGLISH only. "
        "For product inquiries: IMMEDIATELY call list_products(). "
        "For opening accounts: IMMEDIATELY call open_new_account(account_type). "
        "DO NOT provide generic advice without calling tools first. "
        "Just call the appropriate tool immediately and respond in English."
    )
    return client.as_agent(
        name="AdvisorAgent",
        instructions=instructions,
        tools=tools,
    )
