"""Chat route tests. The agent is monkeypatched; nothing here talks to AWS."""

import pytest

# AgentCore requires session ids of at least 33 characters.
VALID_SESSION = "test-session-00000000000000000000000001"
FAKE_ARN = "arn:aws:bedrock-agentcore:eu-west-2:000000000000:runtime/test"


@pytest.fixture
def chat_configured(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ARN", FAKE_ARN)


def test_chat_returns_agent_reply_and_forwards_inputs(client, chat_configured, monkeypatch):
    seen = {}

    def fake_invoke(**kwargs):
        seen.update(kwargs)
        return "We stock a range of graphics cards."

    # Patched where the route looks it up (app.main), not where it's defined.
    monkeypatch.setattr("app.main.invoke_support_agent", fake_invoke)

    response = client.post(
        "/chat", json={"message": "Do you sell GPUs?", "session_id": VALID_SESSION}
    )
    assert response.status_code == 200
    assert response.json() == {"reply": "We stock a range of graphics cards."}
    assert seen["agent_runtime_arn"] == FAKE_ARN
    assert seen["session_id"] == VALID_SESSION
    assert seen["message"] == "Do you sell GPUs?"


def test_chat_503_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("AGENT_RUNTIME_ARN", raising=False)
    response = client.post(
        "/chat", json={"message": "hi", "session_id": VALID_SESSION}
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Chat is not configured"


def test_chat_502_when_agent_fails(client, chat_configured, monkeypatch):
    def broken_invoke(**kwargs):
        raise RuntimeError("ARN arn:aws:secret must not leak")

    monkeypatch.setattr("app.main.invoke_support_agent", broken_invoke)

    response = client.post(
        "/chat", json={"message": "hi", "session_id": VALID_SESSION}
    )
    assert response.status_code == 502
    # The customer-facing message is stable and never echoes the real error.
    assert response.json()["detail"] == "Support agent unavailable"


def test_chat_422_on_short_session_id(client, chat_configured):
    response = client.post("/chat", json={"message": "hi", "session_id": "too-short"})
    assert response.status_code == 422


def test_chat_422_on_oversized_message(client, chat_configured):
    response = client.post(
        "/chat", json={"message": "x" * 501, "session_id": VALID_SESSION}
    )
    assert response.status_code == 422
