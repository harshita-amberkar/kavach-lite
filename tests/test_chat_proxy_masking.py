import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as kavach_app


class MockUpstreamResponse:
    """Simulate a successful response from an AI provider."""

    status_code = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def aiter_bytes(self):
        response = {
            "id": "mock-response",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Mock response successful.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        yield json.dumps(response).encode("utf-8")


class MockUpstreamClient:
    """Capture the request KAVACH would send to the provider."""

    def __init__(self):
        self.captured_payload = None
        self.captured_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    def stream(self, method, url, **kwargs):
        self.captured_payload = kwargs.get("json")
        self.captured_headers = kwargs.get("headers")
        return MockUpstreamResponse()


class ChatProxyMaskingTests(unittest.TestCase):

    def test_email_is_masked_before_forwarding(self):
        mock_client = MockUpstreamClient()

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }

        request_body = {
            "model": "test-model",
            "messages": [
                {
                    "role": "user",
                    "content": "Contact qa@example.com for support.",
                }
            ],
        }

        with patch(
            "app.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with TestClient(kavach_app.app,base_url="http://127.0.0.1",) as client:
                response = client.post(
                    "/v1/chat/completions",
                    headers=headers,
                    json=request_body,
                )

        self.assertEqual(
            response.status_code,
            200,
            response.text,
        )

        self.assertIsNotNone(mock_client.captured_payload)
        self.assertIsNotNone(mock_client.captured_headers)

        # Only the provider authorization and content type should be sent.
        forwarded_header_names = {
            name.lower() for name in mock_client.captured_headers
        }
        self.assertEqual(
            forwarded_header_names,
            {"authorization", "content-type"},
        )
        self.assertEqual(
            mock_client.captured_headers["Authorization"],
            "Bearer test-only-provider-token",
        )

        forwarded_text = (
            mock_client.captured_payload["messages"][0]["content"]
        )

        self.assertNotIn("qa@example.com", forwarded_text)
        self.assertIn("[EMAIL]", forwarded_text)

        # Confirm the KAVACH authentication token is not sent upstream.
        # The mock captures only the JSON payload; the proxy code should
        # forward provider Authorization, not X-KAVACH-Token.

        print("Original email was masked before forwarding.")
        print("Forwarded message:", forwarded_text)


if __name__ == "__main__":
    unittest.main()