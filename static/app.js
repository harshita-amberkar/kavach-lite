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
    const response = await fetch("/api/scan-global", {
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
    const response = await fetch("/api/scan-file", {
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
    const response = await fetch(
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
// Agentic privacy workflow runner
// ------------------------------------------------------------

const agenticButton = $("run-agentic");

if (agenticButton) {
  agenticButton.addEventListener("click", async () => {
    const input = $("inp");
    const status = $("agentic-run-status");
    const results = $("agentic-results");
    const output = $("agentic-output");

    if (!input || !status || !results || !output) {
      return;
    }

    const text = input.value;

    if (!text.trim()) {
      status.textContent =
        "Enter a prompt in the scanner first.";
      return;
    }

    agenticButton.disabled = true;

    status.textContent =
      "Running global detection, AI review, masking and verification...";

    results.hidden = true;

    try {
      const response = await fetch("/api/agentic/scan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text,
          mode: "label"
        })
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
          data.detail || "Agentic workflow failed."
        );
      }

      // Display only the information required by the dashboard.
      // No original prompt or raw sensitive values are displayed
      // as part of the audit-history metadata.
      const display = {
        workflow: data.workflow,
        status: data.status,

        findings: (data.findings || []).map(finding => ({
          type: finding.type,
          confidence: finding.confidence,
          start: finding.start,
          end: finding.end
        })),

        masked_text: data.masked_text,
        risk: data.risk,
        global_detection: data.global_detection,

        agent_review: {
          status: data.agent_review?.status,

          reviews: (
            data.agent_review?.reviews || []
          ).map(review => ({
            assessment: review.assessment,
            reason: review.reason
          }))
        },

        verification: data.verification,
        audit: data.audit,
        requires_human_review: data.requires_human_review,
        steps: data.steps
      };

      output.textContent = JSON.stringify(
        display,
        null,
        2
      );

      results.hidden = false;

      status.textContent =
        `Workflow ${data.status || "finished"}. ` +
        `Audit: ${data.audit?.status || "unknown"}.`;

      // Refresh persisted workflow metadata.
      await loadAgenticHistory();

    } catch (error) {
      status.textContent =
        error.message ||
        "Could not run the agentic workflow.";

    } finally {
      agenticButton.disabled = false;
    }
  });
}