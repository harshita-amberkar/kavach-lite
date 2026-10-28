"""Bounded tool execution for KAVACH's autonomous privacy agent.

The model selects approved actions using safe metadata only.
Python executes the tools. Deterministic detection and masking remain
authoritative; the model cannot access arbitrary files or run shell code.
"""

import json

import httpx

from kavach.agent import AGENT_ENABLED, AGENT_TIMEOUT, OLLAMA_MODEL, OLLAMA_URL
from kavach.global_detector import analyze_global


MAX_TOOL_CALLS = 6
MAX_REMASK_ROUNDS = 2

_REASON_CODES = {
    "agent_planner_error",
    "invalid_agent_action",
    "tool_execution_failed",
    "verification_unavailable",
    "verification_failed",
    "remediation_limit",
    "remediation_failed",
    "premature_completion",
    "step_limit",
}

_TOOL_DESCRIPTIONS = [
    {
        "name": "scan_prompt",
        "description": "Run the deterministic privacy scan and masking.",
        "arguments": {},
    },
    {
        "name": "verify_masked_output",
        "description": "Rescan the current masked output.",
        "arguments": {},
    },
    {
        "name": "remask_remaining_findings",
        "description": "Apply another deterministic masking pass when verification detects residual findings.",
        "arguments": {},
    },
    {
        "name": "request_human_review",
        "description": "Escalate the workflow using an approved reason code.",
        "arguments": {"reason_code": sorted(_REASON_CODES)},
    },
    {
        "name": "complete",
        "description": "Finish only after scanning and successful verification.",
        "arguments": {},
    },
]


class ToolExecutionError(ValueError):
    """Safe, non-sensitive tool execution error."""


def _finding_metadata(findings):
    """Return only finding types, offsets and confidence; never values."""
    output = []

    if not isinstance(findings, list):
        return output

    for item in findings[:200]:
        if not isinstance(item, dict):
            continue

        output.append({
            "type": str(item.get("type", "UNKNOWN"))[:40],
            "start": item.get("start")
                if isinstance(item.get("start"), int) else None,
            "end": item.get("end")
                if isinstance(item.get("end"), int) else None,
            "confidence": item.get("confidence")
                if isinstance(item.get("confidence"), (int, float)) else 0.0,
        })

    return output


