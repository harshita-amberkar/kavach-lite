import asyncio
import unittest
from unittest.mock import patch

import app as kavach_app


class StartupTokenPrivacyTests(unittest.TestCase):
    def test_generated_token_is_not_written_to_logs(self):
        test_token = "TEST-TOKEN-NEVER-LOG"

        with (
            patch.object(kavach_app, "_configured_api_token", ""),
            patch.object(kavach_app, "API_TOKEN", test_token),
            patch.object(
                kavach_app, "configured_upstream_hostname",
                return_value="api.openai.com",
            ),
            patch.object(
                kavach_app, "validate_upstream_url",
                return_value="https://api.openai.com/v1",
            ),
            patch.object(kavach_app, "preload_analyzer", return_value=2.5),
            patch.object(kavach_app.logger, "warning") as mock_warning,
            patch.object(kavach_app.logger, "info") as mock_info,
        ):
            asyncio.run(kavach_app.report_upstream_configuration())

        logged_text = repr(mock_warning.call_args_list)
        logged_text += repr(mock_info.call_args_list)

        self.assertNotIn(test_token, logged_text)
        self.assertTrue(mock_warning.called)

    def test_analyzer_preload_failure_does_not_abort_startup(self):
        with (
            patch.object(kavach_app, "preload_analyzer", side_effect=RuntimeError),
            patch.object(
                kavach_app, "configured_upstream_hostname",
                return_value="api.openai.com",
            ),
            patch.object(
                kavach_app, "validate_upstream_url",
                return_value="https://api.openai.com/v1",
            ),
            patch.object(kavach_app.logger, "warning") as mock_warning,
            patch.object(kavach_app.logger, "info"),
        ):
            asyncio.run(kavach_app.report_upstream_configuration())

        self.assertTrue(
            any("preload failed" in str(call) for call in mock_warning.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
