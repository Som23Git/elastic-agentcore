"""Client script to invoke the deployed agent on AgentCore Runtime.

Usage:
    # Simple invocation
    python -m scripts.invoke_agent "What indices do I have?"

    # With a specific user ID (for memory personalization)
    python -m scripts.invoke_agent "Show me 5xx errors" --user analyst-001

    # Continue a previous session
    python -m scripts.invoke_agent "Now filter by US only" --session <session-id>
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke the Elastic Data Analyst agent")
    parser.add_argument("prompt", help="The question or instruction for the agent")
    parser.add_argument("--user", default="default-analyst", help="User ID for memory")
    parser.add_argument("--session", default=None, help="Session ID to continue")
    parser.add_argument("--region", default=None, help="AWS region override")
    args = parser.parse_args()

    region = args.region or os.getenv("AWS_REGION", "us-east-1")
    agent_arn = os.getenv("AGENT_RUNTIME_ARN")

    if not agent_arn:
        print("ERROR: AGENT_RUNTIME_ARN not set in .env")
        print("Deploy first with `agentcore launch`, then add the ARN to .env")
        sys.exit(1)

    client = boto3.client("bedrock-agentcore", region_name=region)

    payload_dict = {
        "prompt": args.prompt,
        "user_id": args.user,
    }
    if args.session:
        payload_dict["session_id"] = args.session

    # runtimeSessionId must be >= 33 characters
    runtime_session_id = f"invoke-{args.user}".ljust(33, "-")

    print(f"Agent : {agent_arn}")
    print(f"User  : {args.user}")
    print(f"Prompt: {args.prompt}")
    print("-" * 60)

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=runtime_session_id,
        payload=json.dumps(payload_dict).encode(),
        qualifier="DEFAULT",
    )

    body = json.loads(response["response"].read())
    print()
    print(body.get("response", json.dumps(body, indent=2)))
    print()

    if "session_id" in body:
        print(f"(session: {body['session_id']})")


if __name__ == "__main__":
    main()
