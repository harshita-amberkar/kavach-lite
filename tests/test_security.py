import unittest

from fastapi.testclient import TestClient
from app import app


class SecurityMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        )
        self.previous_access_mode = app.state.owner_access_mode
        app.state.owner_access_mode = "local"
        self.auth = {
            "X-KAVACH-Token": app.state.api_token,
        }
        self.addCleanup(self.client.close)
        self.addCleanup(
            setattr, app.state, "owner_access_mode", self.previous_access_mode
        )

    def test_local_owner_dashboard_and_apis_need_no_manual_token(self):
        public = self.client.get("/healthz")
        owner_without_token = self.client.get("/api/health")
        owner_with_invalid_token = self.client.get(
            "/api/health",
            headers={"X-KAVACH-Token": "invalid-token"},
        )
        scan_without_token = self.client.post(
            "/api/scan",
            json={"text": "Ordinary test text."},
        )
        global_scan_without_token = self.client.post(
            "/api/scan-global",
            json={"text": "Ordinary test text."},
        )
        history_without_token = self.client.get("/api/agentic/history")

        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json(), {"status": "ok"})
        self.assertEqual(owner_without_token.status_code, 200)
        self.assertEqual(owner_with_invalid_token.status_code, 200)
        self.assertEqual(scan_without_token.status_code, 200)
        self.assertEqual(global_scan_without_token.status_code, 200)
        self.assertEqual(history_without_token.status_code, 200)

    def test_local_mode_rejects_remote_owner_api_even_with_spoofed_headers(self):
        remote_client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("198.51.100.27", 50000),
        )
        self.addCleanup(remote_client.close)
        response = remote_client.get(
            "/api/health",
            headers={
                **self.auth,
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
                "X-Forwarded-Host": "127.0.0.1",
                "X-Forwarded-Proto": "http",
                "Forwarded": "for=127.0.0.1;proto=http;host=127.0.0.1",
                "Origin": "http://127.0.0.1",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("only from this device", response.json()["detail"])

    def test_token_mode_requires_a_valid_token_and_allows_remote_api_access(self):
        app.state.owner_access_mode = "token"
        remote_client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("198.51.100.27", 50000),
        )
        self.addCleanup(remote_client.close)

        missing = remote_client.get("/api/health")
        allowed = remote_client.get("/api/health", headers=self.auth)

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(allowed.status_code, 200)

    def test_untrusted_host_is_rejected(self):
        response = self.client.get(
            "/api/health",
            headers={**self.auth, "host": "evil.example"},
        )

        self.assertEqual(response.status_code, 400)

    def test_cross_origin_write_is_rejected(self):
        response = self.client.post(
            "/api/scan",
            headers={"Origin": "https://evil.example"},
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 403)

    def test_same_origin_write_without_token_is_allowed_from_loopback(self):
        response = self.client.post(
            "/api/scan",
            headers={"Origin": "http://127.0.0.1"},
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 200)

    def test_token_mode_rejects_missing_or_invalid_token(self):
        app.state.owner_access_mode = "token"
        response = self.client.post(
            "/api/scan",
            headers={"X-KAVACH-Token": "invalid-token"},
            json={"text": "Ordinary test text."},
        )
        missing = self.client.post(
            "/api/scan",
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(missing.status_code, 401)

    def test_originless_loopback_client_is_allowed(self):
        response = self.client.post(
            "/api/scan",
            json={"text": "Ordinary test text."},
        )

        self.assertEqual(response.status_code, 200)

    def test_chat_proxy_requires_kavach_token(self):
        app.state.owner_access_mode = "token"
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
