
import json
import unittest
from unittest.mock import patch

import httpx

from kavach import agent


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.text = "Contact demo@example.com for help"
        self.findings = [{
            "type": "EMAIL",
            "start": 8,
            "end": 24,
            "confidence": 0.97,
        }]

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
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(result["status"], "ok")
        prompt = mock_post.call_args.kwargs["json"]["prompt"]
        self.assertNotIn("demo@example.com", prompt)
        self.assertIn("[REDACTED]", prompt)

    @patch("kavach.agent.httpx.post")
    def test_invalid_model_json_fails_safely(self, mock_post):
        mock_post.return_value.json.return_value = {
            "response": "not valid json"
        }
        mock_post.return_value.raise_for_status.return_value = None

        with patch.object(agent, "AGENT_ENABLED", True):
            result = agent.review_findings(self.text, self.findings)

        self.assertEqual(
            result,
            {"status": "unavailable", "reviews": []},
        )

    def test_disabled_agent_does_not_call_model(self):
        with patch.object(agent, "AGENT_ENABLED", False):
            with patch("kavach.agent.httpx.post") as mock_post:
                result = agent.review_findings(
                    self.text, self.findings
                )

        self.assertEqual(
            result,
            {"status": "disabled", "reviews": []},
        )
        mock_post.assert_not_called()
    def test_sanitizer_redacts_neighboring_sensitive_values(self):
        text = (
            "Contact demo@example.com; "
            "token sk-abcdefghijklmnopqrstuvwxyz1234567890; "
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

        for secret in (
            "demo@example.com",
            "sk-abcdefghijklmnopqrstuvwxyz1234567890",
            "demo@ybl",
            "27AAPFU0939F1ZV",
        ):
            with self.subTest(secret_type=secret):
                self.assertNotIn(secret, context)

        self.assertIn("[REDACTED]", context)

if __name__ == "__main__":
    unittest.main()
