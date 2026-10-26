// --------------------------------------------------
// KAVACH local API authentication
// --------------------------------------------------

const KAVACH_TOKEN_KEY = "kavachApiToken";

function getKavachApiToken() {
  let token = sessionStorage.getItem(KAVACH_TOKEN_KEY);

  if (!token) {
    token = window.prompt(
      "Enter the KAVACH_API_TOKEN value configured for the server:"
    );

    if (!token || !token.trim()) {
      throw new Error("KAVACH API token is required.");
    }

    token = token.trim();
    sessionStorage.setItem(KAVACH_TOKEN_KEY, token);
  }

  return token;
}

async function apiFetch(url, options = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = new Headers(options.headers || {});
    headers.set("X-KAVACH-Token", getKavachApiToken());

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (response.status !== 401 || attempt === 1) {
      return response;
    }

    // A local server restart can rotate a generated session token.
    sessionStorage.removeItem(KAVACH_TOKEN_KEY);
  }
}

const SAMPLES = [
  "Customer Demo User (demo.user@example.com, +91 90000 00000) says refund of Rs 4,500 failed. Please reply. Pay them on demo@okaxis. IFSC HDFC0001234.",
  "Bhai mera PAN ABCPE1234F hai aur आधार नंबर २३४५ ६७८९ ०१२३ hai, loan form bhar do.",
  "const client = new S3({accessKeyId: '<AWS_ACCESS_KEY_ID_PLACEHOLDER>'});\nconst api_key = 'DEMO_API_KEY_PLACEHOLDER';\nconst password = 'DEMO_PASSWORD_PLACEHOLDER';\n// why does upload fail?"
];

const $ = id => document.getElementById(id);

let timer;
let latestMaskedText = "";
let latestFilename = "masked-document.txt";

// ------------------------------------------------------------
// Prompt scanner
// ------------------------------------------------------------

function showPromptPlaceholder() {
  $("out").textContent = "The masked version appears here.";
  $("out").className = "out empty";
}

function renderMaskedPrompt(text) {
  $("out").replaceChildren();
  $("out").className = "out";

  const pattern = /\[([A-Z_]+)\]/g;
  let last = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    $("out").appendChild(
      document.createTextNode(text.slice(last, match.index))
    );

    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = match[0];

    $("out").appendChild(chip);
    last = pattern.lastIndex;
  }

  $("out").appendChild(
    document.createTextNode(text.slice(last))
  );
}

function renderPromptRows(findings) {
  const rows = $("rows");
  rows.replaceChildren();

  if (!findings.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");

    td.colSpan = 3;
    td.className = "empty";
    td.textContent =
      "Nothing detected. No supported sensitive patterns were found.";

    tr.appendChild(td);
    rows.appendChild(tr);
    return;
  }

  findings.forEach(f => {
    const tr = document.createElement("tr");

    [
      f.type,
      `${f.start}-${f.end}`,
      `${Math.round((f.confidence || 0) * 100)}%`
    ].forEach(value => {
      const td = document.createElement("td");
      td.textContent = String(value);
      tr.appendChild(td);
    });

    rows.appendChild(tr);
  });
}

async function run() {
  const text = $("inp").value;

  if (!text.trim()) {
    showPromptPlaceholder();

    $("level").className = "level none";
    $("level").textContent = "No risk found";
    $("score").textContent = "Enter text to begin scanning.";

    renderPromptRows([]);
    return;
  }

  try {
    const response = await apiFetch("/api/scan-global", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      throw new Error("Scan request failed.");
    }

    const data = await response.json();

    renderMaskedPrompt(data.masked_text || "");

    const level = data.risk?.level || "none";

    $("level").className = "level " + level;
    $("level").textContent = level === "none"
      ? "No risk found"
      : level.charAt(0).toUpperCase() + level.slice(1) + " risk";

    const findings = data.findings || [];

    $("score").textContent =
      `${findings.length} item(s) detected`;

    renderPromptRows(findings);

  } catch {
    $("out").textContent =
      "Could not reach the Kavach server. Check that it is running and try again.";

    $("out").className = "out empty";
    $("level").className = "level high";
    $("level").textContent = "Scan unavailable";
    $("score").textContent =
      "Check that the Kavach server is running.";
  }
}

