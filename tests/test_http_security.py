import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as kavach_app


class HttpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(kavach_app.app, base_url="http://127.0.0.1")
        self.auth = {"X-KAVACH-Token": kavach_app.app.state.api_token}
        kavach_app.app.state.rate_limit_events.clear()

    def tearDown(self):
        self.client.close()
        kavach_app.app.state.rate_limit_events.clear()

    def test_dashboard_and_static_assets_have_security_headers(self):
        page = self.client.get("/")
        script = self.client.get("/static/app.js")
        extension = self.client.get("/static/downloads/kavach-chrome-extension.zip")

        self.assertEqual(page.status_code, 200)
        self.assertIn("/static/app.js", page.text)
        self.assertNotIn("<script>", page.text)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(extension.status_code, 200)
        self.assertEqual(page.headers["x-content-type-options"], "nosniff")
        self.assertEqual(page.headers["referrer-policy"], "no-referrer")
        csp = page.headers["content-security-policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("unsafe-eval", csp)

    def test_all_expensive_routes_have_independent_rate_limits(self):
        self.assertEqual(
            set(kavach_app.RATE_LIMITS),
            {"/api/scan", "/api/scan-file", "/v1/chat/completions"},
        )
        for path in kavach_app.RATE_LIMITS:
            request = SimpleNamespace(
                url=SimpleNamespace(path=path),
                client=SimpleNamespace(host="127.0.0.1"),
                app=kavach_app.app,
            )
            kavach_app.app.state.rate_limit_events.clear()
            with patch.dict(kavach_app.RATE_LIMITS, {path: 1}):
                self.assertTrue(kavach_app._rate_limit_allowed(request, now=10.0))
                self.assertFalse(kavach_app._rate_limit_allowed(request, now=11.0))

    def test_health_and_sensitive_api_headers(self):
        health = self.client.get("/api/health")
        scan = self.client.post(
            "/api/scan",
            headers=self.auth,
            json={"text": "Ordinary test text."},
        )
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertIn(health.json()["database"], {"available", "unavailable"})
        self.assertIn(health.json()["ollama"]["status"], {
            "disabled", "available", "unavailable"
        })
        self.assertEqual(scan.status_code, 200)
        for response in (health, scan):
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_health_reports_enabled_ollama_model_state_without_failing_readiness(self):
        response_body = SimpleNamespace(
            status_code=200,
            json=lambda: {"models": [{"name": kavach_app.OLLAMA_MODEL}]},
            raise_for_status=lambda: None,
        )
        with patch.object(kavach_app, "AGENT_ENABLED", True), patch(
            "app.httpx.get", return_value=response_body
        ) as get:
            response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["ollama"], {
            "status": "available", "model_available": True
        })
        get.assert_called_once()

    def test_scan_rate_limit_enforcement_and_window_recovery(self):
        request = SimpleNamespace(
            url=SimpleNamespace(path="/api/scan"),
            client=SimpleNamespace(host="127.0.0.1"),
            app=kavach_app.app,
        )
        with patch.dict(kavach_app.RATE_LIMITS, {"/api/scan": 2}):
            first = self.client.post(
                "/api/scan", headers=self.auth, json={"text": "one"}
            )
            second = self.client.post(
                "/api/scan", headers=self.auth, json={"text": "two"}
            )
            limited = self.client.post(
                "/api/scan", headers=self.auth, json={"text": "three"}
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(limited.status_code, 429)
            self.assertEqual(limited.headers["retry-after"], "60")
            self.assertEqual(limited.headers["cache-control"], "no-store")

            kavach_app.app.state.rate_limit_events.clear()
            self.assertTrue(kavach_app._rate_limit_allowed(request, now=100.0))
            self.assertTrue(kavach_app._rate_limit_allowed(request, now=101.0))
            self.assertFalse(kavach_app._rate_limit_allowed(request, now=102.0))
            self.assertTrue(kavach_app._rate_limit_allowed(request, now=161.0))


if __name__ == "__main__":
    unittest.main()
