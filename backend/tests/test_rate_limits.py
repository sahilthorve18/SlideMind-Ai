"""Tests for rate limiting, error handling, and function calling loop prevention."""
import os
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.genai import errors

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

from agents.agent import run_agent
from agents.registry import ToolContext
from app import create_app
from database import db
from services import gemini


@pytest.fixture()
def client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "DEV_LOGIN_ENABLED": True,
        "RATELIMIT_ENABLED": False
    })
    with app.app_context():
        db.create_all()
        with app.test_client() as c:
            yield c
        db.drop_all()


@pytest.fixture()
def auth_headers(client):
    """Returns authorization headers for a test user."""
    r = client.post("/api/auth/dev-login", json={"email": "test@example.com"})
    assert r.status_code == 200
    token = r.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


class TestGeminiRetryLogic:
    """Test exponential backoff retry logic for Gemini API calls."""

    def test_call_with_retry_success_on_first_attempt(self):
        """Should return immediately on successful first call."""
        mock_func = Mock(return_value="success")
        result = gemini._call_with_retry(mock_func, max_retries=3, base_delay=0.1)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_call_with_retry_success_after_rate_limit(self):
        """Should retry and succeed after encountering rate limit."""
        mock_func = Mock()
        # Create a proper ClientError with response_json
        rate_limit_error = errors.ClientError("429 Too Many Requests", {"error": {"code": 429}})
        rate_limit_error.status_code = 429
        mock_func.side_effect = [rate_limit_error, "success"]

        result = gemini._call_with_retry(mock_func, max_retries=3, base_delay=0.05)
        assert result == "success"
        assert mock_func.call_count == 2

    def test_call_with_retry_exhausts_retries(self):
        """Should raise GeminiRateLimitError after exhausting retries."""
        mock_func = Mock()
        rate_limit_error = errors.ClientError("429 Too Many Requests", {"error": {"code": 429}})
        rate_limit_error.status_code = 429
        mock_func.side_effect = rate_limit_error

        with pytest.raises(gemini.GeminiRateLimitError) as exc_info:
            gemini._call_with_retry(mock_func, max_retries=2, base_delay=0.05)

        assert "rate-limit" in str(exc_info.value).lower()
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_call_with_retry_non_rate_limit_error_raises_immediately(self):
        """Should raise non-rate-limit errors immediately without retry."""
        mock_func = Mock()
        api_error = errors.APIError("Invalid request", {"error": {"message": "Invalid"}})
        mock_func.side_effect = api_error

        with pytest.raises(gemini.GeminiError):
            gemini._call_with_retry(mock_func, max_retries=3, base_delay=0.05)

        assert mock_func.call_count == 1  # No retries

    def test_call_with_retry_exponential_backoff_timing(self):
        """Should implement exponential backoff (1s, 2s, 4s)."""
        mock_func = Mock()
        rate_limit_error = errors.ClientError("429 quota exceeded", {"error": {"code": 429}})
        rate_limit_error.status_code = 429
        mock_func.side_effect = rate_limit_error

        start = time.time()
        with pytest.raises(gemini.GeminiRateLimitError):
            gemini._call_with_retry(mock_func, max_retries=2, base_delay=0.1)
        elapsed = time.time() - start

        # Should wait 0.1 + 0.2 = 0.3s minimum (with some tolerance)
        assert elapsed >= 0.25
        assert mock_func.call_count == 3


class TestAgentLoopPrevention:
    """Test that the agent detects and breaks out of function calling loops."""

    @patch("agents.agent.gemini._client")
    def test_agent_detects_function_calling_loop(self, mock_client, client):
        """Should break out when the same tool is called repeatedly."""
        with client.application.app_context():
            # Create mock responses that repeatedly call the same function
            mock_response_with_calls = MagicMock()
            mock_fc = MagicMock()
            mock_fc.name = "search_knowledge_base"  # Set as string, not MagicMock
            mock_fc.args = {"query": "test"}
            mock_response_with_calls.function_calls = [mock_fc]
            mock_response_with_calls.candidates = [MagicMock(content=MagicMock())]
            mock_response_with_calls.text = None

            # Final response after breaking the loop
            mock_final_response = MagicMock()
            mock_final_response.function_calls = None
            mock_final_response.text = "I cannot find that information."

            mock_generate = Mock()
            # Return the looping response 3 times, then the final response
            mock_generate.side_effect = [
                mock_response_with_calls,
                mock_response_with_calls,
                mock_response_with_calls,
                mock_final_response,
            ]

            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content = mock_generate
            mock_client.return_value = mock_client_instance

            with patch("agents.registry.execute", return_value={"results": []}):
                history = [{"role": "user", "content": "Find information about quantum physics"}]
                ctx = ToolContext(user_id="test_user", conversation_id="test_conv", google_connected=False)

                result = run_agent(history, ctx, active_presentation_id=None, max_steps=10)

                assert "cannot find" in result.lower() or "loop" in result.lower() or "stuck" in result.lower()
                # Should not exhaust all 10 steps due to loop detection
                assert mock_generate.call_count < 10

    @patch("agents.agent.gemini._client")
    def test_agent_allows_different_function_calls(self, mock_client, client):
        """Should not break when different tools are called in sequence."""
        with client.application.app_context():
            # Create varied function calls
            mock_response1 = MagicMock()
            mock_fc1 = MagicMock()
            mock_fc1.name = "search_knowledge_base"
            mock_fc1.args = {"query": "topic A"}
            mock_response1.function_calls = [mock_fc1]
            mock_response1.candidates = [MagicMock(content=MagicMock())]
            mock_response1.text = None

            mock_response2 = MagicMock()
            mock_fc2 = MagicMock()
            mock_fc2.name = "web_research"
            mock_fc2.args = {"query": "topic B"}
            mock_response2.function_calls = [mock_fc2]
            mock_response2.candidates = [MagicMock(content=MagicMock())]
            mock_response2.text = None

            mock_final = MagicMock()
            mock_final.function_calls = None
            mock_final.text = "Here is the answer based on the research."

            mock_generate = Mock(side_effect=[mock_response1, mock_response2, mock_final])

            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content = mock_generate
            mock_client.return_value = mock_client_instance

            with patch("agents.registry.execute", return_value={"results": []}):
                history = [{"role": "user", "content": "Research two topics"}]
                ctx = ToolContext(user_id="test_user", conversation_id="test_conv", google_connected=False)

                result = run_agent(history, ctx, active_presentation_id=None, max_steps=10)

                assert "answer based on the research" in result.lower()
                assert mock_generate.call_count == 3


