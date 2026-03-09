# Elastic Data Analyst Agent on Amazon Bedrock AgentCore

An AI-powered data analyst agent that queries your Elasticsearch weblogs and ecommerce data using natural language. Built with the **Strands Agents SDK**, powered by **Amazon Bedrock** foundation models, connected to **Elastic Cloud Serverless** via the hosted **Agent Builder MCP** endpoint, with **AgentCore Memory** for session continuity and long-term personalization.

## Architecture

```
                                    ┌─────────────────────────────────┐
                                    │    Amazon Bedrock AgentCore     │
                                    │                                 │
  ┌──────────┐   invoke API    ┌────┴──────────────────────┐          │
  │  Client   │ ─────────────► │  AgentCore Runtime        │          │
  │  (curl /  │                │  (Strands agent)          │          │
  │  script / │ ◄───────────── │                           │          │
  │  app)     │   response     │  ┌──────────────────────┐ │          │
  └──────────┘                 │  │ Bedrock Claude/Nova   │ │          │
                               │  │ + Elastic MCP Client ─┼─┼──► Elastic Cloud Serverless
                               │  │ + AgentCore Memory  ──┼─┼──► AgentCore Memory Service
                               │  │ + OTEL Telemetry   ──┼─┼──► CloudWatch GenAI Obs
                               │  └──────────────────────┘ │          │
                               └───────────────────────────┘          │
                                    └─────────────────────────────────┘
```

### AgentCore services used

| Service | Purpose |
|---------|---------|
| **Runtime** | Serverless hosting with session isolation, auto-scaling, `/invocations` endpoint |
| **Memory (short-term)** | Captures every conversational turn so multi-step analyses keep context |
| **Memory (long-term)** | Extracts user preferences, session summaries, and data insights across sessions |
| **Observability** | OTEL auto-instrumentation to CloudWatch traces/spans for every tool call and LLM invocation |

### Elastic services used

| Service | Purpose |
|---------|---------|
| **Elastic Cloud Serverless** | Hosts your weblogs and ecommerce indices |
| **Agent Builder MCP endpoint** | Hosted MCP server (`/api/agent_builder/mcp`) -- no Docker/ECR needed |
| **Agent Builder tools** | ES\|QL queries, index search, mappings, shard info, and custom tools |

---

## Project Structure

```
elastic-agentcore/
├── app.py                   # Streamlit chat UI (conference-ready)
├── src/
│   ├── __init__.py
│   ├── main.py              # Agent entrypoint (deployed to AgentCore Runtime)
│   ├── elastic_mcp.py       # Elastic hosted MCP client setup
│   ├── memory_setup.py      # AgentCore Memory session manager
│   └── config.py            # Centralized environment config
├── scripts/
│   ├── __init__.py
│   ├── setup_memory.py      # One-time: create AgentCore Memory store
│   ├── create_api_key.py    # One-time: create Elastic API key
│   └── invoke_agent.py      # Test client for the deployed agent
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start (Streamlit Chat UI)

If you've already completed the setup below (Elastic + AWS), launch the chat UI with:

```bash
uv run streamlit run app.py
```

This opens a browser-based chat interface at `http://localhost:8501` with:

- A full chat UI -- type questions in plain English
- Beautiful Markdown rendering of tables, lists, and analytics
- Live tool-call status indicators
- Sidebar with architecture diagram, connection status, and example prompts
- Metrics bar tracking messages, tool calls, and response times
- AgentCore Memory integration for session continuity

Perfect for **conference demos** and **live presentations** on a big screen.

> **Headless mode** (for remote servers): `uv run streamlit run app.py --server.headless true`

### GitHub Codespaces (one-click start)

This repo includes a devcontainer config for instant setup in GitHub Codespaces:

1. Click **Code → Codespaces → Create codespace on main** in the GitHub repo
2. Wait for the environment to build (installs Python 3.13, AWS CLI, and all dependencies automatically)
3. In the Codespace terminal:

```bash
cp .env.example .env
# Edit .env with your Elastic credentials (KIBANA_URL, ELASTIC_API_KEY)
aws configure
uv run streamlit run app.py --server.headless true
```

4. The Streamlit UI opens automatically in your browser

---

## Prerequisites

Before you begin, you need:

- **Python 3.10+** (3.13 recommended)
- **uv** package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **AWS account** with credentials configured (`aws configure`)
- **Elastic Cloud account** with a Serverless project

---

## Part 1: Elastic Cloud Setup

### Step 1.1 -- Create or use an Elastic Serverless project

If you don't already have one:

