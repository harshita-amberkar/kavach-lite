"""Bounded autonomous privacy workflow for KAVACH.

The optional local model selects approved tools. Python executes those
tools, while deterministic scanning, masking, and verification remain
authoritative. SQLite stores workflow metadata only.
"""

from kavach.agent import AGENT_ENABLED
from kavach.agent_runtime import run_autonomous_privacy_agent
from kavach.audit import record_run


def run_agentic_workflow(
    text: str,
    mode: str = "label",
    source: str = "api",
) -> dict:
    """Run the autonomous tool workflow and persist audit metadata."""

    result = run_autonomous_privacy_agent(
        text,
        mode=mode,
        enabled=AGENT_ENABLED,
    )

    findings = result.get("findings", [])
    risk_data = result.get("risk", {})
    review = result.get("agent_review", {"status": "unknown", "reviews": []})
    verification = result.get("verification", {})
    steps = result.get("steps", [])
    status = result.get("status", "needs_review")

    if not isinstance(findings, list):
        findings = []
    if not isinstance(risk_data, dict):
        risk_data = {}
    if not isinstance(review, dict):
        review = {"status": "unavailable", "reviews": []}
    if not isinstance(verification, dict):
        verification = {"status": "needs_review"}

    audit = {"status": "unavailable"}

    try:
        run_id = record_run(
            workflow_name="global_privacy_workflow",
            status=status,
            source=source,
            mode=mode,
            findings=findings,
            risk=risk_data,
            agent_review=review,
            verification_status=verification.get(
                "status", "needs_review"
            ),
            requires_human_review=bool(
                result.get("requires_human_review", True)
            ),
            steps=steps if isinstance(steps, list) else [],
        )
        audit = {"status": "saved", "run_id": run_id}
    except Exception as exc:
        audit = {
            "status": "unavailable",
            "reason": type(exc).__name__,
        }
        result["requires_human_review"] = True
        result["status"] = "needs_review"

    result["audit"] = audit
    return result
