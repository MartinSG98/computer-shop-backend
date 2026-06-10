"""Thin client for the support agent on Bedrock AgentCore.

The agent's HTTP contract is {"prompt": ...} in, {"reply": ...} out (see the
computer-shop-support-agent repo). This module is the only place the backend
knows that, mirroring how repository.py is the only place that knows DynamoDB.
"""

import json


def invoke_support_agent(
    agent_runtime_arn: str,
    region_name: str | None,
    session_id: str,
    message: str,
) -> str:
    """Send one customer message to the agent and return its reply text.

    The session id groups messages into a conversation: AgentCore routes the
    same id to the same warm session, which is how follow-up questions keep
    their context. Raises on any AWS/contract failure; the route maps that
    to a 502.
    """
    # Imported lazily so tests and the in-memory dev server never pay for it.
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=region_name)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": message}),
    )
    # The body is a streaming payload, not a dict. We read it fully, then parse.
    body = json.loads(response["response"].read())
    return body["reply"]
