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
// Dashboard preferences (non-sensitive browser-local settings)
// ------------------------------------------------------------

const DASHBOARD_SETTINGS_KEY = "kavachDashboardPreferencesV1";
const DEFAULT_DASHBOARD_SETTINGS = {
  protectionMode: "standard",
  maskingMode: "label"
};

function loadDashboardSettings() {
  try {
    const saved = JSON.parse(
      localStorage.getItem(DASHBOARD_SETTINGS_KEY) || "{}"
    );

    return {
      protectionMode: saved.protectionMode === "autonomous"
        ? "autonomous"
        : "standard",
      maskingMode: saved.maskingMode === "partial"
        ? "partial"
        : "label"
    };
  } catch {
    return { ...DEFAULT_DASHBOARD_SETTINGS };
  }
}

let dashboardSettings = loadDashboardSettings();

function selectProtectionMode(value) {
  document
    .querySelectorAll('input[name="protection-mode"]')
    .forEach(input => {
      input.checked = input.value === value;
    });
}

function syncSettingsControls() {
  $("settings-default-mode").value =
    dashboardSettings.protectionMode;
  $("settings-masking-format").value =
    dashboardSettings.maskingMode;
  selectProtectionMode(dashboardSettings.protectionMode);
}

function saveDashboardSettings(settings) {
  try {
    localStorage.setItem(
      DASHBOARD_SETTINGS_KEY,
      JSON.stringify(settings)
    );
    return true;
  } catch {
    return false;
  }
}

function initializeDashboardSettings() {
  const form = $("settings-form");
  const status = $("settings-status");
  const reset = $("reset-settings");

  if (!form || !status || !reset) return;

  syncSettingsControls();
  status.textContent = "Preferences loaded from this browser.";

  form.addEventListener("submit", event => {
    event.preventDefault();

    const next = {
      protectionMode:
        $("settings-default-mode").value === "autonomous"
          ? "autonomous"
          : "standard",
      maskingMode:
        $("settings-masking-format").value === "partial"
          ? "partial"
          : "label"
    };

    if (!saveDashboardSettings(next)) {
      status.textContent =
        "Could not save preferences. Check browser storage settings.";
      return;
    }

    dashboardSettings = next;
    syncSettingsControls();
    status.textContent =
      "Preferences saved in this browser and applied to the Protect workspace.";
  });

  reset.addEventListener("click", () => {
    const defaults = { ...DEFAULT_DASHBOARD_SETTINGS };

    if (!saveDashboardSettings(defaults)) {
      status.textContent =
        "Could not reset preferences. Check browser storage settings.";
      return;
    }

    dashboardSettings = defaults;
    syncSettingsControls();
    status.textContent =
      "Defaults restored: Standard protection and Label masking.";
  });
}

initializeDashboardSettings();


// ------------------------------------------------------------
// Prompt protection: one deliberate action for both protection modes
// ------------------------------------------------------------

function showPromptPlaceholder() {
  $("out").textContent =
    "Your protected prompt will appear here after scanning.";
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
    td.className = "empty-cell";
    td.textContent =
      "No supported sensitive patterns were detected.";
    tr.appendChild(td);
    rows.appendChild(tr);
    return;
  }

  findings.forEach(finding => {
    const tr = document.createElement("tr");
    [
      finding.type || "Finding",
      `${finding.start ?? "?"}-${finding.end ?? "?"}`,
      `${Math.round((finding.confidence || 0) * 100)}%`
    ].forEach(value => {
      const td = document.createElement("td");
      td.textContent = String(value);
      tr.appendChild(td);
    });
    rows.appendChild(tr);
  });
}

function resetPromptResults(message = "Your prompt has not been scanned yet.") {
  showPromptPlaceholder();

  $("level").className = "level none";
  $("level").textContent = "Not scanned yet";
  $("score").textContent =
    "Choose a mode and select Check & Protect.";

  renderPromptRows([]);
  $("copy-protected").disabled = true;
  $("protection-status").textContent = message;
  $("protection-summary").hidden = true;

  const findingsSummary =
    document.querySelector(".findings-details summary");
  if (findingsSummary) {
    findingsSummary.textContent = "View detected items";
  }
}

function renderProtectionResult(data) {
  const findings = Array.isArray(data.findings)
    ? data.findings
    : [];
  const risk = data.risk && typeof data.risk === "object"
    ? data.risk
    : {};
  const maskedText = typeof data.masked_text === "string"
    ? data.masked_text
    : "";

  renderMaskedPrompt(maskedText);

  const rawLevel = String(risk.level || "none").toLowerCase();
  const allowedLevels = ["none", "low", "medium", "high"];
  const level = allowedLevels.includes(rawLevel) ? rawLevel : "none";

  $("level").className = `level ${level}`;
  $("level").textContent = findings.length === 0
    ? "No supported patterns found"
    : `${level.charAt(0).toUpperCase() + level.slice(1)} risk`;

  $("score").textContent = findings.length
    ? `${findings.length} potential item(s) detected · Risk score: ${risk.score ?? "Not reported"}`
    : `No supported sensitive patterns detected · Risk score: ${risk.score ?? "Not reported"}`;

  renderPromptRows(findings);
  $("copy-protected").disabled = !maskedText;

  const findingsSummary =
    document.querySelector(".findings-details summary");
  if (findingsSummary) {
    findingsSummary.textContent =
      `View detected items (${findings.length})`;
  }

  $("copy-feedback") &&
    ($("copy-feedback").textContent = "");
}

