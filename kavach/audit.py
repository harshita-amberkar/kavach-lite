"""Privacy-conscious SQLite audit storage for KAVACH workflows.

Stores workflow metadata only. Original prompts, masked prompt contents,
raw sensitive values, and free-form AI explanations are never persisted.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.getenv(
        "KAVACH_DB_PATH",
        str(PROJECT_ROOT / "results" / "kavach.db"),
    )
)


def _connect():
    """Open a SQLite connection with a bounded lock timeout."""
    connection = sqlite3.connect(str(DB_PATH), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


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
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


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