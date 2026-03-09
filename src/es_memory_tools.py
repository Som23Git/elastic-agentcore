"""Elasticsearch-backed long-term memory tools for the Strands agent.

These tools let the agent persist and recall memories using an Elasticsearch
index with a `semantic_text` field, enabling vector-based retrieval.

Enabled only when ES_MEMORY_INDEX is set in .env.
"""

from datetime import datetime, timezone

from elasticsearch import Elasticsearch
from strands import tool

from .config import ELASTIC_API_KEY, ELASTICSEARCH_URL, ES_MEMORY_INDEX

_es: Elasticsearch | None = None


def _get_client() -> Elasticsearch:
    """Lazily create and return a shared Elasticsearch client."""
    global _es
    if _es is None:
        if not ELASTICSEARCH_URL:
            raise RuntimeError("ELASTICSEARCH_URL must be set to use ES memory tools")
        _es = Elasticsearch(ELASTICSEARCH_URL, api_key=ELASTIC_API_KEY)
    return _es


@tool
def store_memory(content: str, tags: list[str] | None = None, user_id: str = "default-analyst") -> str:
    """Store a piece of knowledge or insight into long-term memory.

    Use this tool when the user shares a preference, you discover an important
    pattern in their data, or any information worth remembering across sessions.

    Args:
        content: The memory text to store (e.g. "User prefers ES|QL over DSL queries").
        tags: Optional category tags (e.g. ["preference", "query-style"]).
        user_id: The user this memory belongs to.
    """
    doc = {
        "content": content,
        "tags": tags or [],
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = _get_client().index(index=ES_MEMORY_INDEX, document=doc)
    return f"Memory stored (id={result['_id']}): {content}"


@tool
def recall_memories(query: str, top_k: int = 5, user_id: str = "default-analyst") -> str:
    """Search long-term memory for relevant past knowledge and user preferences.

    Use this tool at the start of a conversation or when you need context about
    the user's history, preferences, or previously discovered data patterns.

    Args:
        query: A natural-language description of what to recall.
        top_k: Maximum number of memories to return.
        user_id: Filter memories to this user.
    """
    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": {"semantic": {"field": "content", "query": query}},
                "filter": {"term": {"user_id": user_id}},
            }
        },
    }
    resp = _get_client().search(index=ES_MEMORY_INDEX, body=body)
    hits = resp["hits"]["hits"]

    if not hits:
        return "No relevant memories found."

    lines = []
    for i, hit in enumerate(hits, 1):
        src = hit["_source"]
        score = hit["_score"]
        tags = ", ".join(src.get("tags", [])) or "none"
        lines.append(f"{i}. [{score:.3f}] {src['content']}  (tags: {tags})")

    return "Recalled memories:\n" + "\n".join(lines)
