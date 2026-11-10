import copy
import unittest
from unittest.mock import call, patch

from fastapi.testclient import TestClient

import app as kavach_app


class ProtectModeEndpointTests(unittest.TestCase):
    def setUp(self):
        self.text = "Contact demo@example.com for support."
        self.core_result = {
            "findings": [{
                "type": "EMAIL",
                "start": 8,
                "end": 24,
                "confidence": 0.97,
            }],
            "masked_text": "Contact [EMAIL] for support.",
            "risk": {"score": 8, "level": "low"},
            "global_detection": {"status": "ok"},
            "performance": {"native_detection_ms": 1.0},
        }

    def _scan_both_modes(self, review_result, mode="label"):
        with (
            patch.object(kavach_app, "AGENT_ENABLED", False),
            patch.object(
                kavach_app,
                "analyze_global",
                side_effect=[copy.deepcopy(self.core_result), copy.deepcopy(self.core_result)],
            ) as analyze_global,
            patch.object(
                kavach_app,
                "review_findings",
                return_value=review_result,
            ) as review_findings,
            patch.object(kavach_app, "record_run", return_value=321),
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            standard_response = client.post(
                "/api/scan-global",
                json={"text": self.text, "mode": mode},
            )
            autonomous_response = client.post(
                "/api/agentic/scan",
                json={"text": self.text, "mode": mode},
            )

        self.assertEqual(standard_response.status_code, 200)
        self.assertEqual(autonomous_response.status_code, 200)
        analyze_global.assert_has_calls([
            call(self.text, mode),
            call(self.text, mode),
        ])
        review_findings.assert_called_once()
        return standard_response.json(), autonomous_response.json()

    def test_standard_and_autonomous_share_identical_core_result(self):
        standard, autonomous = self._scan_both_modes({
            "status": "ok",
            "reviews": [{
                "id": 0,
                "assessment": "likely",
                "reason": "The candidate is an email address.",
            }],
        })

        for key in ("findings", "masked_text", "risk", "global_detection"):
            with self.subTest(key=key):
                self.assertEqual(standard[key], autonomous[key])
        self.assertNotIn("agent_review", standard)
        self.assertEqual(autonomous["agent_review"]["status"], "ok")
        self.assertEqual(
            autonomous["agent_review"]["reviews"][0]["assessment"],
            "likely",
        )

    def test_autonomous_keeps_disabled_analyst_status(self):
        _, autonomous = self._scan_both_modes({
            "status": "disabled",
            "reviews": [],
        })

        self.assertEqual(autonomous["agent_review"]["status"], "disabled")
        self.assertEqual(autonomous["masked_text"], self.core_result["masked_text"])

    def test_autonomous_keeps_unavailable_analyst_status(self):
        _, autonomous = self._scan_both_modes({
            "status": "unavailable",
            "reason": "timeout",
            "reviews": [],
        })

        self.assertEqual(autonomous["agent_review"]["status"], "unavailable")
        self.assertEqual(autonomous["agent_review"]["reason"], "timeout")
        self.assertEqual(autonomous["findings"], self.core_result["findings"])
        self.assertEqual(autonomous["masked_text"], self.core_result["masked_text"])

    def test_both_masking_policies_use_the_same_core_result(self):
        for mode in ("label", "partial"):
            with self.subTest(mode=mode):
                standard, autonomous = self._scan_both_modes(
                    {"status": "disabled", "reviews": []},
                    mode=mode,
                )
                for key in ("findings", "masked_text", "risk", "global_detection"):
                    self.assertEqual(standard[key], autonomous[key])

    def test_analyst_exception_does_not_fail_autonomous_scan(self):
        with (
            patch.object(kavach_app, "AGENT_ENABLED", True),
            patch.object(kavach_app, "analyze_global", return_value=copy.deepcopy(self.core_result)),
            patch.object(kavach_app, "review_findings", side_effect=RuntimeError("private model error")),
            patch.object(kavach_app, "record_run", return_value=321),
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                json={"text": self.text, "mode": "label"},
            )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["agent_review"], {"status": "unavailable", "reviews": []})
        self.assertEqual(data["findings"], self.core_result["findings"])
        self.assertEqual(data["masked_text"], self.core_result["masked_text"])

    def test_analyst_cannot_mutate_detector_findings(self):
        def mutating_review(_text, findings):
            findings.clear()
            return {"status": "ok", "reviews": []}

        with (
            patch.object(kavach_app, "AGENT_ENABLED", False),
            patch.object(kavach_app, "analyze_global", return_value=copy.deepcopy(self.core_result)),
            patch.object(kavach_app, "review_findings", side_effect=mutating_review),
            patch.object(kavach_app, "record_run", return_value=321),
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                json={"text": self.text, "mode": "label"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["findings"], self.core_result["findings"])
        self.assertEqual(response.json()["masked_text"], self.core_result["masked_text"])

    def test_unavailable_detection_requires_human_review_in_response_and_audit(self):
        degraded_result = copy.deepcopy(self.core_result)
        degraded_result["global_detection"] = {"status": "unavailable"}
        with (
            patch.object(kavach_app, "analyze_global", return_value=degraded_result),
            patch.object(kavach_app, "review_findings", return_value={"status": "ok", "reviews": []}),
            patch.object(kavach_app, "record_run", return_value=321) as record_run,
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                json={"text": self.text, "mode": "label"},
            )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["global_detection"]["status"], "unavailable")
        self.assertEqual(data["steps"][0]["status"], "unavailable")
        self.assertEqual(data["verification"]["status"], "not_run")
        self.assertTrue(data["requires_human_review"])
        audit = record_run.call_args.kwargs
        self.assertEqual(audit["verification_status"], data["verification"]["status"])
        self.assertEqual(audit["requires_human_review"], data["requires_human_review"])
        self.assertEqual(audit["steps"][0]["status"], data["steps"][0]["status"])
        self.assertEqual(data["findings"], self.core_result["findings"])
        self.assertEqual(data["masked_text"], self.core_result["masked_text"])

    def test_successful_detection_preserves_results_and_records_unrun_verification(self):
        with (
            patch.object(kavach_app, "analyze_global", return_value=copy.deepcopy(self.core_result)),
            patch.object(kavach_app, "review_findings", return_value={"status": "ok", "reviews": []}),
            patch.object(kavach_app, "record_run", return_value=321) as record_run,
            TestClient(
                kavach_app.app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
            ) as client,
        ):
            response = client.post(
                "/api/agentic/scan",
                json={"text": self.text, "mode": "label"},
            )

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["findings"], self.core_result["findings"])
        self.assertEqual(data["masked_text"], self.core_result["masked_text"])
        self.assertEqual(data["risk"], self.core_result["risk"])
        self.assertEqual(data["steps"][0]["status"], "ok")
        self.assertEqual(data["verification"]["status"], "not_run")
        self.assertTrue(data["requires_human_review"])
        audit = record_run.call_args.kwargs
        self.assertEqual(audit["verification_status"], "not_run")
        self.assertTrue(audit["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
