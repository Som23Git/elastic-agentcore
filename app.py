"""Streamlit chat UI for the Elastic Data Analyst Agent.

Run with:
    uv run streamlit run app.py
"""

import time
from contextlib import contextmanager
from datetime import datetime

import streamlit as st
from strands import Agent

from src.config import ES_MEMORY_INDEX, KIBANA_URL, MEMORY_ID, AWS_REGION
from src.elastic_mcp import create_elastic_mcp_client

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Elastic Data Analyst",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for conference-ready look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Dark header bar */
    .main-header {
        background: linear-gradient(135deg, #1B1F3B 0%, #162447 50%, #0F4C75 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .main-header h1 {
        color: #FFFFFF;
        font-size: 1.8rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header .subtitle {
        color: #BBE1FA;
        font-size: 0.95rem;
        margin: 0;
    }
    /* Tool call badges */
    .tool-badge {
        display: inline-block;
        background: #0F4C75;
        color: #BBE1FA;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-family: monospace;
        margin: 0.2rem 0;
    }
    /* Status pills */
    .status-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-active { background: #00E676; color: #1B1F3B; }
    .status-inactive { background: #FF5252; color: #FFFFFF; }
    /* Sidebar styling */
    .sidebar-section {
        background: #f0f2f6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .sidebar-section h3 {
        margin-top: 0;
        font-size: 0.9rem;
        color: #1B1F3B;
    }
    /* Metric cards */
    .metric-row {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        flex: 1;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .metric-card .value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1B1F3B;
    }
    .metric-card .label {
        font-size: 0.7rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <div>
        <h1>🔍 Elastic Data Analyst</h1>
        <p class="subtitle">Powered by Amazon Bedrock AgentCore &bull; Elastic Agent Builder MCP &bull; AgentCore Memory</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Architecture")
    if ES_MEMORY_INDEX:
        st.markdown("""
    ```
    You ──► Streamlit UI
              │
              ▼
         Strands Agent
           ├─ Bedrock Claude (LLM)
           ├─ Elastic MCP (Tools)
           ├─ AgentCore Memory
           └─ ES Memory (semantic)
              │
              ▼
         Elastic Cloud
         Serverless
    ```
    """)
    else:
        st.markdown("""
    ```
    You ──► Streamlit UI
              │
              ▼
         Strands Agent
           ├─ Bedrock Claude (LLM)
           ├─ Elastic MCP (Tools)
           └─ AgentCore Memory
              │
              ▼
         Elastic Cloud
         Serverless
    ```
    """)

    st.divider()

    st.markdown("### Connection Status")
    kibana_short = KIBANA_URL.replace("https://", "").split(".")[0] if KIBANA_URL else "not set"
    memory_status = "Active" if MEMORY_ID else "Disabled"
    memory_class = "status-active" if MEMORY_ID else "status-inactive"

    es_mem_status = "Active" if ES_MEMORY_INDEX else "Disabled"
    es_mem_class = "status-active" if ES_MEMORY_INDEX else "status-inactive"

    st.markdown(f"""
    **Elastic Cluster**: `{kibana_short}`
    <br>**AgentCore Memory**: <span class="status-pill {memory_class}">{memory_status}</span>
    <br>**ES Memory**: <span class="status-pill {es_mem_class}">{es_mem_status}</span>
    <br>**AWS Region**: `{AWS_REGION}`
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### Example Prompts")
    example_prompts = [
        "What indices do I have?",
        "Show me 5xx errors by URL and hour",
        "Top 10 products by revenue",
        "Compare error rates vs revenue by country",
        "Which airlines have the most delays?",
        "Daily dashboard of 5xx errors and revenue",
    ]
    for p in example_prompts:
        if st.button(p, key=f"ex_{p[:20]}", use_container_width=True):
            st.session_state["next_prompt"] = p

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_calls = 0
        st.session_state.total_time = 0.0
        st.rerun()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = 0
if "total_time" not in st.session_state:
    st.session_state.total_time = 0.0
if "agent" not in st.session_state:
    st.session_state.agent = None
if "mcp_client" not in st.session_state:
    st.session_state.mcp_client = None

# ---------------------------------------------------------------------------
# Metrics bar
# ---------------------------------------------------------------------------
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Messages", len(st.session_state.messages))
with col2:
    st.metric("Tool Calls", st.session_state.tool_calls)
with col3:
    st.metric("Total Time", f"{st.session_state.total_time:.1f}s")
with col4:
    st.metric("AgentCore Mem", "On" if MEMORY_ID else "Off")
with col5:
    st.metric("ES Memory", "On" if ES_MEMORY_INDEX else "Off")

st.divider()

# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------
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


@contextmanager
def _get_memory_manager(user_id: str, session_id: str | None):
    """Yield a session manager when MEMORY_ID is configured."""
    if MEMORY_ID:
        from src.memory_setup import create_session_manager, _resolve_session_id
        resolved = _resolve_session_id(session_id)
        with create_session_manager(user_id, resolved) as mgr:
            yield mgr
    else:
        yield None


def get_agent(user_id: str = "conference-demo"):
    """Create or return the cached agent with MCP tools."""
    if st.session_state.mcp_client is None:
        st.session_state.mcp_client = create_elastic_mcp_client()

    agent_kwargs = {
        "system_prompt": SYSTEM_PROMPT,
        "tools": [st.session_state.mcp_client],
    }

    return Agent(**agent_kwargs)


def run_agent(prompt: str, user_id: str = "conference-demo") -> str:
    """Run the agent and return the response text."""
    with _get_memory_manager(user_id, None) as session_manager:
        tools: list = [st.session_state.mcp_client or create_elastic_mcp_client()]
        if ES_MEMORY_INDEX:
            from src.es_memory_tools import recall_memories, store_memory

            tools.extend([store_memory, recall_memories])

        agent_kwargs = {
            "system_prompt": SYSTEM_PROMPT,
            "tools": tools,
        }
        if session_manager is not None:
            agent_kwargs["session_manager"] = session_manager

        agent = Agent(**agent_kwargs)
        result = agent(prompt)
        return str(result)


# ---------------------------------------------------------------------------
# Chat display
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant" and "duration" in msg:
            cols = st.columns([0.92, 0.08])
            with cols[0]:
                st.markdown(msg["content"])
            with cols[1]:
                st.caption(f"⏱ {msg['duration']:.1f}s")
        else:
            st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
next_prompt = st.session_state.pop("next_prompt", None)
user_input = st.chat_input("Ask about your Elasticsearch data...")
prompt = next_prompt or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()

        status_placeholder.markdown(
            '<span class="tool-badge">⚡ Querying Elasticsearch via MCP...</span>',
            unsafe_allow_html=True,
        )

        start = time.time()
        try:
            response_text = run_agent(prompt)
        except Exception as e:
            response_text = f"**Error:** {e}"
        duration = time.time() - start

        status_placeholder.empty()

        cols = st.columns([0.92, 0.08])
        with cols[0]:
            response_placeholder.markdown(response_text)
        with cols[1]:
            st.caption(f"⏱ {duration:.1f}s")

    tool_count = response_text.count("Tool #") if "Tool #" not in response_text else 0
    st.session_state.tool_calls += max(1, response_text.lower().count("tool"))
    st.session_state.total_time += duration
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "duration": duration,
    })
    st.rerun()
