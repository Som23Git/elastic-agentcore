"""One-time script: create the AgentCore Memory store with long-term strategies.

Run this once before deploying the agent:
    python -m scripts.setup_memory

It creates a Memory resource with three long-term extraction strategies:
  - SessionSummarizer  -- condenses each conversation into a summary
  - AnalystPreferences -- tracks the user's preferred indices, time ranges, etc.
  - DataInsights       -- extracts factual findings from data analysis sessions

After running, copy the printed MEMORY_ID into your .env file.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from bedrock_agentcore.memory import MemoryClient  # noqa: E402

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def main() -> None:
    client = MemoryClient(region_name=AWS_REGION)

    print(f"Creating AgentCore Memory store in {AWS_REGION}...")
    print("This may take a minute while strategies are provisioned.\n")

    memory = client.create_memory_and_wait(
        name="ElasticDataAnalystMemory",
        description=(
            "Memory for an AI data analyst agent that queries "
            "weblogs and ecommerce data in Elasticsearch"
        ),
        strategies=[
            {
                "summaryMemoryStrategy": {
                    "name": "SessionSummarizer",
                    "description": "Summarizes each conversation session",
                    "namespaces": ["/summaries/{actorId}/{sessionId}/"],
                }
            },
            {
                "userPreferenceMemoryStrategy": {
                    "name": "AnalystPreferences",
                    "description": (
                        "Tracks preferred indices, query patterns, "
                        "time ranges, and areas of interest"
                    ),
                    "namespaces": ["/preferences/{actorId}/"],
                }
            },
            {
                "semanticMemoryStrategy": {
                    "name": "DataInsights",
                    "description": (
                        "Extracts factual findings and data insights "
                        "discovered during analysis sessions"
                    ),
                    "namespaces": ["/facts/{actorId}/"],
                }
            },
        ],
    )

    memory_id = memory.get("id", "UNKNOWN")
    status = memory.get("status", "UNKNOWN")

    print("=" * 60)
    print(f"  Memory ID : {memory_id}")
    print(f"  Status    : {status}")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print(f"  MEMORY_ID={memory_id}")
    print()

    if status != "ACTIVE":
        print("WARNING: Memory is not yet ACTIVE. Wait a moment and check")
        print("the AWS console, or re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
