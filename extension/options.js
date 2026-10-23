const ACTIONS = { allow: "Allow", warn: "Warn me", mask: "Mask automatically", block: "Block" };
const DEFAULTS = { EMAIL: "warn", IFSC: "allow" };
chrome.storage.sync.get("policy", ({ policy = {} }) => {
  const t = document.getElementById("t");
  Kavach.TYPES.filter((x) => x !== "AADHAAR_POSSIBLE").forEach((type) => {
    const tr = document.createElement("tr"), td1 = document.createElement("td"), td2 = document.createElement("td"), sel = document.createElement("select");
    td1.textContent = type.replace("_", " "); sel.id = type; sel.setAttribute("aria-label", type);
    for (const [v, l] of Object.entries(ACTIONS)) { const o = new Option(l, v); sel.add(o); }
    sel.value = policy[type] || DEFAULTS[type] || "warn";
    td2.appendChild(sel); tr.append(td1, td2); t.appendChild(tr);
  });
});
document.getElementById("save").onclick = () => {
  const policy = {}; document.querySelectorAll("select").forEach((s) => (policy[s.id] = s.value));
  chrome.storage.sync.set({ policy }, () => { document.getElementById("s").textContent = "Saved"; setTimeout(() => (document.getElementById("s").textContent = ""), 2000); });
};
