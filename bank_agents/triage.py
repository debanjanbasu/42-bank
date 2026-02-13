from typing import Protocol, List, Any, Optional, Sequence
from agent_framework import Agent


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_agent(client: ChatClientProtocol) -> Agent:
    return client.as_agent(
        name="TriageAgent",
        instructions=(
            "You are a robotic router. Your ONLY job is to call a handoff tool. "
            "1. IF user wants balance/history/accounts -> CALL 'handoff_to_InquiryAgent()'. "
            "2. IF user wants money movement (send/request/approve/pay) -> CALL 'handoff_to_TransactionAgent()'. "
            "3. IF user wants products/advice -> CALL 'handoff_to_AdvisorAgent()'. "
            "4. IF user wants help -> CALL 'handoff_to_BankManager()'. "
            "STRICT RULES: "
            "- DO NOT GREET. "
            "- DO NOT CHAT. "
            "- DO NOT ASK QUESTIONS. "
            "- CALL THE TOOL IMMEDIATELY BASED ON THE USER PROMPT."
        ),
    )
