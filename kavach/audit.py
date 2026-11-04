"""Privacy-conscious SQLite audit storage for KAVACH workflows.

Stores workflow metadata only. Original prompts, masked prompt contents,
raw sensitive values, and free-form AI explanations are never persisted.
"""

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.getenv(
        "KAVACH_DB_PATH",
        str(PROJECT_ROOT / "results" / "kavach.db"),
    )
)

logger = logging.getLogger(__name__)
DEFAULT_RETENTION_DAYS = 30
_retention_setting = os.getenv("KAVACH_AUDIT_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)).strip()
try:
    AUDIT_RETENTION_DAYS = int(_retention_setting)
    if not 0 <= AUDIT_RETENTION_DAYS <= 36500:
        raise ValueError
except ValueError:
    logger.warning(
        "Invalid KAVACH_AUDIT_RETENTION_DAYS configuration; using the default."
    )
    AUDIT_RETENTION_DAYS = DEFAULT_RETENTION_DAYS

_CLEANUP_INTERVAL_SECONDS = 60 * 60
_CLEANUP_LOCK = threading.Lock()
_LAST_CLEANUP_SCHEDULED: float | None = None


def _connect(db_path: Path | None = None, timeout: float = 5):
    """Open a SQLite connection with a bounded lock timeout."""
    connection = sqlite3.connect(str(db_path or DB_PATH), timeout=timeout)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def database_status() -> str:
    """Check an existing audit database without creating or changing it."""
    if not DB_PATH.is_file():
        return "unavailable"
    try:
        connection = _connect(timeout=0.25)
        try:
            connection.execute("SELECT 1").fetchone()
        finally:
            connection.close()
        return "available"
    except Exception:
        return "unavailable"


def cleanup_expired_runs(
    *,
    db_path: Path | None = None,
    retention_days: int | None = None,
    now: datetime | None = None,
    lock_timeout: float = 5,
) -> int:
    """Delete only expired audit rows, in one immediate transaction.

    A zero retention setting disables cleanup. Missing databases/tables are
    left untouched; this function never initializes or resets the schema.
    """
    selected_path = Path(db_path or DB_PATH)
    days = AUDIT_RETENTION_DAYS if retention_days is None else int(retention_days)
    if days == 0 or not selected_path.is_file():
        return 0
    if days < 0:
        raise ValueError("retention_days must be zero or greater")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = (current_time.astimezone(timezone.utc) - timedelta(days=days)).isoformat()

    connection = _connect(selected_path, timeout=lock_timeout)
    try:
        connection.execute("BEGIN IMMEDIATE")
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("workflow_runs",),
        ).fetchone()
        if not table_exists:
            connection.rollback()
            return 0

        cursor = connection.execute(
            "DELETE FROM workflow_runs WHERE julianday(created_at) < julianday(?)",
            (cutoff,),
        )
        deleted_count = cursor.rowcount
        connection.commit()
        return deleted_count
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _cleanup_worker(db_path: Path, retention_days: int) -> None:
    """Perform best-effort cleanup without exposing database details."""
    try:
        cleanup_expired_runs(
            db_path=db_path,
            retention_days=retention_days,
            lock_timeout=0.25,
        )
    except sqlite3.OperationalError:
        logger.info("Audit retention cleanup deferred due to SQLite contention.")
    except Exception as exc:
        logger.warning("Audit retention cleanup failed (%s).", type(exc).__name__)


def _schedule_cleanup() -> None:
    """Throttle cleanup and run it asynchronously after audit writes."""
    global _LAST_CLEANUP_SCHEDULED
    if AUDIT_RETENTION_DAYS == 0:
        return

    now = time.monotonic()
    with _CLEANUP_LOCK:
        if (
            _LAST_CLEANUP_SCHEDULED is not None
            and now - _LAST_CLEANUP_SCHEDULED < _CLEANUP_INTERVAL_SECONDS
        ):
            return
        _LAST_CLEANUP_SCHEDULED = now

    try:
        cleanup_thread = threading.Thread(
            target=_cleanup_worker,
            args=(Path(DB_PATH), AUDIT_RETENTION_DAYS),
            name="kavach-audit-retention",
            daemon=True,
        )
        cleanup_thread.start()
    except Exception as exc:
        logger.warning("Could not schedule audit retention cleanup (%s).", type(exc).__name__)


def init_db() -> None:
    """Create the audit table if it does not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = _connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                mode TEXT NOT NULL,
                finding_count INTEGER NOT NULL,
                finding_types_json TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                agent_status TEXT NOT NULL,
                agent_review_count INTEGER NOT NULL,
                verification_status TEXT NOT NULL,
                requires_human_review INTEGER NOT NULL,
                steps_json TEXT NOT NULL
            )
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _safe_steps(steps: list[dict] | None) -> list[dict]:
    """Keep only workflow step metadata; exclude arbitrary text fields."""
    safe = []

    for step in (steps or [])[:20]:
        if not isinstance(step, dict):
            continue

        item = {
            "name": str(step.get("name", "unknown"))[:64],
            "status": str(step.get("status", "unknown"))[:32],
        }

        action = step.get("action")
        if isinstance(action, str):
            item["action"] = action[:64]

        for key in ("findings_count", "reviews_count",
                    "remaining_supported_findings"):
            value = step.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                item[key] = max(0, value)

        safe.append(item)

    return safe


def record_run(
    *,
    workflow_name: str,
    status: str,
    source: str,
    mode: str,
    findings: list[dict],
    risk: dict,
    agent_review: dict | None = None,
    verification_status: str = "not_run",
    requires_human_review: bool = False,
    steps: list[dict] | None = None,
) -> int:
    """Persist a workflow result without storing prompt content."""
    init_db()

    finding_types = [
        str(item.get("type", "UNKNOWN"))[:64]
        for item in findings[:200]
        if isinstance(item, dict)
    ]

    review = agent_review or {}
    reviews = review.get("reviews", [])

    risk_score = risk.get("score", 0)
    if not isinstance(risk_score, (int, float)):
        risk_score = 0

    created_at = datetime.now(timezone.utc).isoformat()

    values = (
        created_at,
        str(workflow_name)[:100],
        str(status)[:32],
        str(source)[:64],
        str(mode)[:32],
        len(findings),
        json.dumps(finding_types),
        int(risk_score),
        str(risk.get("level", "unknown"))[:32],
        str(review.get("status", "disabled"))[:32],
        len(reviews) if isinstance(reviews, list) else 0,
        str(verification_status)[:32],
        int(bool(requires_human_review)),
        json.dumps(_safe_steps(steps)),
    )

    connection = _connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO workflow_runs (
                created_at, workflow_name, status, source, mode,
                finding_count, finding_types_json, risk_score, risk_level,
                agent_status, agent_review_count, verification_status,
                requires_human_review, steps_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        connection.commit()
        run_id = int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    _schedule_cleanup()
    return run_id


def list_recent_runs(limit: int = 20) -> list[dict]:
    """Return recent workflow metadata, newest first."""
    init_db()

    limit = max(1, min(int(limit), 100))
    connection = _connect()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM workflow_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    output = []

    for row in rows:
        item = dict(row)
        item["finding_types"] = json.loads(
            item.pop("finding_types_json")
        )
        item["steps"] = json.loads(item.pop("steps_json"))
        item["requires_human_review"] = bool(
            item["requires_human_review"]
        )
        output.append(item)

    return output
