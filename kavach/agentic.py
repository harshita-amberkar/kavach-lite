"""Bounded agentic privacy workflow for KAVACH.

Workflow:
1. Scan with KAVACH and global recognizers.
2. Review findings with the optional local LLM.
3. Mask detected values under deterministic policy.
4. Rescan the masked output.
5. Persist permitted audit metadata in SQLite.

Original prompts and raw sensitive values are not passed to the
SQLite audit-storage function.
"""

from kavach.agent import AGENT_ENABLED, review_findings
from kavach.audit import record_run
from kavach.global_detector import analyze_global


def run_agentic_workflow(
    text: str,
    mode: str = "label",
    source: str = "api",
) -> dict:
    """Execute a scan-review-mask-verify-audit workflow."""

    # Step 1: Global scan.
    initial = analyze_global(text, mode)
    findings = initial.get("findings", [])
    risk_result = initial.get("risk", {})
    global_status = initial.get(
        "global_detection", {}
    ).get("status", "unknown")

    # Step 2: Optional local AI review.
    review = review_findings(text, findings)
    reviews = review.get("reviews", [])

    uncertain_review = any(
        item.get("assessment") in {"uncertain", "unlikely"}
        for item in reviews
        if isinstance(item, dict)
    )

    review_unavailable = (
        AGENT_ENABLED
        and review.get("status") not in {"ok", "no_findings"}
    )

    # Step 3: Apply the deterministic masking result.
    masked_text = initial.get("masked_text", text)

    # Step 4: Verify by rescanning the masked result.
    verification_scan = analyze_global(masked_text, "label")
    remaining_findings = verification_scan.get("findings", [])

    verification_passed = (
        len(remaining_findings) == 0
        and verification_scan.get("global_detection", {}).get("status")
        == "ok"
    )

    requires_human_review = (
        not verification_passed
        or global_status != "ok"
        or uncertain_review
        or review_unavailable
    )

    steps = [
        {
            "name": "global_scan",
            "status": "completed",
            "findings_count": len(findings),
        },
        {
            "name": "local_ai_review",
            "status": review.get("status", "unknown"),
            "reviews_count": len(reviews),
        },
        {
            "name": "policy_masking",
            "status": "completed",
            "action": (
                "mask_detected_findings"
                if findings
                else "no_supported_findings"
            ),
        },
        {
            "name": "verification",
            "status": (
                "passed" if verification_passed else "needs_review"
            ),
            "remaining_supported_findings": len(remaining_findings),
        },
    ]

    status = (
        "completed"
        if verification_passed and global_status == "ok"
        else "needs_review"
    )

    # Step 5: Persist metadata only—never the original prompt or
    # masked prompt contents.
    audit = {"status": "unavailable"}

    try:
        run_id = record_run(
            workflow_name="global_privacy_workflow",
            status=status,
            source=source,
            mode=mode,
            findings=findings,
            risk=risk_result,
            agent_review=review,
            verification_status=(
                "passed" if verification_passed else "needs_review"
            ),
            requires_human_review=requires_human_review,
            steps=steps,
        )
        audit = {
            "status": "saved",
            "run_id": run_id,
        }
    except Exception as exc:
        # Never return the raw prompt as a workaround for an audit error.
        # Preserve the masked result and clearly report degraded auditing.
        audit = {
            "status": "unavailable",
            "reason": type(exc).__name__,
        }
        requires_human_review = True
        status = "needs_review"

    return {
        "workflow": "KAVACH Global Privacy Workflow",
        "status": status,
        "agent_enabled": AGENT_ENABLED,
        "findings": findings,
        "masked_text": masked_text,
        "risk": risk_result,
        "global_detection": initial.get("global_detection", {}),
        "agent_review": review,
        "verification": {
            "status": (
                "passed" if verification_passed else "needs_review"
            ),
            "remaining_supported_findings": len(remaining_findings),
        },
        "audit": audit,
        "requires_human_review": requires_human_review,
        "steps": steps,
    }