class TestChatEndpointErrorHandling:
    """Test that the chat endpoint returns proper error responses."""

    def test_chat_returns_429_on_rate_limit(self, client, auth_headers):
        """Should return 429 status when Gemini is rate-limited."""
        with patch("routes.conversations.run_agent") as mock_agent:
            mock_agent.side_effect = gemini.GeminiRateLimitError("Rate limit exceeded")

            resp = client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )

            assert resp.status_code == 429
            data = resp.get_json()
            assert data["error"]["code"] == "rate_limit_exceeded"
            assert "rate" in data["error"]["message"].lower() and "limit" in data["error"]["message"].lower()
            assert "retry_after" in data["error"]["details"]

    def test_chat_returns_502_on_gemini_error(self, client, auth_headers):
        """Should return 502 status on general Gemini errors."""
        with patch("routes.conversations.run_agent") as mock_agent:
            mock_agent.side_effect = gemini.GeminiError("Service unavailable")

            resp = client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )

            assert resp.status_code == 502
            data = resp.get_json()
            assert data["error"]["code"] == "ai_unavailable"

    def test_chat_returns_503_when_not_configured(self, client, auth_headers):
        """Should return 503 when Gemini API key is not configured."""
        with patch("routes.conversations.run_agent") as mock_agent:
            mock_agent.side_effect = gemini.GeminiNotConfigured("Missing API key")

            resp = client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )

            assert resp.status_code == 503
            data = resp.get_json()
            assert data["error"]["code"] == "ai_not_configured"

    def test_chat_returns_500_on_unexpected_error(self, client, auth_headers):
        """Should return 500 and log unexpected errors."""
        with patch("routes.conversations.run_agent") as mock_agent:
            mock_agent.side_effect = RuntimeError("Unexpected error")

            resp = client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )

            assert resp.status_code == 500
            data = resp.get_json()
            assert data["error"]["code"] == "internal_error"
            assert "unexpected" in data["error"]["message"].lower()

    def test_chat_preserves_conversation_id_in_errors(self, client, auth_headers):
        """Should include conversation_id in error responses for client state management."""
        with patch("routes.conversations.run_agent") as mock_agent:
            mock_agent.side_effect = gemini.GeminiError("Test error")

            resp = client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=auth_headers,
            )

            data = resp.get_json()
            assert "conversation_id" in data["error"]["details"]


class TestToolExecutionFailures:
    """Test that tool failures are handled gracefully."""

    @patch("agents.agent.gemini._client")
    @patch("agents.registry.execute")
    def test_tool_failure_does_not_crash_agent(self, mock_execute, mock_client, client):
        """Tool failures should be returned to the model, not crash the agent."""
        with client.application.app_context():
            # First call with tool invocation
            mock_response_with_call = MagicMock()
            mock_fc = MagicMock()
            mock_fc.name = "search_knowledge_base"
            mock_fc.args = {"query": "test"}
            mock_response_with_call.function_calls = [mock_fc]
            mock_response_with_call.candidates = [MagicMock(content=MagicMock())]
            mock_response_with_call.text = None

            # Final response after tool failure
            mock_final_response = MagicMock()
            mock_final_response.function_calls = None
            mock_final_response.text = "I couldn't find that information."

            mock_generate = Mock(side_effect=[mock_response_with_call, mock_final_response])

            mock_client_instance = MagicMock()
            mock_client_instance.models.generate_content = mock_generate
            mock_client.return_value = mock_client_instance

            # Simulate tool failure
            mock_execute.return_value = {"error": "Tool execution failed"}

            history = [{"role": "user", "content": "Search for something"}]
            ctx = ToolContext(user_id="test_user", conversation_id="test_conv", google_connected=False)

            result = run_agent(history, ctx, active_presentation_id=None, max_steps=10)

            assert result  # Should still return a result
            assert mock_execute.called  # Tool was attempted
            assert mock_generate.call_count == 2  # Model got the failure and responded
