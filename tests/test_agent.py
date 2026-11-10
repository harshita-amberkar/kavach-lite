import json
import os
import unittest
from unittest.mock import patch

import httpx

from kavach import agent


# Construct a synthetic token at runtime so source-code secret scanners
# don't mistake the test fixture for a hardcoded credential.
TEST_API_TOKEN = "sk-" + ("T" * 24)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.text = "Contact demo@example.com for help"
        self.findings = [{
            "type": "EMAIL",
            "start": 8,
            "end": 24,
            "confidence": 0.97,
        }]

    def test_ollama_url_accepts_only_loopback_destinations(self):
        for url in (
            "http://localhost:11434/api/generate",
            "http://127.0.0.1:11434/api/generate",
            "http://[::1]:11434/api/generate",
        ):
            with self.subTest(url=url):
                self.assertEqual(agent.validate_ollama_url(url), url)

        for url in (
            "https://ollama.example/api/generate",
            "http://192.168.1.25:11434/api/generate",
            "not a valid URL",
            "http://localhost:invalid/api/generate",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    agent.validate_ollama_url(url)

    @patch("kavach.agent.httpx.post")
    def test_ollama_request_ignores_environment_proxies(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": json.dumps({
                "reviews": [{
                    "id": 0,
                    "assessment": "likely",
                    "reason": "Email context",
                }]
            })
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.dict(os.environ, {
            "HTTP_PROXY": "http://proxy.invalid:8080",
            "HTTPS_PROXY": "http://proxy.invalid:8080",
            "ALL_PROXY": "http://proxy.invalid:8080",
        }), patch.object(agent, "AGENT_ENABLED", True):
            agent.review_findings(self.text, self.findings)

        self.assertIs(mock_post.call_args.kwargs["trust_env"], False)
        self.assertIs(
            mock_post.call_args.kwargs["follow_redirects"], False
        )

    @patch("kavach.agent.httpx.post")
    def test_remote_ollama_url_is_rejected_before_request(self, mock_post):
        remote_url = "http://192.168.1.25:11434/api/generate"
        with patch.object(agent, "OLLAMA_URL", remote_url), patch.object(
            agent,
            "AGENT_ENABLED",
            True,
        ):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(result["status"], "unavailable")
        mock_post.assert_not_called()

    @patch("kavach.agent.httpx.post")
    def test_sensitive_value_is_not_sent_to_model(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": json.dumps({
                "reviews": [{
                    "id": 0,
                    "assessment": "likely",
                    "reason": "Email context",
                }]
            })
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(
                self.text,
                self.findings,
            )

        self.assertEqual(result["status"], "ok")

        prompt = mock_post.call_args.kwargs["json"]["prompt"]

        self.assertNotIn("demo@example.com", prompt)
        self.assertNotIn("Contact", prompt)
        self.assertIn("[REDACTED]", prompt)
        candidates = json.loads(prompt.split("Candidates:\n", 1)[1])
        self.assertEqual(candidates[0]["context"], "[REDACTED]")

    @patch("kavach.agent.httpx.post")
    def test_review_returns_bounded_model_concerns_and_recommendations(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": json.dumps({
                "reviews": [{
                    "id": 0,
                    "assessment": "likely",
                    "reason": "Candidate type is email.",
                    "privacy_concerns": ["Personal contact information."],
                    "recommendations": ["Review the masked message before sharing."],
                }]
            })
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["reviews"][0]["privacy_concerns"],
            ["Personal contact information."],
        )
        self.assertEqual(
            result["reviews"][0]["recommendations"],
            ["Review the masked message before sharing."],
        )

    @patch("kavach.agent.httpx.post")
    def test_invalid_model_json_fails_safely(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": "not valid json"
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(
                self.text,
                self.findings,
            )

        self.assertEqual(
            result,
            {"status": "unavailable", "reviews": []},
        )

    @patch("kavach.agent.httpx.post")
    def test_non_object_ollama_response_fails_safely(self, mock_post):
        mock_post.return_value.json.return_value = []
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(
            result, {"status": "unavailable", "reviews": []}
        )

    @patch("kavach.agent.httpx.post")
    def test_non_object_model_json_fails_safely(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": "[]"
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(
            result, {"status": "unavailable", "reviews": []}
        )

    @patch("kavach.agent.httpx.post")
    def test_non_list_reviews_fails_safely(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": json.dumps({"reviews": {}})
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(
            result, {"status": "unavailable", "reviews": []}
        )

    def test_disabled_agent_does_not_call_model(self):
        with patch.object(agent, "AGENT_ENABLED", False):
            with patch("kavach.agent.httpx.post") as mock_post:
                result = agent.review_findings(
                    self.text,
                    self.findings,
                )

        self.assertEqual(
            result,
            {"status": "disabled", "reviews": []},
        )
        mock_post.assert_not_called()

    @patch("kavach.agent.httpx.post")
    def test_timeout_is_reported_without_exposing_exception_text(self, mock_post):
        mock_post.side_effect = httpx.ReadTimeout(
            "PRIVATE_EMAIL_SENTINEL"
        )

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "timeout")
        self.assertNotIn("PRIVATE_EMAIL_SENTINEL", repr(result))

    def test_sanitizer_redacts_neighboring_sensitive_values(self):
        text = (
            "Contact demo@example.com; "
            f"token {TEST_API_TOKEN}; "
            "UPI demo@ybl; "
            "GSTIN 27AAPFU0939F1ZV"
        )

        target = "demo@example.com"
        start = text.index(target)

        context = agent._sanitize_context(
            text,
            start,
            start + len(target),
        )

        sensitive_values = (
            ("email", "demo@example.com"),
            ("API token", TEST_API_TOKEN),
            ("UPI ID", "demo@ybl"),
            ("GSTIN", "27AAPFU0939F1ZV"),
        )

        for secret_type, value in sensitive_values:
            with self.subTest(secret_type=secret_type):
                self.assertNotIn(value, context)

        self.assertIn("[REDACTED]", context)


if __name__ == "__main__":
    unittest.main()