1. Go to [cloud.elastic.co](https://cloud.elastic.co)
2. Click **Create project** and choose **Elasticsearch** as the project type
3. Pick your cloud provider (AWS recommended for lowest latency to AgentCore) and region
4. Wait for the project to be created

Once ready, note down two URLs from **Project → Management → Endpoints**:

- **Kibana URL**: `https://your-project.kb.<region>.aws.elastic.cloud`
- **Elasticsearch URL**: `https://your-project.es.<region>.aws.elastic.cloud`

### Step 1.2 -- Load sample data

If you haven't already loaded the sample datasets:

1. Open Kibana
2. Go to **Home → Try sample data**
3. Install both:
   - **Sample web logs** (creates `kibana_sample_data_logs`)
   - **Sample ecommerce orders** (creates `kibana_sample_data_ecommerce`)

You can verify the indices exist by going to **Management → Index Management** or running in Dev Tools:

```
GET _cat/indices/kibana_sample*?v
```

### Step 1.3 -- Verify Agent Builder is available

Agent Builder is available on:
- Elastic Cloud Serverless (all project types)
- Elastic Stack 9.2+ (Preview) / 9.3+ (GA)

In Kibana, navigate to **Search → Agent Builder**. You should see the Tools page listing built-in tools. If you see a "Copy your MCP server URL" button at the top, you're all set.

### Step 1.4 -- Create an API key for MCP access

The agent needs an API key with Agent Builder read permissions. You can create one in two ways:

#### Option A: Kibana Dev Tools (recommended)

Open **Dev Tools** in Kibana and run:

```json
POST /_security/api_key
{
  "name": "agentcore-mcp-key",
  "expiration": "30d",
  "role_descriptors": {
    "mcp-access": {
      "cluster": ["monitor_inference"],
      "indices": [
        {
          "names": [
            "kibana_sample_data_logs",
            "kibana_sample_data_ecommerce"
          ],
          "privileges": ["read", "view_index_metadata"]
        }
      ],
      "applications": [
        {
          "application": "kibana-.kibana",
          "privileges": ["feature_agentBuilder.read"],
          "resources": ["space:default"]
        }
      ]
    }
  }
}
```

Copy the `encoded` value from the response. This is your `ELASTIC_API_KEY`.

> **Adjust the index names** in `names` if your data lives in different indices. Use `["*"]` during development to allow access to all indices (not recommended for production).

#### Option B: Python script

After setting up the project (Part 3), you can also run:

```bash
python -m scripts.create_api_key
```

### Step 1.5 -- Test the MCP endpoint manually (optional)

You can verify your MCP endpoint is reachable:

```bash
curl -s -X POST "https://YOUR_KIBANA_URL/api/agent_builder/mcp" \
  -H "Authorization: ApiKey YOUR_ENCODED_API_KEY" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m json.tool
```

You should see a JSON response listing the available MCP tools (ES|QL query, index search, mappings, etc.).

---

## Part 2: AWS Setup

### Step 2.1 -- Configure AWS credentials

Make sure your AWS CLI is configured:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Step 2.2 -- Enable Bedrock model access

The agent uses a foundation model from Amazon Bedrock (Claude Sonnet by default).

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)
2. In the left sidebar, go to **Model access**
3. Click **Manage model access**
4. Enable **Anthropic → Claude Sonnet** (or Claude Haiku for lower cost during development)
5. Click **Save changes**

Model access can take a few minutes to propagate.

### Step 2.3 -- IAM permissions

Your AWS user/role needs permissions for:

- **Amazon Bedrock** -- invoke foundation models
- **Amazon Bedrock AgentCore** -- create/manage Runtime, Memory
- **Amazon ECR** -- push container images (if using container deploy)
- **Amazon S3** -- upload deployment packages (if using direct deploy)
- **Amazon CloudWatch** -- observability (optional)

For development, the simplest approach is to use a user/role with these managed policies:

```
AmazonBedrockFullAccess
AmazonBedrockAgentCoreFullAccess
```

For production, scope down to least-privilege. The AgentCore docs have detailed [IAM permission guides](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html).

### Step 2.4 -- Create the AgentCore Memory store

This is a one-time setup that creates a managed memory resource with three long-term strategies.

First, set up the project (see Part 3 below), then run:

```bash
python -m scripts.setup_memory
```

This will output a `MEMORY_ID` -- add it to your `.env` file.

**What the three strategies do:**

| Strategy | Type | What it extracts |
|----------|------|-----------------|
| `SessionSummarizer` | Summary | A condensed summary of each conversation |
| `AnalystPreferences` | User Preference | Preferred indices, time ranges, areas of interest |
| `DataInsights` | Semantic / Facts | Factual findings discovered during analysis |

You can also create the memory store from the AWS CLI:

```bash
pip install bedrock-agentcore-starter-toolkit

agentcore memory create ElasticDataAnalystMemory \
  --region us-east-1 \
  --strategies '[
    {"summaryMemoryStrategy": {"name": "SessionSummarizer", "namespaces": ["/summaries/{actorId}/{sessionId}/"]}},
    {"userPreferenceMemoryStrategy": {"name": "AnalystPreferences", "namespaces": ["/preferences/{actorId}/"]}},
    {"semanticMemoryStrategy": {"name": "DataInsights", "namespaces": ["/facts/{actorId}/"]}}
  ]' \
  --wait
```

### Step 2.5 -- Enable Observability (optional but recommended)

To get traces and metrics in CloudWatch:

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Go to **Application Signals (APM) → Transaction Search**
3. Click **Enable Transaction Search**
4. Check "Ingest spans as structured logs"
5. Set X-Ray trace indexing percentage (1% default is fine)
6. Save

After deploying (Part 4), add `aws-opentelemetry-distro` to your requirements and the starter toolkit will auto-instrument on deploy.

---

## Part 3: Project Setup

### Step 3.1 -- Clone and initialize

```bash
cd /path/to/elastic-agentcore

# Initialize with uv
uv init --python 3.13
uv add strands-agents bedrock-agentcore mcp python-dotenv boto3 elasticsearch

# Install dev tools
uv add --dev bedrock-agentcore-starter-toolkit
```

### Step 3.2 -- Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```bash
# From Part 1
KIBANA_URL=https://your-project.kb.us-east-1.aws.elastic.cloud
ELASTIC_API_KEY=your_encoded_api_key_from_step_1.4

# From Part 2
AWS_REGION=us-east-1
MEMORY_ID=your_memory_id_from_step_2.4
```

### Step 3.3 -- Create the Memory store

```bash
python -m scripts.setup_memory
```

Copy the printed `MEMORY_ID` into your `.env` file.

### Step 3.4 -- Test locally

```bash
# Start the agent locally on port 8080
python -m src.main
```

In another terminal:

```bash
# List available indices
curl -s -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What indices do I have?", "user_id": "analyst-001"}' | python -m json.tool

# Query weblogs
curl -s -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me the top 10 URLs with the most 5xx errors", "user_id": "analyst-001"}' | python -m json.tool

# Query ecommerce
curl -s -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Which product categories generate the most revenue?", "user_id": "analyst-001"}' | python -m json.tool
```

---

## Part 4: Deploy to AgentCore Runtime

### Step 4.1 -- Configure deployment

```bash
agentcore configure --entrypoint src/main.py
```

The CLI will prompt you for:
- **Execution role**: Choose "Create and use a new service role" for first-time setup
- **ECR**: Press Enter to auto-create
- **Dependencies**: Auto-detected from `requirements.txt`
- **OAuth**: Type `no` for development (use IAM auth)

### Step 4.2 -- Deploy

```bash
agentcore launch
```

This will:
1. Package your code (zip or container based on your setup)
2. Push to AWS (S3 or ECR)
3. Create the AgentCore Runtime
4. Output the **Agent Runtime ARN**

Copy the ARN into your `.env`:

```bash
AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/elastic-data-analyst-xyz
```

### Step 4.3 -- Test the deployed agent

Using the starter toolkit CLI:

```bash
agentcore invoke '{"prompt": "What indices are available?", "user_id": "analyst-001"}'
```

Using the Python client script:

```bash
python -m scripts.invoke_agent "What indices do I have?"
python -m scripts.invoke_agent "Show me 5xx error trends in the weblogs" --user analyst-001
python -m scripts.invoke_agent "Which customers spent the most?" --user analyst-001
```

### Step 4.4 -- Verify Memory is working

Try a multi-turn conversation:

```bash
# Turn 1
agentcore invoke '{"prompt": "I mostly work with the weblogs index and care about 5xx errors", "user_id": "analyst-001"}'

# Turn 2 (new session -- long-term memory should recall the preference)
agentcore invoke '{"prompt": "What should I look at today?", "user_id": "analyst-001"}'
```

The agent should remember the 5xx error preference from the first session.

---

## Part 5: Observability (Optional)

### Step 5.1 -- Add OTEL instrumentation

Add to your `requirements.txt`:

```
aws-opentelemetry-distro>=0.10.1
```

Then redeploy:

```bash
agentcore launch
```

### Step 5.2 -- View traces

1. Open the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. Navigate to **Application Signals → GenAI Observability**
3. Find your agent service
4. Click into traces to see:
   - LLM invocations (model, tokens, latency)
   - MCP tool calls (which Elastic tools were called, parameters, response times)
   - Memory operations (reads/writes)

---

## Part 6: Streamlit Chat UI (Conference Demo)

### Step 6.1 -- Launch the UI

Make sure the server from Part 3 is **not** running (the Streamlit app runs the agent directly, no separate server needed).

```bash
uv run streamlit run app.py
```

Your browser will open to `http://localhost:8501`.

