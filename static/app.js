const SAMPLES = [
  "Customer Demo User (demo.user@example.com, +91 90000 00000) says refund of Rs 4,500 failed. Please reply. Pay them on demo@okaxis. IFSC HDFC0001234.",
  "Bhai mera PAN ABCPE1234F hai aur आधार नंबर २३४५ ६७८९ ०१२३ hai, loan form bhar do.",
  "const client = new S3({accessKeyId: '<AWS_ACCESS_KEY_ID_PLACEHOLDER>'});\nconst api_key = 'DEMO_API_KEY_PLACEHOLDER';\nconst password = 'DEMO_PASSWORD_PLACEHOLDER';\n// why does upload fail?"
];

const $ = id => document.getElementById(id);
let timer;
let latestMaskedText = "";
let latestFilename = "masked-document.txt";

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
    $("out").appendChild(document.createTextNode(text.slice(last, match.index)));
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = match[0];
    $("out").appendChild(chip);
    last = pattern.lastIndex;
  }
  $("out").appendChild(document.createTextNode(text.slice(last)));
}

function renderPromptRows(findings) {
  const rows = $("rows");
  rows.replaceChildren();

  if (!findings.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 3;
    td.className = "empty";
    td.textContent = "Nothing detected. No supported sensitive patterns were found.";
    tr.appendChild(td);
    rows.appendChild(tr);
    return;
  }

  findings.forEach(f => {
    const tr = document.createElement("tr");
    [f.type, `${f.start}-${f.end}`, `${Math.round((f.confidence || 0) * 100)}%`].forEach(value => {
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
    const response = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!response.ok) throw new Error("Scan request failed.");
    const data = await response.json();
    renderMaskedPrompt(data.masked_text || "");

    const level = data.risk?.level || "none";
    $("level").className = "level " + level;
    $("level").textContent = level === "none"
      ? "No risk found"
      : level.charAt(0).toUpperCase() + level.slice(1) + " risk";

    const findings = data.findings || [];
    $("score").textContent = `${findings.length} item(s) detected`;
    renderPromptRows(findings);
  } catch (error) {
    $("out").textContent = "Could not reach the Kavach server. Check that it is running and try again.";
    $("out").className = "out empty";
    $("level").className = "level high";
    $("level").textContent = "Scan unavailable";
    $("score").textContent = "Check that the Kavach server is running.";
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

$("file-form").addEventListener("submit", async event => {
  event.preventDefault();
  const file = $("file-input").files[0];

  if (!file) {
    $("file-status").textContent = "Please choose a file first.";
    return;
  }
  const extension = file.name.split(".").pop().toLowerCase();
  if (!["txt", "pdf"].includes(extension)) {
    $("file-status").textContent = "Only TXT and PDF files are supported.";
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    $("file-status").textContent = "The file exceeds the 5 MB limit.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  const button = $("scan-file-button");
  button.disabled = true;
  button.textContent = "Scanning…";
  $("file-status").textContent = "Scanning your document…";
  $("file-results").hidden = true;

  try {
    const response = await fetch("/api/scan-file", { method: "POST", body: formData });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("The server returned an unexpected response.");
    }
    if (!response.ok) throw new Error(data.detail || "Document scanning failed.");

    $("file-name").textContent = data.filename || file.name;
    $("file-pages").textContent = data.page_count == null
      ? "Not applicable (TXT file)"
      : String(data.page_count);
    $("file-count").textContent = String(data.count ?? (data.findings || []).length);

    const risk = data.risk || {};
    $("file-risk").textContent = `${risk.level || "unknown"} (score: ${risk.score ?? "N/A"})`;

    const findingsBox = $("file-findings");
    findingsBox.replaceChildren();
    const findings = data.findings || [];

    if (!findings.length) {
      findingsBox.textContent = "No supported sensitive patterns were detected.";
    } else {
      findings.forEach(finding => {
        const item = document.createElement("p");
        const confidence = typeof finding.confidence === "number"
          ? ` · Confidence: ${Math.round(finding.confidence * 100)}%`
          : "";
        item.textContent = `${finding.type || "Finding"} · Positions ${finding.start ?? "?"}-${finding.end ?? "?"}${confidence}`;
        findingsBox.appendChild(item);
      });
    }

    latestMaskedText = data.masked_text || "";
    latestFilename = (data.filename || file.name).replace(/\.[^.]+$/, "") + "-masked.txt";
    $("file-masked").textContent = latestMaskedText;
    $("file-results").hidden = false;
    $("file-status").textContent = "Document scan completed successfully.";
  } catch (error) {
    $("file-status").textContent = error.message || "Could not scan the document. Please try again.";
  } finally {
    button.disabled = false;
    button.textContent = "Scan document";
  }
});

$("download-masked").addEventListener("click", () => {
  const blob = new Blob([latestMaskedText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = latestFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
