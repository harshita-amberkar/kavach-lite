// --------------------------------------------------
// KAVACH local API authentication
// --------------------------------------------------

const KAVACH_TOKEN_KEY = "kavachApiToken";

async function getKavachApiToken() {
  let token = sessionStorage.getItem(KAVACH_TOKEN_KEY);

  if (!token) {
    const dialog = $("token-dialog");
    const form = $("token-form");
    const input = $("token-input");
    const cancel = $("token-cancel");
    if (!dialog || !form || !input || !cancel || typeof dialog.showModal !== "function") {
      throw new Error("KAVACH server access needs a browser that supports secure token entry.");
    }

    token = await new Promise(resolve => {
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

    if (!token) {
      throw new Error("KAVACH API token is required.");
    }

    return token;
  }

  return token;
}

async function apiFetch(url, options = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const headers = new Headers(options.headers || {});
    headers.set("X-KAVACH-Token", await getKavachApiToken());

    setHeroScanning(true);
    let response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
        signal: AbortSignal.timeout(60000)
      });
    } finally {
      setHeroScanning(false);
    }

    if (response.status === 401) {
      // A local server restart can rotate a generated session token.
      sessionStorage.removeItem(KAVACH_TOKEN_KEY);
      if (attempt === 1) {
        throw new Error("Your session expired. Check your access code and try again.");
      }
      continue;
    }

    return response;
  }
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

const SAMPLES = [
  "Customer Demo User (demo.user@example.com, +91 90000 00000) says refund of Rs 4,500 failed. Please reply. Pay them on demo@okaxis. IFSC HDFC0001234.",
  "Bhai mera PAN ABCPE1234F hai aur आधार नंबर २३४५ ६७८९ ०१२३ hai, loan form bhar do.",
  "const client = new S3({accessKeyId: '<AWS_ACCESS_KEY_ID_PLACEHOLDER>'});\nconst api_key = 'DEMO_API_KEY_PLACEHOLDER';\nconst password = 'DEMO_PASSWORD_PLACEHOLDER';\n// why does upload fail?"
];

const $ = id => document.getElementById(id);
let activeScanCount = 0;

function setHeroScanning(active) {
  activeScanCount = Math.max(0, activeScanCount + (active ? 1 : -1));
  $("hero-visual")?.classList.toggle("is-scanning", activeScanCount > 0);
}

async function refreshBackendHealth() {
  const indicator = $("backend-health");
  const label = $("backend-health-label");
  if (!indicator || !label) return;

  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const data = response.ok ? await response.json() : null;
    const healthy = data && data.status === "ok";
    indicator.dataset.state = healthy ? "online" : "unavailable";
    if (!healthy) {
      label.textContent = "KAVACH is unavailable";
      return;
    }
    const databaseReady = data.database === "available";
    const assistant = data.ollama?.status === "disabled"
      ? "Local AI assistant optional"
      : data.ollama?.status !== "available"
        ? "Local AI assistant is offline"
        : data.ollama.model_available
          ? "Local AI assistant ready"
          : "Local AI assistant needs setup";
    indicator.dataset.state = databaseReady ? "online" : "warning";
    label.textContent = `${databaseReady ? "KAVACH ready · Secure storage ready" : "Secure storage unavailable"} · ${assistant}`;
  } catch {
    indicator.dataset.state = "unavailable";
    label.textContent = "KAVACH is unavailable";
  }
}

refreshBackendHealth();
window.setInterval(refreshBackendHealth, 30000);

