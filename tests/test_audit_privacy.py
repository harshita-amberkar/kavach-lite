import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kavach import audit


class AuditPrivacyTests(unittest.TestCase):
    def test_raw_prompt_values_and_ai_reasons_are_not_persisted(self):
        sensitive_markers = [
            "PRIVATE_PROMPT_SENTINEL",
            "PRIVATE_EMAIL_SENTINEL",
            "PRIVATE_AI_REASON_SENTINEL",
            "PRIVATE_STEP_TEXT_SENTINEL",
            "PRIVATE_PASSWORD_SENTINEL",
            "PRIVATE_TOKEN_SENTINEL",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "audit_test.db"

            with (
                patch.object(audit, "DB_PATH", db_path),
                patch.object(audit, "_schedule_cleanup"),
            ):
                run_id = audit.record_run(
                    workflow_name="privacy_test",
                    status="completed",
                    source="test",
                    mode="label",
                    findings=[
                        {
                            "type": "EMAIL",
                            "value": "PRIVATE_EMAIL_SENTINEL",
                            "text": "PRIVATE_PROMPT_SENTINEL",
                            "password": "PRIVATE_PASSWORD_SENTINEL",
                            "token": "PRIVATE_TOKEN_SENTINEL",
                        }
                    ],
                    risk={
                        "score": 8,
                        "level": "low",
                        "prompt": "PRIVATE_PROMPT_SENTINEL",
                    },
                    agent_review={
                        "status": "ok",
                        "reviews": [
                            {
                                "id": 0,
                                "assessment": "likely",
                                "reason": "PRIVATE_AI_REASON_SENTINEL",
                            }
                        ],
                    },
                    verification_status="passed",
                    requires_human_review=False,
                    steps=[
                        {
                            "name": "global_scan",
                            "status": "completed",
                            "findings_count": 1,
                            "prompt": "PRIVATE_STEP_TEXT_SENTINEL",
                        }
                    ],
                )

                self.assertGreater(run_id, 0)

                connection = audit._connect()
                try:
                    rows = connection.execute(
                        "SELECT * FROM workflow_runs"
                    ).fetchall()
                finally:
                    connection.close()

                recent_runs = audit.list_recent_runs(10)

                self.assertEqual(len(rows), 1)
                self.assertEqual(len(recent_runs), 1)

                stored_data = repr([dict(row) for row in rows])
                returned_data = repr(recent_runs)

                for marker in sensitive_markers:
                    with self.subTest(marker=marker):
                        self.assertNotIn(marker, stored_data)
                        self.assertNotIn(marker, returned_data)

                self.assertEqual(
                    recent_runs[0]["finding_types"],
                    ["EMAIL"],
                )
                self.assertEqual(
                    recent_runs[0]["steps"],
                    [{
                        "name": "global_scan",
                        "status": "completed",
                        "findings_count": 1,
                    }],
                )


if __name__ == "__main__":
    unittest.main()