class PrivacyToolRuntime:
    """Own the prompt in local memory and expose only safe tool observations."""

    def __init__(self, text, mode="label"):
        if not isinstance(text, str):
            raise ToolExecutionError("invalid_input")

        self._original_text = text
        self._mode = mode
        self._scan = None
        self._masked_text = None
        self._verification = None
        self._remask_rounds = 0
        self._review_reasons = []
        self.tool_calls = []
        self.steps = []
        self.last_observation = {"state": "not_started"}

    @property
    def verification_passed(self):
        if not isinstance(self._verification, dict):
            return False

        findings = self._verification.get("findings", [])
        detection = self._verification.get("global_detection", {})

        return (
            isinstance(findings, list)
            and len(findings) == 0
            and isinstance(detection, dict)
            and detection.get("status") == "ok"
        )

    @property
    def requires_human_review(self):
        initial_detection = (
            self._scan.get("global_detection", {})
            if isinstance(self._scan, dict) else {}
        )

        return (
            bool(self._review_reasons)
            or not self.verification_passed
            or not isinstance(initial_detection, dict)
            or initial_detection.get("status") != "ok"
        )

    def summary(self):
        """Safe planner context: no original or masked prompt text."""
        findings = (
            self._scan.get("findings", [])
            if isinstance(self._scan, dict) else []
        )
        risk_data = (
            self._scan.get("risk", {})
            if isinstance(self._scan, dict) else {}
        )
        initial_detection = (
            self._scan.get("global_detection", {})
            if isinstance(self._scan, dict) else {}
        )
        remaining = (
            self._verification.get("findings", [])
            if isinstance(self._verification, dict) else []
        )

        return {
            "scan_complete": self._scan is not None,
            "finding_count": len(findings) if isinstance(findings, list) else 0,
            "finding_types": sorted({
                str(item.get("type", "UNKNOWN"))[:40]
                for item in findings
                if isinstance(item, dict)
            }) if isinstance(findings, list) else [],
            "risk_level": (
                str(risk_data.get("level", "unknown"))[:32]
                if isinstance(risk_data, dict) else "unknown"
            ),
            "risk_score": (
                risk_data.get("score", 0)
                if isinstance(risk_data, dict)
                and isinstance(risk_data.get("score", 0), (int, float))
                else 0
            ),
            "global_detection_status": (
                initial_detection.get("status", "unknown")
                if isinstance(initial_detection, dict) else "unknown"
            ),
            "verification_status": (
                "passed" if self.verification_passed
                else "needs_review" if self._verification is not None
                else "pending"
            ),
            "remaining_findings_count": (
                len(remaining) if isinstance(remaining, list) else 0
            ),
            "remask_rounds": self._remask_rounds,
            "human_review_requested": bool(self._review_reasons),
            "review_reason_codes": list(self._review_reasons),
            "last_observation": self.last_observation,
        }

    def _record(self, name, status, observation):
        self.tool_calls.append(name)
        self.steps.append({
            "name": name,
            "status": status,
            "action": name,
            "findings_count": observation.get("finding_count", 0)
                if isinstance(observation, dict) else 0,
            "remaining_supported_findings": observation.get(
                "remaining_findings_count", 0
            ) if isinstance(observation, dict) else 0,
        })
        self.last_observation = {
            "tool": name,
            "status": status,
            "observation": observation,
        }

    def request_review(self, reason_code):
        if reason_code not in _REASON_CODES:
            reason_code = "invalid_agent_action"

        if reason_code not in self._review_reasons:
            self._review_reasons.append(reason_code)

        self._record(
            "request_human_review",
            "completed",
            {"human_review_requested": True, "reason_code": reason_code},
        )
        return {
            "human_review_requested": True,
            "reason_code": reason_code,
        }

    def execute(self, name, arguments):
        """Execute one allowlisted tool with strict argument validation."""
        if not isinstance(arguments, dict):
            raise ToolExecutionError("invalid_arguments")

        if name == "request_human_review":
            if set(arguments) != {"reason_code"}:
                raise ToolExecutionError("invalid_arguments")
            reason_code = arguments.get("reason_code")
            if not isinstance(reason_code, str) or reason_code not in _REASON_CODES:
                raise ToolExecutionError("invalid_arguments")
            return self.request_review(reason_code)

        if name not in {
            "scan_prompt",
            "verify_masked_output",
            "remask_remaining_findings",
        }:
            raise ToolExecutionError("tool_not_allowed")

        if arguments:
            raise ToolExecutionError("invalid_arguments")

        if name == "scan_prompt":
            if self._scan is not None:
                raise ToolExecutionError("scan_already_completed")

            result = analyze_global(self._original_text, self._mode)
            if not isinstance(result, dict):
                raise ToolExecutionError("invalid_scan_result")

            masked_text = result.get("masked_text")
            if not isinstance(masked_text, str):
                raise ToolExecutionError("invalid_masking_result")

            findings = _finding_metadata(result.get("findings", []))
            self._scan = {
                **result,
                "findings": findings,
            }
            self._masked_text = masked_text

            observation = {
                "scan_complete": True,
                "finding_count": len(findings),
                "finding_types": sorted({item["type"] for item in findings}),
                "masking_changed_text": masked_text != self._original_text,
                "risk_level": str(result.get("risk", {}).get("level", "unknown"))
                    if isinstance(result.get("risk"), dict) else "unknown",
                "global_detection_status": (
                    result.get("global_detection", {}).get("status", "unknown")
                    if isinstance(result.get("global_detection"), dict)
                    else "unknown"
                ),
            }

        elif name == "verify_masked_output":
            if self._scan is None or self._masked_text is None:
                raise ToolExecutionError("scan_required")

            result = analyze_global(self._masked_text, "label")
            if not isinstance(result, dict):
                raise ToolExecutionError("invalid_verification_result")

            self._verification = {
                **result,
                "findings": _finding_metadata(result.get("findings", [])),
            }

            remaining = self._verification["findings"]
            detection = result.get("global_detection", {})

            observation = {
                "verification_status": (
                    "passed" if self.verification_passed else "needs_review"
                ),
                "remaining_findings_count": len(remaining),
                "remaining_finding_types": sorted({
                    item["type"] for item in remaining
                }),
                "global_detection_status": (
                    detection.get("status", "unknown")
                    if isinstance(detection, dict) else "unknown"
                ),
            }

        else:  # remask_remaining_findings
            if self._verification is None:
                raise ToolExecutionError("verification_required")

            residual = self._verification.get("findings", [])
            if not residual:
                observation = {
                    "remasked": False,
                    "reason": "no_remaining_findings",
                    "remaining_findings_count": 0,
                }
            elif self._remask_rounds >= MAX_REMASK_ROUNDS:
                self.request_review("remediation_limit")
                observation = {
                    "remasked": False,
                    "reason": "remediation_limit",
                    "remaining_findings_count": len(residual),
                }
            else:
                candidate = self._verification.get("masked_text")
                if not isinstance(candidate, str) or candidate == self._masked_text:
                    self.request_review("remediation_failed")
                    observation = {
                        "remasked": False,
                        "reason": "no_masking_progress",
                        "remaining_findings_count": len(residual),
                    }
                else:
                    self._masked_text = candidate
                    self._verification = None
                    self._remask_rounds += 1
                    observation = {
                        "remasked": True,
                        "remask_round": self._remask_rounds,
                    }

        self._record(name, "completed", observation)
        return observation

    def result(self, agent_status, fallback_used):
        """Build the public workflow result without exposing raw values to the agent."""
        scan = self._scan if isinstance(self._scan, dict) else {}
        findings = _finding_metadata(scan.get("findings", []))
        risk_data = scan.get("risk", {})
        detection = scan.get("global_detection", {})

        risk_result = {
            "score": risk_data.get("score", 0),
            "level": str(risk_data.get("level", "unknown"))[:32],
        } if isinstance(risk_data, dict) else {"score": 0, "level": "unknown"}

        remaining = (
            self._verification.get("findings", [])
            if isinstance(self._verification, dict) else []
        )

        final_status = (
            "completed"
            if self.verification_passed and not self.requires_human_review
            else "needs_review"
        )

        steps = [
            {
                "name": "global_scan",
                "status": "completed" if self._scan is not None else "failed",
                "findings_count": len(findings),
            },
            {
                "name": "autonomous_agent",
                "status": agent_status,
                "action": "bounded_tool_execution",
                "reviews_count": 0,
            },
            {
                "name": "policy_masking",
                "status": "completed" if self._scan is not None else "failed",
                "action": "mask_detected_findings" if findings else "no_supported_findings",
            },
            {
                "name": "agent_tools",
                "status": "completed" if self.tool_calls else "not_run",
                "action": ",".join(self.tool_calls)[:64] or "none",
            },
            {
                "name": "verification",
                "status": "passed" if self.verification_passed else "needs_review",
                "remaining_supported_findings": len(remaining)
                    if isinstance(remaining, list) else 0,
            },
        ]

        if not isinstance(detection, dict):
            detection = {"status": "unavailable"}

        if self._scan is None:
            # Fail closed: never use the original prompt as a fallback output.
            masked_output = "[KAVACH_ERROR: masking_unavailable]"
            detection = {"status": "unavailable", "reason": "scan_failed"}
        else:
            masked_output = self._masked_text

        return {
            "workflow": "KAVACH Autonomous Privacy Workflow",
            "status": final_status,
            "agent_enabled": agent_status != "disabled",
            "findings": findings,
            "masked_text": masked_output,
            "risk": risk_result,
            "global_detection": detection,
            "agent_review": {"status": agent_status, "reviews": []},
            "agent_execution": {
                "status": "completed" if final_status == "completed" else "needs_review",
                "tool_calls": list(self.tool_calls),
                "fallback_used": bool(fallback_used),
                "review_reason_codes": list(self._review_reasons),
            },
            "verification": {
                "status": "passed" if self.verification_passed else "needs_review",
                "remaining_supported_findings": len(remaining)
                    if isinstance(remaining, list) else 0,
            },
            "requires_human_review": self.requires_human_review,
            "steps": steps,
        }


