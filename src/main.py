"""Elastic Data Analyst Agent -- deployed to Amazon Bedrock AgentCore Runtime.

Connects to Elastic Cloud Serverless via the hosted Agent Builder MCP endpoint
and uses AgentCore Memory for session continuity and long-term user insights.
"""

from contextlib import contextmanager

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

from .config import ES_MEMORY_INDEX, MEMORY_ID
from .elastic_mcp import create_elastic_mcp_client

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """\
You are an expert data analyst assistant connected to Elasticsearch via MCP tools.
The user has weblogs and ecommerce data in their Elastic Cloud Serverless project.

## Your capabilities

- **Index discovery**: list available indices, inspect mappings and shard info.
- **ES|QL queries**: write and execute ES|QL to analyze weblogs
  (status codes, response times, geoip, user agents, URLs) and ecommerce data
  (orders, products, customers, revenue, categories).
- **Search**: run full-text and structured search against any index.

## Guidelines

1. If the user's question is ambiguous, first discover which indices exist.
2. Prefer ES|QL for analytical / aggregation queries -- it is purpose-built for that.
3. Present results as clear Markdown tables or bullet-point summaries.
4. After answering, suggest one or two follow-up analyses the user might find useful.
5. Use what you remember about the user (preferred indices, past queries,
   areas of interest) to personalize your responses.
"""

elastic_mcp = create_elastic_mcp_client()


@contextmanager
def _optional_memory(user_id: str, session_id: str | None):
    """Yield (session_manager, session_id) when MEMORY_ID is configured."""
    if MEMORY_ID:
        from .memory_setup import create_session_manager, _resolve_session_id

        resolved_sid = _resolve_session_id(session_id)
        with create_session_manager(user_id, resolved_sid) as mgr:
            yield mgr, resolved_sid
    else:
        yield None, "no-memory"


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Handle an invocation from AgentCore Runtime or local testing."""
    user_id = payload.get("user_id", "default-analyst")
    session_id = payload.get("session_id")
    prompt = payload.get("prompt", "What indices are available?")

    with _optional_memory(user_id, session_id) as (session_manager, resolved_session_id):
        tools: list = [elastic_mcp]
        if ES_MEMORY_INDEX:
            from .es_memory_tools import recall_memories, store_memory

            tools.extend([store_memory, recall_memories])

        agent_kwargs = {
            "system_prompt": SYSTEM_PROMPT,
            "tools": tools,
        }
        if session_manager is not None:
            agent_kwargs["session_manager"] = session_manager

        agent = Agent(**agent_kwargs)
        result = agent(prompt)

        return {
            "response": str(result),
            "session_id": resolved_session_id,
            "user_id": user_id,
        }


if __name__ == "__main__":
    app.run()
