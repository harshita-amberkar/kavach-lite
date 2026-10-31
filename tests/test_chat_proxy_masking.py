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


    def test_global_finding_is_masked_before_forwarding(self):
        """The chat proxy must use global detection and forward masked text."""
        mock_client = MockUpstreamClient()
        content = "Morgan Example is assigned to the case."

        global_result = {
            "findings": [
                {
                    "type": "PERSON",
                    "start": 0,
                    "end": 14,
                    "confidence": 0.99,
                    "value": "Morgan Example",
                }
            ],
            "masked_text": "[PERSON] is assigned to the case.",
            "risk": {"level": "medium", "score": 15},
        }

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }
        request_body = {
            "model": "test-model",
            "messages": [{"role": "user", "content": content}],
        }

        with patch(
            "app.analyze_global",
            return_value=global_result,
        ) as global_scan:
            with patch(
                "app.analyze",
                side_effect=AssertionError(
                    "The chat proxy must use analyze_global(), not analyze()."
                ),
            ):
                with patch(
                    "app.httpx.AsyncClient",
                    return_value=mock_client,
                ):
                    with TestClient(
                        kavach_app.app,
                        base_url="http://127.0.0.1",
                    ) as client:
                        response = client.post(
                            "/v1/chat/completions",
                            headers=headers,
                            json=request_body,
                        )

        self.assertEqual(response.status_code, 200, response.text)
        global_scan.assert_called_once_with(content)
        self.assertIsNotNone(mock_client.captured_payload)

        forwarded_text = mock_client.captured_payload["messages"][0]["content"]
        self.assertEqual(
            forwarded_text,
            "[PERSON] is assigned to the case.",
        )
        self.assertNotIn("Morgan Example", forwarded_text)
        self.assertEqual(response.headers.get("X-Kavach-Redactions"), "1")


    def test_real_global_context_finding_is_masked_before_forwarding(self):
        """Exercise a real global-only context rule through the proxy."""
        mock_client = MockUpstreamClient()
        content = "Our fictional company has an unannounced product roadmap."

        legacy_result = kavach_app.analyze(content)
        self.assertFalse(
            any(
                finding.get("type") == "CONFIDENTIAL_BUSINESS"
                for finding in legacy_result.get("findings", [])
            ),
            "The fixture should be global-only, not detected by analyze().",
        )

        direct_global_result = kavach_app.analyze_global(content)
        self.assertIn("[CONFIDENTIAL_BUSINESS]", direct_global_result.get("masked_text", ""))
        self.assertTrue(
            any(
                finding.get("type") == "CONFIDENTIAL_BUSINESS"
                for finding in direct_global_result.get("findings", [])
            ),
            "The global contextual rule should detect the synthetic fixture.",
        )

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }
        request_body = {
            "model": "test-model",
            "messages": [{"role": "user", "content": content}],
        }

        with patch(
            "app.analyze_global",
            wraps=kavach_app.analyze_global,
        ) as global_scan:
            with patch(
                "app.analyze",
                side_effect=AssertionError(
                    "The chat proxy must not fall back to analyze()."
                ),
            ):
                with patch(
                    "app.httpx.AsyncClient",
                    return_value=mock_client,
                ):
                    with TestClient(
                        kavach_app.app,
                        base_url="http://127.0.0.1",
                    ) as client:
                        response = client.post(
                            "/v1/chat/completions",
                            headers=headers,
                            json=request_body,
                        )

        self.assertEqual(response.status_code, 200, response.text)
        global_scan.assert_called_once_with(content)
        self.assertIsNotNone(mock_client.captured_payload)
        forwarded_text = mock_client.captured_payload["messages"][0]["content"]
        self.assertIn("[CONFIDENTIAL_BUSINESS]", forwarded_text)
        self.assertNotIn("unannounced product roadmap", forwarded_text.lower())
        self.assertEqual(
            response.headers.get("X-Kavach-Redactions"),
            str(len(direct_global_result.get("findings", []))),
        )



    def test_bearer_secret_is_masked_before_forwarding(self):
        """A synthetic bearer secret must not reach the mock upstream."""
        mock_client = MockUpstreamClient()
        canary = "kavach-test-secret-DO-NOT-USE-123456789"
        content = f"Authorization: Bearer {canary}"

        direct_result = kavach_app.analyze_global(content)
        self.assertTrue(
            any(
                finding.get("type") == "API_KEY"
                for finding in direct_result.get("findings", [])
            ),
            "The global detector must identify the synthetic bearer secret.",
        )
        self.assertNotIn(canary, direct_result.get("masked_text", ""))

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }
        request_body = {
            "model": "test-model",
            "messages": [{"role": "user", "content": content}],
        }

        with patch(
            "app.analyze_global",
            wraps=kavach_app.analyze_global,
        ) as global_scan:
            with patch(
                "app.analyze",
                side_effect=AssertionError(
                    "The chat proxy must use the global detector."
                ),
            ):
                with patch(
                    "app.httpx.AsyncClient",
                    return_value=mock_client,
                ):
                    with TestClient(
                        kavach_app.app,
                        base_url="http://127.0.0.1",
                    ) as client:
                        response = client.post(
                            "/v1/chat/completions",
                            headers=headers,
                            json=request_body,
                        )

        self.assertEqual(response.status_code, 200, response.text)
        global_scan.assert_called_once_with(content)
        self.assertIsNotNone(mock_client.captured_payload)

        forwarded_text = mock_client.captured_payload["messages"][0]["content"]
        self.assertIn("[API_KEY]", forwarded_text)
        self.assertNotIn(canary, forwarded_text)
        self.assertNotIn(content, forwarded_text)

        self.assertEqual(
            response.headers.get("X-Kavach-Redactions"),
            str(len(direct_result.get("findings", []))),
        )

        print("PASS: Synthetic bearer secret was masked before mock forwarding.")



    def test_high_risk_prompt_is_blocked_before_forwarding(self):
        """High-risk prompts must not reach the upstream."""
        mock_client = MockUpstreamClient()
        canary = "kavach-test-secret-DO-NOT-USE-123456789"
        content = f"Authorization: Bearer {canary}"

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }
        request_body = {
            "model": "test-model",
            "messages": [{"role": "user", "content": content}],
        }

        with patch("app.BLOCK_HIGH", True):
            with patch("app.httpx.AsyncClient", return_value=mock_client):
                with TestClient(
                    kavach_app.app,
                    base_url="http://127.0.0.1",
                ) as client:
                    response = client.post(
                        "/v1/chat/completions",
                        headers=headers,
                        json=request_body,
                    )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("Blocked", response.json().get("error", ""))
        self.assertIsNone(mock_client.captured_payload)
        self.assertIsNone(mock_client.captured_headers)
        self.assertNotIn(canary, response.text)

        print("PASS: High-risk prompt blocked before upstream forwarding.")


    def test_proxy_fallback_masks_context_when_presidio_unavailable(self):
        """Context rules must still protect prompts when Presidio fails."""
        mock_client = MockUpstreamClient()
        content = "Our fictional company has an unannounced product roadmap."

        headers = {
            "x-kavach-token": kavach_app.app.state.api_token,
            "Authorization": "Bearer test-only-provider-token",
        }
        request_body = {
            "model": "test-model",
            "messages": [{"role": "user", "content": content}],
        }

        with patch(
            "kavach.global_detector._get_analyzer",
            side_effect=RuntimeError("synthetic Presidio unavailable"),
        ) as presidio_failure:
            with patch(
                "app.httpx.AsyncClient",
                return_value=mock_client,
            ):
                with TestClient(
                    kavach_app.app,
                    base_url="http://127.0.0.1",
                ) as client:
                    response = client.post(
                        "/v1/chat/completions",
                        headers=headers,
                        json=request_body,
                    )

        self.assertEqual(response.status_code, 200, response.text)
        presidio_failure.assert_called_once()
        self.assertIsNotNone(mock_client.captured_payload)

        forwarded_text = mock_client.captured_payload["messages"][0]["content"]
        self.assertIn("[CONFIDENTIAL_BUSINESS]", forwarded_text)
        self.assertNotIn("unannounced product roadmap", forwarded_text.lower())

        print("PASS: Context masking survived simulated Presidio failure.")
if __name__ == "__main__":
    unittest.main()