def _ask_model(runtime):
    """Ask Ollama for one JSON tool action using metadata only."""
    prompt = (
        "You control a bounded privacy workflow. Choose exactly one next action "
        "from the supplied allowlist. Return JSON only with keys tool and arguments. "
        "Do not invent tools or arguments. Do not ask for the original prompt; "
        "it is intentionally not provided. The Python runtime executes tools. "
        "Never claim verification passed unless the state says it passed. "
        "Allowed actions:\n"
        + json.dumps(_TOOL_DESCRIPTIONS, ensure_ascii=True)
        + "\nCurrent safe state:\n"
        + json.dumps(runtime.summary(), ensure_ascii=True)
        + '\nReturn e.g. {"tool":"verify_masked_output","arguments":{}}'
    )

    response = httpx.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=AGENT_TIMEOUT,
    )
    response.raise_for_status()

    envelope = response.json()
    if not isinstance(envelope, dict):
        raise ValueError("invalid_model_envelope")

    raw = envelope.get("response")
    if not isinstance(raw, str):
        raise ValueError("invalid_model_response")

    action = json.loads(raw)
    if not isinstance(action, dict):
        raise ValueError("invalid_action_json")

    return action


def _ensure_safe_completion(runtime):
    """Enforce scan, masking, and verification even if the planner fails."""
    if runtime._scan is None:
        try:
            runtime.execute("scan_prompt", {})
        except Exception:
            runtime.request_review("tool_execution_failed")
            return

    for _ in range(MAX_REMASK_ROUNDS + 1):
        if runtime._verification is None:
            try:
                runtime.execute("verify_masked_output", {})
            except Exception:
                runtime.request_review("verification_unavailable")
                return

        if runtime.verification_passed:
            return

        findings = runtime._verification.get("findings", [])
        if not findings:
            runtime.request_review("verification_failed")
            return

        if runtime._remask_rounds >= MAX_REMASK_ROUNDS:
            runtime.request_review("remediation_limit")
            return

        try:
            runtime.execute("remask_remaining_findings", {})
        except Exception:
            runtime.request_review("remediation_failed")
            return

    if not runtime.verification_passed:
        runtime.request_review("verification_failed")