document.addEventListener("DOMContentLoaded", () => {
  const navLinks = Array.from(document.querySelectorAll(".nav-link[href^='#']"));
  const sections = navLinks.map(link => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    navLinks.forEach(link => link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`));
    const breadcrumb = document.querySelector(".breadcrumbs strong");
    if (breadcrumb) breadcrumb.textContent = visible.target.id === "scan"
      ? "Protect"
      : visible.target.id === "security" ? "Settings" : "Help & Extensions";
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
    "Your protected copy will appear here after checking.";
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
    title.textContent = friendlyFindingLabel(finding.type);
    content.append(title);
    card.append(icon, content);
    rows.appendChild(card);
  });
}

function resetPromptResults(message = "Your text has not been protected yet.") {
  showPromptPlaceholder();
  const resultPanel = document.querySelector(".result-panel");
  resultPanel?.classList.remove("has-result");
  resultPanel?.removeAttribute("data-risk");
  renderPromptRows([]);
  $("copy-protected").disabled = true;
  $("protection-status").textContent = message;
  $("protection-summary").hidden = true;
  const findingsSummary = document.querySelector(".findings-details summary");
  if (findingsSummary) findingsSummary.textContent = "View what was found";
}

function renderProtectionResult(data) {
  const findings = Array.isArray(data.findings)
    ? data.findings
    : [];
  const maskedText = typeof data.masked_text === "string"
    ? data.masked_text
    : "";

  renderMaskedPrompt(maskedText);

  const resultPanel = document.querySelector(".result-panel");
  resultPanel?.classList.add("has-result");
  resultPanel?.removeAttribute("data-risk");

  renderPromptRows(findings);
  $("copy-protected").disabled = !maskedText;

  const findingsSummary =
    document.querySelector(".findings-details summary");
  if (findingsSummary) {
    findingsSummary.textContent = `View what was found (${findings.length})`;
  }

  $("copy-feedback") &&
    ($("copy-feedback").textContent = "");
}

function renderProtectionSummary(data, mode) {
  const findings = Array.isArray(data.findings) ? data.findings : [];
  const autonomous = mode === "autonomous";
  const verification = data.verification && typeof data.verification === "object"
    ? String(data.verification.status || "").toLowerCase()
    : "not_reported";
  const needsReview = autonomous && (
    verification !== "passed" || data.requires_human_review === true
  );
  const globalDetection = data.global_detection && typeof data.global_detection === "object"
    ? data.global_detection
    : null;

  let title = findings.length
    ? "Your information is protected"
    : "Your check is complete";
  let message = findings.length
    ? `Your information is protected. KAVACH found ${findings.length} sensitive item${findings.length === 1 ? "" : "s"} and prepared a copy for you to review.`
    : "KAVACH did not find supported sensitive information. It can miss items, so review the text before sharing.";
  let statusLabel = findings.length ? "Ready to review" : "No findings";
  let statusKind = "neutral";

  if (needsReview) {
    title = "Please review your protected copy";
    message = "This scan needs a careful human check. Review the findings and protected text before sharing.";
    statusLabel = "Review needed";
    statusKind = "warning";
  } else if (findings.length) {
    statusKind = "success";
  }

  if (globalDetection && String(globalDetection.status || "").toLowerCase() === "unavailable") {
    message += " Some checks were unavailable, so review the protected text carefully.";
    statusLabel = "Review carefully";
    statusKind = "warning";
  }

  const review = data.agent_review && typeof data.agent_review === "object"
    ? data.agent_review
    : {};
  const reviewUnavailable = String(review.status || "").toLowerCase() === "unavailable";
  if (reviewUnavailable) {
    message += review.reason === "timeout"
      ? " The local AI assistant is taking too long; your scan and masking are complete."
      : " The local AI assistant is offline; your scan and masking are complete.";
  }

  $("protection-summary-title").textContent = title;
  $("protection-summary-message").textContent = message;
  $("protection-summary-count").textContent = String(findings.length);
  const badge = $("protection-summary-status");
  badge.textContent = statusLabel;
  badge.className = `protection-summary-badge ${statusKind}`;

  const agentStatus = $("agent-review-status");
  const reviewCompleted = String(review.status || "").toLowerCase() === "ok";
  agentStatus.hidden = !reviewCompleted;
  if (reviewCompleted) {
    $("agent-review-message").textContent = "An optional AI review is complete. Check the protected text yourself before sharing.";
    $("agent-review-badge").textContent = "Completed";
    $("agent-review-badge").className = "agent-review-badge success";
  }

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
      "Protected text copied. Review it before pasting into your AI tool.";
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
      ? "Protected text copied. Review it before pasting into your AI tool."
      : "Copy was blocked. Select the protected text and copy it manually.";
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
  status.textContent = "Checking your text...";

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
      throw new Error(friendlyRequestError(
        response.status,
        "KAVACH could not finish this check. Try again in a moment."
      ));
    }

    renderProtectionResult(data);
    renderProtectionSummary(data, mode);

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
    resetPromptResults(message);

  } finally {
    button.disabled = false;
    input.disabled = false;
    promptPanel?.classList.remove("is-scanning");
    button.textContent = "Check & Protect";
  }
}

$("inp").addEventListener("input", () => {
  resetPromptResults("Text changed. Select Check & Protect to continue.");
});

document.querySelectorAll("[data-s]").forEach(button => {
  button.addEventListener("click", () => {
    $("inp").value = SAMPLES[Number(button.dataset.s)];
    resetPromptResults("Sample loaded. Select Check & Protect to continue.");
    $("inp").focus();
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

    const findings = Array.isArray(data.findings) ? data.findings : [];
    $("file-count").textContent = `Sensitive items found: ${Number(data.count ?? findings.length)}`;

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
        type.textContent = friendlyFindingLabel(finding.type);
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
