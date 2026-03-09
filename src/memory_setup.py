from datetime import datetime

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)

from .config import AWS_REGION, MEMORY_ID


def _resolve_session_id(session_id: str | None) -> str:
    """Return the given session_id or generate a timestamp-based one."""
    return session_id or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def create_session_manager(
    user_id: str,
    session_id: str | None = None,
) -> AgentCoreMemorySessionManager:
    """Create a memory-backed session manager for the Strands agent.

    Short-term memory: captures every conversational turn within the session
    so multi-step analyses maintain full context.

    Long-term memory: asynchronously extracts summaries, user preferences,
    and factual insights that persist across sessions.
    """
    if not session_id:
        session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=user_id,
    )

    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=AWS_REGION,
    )
