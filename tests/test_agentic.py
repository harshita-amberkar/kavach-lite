import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as kavach_app


class AgenticEndpointTests(unittest.TestCase):
    def setUp(self):
        self.prompt = "Contact demo@example.com for support."

    def _core_result(self):
        return {
            "findings": [{
                "type": "EMAIL",
                "start": 8,
                "end": 24,
                "confidence": 0.97,
            }],
            "masked_text": "Contact [EMAIL] for support.",
            "risk": {"score": 8, "level": "low"},
            "global_detection": {"status": "ok"},
            "performance": {"native_detection_ms": 1.2},
        }

    def test_agentic_scan_returns_shared_core_and_real_analyst_review(self):
        review = {
            "status": "ok",
            "reviews": [{
                "id": 0,
                "assessment": "likely",
                "reason": "The detector candidate is an email address.",
            }],
        }
        with (
            patch(
                "app.analyze_global",
                return_value=self._core_result(),
            ) as analyze_global,
            patch("app.AGENT_ENABLED", True),
            patch("app.review_findings", return_value=review) as review_findings,
            patch(
                "app.record_run",
                return_value=321,
            ) as record_run,
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                json={"text": self.prompt, "mode": "label"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()

        self.assertEqual(
            data["masked_text"],
            "Contact [EMAIL] for support.",
        )
        self.assertEqual(data["agent_review"], review)
        self.assertEqual(data["verification"]["status"], "not_run")
        self.assertEqual(data["agent_execution"]["tool_calls"], [])
        self.assertEqual(data["audit"]["status"], "saved")
        self.assertEqual(data["audit"]["run_id"], 321)
        performance = data["performance"]
        self.assertGreaterEqual(performance["total_backend_processing_ms"], 0)
        self.assertGreaterEqual(performance["audit_write_ms"], 0)
        self.assertGreaterEqual(performance["ollama_review_ms"], 0)

        analyze_global.assert_called_once_with(self.prompt, "label")
        review_findings.assert_called_once()
        record_run.assert_called_once()

        audit_arguments = record_run.call_args.kwargs
        self.assertNotIn("text", audit_arguments)
        self.assertNotIn("prompt", audit_arguments)
        self.assertEqual(
            audit_arguments["workflow_name"],
            "global_privacy_workflow",
        )

    def test_agentic_scan_requires_token_in_explicit_token_mode(self):
        with patch.object(kavach_app.app.state, "owner_access_mode", "token"):
            with TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client:
                response = client.post(
                    "/api/agentic/scan",
                    json={"text": self.prompt, "mode": "label"},
                )

        self.assertEqual(response.status_code, 401)

    def test_agentic_history_returns_metadata(self):
        fake_history = [{
            "id": 123,
            "workflow_name": "global_privacy_workflow",
            "status": "completed",
            "agent_status": "ok",
            "agent_review_count": 1,
            "verification_status": "passed",
            "requires_human_review": False,
        }]

        with (
            patch(
                "app.list_recent_runs",
                return_value=fake_history,
            ) as list_runs,
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.get(
                "/api/agentic/history?limit=3",
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()

        self.assertEqual(data["runs"], fake_history)
        list_runs.assert_called_once_with(3)

        serialized = response.text
        self.assertNotIn("demo@example.com", serialized)
        self.assertNotIn("raw_prompt", serialized)


if __name__ == "__main__":
    unittest.main()
