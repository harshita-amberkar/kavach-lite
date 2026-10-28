import json
import unittest
from unittest.mock import patch

from kavach.agent_runtime import run_autonomous_privacy_agent


def scan_result(findings, masked_text, status="ok"):
    return {
        "findings": findings,
        "masked_text": masked_text,
        "risk": {"score": 8, "level": "low"},
        "global_detection": {"status": status, "engine": "test"},
    }


class AutonomousAgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.prompt = "Contact demo@example.com for support."
        self.finding = {
            "type": "EMAIL",
            "start": 8,
            "end": 24,
            "confidence": 0.97,
        }

    def test_agent_selects_and_executes_tools_without_prompt_context(self):
        actions = iter([
            {"tool": "scan_prompt", "arguments": {}},
            {"tool": "verify_masked_output", "arguments": {}},
            {"tool": "complete", "arguments": {}},
        ])

        def planner(runtime):
            safe_context = json.dumps(runtime.summary())
            self.assertNotIn(self.prompt, safe_context)
            self.assertNotIn("demo@example.com", safe_context)
            return next(actions)

        with patch(
            "kavach.agent_runtime.analyze_global",
            side_effect=[
                scan_result([self.finding], "Contact [EMAIL] for support."),
                scan_result([], "Contact [EMAIL] for support."),
            ],
        ):
            result = run_autonomous_privacy_agent(
                self.prompt, enabled=True, planner=planner
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["masked_text"], "Contact [EMAIL] for support.")
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertEqual(result["agent_review"]["status"], "ok")
        self.assertEqual(
            result["agent_execution"]["tool_calls"],
            ["scan_prompt", "verify_masked_output"],
        )
        self.assertFalse(result["requires_human_review"])

    def test_disabled_agent_uses_deterministic_safe_path(self):
        with patch("kavach.agent_runtime.analyze_global", side_effect=[
            scan_result([self.finding], "Contact [EMAIL] for support."),
            scan_result([], "Contact [EMAIL] for support."),
        ]):
            result = run_autonomous_privacy_agent(
                self.prompt,
                enabled=False,
                planner=lambda runtime: self.fail("Planner must not be called"),
            )

        self.assertEqual(result["agent_review"]["status"], "disabled")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["masked_text"], "Contact [EMAIL] for support.")
        self.assertEqual(result["verification"]["status"], "passed")

    def test_invalid_tool_arguments_fail_safe_and_request_review(self):
        actions = iter([
            {
                "tool": "scan_prompt",
                "arguments": {"text": self.prompt},
            },
        ])

        with patch("kavach.agent_runtime.analyze_global", side_effect=[
            scan_result([self.finding], "Contact [EMAIL] for support."),
            scan_result([], "Contact [EMAIL] for support."),
        ]):
            result = run_autonomous_privacy_agent(
                self.prompt,
                enabled=True,
                planner=lambda runtime: next(actions),
            )

        self.assertEqual(result["agent_review"]["status"], "unavailable")
        self.assertEqual(result["masked_text"], "Contact [EMAIL] for support.")
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertTrue(result["requires_human_review"])
        self.assertTrue(result["agent_execution"]["fallback_used"])

    def test_planner_failure_still_runs_scan_and_verification(self):
        def broken_planner(runtime):
            raise RuntimeError("synthetic planner failure")

        with patch("kavach.agent_runtime.analyze_global", side_effect=[
            scan_result([self.finding], "Contact [EMAIL] for support."),
            scan_result([], "Contact [EMAIL] for support."),
        ]):
            result = run_autonomous_privacy_agent(
                self.prompt, enabled=True, planner=broken_planner
            )

        self.assertEqual(result["agent_review"]["status"], "unavailable")
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertEqual(result["masked_text"], "Contact [EMAIL] for support.")
        self.assertTrue(result["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
