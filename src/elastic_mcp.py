from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

from .config import ELASTIC_API_KEY, KIBANA_URL


def create_elastic_mcp_client() -> MCPClient:
    """Connect to the Elastic Agent Builder hosted MCP endpoint.

    The endpoint is built into Elastic Cloud Serverless (9.2+) and
    Elastic Stack 9.3+.  No Docker container or ECR deployment needed.

    The hosted MCP exposes all built-in Agent Builder tools:
      - ES|QL queries
      - Index search
      - Index mappings / shard info
      - Plus any custom tools defined in Kibana → Agent Builder → Tools
    """
    mcp_url = f"{KIBANA_URL}/api/agent_builder/mcp"

    return MCPClient(
        lambda: streamablehttp_client(
            url=mcp_url,
            headers={
                "Authorization": f"ApiKey {ELASTIC_API_KEY}",
                "kbn-xsrf": "true",
            },
        ),
        prefix="elastic",
    )
