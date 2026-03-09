import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

KIBANA_URL = os.environ["KIBANA_URL"]
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "")
ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MEMORY_ID = os.getenv("MEMORY_ID", "")
AGENT_RUNTIME_ARN = os.getenv("AGENT_RUNTIME_ARN", "")
ES_MEMORY_INDEX = os.getenv("ES_MEMORY_INDEX", "")