$("inp").addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(run, 250);
});

document.querySelectorAll("[data-s]").forEach(button => {
  button.addEventListener("click", () => {
    $("inp").value = SAMPLES[Number(button.dataset.s)];
    run();
  });
});

$("clear").addEventListener("click", () => {
  $("inp").value = "";
  run();
});

// ------------------------------------------------------------
// Document scanner
// ------------------------------------------------------------

$("file-form").addEventListener("submit", async event => {
  event.preventDefault();

  const file = $("file-input").files[0];

  if (!file) {
    $("file-status").textContent =
      "Please choose a file first.";
    return;
  }

  const extension = file.name.split(".").pop().toLowerCase();

  if (!["txt", "pdf"].includes(extension)) {
    $("file-status").textContent =
      "Only TXT and PDF files are supported.";
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    $("file-status").textContent =
      "The file exceeds the 5 MB limit.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const button = $("scan-file-button");

  button.disabled = true;
  button.textContent = "Scanning…";

  $("file-status").textContent =
    "Scanning your document...";

  $("file-results").hidden = true;

  try {
    const response = await apiFetch("/api/scan-file", {
      method: "POST",
      body: formData
    });

    let data;

    try {
      data = await response.json();
    } catch {
      throw new Error(
        "The server returned an unexpected response."
      );
    }

    if (!response.ok) {
      throw new Error(
        data.detail || "Document scanning failed."
      );
    }

    $("file-name").textContent =
      data.filename || file.name;

    $("file-pages").textContent =
      data.page_count == null
        ? "Not applicable (TXT file)"
        : String(data.page_count);

    $("file-count").textContent =
      String(data.count ?? (data.findings || []).length);

    const risk = data.risk || {};

    $("file-risk").textContent =
      `${risk.level || "unknown"} (score: ${risk.score ?? "N/A"})`;

    const findingsBox = $("file-findings");
    findingsBox.replaceChildren();

    const findings = data.findings || [];

    if (!findings.length) {
      findingsBox.textContent =
        "No supported sensitive patterns were detected.";
    } else {
      findings.forEach(finding => {
        const item = document.createElement("p");

        const confidence =
          typeof finding.confidence === "number"
            ? ` · Confidence: ${Math.round(finding.confidence * 100)}%`
            : "";

        item.textContent =
          `${finding.type || "Finding"} · Positions ` +
          `${finding.start ?? "?"}-${finding.end ?? "?"}${confidence}`;

        findingsBox.appendChild(item);
      });
    }

    latestMaskedText = data.masked_text || "";

    latestFilename =
      (data.filename || file.name).replace(/\.[^.]+$/, "") +
      "-masked.txt";

    $("file-masked").textContent = latestMaskedText;
    $("file-results").hidden = false;

    $("file-status").textContent =
      "Document scan completed successfully.";

  } catch (error) {
    $("file-status").textContent =
      error.message ||
      "Could not scan the document. Please try again.";

  } finally {
    button.disabled = false;
    button.textContent = "Scan document";
  }
});

$("download-masked").addEventListener("click", () => {
  const blob = new Blob(
    [latestMaskedText],
    { type: "text/plain;charset=utf-8" }
  );

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = latestFilename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

// ------------------------------------------------------------
// Agentic workflow history
// ------------------------------------------------------------

function formatHistoryDate(value) {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Unknown time"
    : date.toLocaleString();
}

async function loadAgenticHistory() {
  const list = $("history-list");
  const status = $("history-status");
  const button = $("refresh-history");

  if (!list || !status) {
    return;
  }

  if (button) {
    button.disabled = true;
  }

  status.textContent = "Loading workflow history...";
  list.replaceChildren();

  try {
    const response = await apiFetch(
      "/api/agentic/history?limit=10",
      {
        headers: {
          Accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      throw new Error("History request failed.");
    }

    const data = await response.json();
    const runs = Array.isArray(data.runs) ? data.runs : [];

    if (!runs.length) {
      status.textContent = "No workflow history found yet.";
      return;
    }

    status.textContent =
      `Showing ${runs.length} recent workflow run(s).`;

    runs.forEach(run => {
      const card = document.createElement("article");
      card.className = "workflow-history-card";

      const heading = document.createElement("h3");

      heading.textContent =
        `Run #${run.id ?? "—"} · ` +
        `${run.workflow_name ?? "Privacy workflow"}`;

      card.appendChild(heading);

      const fields = [
        ["Created", formatHistoryDate(run.created_at)],
        ["Status", run.status ?? "Unknown"],
        [
          "Risk",
          `${run.risk_level ?? "Unknown"} (${run.risk_score ?? "N/A"})`
        ],
        [
          "Findings",
          Array.isArray(run.finding_types) &&
          run.finding_types.length
            ? run.finding_types.join(", ")
            : "None recorded"
        ],
        [
          "Agent review",
          `${run.agent_status ?? "Unknown"} ` +
          `(${run.agent_review_count ?? 0} review(s))`
        ],
        [
          "Verification",
          run.verification_status ?? "Unknown"
        ],
        [
          "Human review",
          run.requires_human_review
            ? "Required"
            : "Not flagged"
        ],
        [
          "Workflow steps",
          Array.isArray(run.steps)
            ? run.steps.map(
                step => `${step.name}: ${step.status}`
              ).join(" · ")
            : "Unavailable"
        ]
      ];

      fields.forEach(([label, value]) => {
        const row = document.createElement("p");
        const strong = document.createElement("strong");

        strong.textContent = `${label}: `;

        row.appendChild(strong);
        row.appendChild(
          document.createTextNode(String(value))
        );

        card.appendChild(row);
      });

      list.appendChild(card);
    });

  } catch {
    status.textContent =
      "Could not load workflow history. " +
      "Check that KAVACH is running and try again.";

  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

$("refresh-history")?.addEventListener(
  "click",
  loadAgenticHistory
);

// Load history when the dashboard opens.
loadAgenticHistory();

// ------------------------------------------------------------
// Agentic privacy workflow runner — user-friendly results
// ------------------------------------------------------------

function friendlyStatus(value, fallback = "Not reported") {
  if (typeof value === "string" && value.trim()) {
    return value.trim().toLowerCase();
  }
  if (value && typeof value === "object") {
    if (typeof value.status === "string" && value.status.trim()) {
      return value.status.trim().toLowerCase();
    }
    if (typeof value.verification_status === "string") {
      return value.verification_status.trim().toLowerCase();
    }
    if (typeof value.passed === "boolean") {
      return value.passed ? "passed" : "not passed";
    }
    if (typeof value.verified === "boolean") {
      return value.verified ? "passed" : "not passed";
    }
  }
  return fallback;
}

function humanizeWorkflowStep(name) {
  const labels = {
    global_scan: "Sensitive information scan",
    local_ai_review: "AI-assisted review",
    policy_masking: "Mask sensitive information",
    masking: "Mask sensitive information",
    verification: "Check the protected prompt",
    audit: "Save workflow record"
  };
  const key = String(name || "").toLowerCase().replace(/[ -]+/g, "_");
  return labels[key] || key.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase()) || "Workflow step";
}

function statusKind(value) {
  const normalized = String(value || "").toLowerCase();
  if (["passed", "completed", "complete", "ok", "success", "succeeded", "verified", "saved", "recorded", "inserted"].includes(normalized)) return "success";
  if (["failed", "error", "blocked", "unavailable", "not passed"].includes(normalized)) return "warning";
  return "neutral";
}

function displayStatusLabel(value) {
  const normalized = String(value || "not reported").trim().toLowerCase();
  const labels = {
    ok: "Completed",
    success: "Completed",
    succeeded: "Completed",
    completed: "Completed",
    complete: "Completed",
    passed: "Passed",
    verified: "Verified",
    disabled: "Turned off",
    unavailable: "Unavailable",
    error: "Unavailable",
    failed: "Needs attention",
    blocked: "Blocked",
    "not passed": "Needs attention",
    "not reported": "Not reported",
    skipped: "Skipped",
    saved: "Saved",
    recorded: "Saved",
    inserted: "Saved",
    "not required": "Not required"
  };
  return labels[normalized] || normalized.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase());
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = String(text);
  return element;
}

function getAgenticResultsView(results, output) {
  output.hidden = true;
  let view = results.querySelector(".agentic-friendly-results");
  if (!view) {
    view = createElement("div", "agentic-friendly-results");
    output.insertAdjacentElement("afterend", view);
  }
  return view;
}

function addResultStatus(parent, label, value, detail = "") {
  const row = createElement("div", "agentic-status-row");
  const left = createElement("div", "agentic-status-copy");
  left.appendChild(createElement("strong", "", label));
  if (detail) left.appendChild(createElement("small", "", detail));
  const status = createElement("span", `agentic-status-pill ${statusKind(value)}`, displayStatusLabel(value));
  row.append(left, status);
  parent.appendChild(row);
}

function renderAgenticResults(data, results, output) {
  const view = getAgenticResultsView(results, output);
  view.replaceChildren();

  const findings = Array.isArray(data.findings) ? data.findings : [];
  const risk = data.risk && typeof data.risk === "object" ? data.risk : {};
  const riskLevel = String(risk.level || "unknown").toLowerCase();
  const riskScore = typeof risk.score === "number" ? risk.score : null;
  const agentReview = data.agent_review && typeof data.agent_review === "object"
    ? data.agent_review
    : { status: "disabled", reviews: [] };
  const reviews = Array.isArray(agentReview.reviews) ? agentReview.reviews : [];
  const verificationStatus = friendlyStatus(data.verification, "not reported");
  const auditStatus = friendlyStatus(data.audit, "not reported");
  const overallStatus = friendlyStatus(data.status, "completed");
  const requiresHumanReview = data.requires_human_review === true;

  // High-level outcome: readable language instead of a JSON dump.
  const summary = createElement("section", "agentic-summary-card");
  const summaryTop = createElement("div", "agentic-summary-top");
  const summaryCopy = createElement("div", "agentic-summary-copy");
  summaryCopy.appendChild(createElement("p", "agentic-summary-eyebrow", "YOUR PRIVACY CHECK"));
  summaryCopy.appendChild(createElement("h3", "agentic-summary-title", "Workflow results"));
  const summaryText = findings.length === 0
    ? "KAVACH did not find any supported sensitive patterns in this prompt."
    : `KAVACH found ${findings.length} potential sensitive ${findings.length === 1 ? "item" : "items"} and prepared a protected version.`;
  summaryCopy.appendChild(createElement("p", "agentic-summary-description", summaryText));
  const statusBadge = createElement("span", `agentic-overall-badge ${statusKind(overallStatus)}`, displayStatusLabel(overallStatus));
  summaryTop.append(summaryCopy, statusBadge);
  summary.appendChild(summaryTop);

  const metrics = createElement("div", "agentic-metrics");
  const metricItems = [
    ["Sensitive items", String(findings.length)],
    ["Risk level", riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)],
    ["Risk score", riskScore === null ? "Not reported" : String(riskScore)]
  ];
  metricItems.forEach(([label, value]) => {
    const metric = createElement("div", "agentic-metric");
    metric.appendChild(createElement("span", "", label));
    metric.appendChild(createElement("strong", "", value));
    metrics.appendChild(metric);
  });
  summary.appendChild(metrics);
  view.appendChild(summary);

  // Summarize the stages the server actually reports; do not invent progress.
  const stages = createElement("section", "agentic-friendly-section");
  stages.appendChild(createElement("h4", "agentic-friendly-heading", "What KAVACH did"));
  const stageList = createElement("div", "agentic-status-list");
  const steps = Array.isArray(data.steps) ? data.steps : [];
  if (steps.length) {
    steps.forEach(step => {
      const name = typeof step === "string" ? step : (step.name || step.step || "Workflow step");
      const stepStatus = typeof step === "string" ? "completed" : friendlyStatus(step.status, "not reported");
      const notes = typeof step === "object" ? (step.detail || step.message || "") : "";
      addResultStatus(stageList, humanizeWorkflowStep(name), stepStatus, notes);
    });
  } else {
    addResultStatus(stageList, "Sensitive information scan", "completed");
    addResultStatus(stageList, "AI-assisted review", friendlyStatus(agentReview.status, "not reported"));
    addResultStatus(stageList, "Masking and verification", verificationStatus);
  }
  stages.appendChild(stageList);
  view.appendChild(stages);

  // Explain local AI availability and its advisory-only role.
  const reviewPanel = createElement("section", "agentic-review-panel");
  const reviewHeading = createElement("div", "agentic-review-heading");
  const reviewTitleBlock = createElement("div", "");
  reviewTitleBlock.appendChild(createElement("h4", "agentic-friendly-heading", "AI-assisted review"));
  reviewTitleBlock.appendChild(createElement("p", "agentic-review-subtitle", "The local model provides advice; KAVACH's detector controls the findings and masking."));
  reviewHeading.appendChild(reviewTitleBlock);
  reviewHeading.appendChild(createElement("span", `agentic-status-pill ${statusKind(friendlyStatus(agentReview.status, "not reported"))}`, displayStatusLabel(friendlyStatus(agentReview.status, "not reported"))));
  reviewPanel.appendChild(reviewHeading);

  const reviewStatus = friendlyStatus(agentReview.status, "not reported");
  let reviewSummary;
  if (reviewStatus === "ok" || reviewStatus === "success" || reviewStatus === "completed") {
    reviewSummary = reviews.length
      ? `Local AI review returned ${reviews.length} advisory ${reviews.length === 1 ? "assessment" : "assessments"}.`
      : "The local AI review completed without returning individual assessments.";
  } else if (reviewStatus === "disabled") {
    reviewSummary = "AI review is switched off. KAVACH can still scan and mask using its detection rules.";
  } else if (reviewStatus === "unavailable" || reviewStatus === "error" || reviewStatus === "failed") {
    reviewSummary = "The local AI reviewer was not available for this run. Treat the detector's result as the protection output and review uncertain items yourself.";
  } else {
    reviewSummary = "The AI review status was not reported. This review is advisory and must not be treated as a guarantee.";
  }
  reviewPanel.appendChild(createElement("p", "agentic-review-summary", reviewSummary));

  if (reviews.length) {
    const reviewList = createElement("div", "agentic-individual-reviews");
    reviews.forEach((review, index) => {
      const card = createElement("article", "agentic-review-item");
      const assessment = String(review.assessment || "assessment").replace(/_/g, " ");
      card.appendChild(createElement("strong", "", `Assessment ${index + 1}: ${assessment}`));
      if (review.reason) card.appendChild(createElement("p", "", review.reason));
      reviewList.appendChild(card);
    });
    reviewPanel.appendChild(reviewList);
  }
  view.appendChild(reviewPanel);

  // Show only the protected text, never the unmasked original prompt.
  const protectedPanel = createElement("section", "agentic-protected-panel");
  const protectedTop = createElement("div", "agentic-protected-top");
  const protectedHeading = createElement("div", "");
  protectedHeading.appendChild(createElement("h4", "agentic-friendly-heading", "Protected prompt"));
  protectedHeading.appendChild(createElement("p", "agentic-review-subtitle", "Copy this masked version into your AI tool after reviewing it."));
  protectedTop.appendChild(protectedHeading);
  const maskedText = typeof data.masked_text === "string" ? data.masked_text : "";
  const copyButton = createElement("button", "button button-primary agentic-copy-button", "Copy protected prompt");
  copyButton.type = "button";
  copyButton.disabled = !maskedText;
  protectedTop.appendChild(copyButton);
  protectedPanel.appendChild(protectedTop);
  const maskedBox = createElement("div", "agentic-protected-text", maskedText || "No protected text was returned by the workflow.");
  maskedBox.setAttribute("aria-label", "Protected prompt text");
  protectedPanel.appendChild(maskedBox);
  const copyFeedback = createElement("p", "agentic-copy-feedback");
  copyFeedback.setAttribute("aria-live", "polite");
  protectedPanel.appendChild(copyFeedback);
  copyButton.addEventListener("click", async () => {
    if (!maskedText) return;
    try {
      await navigator.clipboard.writeText(maskedText);
      copyFeedback.textContent = "Protected prompt copied. Review it before pasting into your AI tool.";
    } catch {
      const temporary = createElement("textarea", "agentic-copy-fallback");
      temporary.value = maskedText;
      temporary.setAttribute("readonly", "");
      document.body.appendChild(temporary);
      temporary.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch { copied = false; }
      temporary.remove();
      copyFeedback.textContent = copied
        ? "Protected prompt copied. Review it before pasting into your AI tool."
        : "Copy was blocked by the browser. Select the protected prompt text and copy it manually.";
    }
  });
  view.appendChild(protectedPanel);

  // Verification, audit, and human review in plain language.
  const safetyFooter = createElement("section", "agentic-final-checks");
  addResultStatus(safetyFooter, "Masking verification", verificationStatus,
    verificationStatus === "passed" ? "The workflow reports that verification passed." : "Review the protected prompt if the status is uncertain.");
  addResultStatus(safetyFooter, "Workflow record", auditStatus,
    auditStatus === "saved" || auditStatus === "ok" || auditStatus === "completed" ? "Workflow metadata was recorded." : "Audit status is reported by the server.");
  if (requiresHumanReview) {
    const notice = createElement("div", "agentic-human-review-notice");
    notice.appendChild(createElement("strong", "", "Human review recommended"));
    notice.appendChild(createElement("p", "", "KAVACH flagged this run for a person to review. Check the detected items and protected prompt before using it."));
    safetyFooter.appendChild(notice);
  } else {
    const notice = createElement("div", "agentic-human-review-ok");
    notice.appendChild(createElement("strong", "", "No additional human-review flag"));
    notice.appendChild(createElement("p", "", "This does not guarantee that every sensitive value was detected. Review the protected prompt before sharing it."));
    safetyFooter.appendChild(notice);
  }
  view.appendChild(safetyFooter);
}

const agenticButton = $("run-agentic");

if (agenticButton) {
  agenticButton.addEventListener("click", async () => {
    const input = $("inp");
    const status = $("agentic-run-status");
    const results = $("agentic-results");
    const output = $("agentic-output");

    if (!input || !status || !results || !output) return;

    const text = input.value;
    if (!text.trim()) {
      status.textContent = "Enter a prompt in the scanner first.";
      input.focus();
      return;
    }

    agenticButton.disabled = true;
    status.textContent = "KAVACH is scanning, reviewing, masking, and checking the protected prompt…";
    results.hidden = true;

    try {
      const response = await apiFetch("/api/agentic/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, mode: "label" })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("The server returned an unexpected response.");
      }

      if (!response.ok) {
        throw new Error(data.detail || "The privacy workflow could not be completed.");
      }

      renderAgenticResults(data, results, output);
      results.hidden = false;

      const reviewStatus = friendlyStatus(data.agent_review?.status, "not reported");
      status.textContent = data.requires_human_review === true
        ? "Workflow finished. Please review the findings before using the prompt."
        : reviewStatus === "unavailable" || reviewStatus === "disabled"
          ? "Workflow finished. The local AI review was not active; please review the protected prompt."
          : "Workflow finished. Review the protected prompt before using it.";

      await loadAgenticHistory();
    } catch (error) {
      status.textContent = error.message || "Could not run the privacy workflow.";
    } finally {
      agenticButton.disabled = false;
    }
  });
}