### Step 6.2 -- What you'll see

The UI has three main areas:

**Sidebar (left)**:
- Architecture diagram showing the full stack
- Connection status (Elastic cluster, Memory, AWS region)
- Clickable example prompts -- just click to auto-submit
- Clear chat button

**Metrics bar (top)**:
- Messages count
- Tool calls count
- Total response time
- Memory status (Active/Off)

**Chat area (center)**:
- User messages with 👤 avatar
- Agent responses with 🤖 avatar, rendered as rich Markdown
- Response time shown on each message
- Live "Querying Elasticsearch via MCP..." indicator while processing

### Step 6.3 -- Conference presentation tips

- **Use fullscreen mode** (F11 or Cmd+Shift+F in most browsers)
- **Start with discovery**: "What indices do I have?"
- **Show tool orchestration**: "Compare 5xx error rates vs revenue by country" (agent chains multiple tool calls)
- **Demo memory**: Tell it a preference, then ask a vague follow-up -- it remembers
- **Zoom in** on the browser (Cmd/Ctrl + `+`) for visibility on large screens
- **Streamlit dark theme**: Add `--theme.base dark` for a dark-mode conference look:

```bash
uv run streamlit run app.py -- --theme.base dark
```

### Step 6.4 -- Running both modes

| Mode | Command | Use case |
|------|---------|----------|
| **Streamlit UI** | `uv run streamlit run app.py` | Demos, presentations, interactive exploration |
| **API server** | `uv run python -m src.main` | Programmatic access, curl testing, AgentCore Runtime deploy |

Both modes use the same agent code, Elastic MCP connection, and memory configuration.

---

## Example Queries

Here are some example prompts to try with your agent:

### Weblogs analysis

```
"What indices are available?"
"Show me the top 10 URLs with the most 5xx errors"
"What's the average response size by HTTP status code?"
"Compare traffic between weekdays and weekends"
"Which countries generate the most 404 errors?"
"Show me response time trends over the last 7 days"
"What user agents are most associated with errors?"
```

### Ecommerce analysis

```
"Which product categories generate the most revenue?"
"Show me the top 10 customers by total spend"
"What's the average order value by day of week?"
"Which cities have the most orders?"
"Show me products that are frequently bought together"
"What's the revenue trend over the last 30 days?"
"Compare men's vs women's clothing revenue"
```

### Cross-index analysis

```
"Do high-traffic periods in weblogs correlate with more ecommerce orders?"
"Show me a summary of both datasets -- what do I have?"
```

---

## Cleanup

### Stop a running session (save costs)

```bash
agentcore stop-session
```

### Delete the AgentCore Runtime

```bash
agentcore destroy
```

### Delete the Memory store

Use the AWS console:
1. Go to **Amazon Bedrock AgentCore → Memory**
2. Select your memory store
3. Click **Delete**

### Rotate the Elastic API key

Create a new key (Step 1.4), update `.env`, and redeploy.

---

## Troubleshooting

### "Connection refused" when testing locally

Make sure the agent is running on port 8080:

```bash
python src/main.py
```

Check that no other process is using port 8080:

```bash
lsof -i :8080
```

### "401 Unauthorized" from Elastic MCP

- Verify your `ELASTIC_API_KEY` is the **encoded** value (not the ID)
- Check the key hasn't expired
- Ensure the key has `feature_agentBuilder.read` application privilege
- Try the manual curl test from Step 1.5

### "AccessDeniedException" from Bedrock

- Ensure model access is enabled (Step 2.2)
- Verify your IAM role has `bedrock:InvokeModel` permission
- Check you're using a supported region (us-east-1, us-west-2, etc.)

### Memory not working

- Verify `MEMORY_ID` is set in `.env`
- Check the memory store status is `ACTIVE` in the AWS console
- Long-term memory extraction is **asynchronous** -- it may take a few seconds after a session ends before preferences and facts appear

### Agent deploy fails

- Check IAM permissions (Step 2.3)
- Ensure your `requirements.txt` doesn't have incompatible packages
- Look at CloudWatch logs for the Runtime for detailed errors
- Try `agentcore launch --local` first (requires Docker) to test the container locally

---

## Reference Links

- [Elastic Agent Builder MCP Server docs](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/mcp-server)
- [Elastic Agent Builder Tools reference](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/tools/builtin-tools-reference)
- [Amazon Bedrock AgentCore docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-getting-started.html)
- [AgentCore Memory with Strands SDK](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/strands-sdk-memory.html)
- [AgentCore Runtime deployment guide](https://strandsagents.com/latest/documentation/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/)
- [Strands Agents MCP tools](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/)
- [Original blog post (Sep 2025)](https://www.elastic.co/search-labs/blog/elastic-mcp-server-amazon-bedrock-agentcore-runtime)
