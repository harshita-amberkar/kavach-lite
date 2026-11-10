// --------------------------------------------------
// Remote token authentication is requested only when the server requires it.
// --------------------------------------------------

const KAVACH_TOKEN_KEY = "kavachApiToken";

async function promptForKavachApiToken() {
  const dialog = $("token-dialog");
  const form = $("token-form");
  const input = $("token-input");
  const cancel = $("token-cancel");
  if (!dialog || !form || !input || !cancel || typeof dialog.showModal !== "function") {
    throw new Error("KAVACH server access needs a browser that supports secure token entry.");
  }

  const token = await new Promise(resolve => {
    let settled = false;
    const finish = value => {
      if (settled) return;
      settled = true;
      form.removeEventListener("submit", submitToken);
      dialog.removeEventListener("close", handleClose);
      cancel.removeEventListener("click", cancelToken);
      input.value = "";
      resolve(value);
    };
    const submitToken = event => {
      event.preventDefault();
      const value = input.value.trim();
      if (!value) {
        input.focus();
        return;
      }
      try {
        sessionStorage.setItem(KAVACH_TOKEN_KEY, value);
      } catch {
        finish(null);
        return;
      }
      finish(value);
      dialog.close();
    };
    const cancelToken = () => dialog.close();
    const handleClose = () => finish(null);

    input.value = "";
    form.addEventListener("submit", submitToken);
    dialog.addEventListener("close", handleClose);
    cancel.addEventListener("click", cancelToken);
    dialog.showModal();
    input.focus();
  });

  if (!token) throw new Error("KAVACH API token is required.");
  return token;
}

async function apiFetch(url, options = {}) {
  const send = async token => {
    const headers = new Headers(options.headers || {});
    if (token) headers.set("X-KAVACH-Token", token);
    else headers.delete("X-KAVACH-Token");

    return fetch(url, {
      ...options,
      headers,
      signal: AbortSignal.timeout(60000)
    });
  };

  let token = sessionStorage.getItem(KAVACH_TOKEN_KEY);
  let response = await send(token);
  if (response.status !== 401) return response;

  sessionStorage.removeItem(KAVACH_TOKEN_KEY);
  token = await promptForKavachApiToken();
  response = await send(token);
  if (response.status === 401) {
    sessionStorage.removeItem(KAVACH_TOKEN_KEY);
    throw new Error("Your session expired. Check your access code and try again.");
  }
  return response;
}

function friendlyRequestError(status, fallback) {
  if (status === 401) return "Your session expired. Check your access code and try again.";
  if (status === 413) return "This is larger than KAVACH can check. Choose a smaller file or shorten your text.";
  if (status === 422) return "Please check your text or file and try again.";
  if (status === 429) return "Too many checks in a short time. Wait a minute, then try again.";
  if (status === 502) return "KAVACH could not reach the service it needs. Try again in a moment.";
  if (status === 504) return "The AI service is taking too long. Try again in a moment.";
  return fallback;
}

const $ = id => document.getElementById(id);

async function refreshBackendHealth() {
  const indicator = $("backend-health");
  const label = $("backend-health-label");
  if (!indicator || !label) return;

  try {
    const response = await apiFetch("/api/health", { cache: "no-store" });
    if (!response.ok) throw new Error("Health request failed.");
    const data = await response.json();
    label.textContent = data && data.status === "ok" ? "ready" : "unavailable";
  } catch {
    label.textContent = "unavailable";
  }
  indicator.hidden = false;
}

refreshBackendHealth();
window.setInterval(refreshBackendHealth, 30000);

