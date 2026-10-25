import unittest

from fastapi.testclient import TestClient
from app import app


class SecurityMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            app,
            base_url="http://127.0.0.1",
        )

        # Use the API token configured by the current app instance.
        self.auth = {
            "X-KAVACH-Token": app.state.api_token,
        }

        self.addCleanup(self.client.close)

    def test_local_health_endpoint_needs_no_token(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)

    def test_untrusted_host_is_rejected(self):
        response = self.client.get(
            "/api/health",
            headers={"host": "evil.example"},
        )

        self.assertEqual(response.status_code, 400)

    def test_cross_origin_write_is_rejected(self):
        response = self.client.post(
            "/api/scan",
            headers={"Origin": "https://evil.example"},
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 403)

    def test_same_origin_write_with_token_is_allowed(self):
        response = self.client.post(
            "/api/scan",
            headers={
                **self.auth,
                "Origin": "http://127.0.0.1",
            },
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 200)

    def test_missing_token_is_rejected(self):
        response = self.client.post(
            "/api/scan",
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_rejected(self):
        response = self.client.post(
            "/api/scan",
            headers={"X-KAVACH-Token": "invalid-token"},
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 401)

    def test_originless_client_with_token_is_allowed(self):
        response = self.client.post(
            "/api/scan",
            headers=self.auth,
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 200)
    def test_chat_proxy_requires_kavach_token(self):
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid or missing KAVACH API token.",
        )

    def test_chat_proxy_still_requires_provider_bearer(self):
        response = self.client.post(
            "/v1/chat/completions",
            headers=self.auth,
            json={
                "model": "test-model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("Bearer", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()