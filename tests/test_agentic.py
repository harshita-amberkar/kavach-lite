import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as kavach_app


class AgenticEndpointTests(unittest.TestCase):
    def setUp(self):
        self.token = kavach_app.app.state.api_token
        self.headers = {"X-KAVACH-Token": self.token}
        self.prompt = "Contact demo@example.com for support."

    def _runtime_result(self):
        return {
            "workflow": "KAVACH Autonomous Privacy Workflow",
            "status": "completed",
            "agent_enabled": True,
            "findings": [{
                "type": "EMAIL",
                "start": 8,
                "end": 24,
                "confidence": 0.97,
            }],
            "masked_text": "Contact [EMAIL] for support.",
            "risk": {"score": 8, "level": "low"},
            "global_detection": {"status": "ok"},
            "agent_review": {"status": "ok", "reviews": []},
            "agent_execution": {
                "status": "completed",
                "tool_calls": ["scan_prompt", "verify_masked_output"],
                "fallback_used": False,
                "review_reason_codes": [],
            },
            "verification": {
                "status": "passed",
                "remaining_supported_findings": 0,
            },
            "requires_human_review": False,
            "steps": [{
                "name": "global_scan",
                "status": "completed",
                "findings_count": 1,
            }],
        }

    def test_agentic_scan_runs_runtime_and_returns_masked_result(self):
        with (
            patch(
                "kavach.agentic.run_autonomous_privacy_agent",
                return_value=self._runtime_result(),
            ) as runtime,
            patch(
                "kavach.agentic.record_run",
                return_value=321,
            ) as record_run,
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                headers=self.headers,
                json={"text": self.prompt, "mode": "label"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()

        self.assertEqual(
            data["masked_text"],
            "Contact [EMAIL] for support.",
        )
        self.assertEqual(data["verification"]["status"], "passed")
        self.assertEqual(data["audit"]["status"], "saved")
        self.assertEqual(data["audit"]["run_id"], 321)

        runtime.assert_called_once()
        self.assertEqual(runtime.call_args.args[0], self.prompt)
        record_run.assert_called_once()

        audit_arguments = record_run.call_args.kwargs
        self.assertNotIn("text", audit_arguments)
        self.assertNotIn("prompt", audit_arguments)
        self.assertEqual(
            audit_arguments["workflow_name"],
            "global_privacy_workflow",
        )

    def test_agentic_scan_rejects_missing_token(self):
        with TestClient(
            kavach_app.app,
            base_url="http://127.0.0.1",
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
            ) as client,
        ):
            response = client.get(
                "/api/agentic/history?limit=3",
                headers=self.headers,
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
