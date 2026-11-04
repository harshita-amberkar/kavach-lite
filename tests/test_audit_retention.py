import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from kavach import audit


class AuditRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "retention_test.db"
        with patch.object(audit, "DB_PATH", self.db_path):
            audit.init_db()
        self.now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)

    def _insert_row(self, created_at):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                """
                INSERT INTO workflow_runs (
                    created_at, workflow_name, status, source, mode,
                    finding_count, finding_types_json, risk_score, risk_level,
                    agent_status, agent_review_count, verification_status,
                    requires_human_review, steps_json
                ) VALUES (?, 'test_workflow', 'completed', 'test', 'label',
                          0, '[]', 0, 'low', 'disabled', 0, 'passed', 0, '[]')
                """,
                (created_at.isoformat(),),
            )
            connection.commit()
            return int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
        finally:
            connection.close()

    def test_cleanup_deletes_only_expired_workflow_rows(self):
        expired_id = self._insert_row(self.now - timedelta(days=31))
        retained_id = self._insert_row(self.now - timedelta(days=29))
        self._insert_row(self.now + timedelta(days=1))

        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
            connection.execute("INSERT INTO unrelated VALUES ('keep')")
            connection.commit()
        finally:
            connection.close()

        deleted = audit.cleanup_expired_runs(
            db_path=self.db_path,
            retention_days=30,
            now=self.now,
        )

        self.assertEqual(deleted, 1)
        connection = sqlite3.connect(self.db_path)
        try:
            remaining_ids = {
                row[0] for row in connection.execute("SELECT id FROM workflow_runs")
            }
            self.assertNotIn(expired_id, remaining_ids)
            self.assertIn(retained_id, remaining_ids)
            self.assertEqual(connection.execute("SELECT value FROM unrelated").fetchone()[0], "keep")
            self.assertIsNotNone(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_runs'"
                ).fetchone()
            )
        finally:
            connection.close()

    def test_zero_retention_disables_cleanup(self):
        row_id = self._insert_row(self.now - timedelta(days=400))
        deleted = audit.cleanup_expired_runs(
            db_path=self.db_path,
            retention_days=0,
            now=self.now,
        )
        self.assertEqual(deleted, 0)
        connection = sqlite3.connect(self.db_path)
        try:
            self.assertIsNotNone(
                connection.execute("SELECT 1 FROM workflow_runs WHERE id=?", (row_id,)).fetchone()
            )
        finally:
            connection.close()

    def test_cleanup_defers_safely_when_database_is_locked(self):
        row_id = self._insert_row(self.now - timedelta(days=31))
        lock_connection = sqlite3.connect(self.db_path, timeout=1)
        lock_connection.execute("BEGIN EXCLUSIVE")
        try:
            with patch.object(audit, "AUDIT_RETENTION_DAYS", 30):
                audit._cleanup_worker(self.db_path, 30)
        finally:
            lock_connection.rollback()
            lock_connection.close()

        connection = sqlite3.connect(self.db_path)
        try:
            self.assertIsNotNone(
                connection.execute("SELECT 1 FROM workflow_runs WHERE id=?", (row_id,)).fetchone()
            )
        finally:
            connection.close()

    def test_cleanup_errors_are_swallowed_by_background_worker(self):
        with patch.object(
            audit,
            "cleanup_expired_runs",
            side_effect=sqlite3.OperationalError("database is locked"),
        ):
            audit._cleanup_worker(self.db_path, 30)

    def test_nonexistent_database_is_not_created_by_cleanup(self):
        missing_path = Path(self.temp.name) / "absent.db"
        self.assertEqual(
            audit.cleanup_expired_runs(db_path=missing_path, retention_days=30),
            0,
        )
        self.assertFalse(missing_path.exists())

    def test_retention_default_is_thirty_days(self):
        self.assertEqual(audit.DEFAULT_RETENTION_DAYS, 30)


if __name__ == "__main__":
    unittest.main()