function renderProtectionSummary(data, mode) {
  const findings = Array.isArray(data.findings)
    ? data.findings
    : [];

  const autonomous = mode === "autonomous";
  const verification = data.verification &&
    typeof data.verification === "object"
      ? String(data.verification.status || "").toLowerCase()
      : "not_reported";

  const humanReviewRequired =
    data.requires_human_review === true;

  const verified =
    autonomous &&
    verification === "passed" &&
    !humanReviewRequired;

  const needsReview =
    autonomous &&
    !verified;

  let title;
  let message;
  let statusLabel;
  let statusKind;

  if (needsReview) {
    title = "Review recommended";
    message =
      "KAVACH prepared a protected preview, but this workflow needs a human check. Review the detected items and protected prompt before sharing.";
    statusLabel = "Review needed";
    statusKind = "warning";
  } else if (verified) {
    title = "Protection check completed";
    message = findings.length
      ? `KAVACH detected and masked ${findings.length} sensitive item(s). The protected output passed verification. Review it before sharing.`
      : "KAVACH did not find supported sensitive patterns, and the workflow verification passed. Review the prompt before sharing.";
    statusLabel = "Verified";
    statusKind = "success";
  } else if (findings.length) {
    title = "Protection preview ready";
    message =
      `KAVACH detected and masked ${findings.length} sensitive item(s). Review the detected items and protected prompt before sharing.`;
    statusLabel = "Scan complete";
    statusKind = "neutral";
  } else {
    title = "No supported patterns found";
    message =
      "KAVACH did not find supported sensitive patterns. Detection is heuristic, so review your prompt before sharing.";
    statusLabel = "No findings";
    statusKind = "neutral";
  }

  $("protection-summary-title").textContent = title;
  $("protection-summary-message").textContent = message;
  $("protection-summary-count").textContent = String(findings.length);

  const badge = $("protection-summary-status");
  badge.textContent = statusLabel;
  badge.className =
    `protection-summary-badge ${statusKind}`;

  $("protection-summary").hidden = false;
}

async function copyProtectedPrompt() {
  const text = $("out").textContent;
  const feedback = $("copy-feedback");

  if (!text || $("copy-protected").disabled) {
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    feedback.textContent =
      "Protected prompt copied. Review it before pasting into your AI tool.";
  } catch {
    const temporary = document.createElement("textarea");
    temporary.value = text;
    temporary.setAttribute("readonly", "");
    temporary.style.position = "fixed";
    temporary.style.left = "-10000px";
    document.body.appendChild(temporary);
    temporary.select();

    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }

    temporary.remove();
    feedback.textContent = copied
      ? "Protected prompt copied. Review it before pasting into your AI tool."
      : "Copy was blocked. Select the protected prompt and copy it manually.";
  }
}

async function protectPrompt() {
  const input = $("inp");
  const button = $("protect-button");
  const status = $("protection-status");

  const text = input.value;
  if (!text.trim()) {
    status.textContent = "Enter a prompt before protecting it.";
    input.focus();
    return;
  }

  const selectedMode =
    document.querySelector('input[name="protection-mode"]:checked');
  const mode = selectedMode?.value === "autonomous"
    ? "autonomous"
    : "standard";

  const endpoint = mode === "autonomous"
    ? "/api/agentic/scan"
    : "/api/scan-global";

  button.disabled = true;
  input.disabled = true;
  button.textContent = "Protecting...";
  status.textContent = mode === "autonomous"
    ? "Running the autonomous privacy workflow..."
    : "Checking your prompt for supported sensitive patterns...";

  resetPromptResults(status.textContent);

  try {
    const response = await apiFetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ text, mode: dashboardSettings.maskingMode })
    });

    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("The server returned an unexpected response.");
    }

    if (!response.ok) {
      throw new Error(
        data.detail || "The protection check could not be completed."
      );
    }

    renderProtectionResult(data);
    renderProtectionSummary(data, mode);

    if (mode === "autonomous") {
      status.textContent = data.requires_human_review === true
        ? "Protection completed. Please review the protected prompt before sharing."
        : "Protection completed. Review the protected prompt before sharing.";
    } else {
      status.textContent =
        "Protection check completed. Review the detected items and protected prompt before sharing.";
    }
  } catch (error) {
    resetPromptResults(
      error.message || "Could not complete the protection check."
    );
    $("level").className = "level high";
    $("level").textContent = "Protection unavailable";
    $("score").textContent =
      "Check that the KAVACH server is running and try again.";

  } finally {
    button.disabled = false;
    input.disabled = false;
    button.textContent = "Check & Protect";
  }
}

$("inp").addEventListener("input", () => {
  resetPromptResults(
    "Prompt changed. Select Check & Protect to scan the updated text."
  );
});

document.querySelectorAll("[data-s]").forEach(button => {
  button.addEventListener("click", () => {
    $("inp").value = SAMPLES[Number(button.dataset.s)];
    resetPromptResults(
      "Sample loaded. Select Check & Protect to scan it."
    );
    $("inp").focus();
  });
});

$("clear").addEventListener("click", () => {
  $("inp").value = "";
  resetPromptResults("Prompt cleared.");
  $("inp").focus();
});

$("protect-button").addEventListener("click", protectPrompt);
$("copy-protected").addEventListener("click", copyProtectedPrompt);

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

// Autonomous details are shown only inside the optional disclosure.
