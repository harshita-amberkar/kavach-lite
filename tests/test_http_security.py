import unittest
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as kavach_app


class HttpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            kavach_app.app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        )
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

    def test_public_demo_routes_are_retired_and_owner_dashboard_remains(self):
        page = self.client.get("/")
        retired_page = self.client.get("/demo")
        retired_scan = self.client.post("/api/demo/scan", json={"text": "sample"})

        self.assertEqual(page.status_code, 200)
        self.assertIn('id="security"', page.text)
        self.assertIn('id="document-scanner"', page.text)
        self.assertIn('id="help"', page.text)
        self.assertEqual(retired_page.status_code, 404)
        self.assertEqual(retired_scan.status_code, 404)

    def test_dashboard_does_not_prompt_before_local_owner_request(self):
        script = self.client.get("/static/app.js")

        self.assertEqual(script.status_code, 200)
        self.assertIn('apiFetch("/api/health", { cache: "no-store" })', script.text)
        self.assertNotIn('fetch("/api/health"', script.text)
        self.assertNotIn("KAVACH_API_TOKEN", script.text)
        self.assertIn("if (response.status !== 401) return response;", script.text)
        self.assertIn("promptForKavachApiToken()", script.text)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required to exercise dashboard rendering")
    def test_dashboard_renders_autonomous_human_review_and_missing_output(self):
        app_js = Path(__file__).resolve().parents[1] / "static" / "app.js"
        harness = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("function renderProtectionSummary(data) {");
const end = source.indexOf("\nfunction reviewFieldValues(", start);
assert.notEqual(start, -1, "renderer exists in static/app.js");
assert.notEqual(end, -1, "renderer boundary exists in static/app.js");

const element = () => ({ textContent: "", hidden: false, className: "", open: false });
const elements = Object.fromEntries([
  "inp", "protection-summary-risk", "protection-summary-count-label",
  "protection-summary-count", "protection-summary-title",
  "protection-summary-message", "protection-summary-status", "protection-summary"
].map(id => [id, element()]));
elements.inp.value = "Original message";
const maskedTag = element();
const findingsDetails = element();
const context = {
  $: id => elements[id],
  friendlyFindingLabel: type => type,
  document: { querySelector(selector) {
    if (selector === ".masked-state-tag") return maskedTag;
    if (selector === ".findings-details") return findingsDetails;
    throw new Error(`Unexpected selector: ${selector}`);
  } }
};
const renderProtectionSummary = vm.runInNewContext(
  `${source.slice(start, end)}\nrenderProtectionSummary`, context
);

renderProtectionSummary({
  findings: [], masked_text: "Protected message", requires_human_review: true,
  verification: { status: "not_run" }
});
assert.equal(elements["protection-summary-status"].textContent, "Human review required");
assert.match(elements["protection-summary-message"].textContent,
  /verification was not performed/i);

renderProtectionSummary({
  findings: [{ type: "EMAIL" }], masked_text: "", requires_human_review: true,
  verification: { status: "not_run" }
});
assert.equal(elements["protection-summary-status"].textContent, "Not protected");
assert.match(elements["protection-summary-title"].textContent,
  /couldn't prepare a protected message/i);
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", harness, str(app_js)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

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
        health = self.client.get("/api/health", headers=self.auth)
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

    def test_scan_responses_include_separate_timing_metrics(self):
        native = self.client.post(
            "/api/scan",
            headers=self.auth,
            json={"text": "Contact sample@example.com."},
        )
        global_scan = self.client.post(
            "/api/scan-global",
            headers=self.auth,
            json={"text": "Contact sample@example.com."},
        )

        self.assertEqual(native.status_code, 200)
        self.assertEqual(global_scan.status_code, 200)
        self.assertEqual(native.json()["performance"]["presidio_detection_ms"], None)
        self.assertEqual(global_scan.json()["performance"]["ollama_review_ms"], None)
        for response in (native, global_scan):
            performance = response.json()["performance"]
            for field in ("native_detection_ms", "total_backend_processing_ms"):
                self.assertIsInstance(performance[field], float)
                self.assertGreaterEqual(performance[field], 0)
        global_performance = global_scan.json()["performance"]
        for field in ("presidio_detection_ms", "global_detection_ms"):
            self.assertIsInstance(global_performance[field], float)
            self.assertGreaterEqual(global_performance[field], 0)

    def test_health_reports_enabled_ollama_model_state_without_failing_readiness(self):
        response_body = SimpleNamespace(
            status_code=200,
            json=lambda: {"models": [{"name": kavach_app.OLLAMA_MODEL}]},
            raise_for_status=lambda: None,
        )
        with patch.object(kavach_app, "AGENT_ENABLED", True), patch(
            "app.httpx.get", return_value=response_body
        ) as get:
            response = self.client.get("/api/health", headers=self.auth)

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
