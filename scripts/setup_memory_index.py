"""One-time script: create the Elasticsearch index for agent long-term memory.

Run this once before enabling ES memory:
    uv run python -m scripts.setup_memory_index

The index uses a `semantic_text` field for the memory content, which
automatically chunks and generates embeddings via Elastic's built-in
inference. After running, set ES_MEMORY_INDEX in your .env to the
index name printed below.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ELASTICSEARCH_URL = os.environ["ELASTICSEARCH_URL"]
ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]
INDEX_NAME = "agent-memory"

MAPPING = {
    "mappings": {
        "properties": {
            "content": {"type": "semantic_text"},
            "tags": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
        }
    }
}


def main() -> None:
    es = Elasticsearch(ELASTICSEARCH_URL, api_key=ELASTIC_API_KEY)

    if es.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists -- skipping creation.")
    else:
        print(f"Creating index '{INDEX_NAME}' with semantic_text mapping...")
        es.indices.create(index=INDEX_NAME, body=MAPPING)
        print("Index created successfully.")

    print()
    print("=" * 60)
    print(f"  Index name : {INDEX_NAME}")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print(f"  ES_MEMORY_INDEX={INDEX_NAME}")
    print()


if __name__ == "__main__":
    main()