def run_autonomous_privacy_agent(text, mode="label", enabled=None, planner=None):
    """Run a bounded model/tool loop, then enforce deterministic safety checks.

    `planner` is injectable for tests. Production uses the configured Ollama model.
    """
    use_agent = AGENT_ENABLED if enabled is None else bool(enabled)
    runtime = PrivacyToolRuntime(text, mode)
    agent_status = "ok" if use_agent else "disabled"
    fallback_used = not use_agent

    if use_agent:
        planner_failed = None

        for _ in range(MAX_TOOL_CALLS):
            try:
                action = planner(runtime) if planner is not None else _ask_model(runtime)

                if (
                    not isinstance(action, dict)
                    or set(action) != {"tool", "arguments"}
                    or not isinstance(action.get("tool"), str)
                    or not isinstance(action.get("arguments"), dict)
                ):
                    raise ToolExecutionError("invalid_agent_action")

                name = action["tool"]
                arguments = action["arguments"]

                if name == "complete":
                    if arguments or not runtime.verification_passed:
                        raise ToolExecutionError("premature_completion")
                    break

                runtime.execute(name, arguments)

            except Exception as exc:
                allowed_failures = {
                    "invalid_agent_action",
                    "premature_completion",
                    "tool_not_allowed",
                    "invalid_arguments",
                    "scan_already_completed",
                    "scan_required",
                    "verification_required",
                }
                planner_failed = (
                    str(exc) if str(exc) in allowed_failures
                    else "agent_planner_error"
                )
                break
        else:
            planner_failed = "step_limit"

        if planner_failed:
            runtime.request_review(planner_failed)
            agent_status = "unavailable"
            fallback_used = True

    _ensure_safe_completion(runtime)

    if use_agent and runtime._scan is not None and not planner_failed if use_agent else False:
        # A successful planner may still explicitly request human review.
        agent_status = "ok"

    return runtime.result(agent_status, fallback_used)