document.addEventListener("DOMContentLoaded", () => {
  const navLinks = Array.from(document.querySelectorAll(".nav-link[href^='#']"));
  const sections = navLinks.map(link => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  if (!("IntersectionObserver" in window)) return;
  const sectionLabels = {
    scan: "Protect",
    security: "Settings",
    help: "Help & Extensions"
  };
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    navLinks.forEach(link => link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`));
    const breadcrumb = document.querySelector(".breadcrumbs strong");
    if (breadcrumb) breadcrumb.textContent =
      sectionLabels[visible.target.id] || "Protect";
  }, { rootMargin: "-18% 0px -65% 0px", threshold: [0, 0.15, 0.35] });
  sections.forEach(section => observer.observe(section));
});

let timer;
let latestMaskedText = "";
let latestFilename = "masked-document.txt";

// ------------------------------------------------------------
// Dashboard preferences (non-sensitive browser-local settings)
// ------------------------------------------------------------

const DASHBOARD_SETTINGS_KEY = "kavachDashboardPreferencesV1";
const DEFAULT_DASHBOARD_SETTINGS = { maskingMode: "label" };

function loadDashboardSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(DASHBOARD_SETTINGS_KEY) || "{}");
    return { maskingMode: saved.maskingMode === "partial" ? "partial" : "label" };
  } catch {
    return { ...DEFAULT_DASHBOARD_SETTINGS };
  }
}

let dashboardSettings = loadDashboardSettings();

function syncSettingsControls() {
  const masking = $("settings-masking-format");
  if (masking) masking.value = dashboardSettings.maskingMode;
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
  status.textContent = "Your saved preference is ready.";

  form.addEventListener("submit", event => {
    event.preventDefault();

    const next = {
      maskingMode: $("settings-masking-format").value === "partial"
        ? "partial"
        : "label"
    };

    if (!saveDashboardSettings(next)) {
      status.textContent =
        "Your preference could not be saved. Check this browser's storage settings.";
      return;
    }

    dashboardSettings = next;
    syncSettingsControls();
    status.textContent = "Your masking preference is saved for the next check.";
  });

  reset.addEventListener("click", () => {
    const defaults = { ...DEFAULT_DASHBOARD_SETTINGS };

    if (!saveDashboardSettings(defaults)) {
      status.textContent =
        "Your preference could not be reset. Check this browser's storage settings.";
      return;
    }

    dashboardSettings = defaults;
    syncSettingsControls();
    status.textContent = "Your preference is reset. Labels will be used next time.";
  });
}

initializeDashboardSettings();

// ------------------------------------------------------------
// Prompt protection: one deliberate action for both protection modes
// ------------------------------------------------------------

function showPromptPlaceholder() {
  $("out").textContent =
    "Your protected message will appear here after scanning.";
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

const FINDING_LABELS = {
  AADHAAR: "Aadhaar number", AADHAAR_POSSIBLE: "Possible Aadhaar number",
  GSTIN: "GSTIN", API_KEY: "API key or secret", CARD: "Payment card",
  PAN: "PAN", UPI_ID: "UPI ID", IFSC: "IFSC code", EMAIL: "Email address",
  PHONE: "Phone number", OTP: "One-time code", PASSPORT: "Passport number",
  PERSON: "Person's name", LOCATION: "Location", IP_ADDRESS: "IP address",
  MAC_ADDRESS: "Device address", CRYPTO: "Crypto wallet address",
  MEDICAL_LICENSE: "Medical license", NRP: "National registration number",
  US_SSN: "US Social Security number", US_ITIN: "US tax ID",
  US_DRIVER_LICENSE: "US driver's license", US_PASSPORT: "US passport",
  US_BANK_NUMBER: "US bank number", UK_NINO: "UK National Insurance number",
  UK_NHS: "UK NHS number", UK_PASSPORT: "UK passport", AU_ABN: "Australian business number",
  AU_ACN: "Australian company number", AU_TFN: "Australian tax number",
  AU_MEDICARE: "Australian Medicare number", MEDICAL_INFO: "Medical information",
  CONFIDENTIAL_BUSINESS: "Confidential business information", IBAN: "IBAN"
};

function friendlyFindingLabel(type) {
  const key = String(type || "").toUpperCase();
  return FINDING_LABELS[key] || "Sensitive information";
}

function renderPromptRows(findings) {
  const rows = $("rows");
  rows.replaceChildren();
  if (!findings.length) {
    const empty = document.createElement("div");
    empty.className = "finding-empty";
    empty.textContent = "No supported sensitive information was found.";
    rows.appendChild(empty);
    return;
  }

  findings.forEach(finding => {
    const card = document.createElement("article");
    card.className = "finding-card";
    const icon = document.createElement("span");
    icon.className = "finding-card-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "!";
    const content = document.createElement("div");
    content.className = "finding-card-content";
    const title = document.createElement("strong");
    title.textContent = `${friendlyFindingLabel(finding.type)} detected.`;
    content.append(title);
    card.append(icon, content);
    rows.appendChild(card);
  });
}

function setResultState(message, state) {
  const resultState = $("result-state");
  resultState.textContent = message;
  resultState.className = `result-state ${state}`;
  resultState.hidden = !message;
}

function resetPromptResults(
  message = "Your results will appear here after scanning.",
  state = "empty"
) {
  showPromptPlaceholder();
  const resultPanel = document.querySelector(".result-panel");
  document.querySelector(".scanner-grid")?.classList.remove("has-result");
  resultPanel?.classList.remove("has-result");
  resultPanel?.removeAttribute("data-risk");
  setResultState(message, state);
  renderPromptRows([]);
  $("copy-protected").disabled = true;
  $("protection-status").textContent = message;
  $("protection-summary").hidden = true;
  $("protection-summary-risk").hidden = true;
  const aiReview = $("ai-review");
  if (aiReview) aiReview.hidden = true;
  $("ai-review-content")?.replaceChildren();
  $("ai-review-state").textContent = "";
  $("ai-review-badge").textContent = "Not run";
  $("ai-review-badge").className = "ai-review-badge";
  document.querySelector(".masked-state-tag").hidden = true;
  $("copy-feedback").textContent = "";
  document.querySelector(".findings-details").open = false;
  const findingsSummary = document.querySelector(".findings-details summary");
  if (findingsSummary) findingsSummary.textContent = "See detected information";
}

function renderProtectionResult(data) {
  const findings = Array.isArray(data.findings)
    ? data.findings
    : [];
  const maskedText = typeof data.masked_text === "string"
    ? data.masked_text
    : "";
  const outputAvailable = Boolean(maskedText.trim()) &&
    !(findings.length > 0 && maskedText === $("inp").value);

  renderMaskedPrompt(outputAvailable ? maskedText : "");

  const resultPanel = document.querySelector(".result-panel");
  document.querySelector(".scanner-grid")?.classList.add("has-result");
  resultPanel?.classList.add("has-result");
  resultPanel?.removeAttribute("data-risk");
  setResultState("", "empty");

  renderPromptRows(findings);
  $("copy-protected").disabled = !outputAvailable;

  const findingsSummary =
    document.querySelector(".findings-details summary");
  if (findingsSummary) {
    findingsSummary.textContent = `See detected information (${findings.length})`;
  }

  $("copy-feedback") &&
    ($("copy-feedback").textContent = "");
}

function renderProtectionSummary(data) {
  const findings = Array.isArray(data.findings) ? data.findings : [];
  const maskedText = typeof data.masked_text === "string" ? data.masked_text : "";
  const outputAvailable = Boolean(maskedText.trim()) &&
    !(findings.length > 0 && maskedText === $("inp").value);
  const globalDetection = data.global_detection && typeof data.global_detection === "object"
    ? data.global_detection
    : null;
  const checksUnavailable = globalDetection &&
    String(globalDetection.status || "").toLowerCase() === "unavailable";
  const requiresHumanReview = data.requires_human_review === true;
  const verificationStatus = data.verification &&
    typeof data.verification === "object"
    ? String(data.verification.status || "").toLowerCase()
    : "not_reported";
  const types = [...new Set(findings.map(item => friendlyFindingLabel(item.type)))];
  const risk = data.risk && typeof data.risk === "object" ? data.risk : {};
  const riskNode = $("protection-summary-risk");
  const riskLevel = typeof risk.level === "string" ? risk.level.trim() : "";
  const riskScore = typeof risk.score === "number" && Number.isFinite(risk.score)
    ? ` (score ${risk.score})`
    : "";
  riskNode.textContent = riskLevel ? `Risk: ${riskLevel}${riskScore}` : "";
  riskNode.hidden = !riskLevel;
  const countLabel = $("protection-summary-count-label");
  countLabel.textContent = findings.length === 1 ? "Sensitive item found" : "Sensitive items found";
  $("protection-summary-count").textContent = String(findings.length);

  let title;
  let message;
  let statusLabel;
  let statusKind;
  if (!outputAvailable) {
    title = "We couldn't prepare a protected message.";
    message = "Do not share the original message. Try again or remove sensitive information yourself.";
    statusLabel = "Not protected";
    statusKind = "warning";
  } else if (requiresHumanReview) {
    title = "Automated protection ran; please review before sharing.";
    message = checksUnavailable
      ? "Automated protection ran, but some detection checks were unavailable. Review the findings and protected message before sharing."
      : verificationStatus === "not_run"
        ? "Automated detection and masking ran, but verification was not performed. Review the findings and protected message before sharing."
        : "Automated protection ran, but this result still requires human review. Review the findings and protected message before sharing.";
    statusLabel = "Human review required";
    statusKind = "warning";
  } else if (checksUnavailable) {
    title = "Please review this message before sharing.";
    message = "Some detection checks were unavailable. Review the protected message carefully before sharing.";
    statusLabel = "Review needed";
    statusKind = "warning";
  } else if (findings.length) {
    title = "Your message is protected.";
    message = `We found ${findings.length} sensitive item${findings.length === 1 ? "" : "s"}. ${types.join(", ")} detected. Your protected message is ready. Please review this message before sharing.`;
    statusLabel = "Protected";
    statusKind = "success";
  } else {
    title = "Your message is protected.";
    message = "No supported sensitive items were found. Please review this message before sharing.";
    statusLabel = "Checked";
    statusKind = "success";
  }

  $("protection-summary-title").textContent = title;
  $("protection-summary-message").textContent = message;
  const badge = $("protection-summary-status");
  badge.textContent = statusLabel;
  badge.className = `protection-summary-badge ${statusKind}`;

  const protectedTag = document.querySelector(".masked-state-tag");
  if (protectedTag) protectedTag.hidden = !outputAvailable;
  const findingsDetails = document.querySelector(".findings-details");
  if (findingsDetails) findingsDetails.open = findings.length > 0;
  $("protection-summary").hidden = false;
}

function reviewFieldValues(value) {
  const values = Array.isArray(value) ? value : [value];
  return values
    .filter(item => typeof item === "string" && item.trim())
    .map(item => item.trim().slice(0, 500));
}

function appendAiReviewField(container, label, value) {
  const values = reviewFieldValues(value);
  if (!values.length) return;

  const section = document.createElement("div");
  section.className = "ai-review-field";
  const heading = document.createElement("strong");
  heading.textContent = label;
  const list = document.createElement(values.length > 1 ? "ul" : "p");
  values.forEach(valueText => {
    const item = values.length > 1 ? document.createElement("li") : list;
    item.textContent = valueText;
    if (values.length > 1) list.appendChild(item);
  });
  section.append(heading, list);
  container.appendChild(section);
}

function renderAiReview(data, mode) {
  const section = $("ai-review");
  const content = $("ai-review-content");
  const state = $("ai-review-state");
  const badge = $("ai-review-badge");
  content.replaceChildren();
  state.textContent = "";
  section.hidden = mode !== "autonomous";
  if (section.hidden) return;

  const review = data.agent_review && typeof data.agent_review === "object"
    ? data.agent_review
    : {};
  const status = String(review.status || "unavailable").trim().toLowerCase();
  if (status === "no_findings") {
    badge.textContent = "No findings to review";
    badge.className = "ai-review-badge neutral";
    state.textContent = "The detector returned no findings for the AI analyst to assess.";
    return;
  }

  if (status !== "ok") {
    badge.textContent = "AI review unavailable";
    badge.className = "ai-review-badge unavailable";
    state.textContent = review.reason === "timeout"
      ? "The local AI analyst timed out. Detection and masking are unchanged."
      : status === "disabled"
        ? "The local AI analyst is disabled. Detection and masking are unchanged."
        : "The local AI analyst could not complete a review. Detection and masking are unchanged.";
    return;
  }

  badge.textContent = "Review complete";
  badge.className = "ai-review-badge success";
  const findings = Array.isArray(data.findings) ? data.findings : [];
  const reviews = Array.isArray(review.reviews) ? review.reviews : [];
  reviews.forEach(item => {
    if (!item || typeof item !== "object") return;
    const card = document.createElement("article");
    card.className = "ai-review-item";
    const finding = Number.isInteger(item.id) ? findings[item.id] : null;
    const title = document.createElement("h5");
    const assessment = typeof item.assessment === "string"
      ? item.assessment.trim()
      : "";
    title.textContent = `${finding ? `${friendlyFindingLabel(finding.type)} · ` : ""}AI assessment${assessment ? `: ${assessment}` : ""}`;
    card.appendChild(title);
    appendAiReviewField(card, "Assessment detail", item.reason);
    appendAiReviewField(card, "Privacy concerns", item.privacy_concerns ?? item.privacy_concern);
    appendAiReviewField(card, "Recommendations", item.recommendations ?? item.recommendation);
    content.appendChild(card);
  });

  appendAiReviewField(content, "Privacy concerns", review.privacy_concerns);
  appendAiReviewField(content, "Recommendations", review.recommendations ?? review.recommendation);
  if (!reviews.length && !content.childElementCount) {
    state.textContent = "The analyst completed the review but returned no assessment details.";
  }
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
      "Protected message copied. Review it before sharing.";
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
      ? "Protected message copied. Review it before sharing."
      : "Copy was blocked. Select the protected message and copy it manually.";
  }
}

async function protectPrompt() {
  const input = $("inp");
  const button = $("protect-button");
  const status = $("protection-status");
  const promptPanel = input.closest(".prompt-panel");

  const text = input.value;
  if (!text.trim()) {
    status.textContent = "Add some text first.";
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
  promptPanel?.classList.add("is-scanning");
  button.textContent = "Checking your text…";
  status.textContent = "Scanning your message...";

  resetPromptResults(status.textContent, "loading");

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
      throw new Error(friendlyRequestError(
        response.status,
        "KAVACH could not finish this check. Try again in a moment."
      ));
    }

    renderProtectionResult(data);
    renderProtectionSummary(data);
    renderAiReview(data, mode);

    status.textContent = "";
  } catch (error) {
    const safeMessages = new Set([
      "Your session expired. Check your access code and try again.",
      "KAVACH API token is required.",
      "KAVACH server access needs a browser that supports secure token entry."
    ]);
    const message = error?.name === "TimeoutError"
      ? "The AI service is taking too long. Try again in a moment."
      : safeMessages.has(error?.message)
        ? error.message === "KAVACH API token is required."
          ? "Enter your access code to continue."
          : error.message
        : "KAVACH could not finish this check. Try again in a moment.";
    resetPromptResults(message, "error");

  } finally {
    button.disabled = false;
    input.disabled = false;
    promptPanel?.classList.remove("is-scanning");
    button.textContent = "Scan message";
  }
}

$("inp").addEventListener("input", () => {
  resetPromptResults("Message changed. Scan again to update your result.");
});

document.querySelectorAll('input[name="protection-mode"]').forEach(option => {
  option.addEventListener("change", () => {
    resetPromptResults("Mode changed. Scan again to update your result.");
  });
});

$("clear").addEventListener("click", () => {
  $("inp").value = "";
  resetPromptResults("Text cleared.");
  $("inp").focus();
});

$("protect-button").addEventListener("click", protectPrompt);
$("copy-protected").addEventListener("click", copyProtectedPrompt);

// Document scanner
// ------------------------------------------------------------

let isFileScanning = false;

function setFileStatus(message, state = "") {
  const status = $("file-status");
  status.textContent = message;
  status.className = `status-line file-status${state ? ` ${state}` : ""}`;
}

function getFileValidationError(file) {
  const extension = file.name.split(".").pop().toLowerCase();

  if (!["txt", "pdf"].includes(extension)) {
    return "This file type is not supported. Choose a TXT or PDF file.";
  }

  if (file.size > 5 * 1024 * 1024) {
    return "This file is larger than 5 MB. Choose a smaller document.";
  }

  return "";
}

function formatFileSize(size) {
  if (size < 1024) return `${size} bytes`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function clearFileResults() {
  $("file-results").hidden = true;
  $("download-feedback").textContent = "";
  latestMaskedText = "";
  latestFilename = "masked-document.txt";
}

function updateFileSelection() {
  const file = $("file-input").files[0];
  const selection = $("file-selection");

  clearFileResults();

  if (!file) {
    selection.hidden = true;
    setFileStatus("Choose a TXT or PDF file to check.");
    return;
  }

  $("selected-file-name").textContent = file.name;
  $("selected-file-size").textContent = formatFileSize(file.size);
  selection.hidden = false;

  const validationError = getFileValidationError(file);
  if (validationError) {
    setFileStatus(validationError, "status-error");
    return;
  }

  setFileStatus("Document ready to check.", "status-ready");
}

$("file-input").addEventListener("change", updateFileSelection);

$("clear-file").addEventListener("click", () => {
  if (isFileScanning) return;
  $("file-input").value = "";
  updateFileSelection();
});

const uploadDrop = $("upload-drop");

["dragenter", "dragover"].forEach(eventName => {
  uploadDrop.addEventListener(eventName, event => {
    event.preventDefault();
    if (!isFileScanning) uploadDrop.classList.add("is-dragover");
  });
});

["dragleave", "drop"].forEach(eventName => {
  uploadDrop.addEventListener(eventName, event => {
    event.preventDefault();
    uploadDrop.classList.remove("is-dragover");
  });
});

uploadDrop.addEventListener("drop", event => {
  if (isFileScanning) return;
  const file = event.dataTransfer.files[0];

  if (!file) {
    setFileStatus("No file was found. Choose a TXT or PDF document.", "status-error");
    return;
  }

  try {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    $("file-input").files = transfer.files;
    updateFileSelection();
  } catch {
    setFileStatus(
      "This browser could not add the dropped file. Use browse files instead.",
      "status-error"
    );
  }
});

$("file-form").addEventListener("submit", async event => {
  event.preventDefault();

  if (isFileScanning) return;

  const file = $("file-input").files[0];

  if (!file) {
    setFileStatus("Choose a document before checking it.", "status-error");
    return;
  }

  const validationError = getFileValidationError(file);
  if (validationError) {
    setFileStatus(validationError, "status-error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const button = $("scan-file-button");
  isFileScanning = true;
  button.disabled = true;
  $("file-input").disabled = true;
  $("clear-file").disabled = true;
  $("document-scanner").setAttribute("aria-busy", "true");
  $("document-scanner").classList.add("is-scanning");
  $("file-progress").hidden = false;
  $("scan-button-text").textContent = "Checking document…";
  setFileStatus("Scanning your document. This may take a moment…", "status-scanning");
  clearFileResults();

  try {
    const response = await apiFetch("/api/scan-file", {
      method: "POST",
      body: formData,
      signal: AbortSignal.timeout(60000)
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
      const knownMessage = typeof data.detail === "string" ? data.detail : "";
      const friendlyErrors = {
        "Only TXT and PDF files are supported.": "Choose a TXT or PDF document.",
        "File is too large. Maximum size is 5 MB.": "This document is larger than 5 MB. Choose a smaller file.",
        "The uploaded file is empty.": "This file is empty. Choose a document with text.",
        "The TXT file must use UTF-8 text encoding.": "This text file could not be read. Save it as UTF-8 and try again.",
        "The uploaded file does not appear to be a valid PDF.": "This PDF could not be opened. Check the file and try again.",
        "Could not read this PDF. Try a valid, text-based PDF.": "This PDF could not be read. Choose a valid, text-based PDF.",
        "Password-protected PDFs are not supported.": "This PDF is password protected. Choose an unlocked copy.",
        "PDFs are limited to 20 pages.": "This PDF has more than 20 pages. Choose a shorter document.",
        "No readable text found. Scanned-image PDFs need OCR.": "No readable text was found. Scanned-image PDFs are not supported."
      };
      throw new Error(friendlyErrors[knownMessage] || friendlyRequestError(
        response.status,
        "KAVACH could not check this document. Try again in a moment."
      ));
    }

    if (typeof data.masked_text !== "string" || !data.masked_text.trim()) {
      throw new Error("A protected copy could not be prepared. Do not share the original document.");
    }

    const findings = Array.isArray(data.findings) ? data.findings : [];
    const count = Number(data.count ?? findings.length);
    $("file-count").textContent = count === 1
      ? "We found 1 sensitive item."
      : `We found ${count} sensitive items.`;

    const findingsBox = $("file-findings");
    findingsBox.replaceChildren();

    if (!findings.length) {
      const emptyState = document.createElement("p");
      emptyState.className = "findings-empty";
      emptyState.textContent =
        "No supported sensitive data types were detected. Review the protected text before sharing.";
      findingsBox.appendChild(emptyState);
    } else {
      findings.forEach(finding => {
        const item = document.createElement("article");
        item.className = "finding-card";

        const heading = document.createElement("div");
        heading.className = "finding-card-heading";

        const type = document.createElement("strong");
        type.className = "finding-type";
        type.textContent = `${friendlyFindingLabel(finding.type)} detected.`;
        heading.appendChild(type);

        item.appendChild(heading);

        findingsBox.appendChild(item);
      });
    }

    latestMaskedText = data.masked_text || "";

    latestFilename =
      (data.filename || file.name).replace(/\.[^.]+$/, "") +
      "-masked.txt";

    $("file-masked").textContent = latestMaskedText;
    $("file-results").hidden = false;

    setFileStatus(
      "Your protected copy is ready. Review it before sharing.",
      "status-success"
    );

  } catch (error) {
    const safeMessages = new Set([
      "The server returned an unexpected response.",
      "Choose a TXT or PDF document.",
      "This document is larger than 5 MB. Choose a smaller file.",
      "This file is empty. Choose a document with text.",
      "This text file could not be read. Save it as UTF-8 and try again.",
      "This PDF could not be opened. Check the file and try again.",
      "This PDF could not be read. Choose a valid, text-based PDF.",
      "This PDF is password protected. Choose an unlocked copy.",
      "This PDF has more than 20 pages. Choose a shorter document.",
      "No readable text was found. Scanned-image PDFs are not supported.",
      "A protected copy could not be prepared. Do not share the original document.",
      "This is larger than KAVACH can check. Choose a smaller file or shorten your text.",
      "Too many checks in a short time. Wait a minute, then try again.",
      "Your session expired. Check your access code and try again.",
      "KAVACH API token is required.",
      "KAVACH server access needs a browser that supports secure token entry."
    ]);
    const message = safeMessages.has(error.message)
      ? error.message
      : error?.name === "TimeoutError"
        ? "The AI service is taking too long. Try again in a moment."
        : safeMessages.has(error?.message)
          ? error.message === "KAVACH API token is required."
            ? "Enter your access code to continue."
            : error.message
          : "KAVACH could not check this document. Try again in a moment.";
    setFileStatus(message, "status-error");

  } finally {
    isFileScanning = false;
    button.disabled = false;
    $("file-input").disabled = false;
    $("clear-file").disabled = false;
    $("document-scanner").setAttribute("aria-busy", "false");
    $("document-scanner").classList.remove("is-scanning");
    $("file-progress").hidden = true;
    $("scan-button-text").textContent = "Protect document";
  }
});

$("download-masked").addEventListener("click", () => {
  if ($("file-results").hidden) return;

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

  $("download-feedback").textContent =
    "Protected text download started.";

  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

// Pointer-only presentation effects. These never run on touch devices or
// when the user asks the browser to reduce motion.
const reducedMotionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
const finePointerPreference = window.matchMedia("(hover: hover) and (pointer: fine)");

if (finePointerPreference.matches) {
  const reactiveSelector = ".mode-option, .finding-card, .risk-banner, .document-stats > div, .security-card";
  let activeSurface = null;
  let pendingPointer = null;
  let framePending = false;
  const protectButton = $("protect-button");
  const heroVisual = $("hero-visual");
  const appShell = document.querySelector(".app-shell");

  const resetAmbientPointer = () => {
    document.body.style.removeProperty("--pointer-light-x");
    document.body.style.removeProperty("--pointer-light-y");
    appShell?.style.removeProperty("--ambient-parallax-x");
    appShell?.style.removeProperty("--ambient-parallax-y");
  };

  const clearSurface = surface => {
    if (!surface) return;
    surface.classList.remove("pointer-reactive");
    surface.style.removeProperty("--pointer-x");
    surface.style.removeProperty("--pointer-y");
    surface.style.removeProperty("--tilt-x");
    surface.style.removeProperty("--tilt-y");
  };

  document.addEventListener("pointermove", event => {
    if (event.pointerType !== "mouse" || reducedMotionPreference.matches) return;

    const surface = event.target.closest(reactiveSelector);
    if (surface !== activeSurface) {
      clearSurface(activeSurface);
      activeSurface = surface;
      activeSurface?.classList.add("pointer-reactive");
    }

    pendingPointer = {
      surface: activeSurface,
      clientX: event.clientX,
      clientY: event.clientY,
      parallaxX: ((event.clientX / window.innerWidth) - .5) * 8,
      parallaxY: ((event.clientY / window.innerHeight) - .5) * 6
    };

    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(() => {
      framePending = false;
      if (!pendingPointer) return;

      const { surface: current, clientX, clientY, parallaxX, parallaxY } = pendingPointer;
      if (current?.isConnected) {
        const rect = current.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
        current.style.setProperty("--pointer-x", `${(x * 100).toFixed(1)}%`);
        current.style.setProperty("--pointer-y", `${(y * 100).toFixed(1)}%`);
        current.style.setProperty("--tilt-x", `${((x - .5) * 5).toFixed(2)}deg`);
        current.style.setProperty("--tilt-y", `${((.5 - y) * 4).toFixed(2)}deg`);
      }

      const buttonRect = protectButton?.getBoundingClientRect();
      const buttonInside = Boolean(buttonRect && clientX >= buttonRect.left && clientX <= buttonRect.right && clientY >= buttonRect.top && clientY <= buttonRect.bottom);
      if (protectButton && !protectButton.disabled && buttonInside) {
        const buttonX = clientX - (buttonRect.left + buttonRect.width / 2);
        const buttonY = clientY - (buttonRect.top + buttonRect.height / 2);
        protectButton.style.setProperty("--magnetic-x", `${Math.max(-2, Math.min(2, buttonX * .035)).toFixed(2)}px`);
        protectButton.style.setProperty("--magnetic-y", `${Math.max(-2, Math.min(2, buttonY * .035)).toFixed(2)}px`);
      } else if (protectButton) {
        protectButton.style.removeProperty("--magnetic-x");
        protectButton.style.removeProperty("--magnetic-y");
      }

      if (heroVisual) {
        heroVisual.style.setProperty("--hero-parallax-x", `${parallaxX.toFixed(2)}px`);
        heroVisual.style.setProperty("--hero-parallax-y", `${parallaxY.toFixed(2)}px`);
        heroVisual.style.setProperty("--hero-counter-x", `${(parallaxX * -.55).toFixed(2)}px`);
        heroVisual.style.setProperty("--hero-counter-y", `${(parallaxY * -.55).toFixed(2)}px`);
        heroVisual.style.setProperty("--shield-parallax-x", `${(parallaxX * .35).toFixed(2)}px`);
        heroVisual.style.setProperty("--shield-parallax-y", `${(parallaxY * .35).toFixed(2)}px`);
      }
      document.body.style.setProperty("--pointer-light-x", `${((clientX / window.innerWidth) * 100).toFixed(1)}%`);
      document.body.style.setProperty("--pointer-light-y", `${((clientY / window.innerHeight) * 100).toFixed(1)}%`);
      appShell?.style.setProperty("--ambient-parallax-x", `${(parallaxX * .55).toFixed(2)}px`);
      appShell?.style.setProperty("--ambient-parallax-y", `${(parallaxY * .55).toFixed(2)}px`);
    });
  }, { passive: true });

  document.addEventListener("pointerout", event => {
    if (!event.relatedTarget) {
      resetAmbientPointer();
      heroVisual?.style.removeProperty("--hero-parallax-x");
      heroVisual?.style.removeProperty("--hero-parallax-y");
      heroVisual?.style.removeProperty("--hero-counter-x");
      heroVisual?.style.removeProperty("--hero-counter-y");
      heroVisual?.style.removeProperty("--shield-parallax-x");
      heroVisual?.style.removeProperty("--shield-parallax-y");
    }
    if (protectButton?.contains(event.target) && (!event.relatedTarget || !protectButton.contains(event.relatedTarget))) {
      protectButton.style.removeProperty("--magnetic-x");
      protectButton.style.removeProperty("--magnetic-y");
    }
    if (!activeSurface || !activeSurface.contains(event.target)) return;
    if (event.relatedTarget && activeSurface.contains(event.relatedTarget)) return;
    clearSurface(activeSurface);
    activeSurface = null;
    if (protectButton) {
      protectButton.style.removeProperty("--magnetic-x");
      protectButton.style.removeProperty("--magnetic-y");
    }
  });

  window.addEventListener("blur", () => {
    clearSurface(activeSurface);
    activeSurface = null;
    pendingPointer = null;
    resetAmbientPointer();
    protectButton?.style.removeProperty("--magnetic-x");
    protectButton?.style.removeProperty("--magnetic-y");
    heroVisual?.style.removeProperty("--hero-parallax-x");
    heroVisual?.style.removeProperty("--hero-parallax-y");
    heroVisual?.style.removeProperty("--hero-counter-x");
    heroVisual?.style.removeProperty("--hero-counter-y");
    heroVisual?.style.removeProperty("--shield-parallax-x");
    heroVisual?.style.removeProperty("--shield-parallax-y");
  });

  reducedMotionPreference.addEventListener("change", event => {
    if (!event.matches) return;
    clearSurface(activeSurface);
    activeSurface = null;
    pendingPointer = null;
    resetAmbientPointer();
    protectButton?.style.removeProperty("--magnetic-x");
    protectButton?.style.removeProperty("--magnetic-y");
    heroVisual?.style.removeProperty("--hero-parallax-x");
    heroVisual?.style.removeProperty("--hero-parallax-y");
    heroVisual?.style.removeProperty("--hero-counter-x");
    heroVisual?.style.removeProperty("--hero-counter-y");
    heroVisual?.style.removeProperty("--shield-parallax-x");
    heroVisual?.style.removeProperty("--shield-parallax-y");
  });
}

// Autonomous details are shown only inside the optional disclosure.
