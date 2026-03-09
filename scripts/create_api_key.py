"""Create an Elasticsearch API key scoped for Agent Builder MCP access.

This is a convenience script. You can also create the key directly in
Kibana Dev Tools -- see the README for the raw request body.

Usage:
    python -m scripts.create_api_key

Prerequisites:
    - ELASTICSEARCH_URL set in .env (your Elasticsearch endpoint)
    - ELASTIC_ADMIN_API_KEY set in .env or as env var
      (an existing admin-level API key or user:pass for bootstrap)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from elasticsearch import Elasticsearch  # noqa: E402


def main() -> None:
    es_url = os.getenv("ELASTICSEARCH_URL")
    admin_key = os.getenv("ELASTIC_ADMIN_API_KEY")

    if not es_url:
        print("ERROR: Set ELASTICSEARCH_URL in your .env file")
        sys.exit(1)

    if admin_key:
        es = Elasticsearch(es_url, api_key=admin_key)
    else:
        print("No ELASTIC_ADMIN_API_KEY found -- trying basic auth.")
        username = input("Elasticsearch username: ")
        password = input("Elasticsearch password: ")
        es = Elasticsearch(es_url, basic_auth=(username, password))

    # Adjust index names to match your actual data
    index_patterns = [
        "kibana_sample_data_logs",
        "kibana_sample_data_ecommerce",
    ]

    print(f"\nCreating API key with read access to: {index_patterns}")

    response = es.security.create_api_key(
        name="agentcore-mcp-key",
        expiration="30d",
        role_descriptors={
            "mcp-access": {
                "cluster": ["monitor_inference"],
                "indices": [
                    {
                        "names": index_patterns,
                        "privileges": ["read", "view_index_metadata"],
                    }
                ],
                "applications": [
                    {
                        "application": "kibana-.kibana",
                        "privileges": ["feature_agentBuilder.read"],
                        "resources": ["space:default"],
                    }
                ],
            }
        },
    )

    print()
    print("=" * 60)
    print(f"  API Key ID : {response['id']}")
    print(f"  Name       : {response['name']}")
    print(f"  Encoded    : {response['encoded']}")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print(f"  ELASTIC_API_KEY={response['encoded']}")
    print()
    print("This key expires in 30 days. Rotate before expiry.")


if __name__ == "__main__":
    main()
