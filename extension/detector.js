/* Browser-local native detector port plus selected deterministic global rules. */
(function (root) {
  const D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]];
  const P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]];
  const GST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const digits = (s) => s.replace(/\D/g, "");
  function verhoeff(n) { let c = 0; const r = [...n].reverse(); for (let i = 0; i < r.length; i++) c = D[c][P[i % 8][+r[i]]]; return c === 0; }
  function luhn(n) { let t = 0; const r = [...n].reverse(); for (let i = 0; i < r.length; i++) { let v = +r[i]; if (i % 2 === 1) v = v > 4 ? v * 2 - 9 : v * 2; t += v; } return t % 10 === 0; }
  function gstinCheck(f) { let t = 0; for (let i = 0; i < 14; i++) { const v = GST.indexOf(f[i]) * (i % 2 === 0 ? 1 : 2); t += Math.floor(v / 36) + (v % 36); } return GST[(36 - (t % 36)) % 36]; }

  const UPI = "ybl|ibl|axl|okhdfcbank|okicici|okaxis|oksbi|paytm|apl|upi|sbi|hdfcbank|icici|axisbank|pnb|barodampay|kotak|indus|fbl|airtel|jio|postbank";
  const CTX = /aadhaar|aadhar|adhar|uidai|\buid\b|आधार/i;
  const AAD = String.raw`(?<!\d)(?<!\d[\s-])[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)(?![\s-]\d{4}(?!\d))`;

  // Mirrors _PHONE_NEGATIVE_CTX in detectors.py: suppress phone matches labelled as score/order/reference/transaction numbers.
  const PHONE_NEG = /(?:\bscore\b[^.!?\n]{0,25}|\border\s*(?:id|number|no\.?)?\s*[:#-]?\s*|\breference\s*(?:id|number|no\.?)?\s*[:#-]?\s*|\btransaction\s*(?:id|number|no\.?)?\s*[:#-]?\s*)$/i;
  // Mirrors _AADHAAR_NEGATIVE_CTX in detectors.py: a checksum-valid 12-digit number right after these words,
  // with no Aadhaar context nearby, a checksum-valid number after these
  // business labels is suppressed, matching the native Python detector.
  const AAD_NEG_EXTRA = /\b(?:batch|timestamp|time\s+stamp|build|run|job|sequence|serial)\b\s*(?:(?:id|number|num|no\.?)\s*)?[:#-]?\s*$/i;
  const PLACEHOLDER_SECRET = /(?:\b(?:redacted|placeholder|dummy|changeme|replace[_-]?me)\b|\b(?:your|insert)[_-]?(?:api[_-]?)?key\b)/i;
  const GLOBAL_SECRET_RULES = [
    ["API_KEY", /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----/gi, 0.99],
    ["API_KEY", /\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|mssql|sqlserver):\/\/[^\s"'`<>]+/gi, 0.98],
    ["API_KEY", /\b(?:authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/-]+=*/gi, 0.98],
    ["API_KEY", /\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b/g, 0.98],
  ];
  const GLOBAL_SSN = /\b(?:SSN|social security(?: number| no\.?)?)\s*(?:is\s*)?[:#=]?\s*(\d{3}[- ]\d{2}[- ]\d{4})\b/gi;
  const GLOBAL_CONTEXT_RULES = [
    ["MEDICAL_INFO", /\b(?:the\s+)?(?:patient|i|he|she|they)\s+(?:has|have|had|was diagnosed with|were diagnosed with|suffers from|is taking|are taking|takes|take)\b[^.!?\n]{0,120}\b(?:diabetes|metformin|hypertension|cancer|asthma|HIV|depression|anxiety|arthritis|epilepsy|medication|prescription|diagnosis|medical history|blood pressure|lab results?)\b[^.!?\n]*[.!?]?/gi, 0.80],
    ["CONFIDENTIAL_BUSINESS", /\b(?:our|the)\s+(?:fictional\s+)?company\b[^.!?\n]{0,150}\b(?:confidential|non-public|unannounced|proprietary|trade secret|customer list|product roadmap|layoff plan|source code)\b[^.!?\n]*[.!?]?/gi, 0.80],
  ];
  const AAD_NEG = /(?:\b(?:order|po|purchase\s+order|ticket|reference|ref|tracking|consignment|invoice|transaction|txn|awb|case)\b|ऑर्डर|ट्रैकिंग|टिकट)\s*(?:(?:id|number|num|no\.?|क्रमांक|नंबर)\s*)?[:#\-]?\s*$/i;

  const RULES = [ // [name, regex, flags, priority, check(raw, text, start), confidence]
    ["AADHAAR", AAD, "", 1, (r) => verhoeff(digits(r)), 0.98],
    ["GSTIN", String.raw`\b(?:0[1-9]|[12]\d|3[0-8])[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b`, "", 1, (r) => gstinCheck(r.slice(0, 14)) === r[14], 0.97],
    ["API_KEY", String.raw`\bAKIA[0-9A-Z]{16}\b|\bsk-[A-Za-z0-9_\-]{20,}|\bgh[pousr]_[A-Za-z0-9]{36,}`, "", 1, null, 0.95],
    ["API_KEY", String.raw`\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*(?:"[^"\r\n]{8,}"|'[^'\r\n]{8,}'|[^\s'"\x60]{8,})`, "i", 1, null, 0.85],
    ["CARD", String.raw`(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)`, "", 2, (r) => { const d = digits(r); return d.length >= 13 && d.length <= 19 && luhn(d); }, 0.95],
    ["PAN", String.raw`\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b`, "i", 2, null, 0.92],
    ["UPI_ID", String.raw`(?<![\w.\-@])[\w.\-]{2,64}@(?:${UPI})(?![\w\-]|\.[a-z])`, "i", 3, null, 0.93],
    ["IFSC", String.raw`\b[A-Z]{4}0[A-Z0-9]{6}\b`, "", 3, null, 0.88],
    ["EMAIL", String.raw`[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}`, "", 4, null, 0.97],
    ["PHONE", String.raw`(?<![\d])(?:\+91[\-\s]?|91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}(?!\d)`, "", 5, null, 0.85],
    ["AADHAAR_POSSIBLE", AAD, "", 6, (r, t, s) => CTX.test(t.slice(Math.max(0, s - 40), s)), 0.6],
    ["PASSWORD", String.raw`\b(?:password|passcode|passwd|pwd|pin)\s+(?:is|was)\s+[^\s,;]{4,}`, "i", 1, (r) => /[\d@#$%^&*!_]/.test(r.trim().split(/\s+/).pop()), 0.8],
    ["OTP", String.raw`\b(?:otp|verification code|one[- ]time (?:password|passcode|code))\s*(?:is|was|=|:)?\s*\d{4,8}(?!\d)`, "i", 1, null, 0.85],
    ["PASSPORT", String.raw`\bpassport(?:\s*(?:no\.?|number|num|#))?\s*(?:is|:|=)?\s*[A-Z]\d{7}\b`, "i", 1, null, 0.85],
  ].map(([n, rx, fl, p, c, conf]) => ({ n, rx: new RegExp(rx, "g" + fl), p, c, conf }));
  const WEIGHT = { AADHAAR: 40, CARD: 40, API_KEY: 40, PAN: 30, GSTIN: 20, UPI_ID: 15, AADHAAR_POSSIBLE: 15, PHONE: 10, EMAIL: 8, IFSC: 5, PASSWORD: 40, OTP: 30, PASSPORT: 30, US_SSN: 30, MEDICAL_INFO: 30, CONFIDENTIAL_BUSINESS: 25 };

  function scanNative(text) {
    const t = text.replace(/[\u0966-\u096F]/g, (c) => String(c.charCodeAt(0) - 0x966)); // Devanagari digits, 1:1
    const hits = [];
    for (const r of RULES) {
      r.rx.lastIndex = 0;
      for (const m of t.matchAll(r.rx)) {
        if (m[0].length === 0) continue;
        if (r.c && !r.c(m[0], t, m.index)) continue;
        if (r.n === "API_KEY" && PLACEHOLDER_SECRET.test(m[0])) continue;
        let n = r.n, conf = r.conf;
        const ctx = t.slice(Math.max(0, m.index - 40), m.index);
        if (n === "PHONE" && PHONE_NEG.test(ctx)) continue;
        if (n === "AADHAAR" && (AAD_NEG.test(ctx) || AAD_NEG_EXTRA.test(ctx)) && !CTX.test(ctx)) continue;
        hits.push({ p: r.p, len: -m[0].length, s: m.index, e: m.index + m[0].length, n, conf });
      }
    }
    hits.sort((a, b) => a.p - b.p || a.len - b.len || a.s - b.s || a.e - b.e || (a.n < b.n ? -1 : a.n > b.n ? 1 : 0));
    const kept = [];
    for (const h of hits) if (kept.every((k) => h.e <= k.start || h.s >= k.end)) kept.push({ type: h.n, start: h.s, end: h.e, confidence: h.conf });
    return kept.sort((a, b) => a.start - b.start);
  }
  function scan(text) {
    const findings = [];
    const add = (type, start, end, confidence) => {
      if (start >= 0 && end > start && !findings.some((f) => start < f.end && end > f.start)) {
        findings.push({ type, start, end, confidence });
      }
    };

    for (const [type, rx, confidence] of GLOBAL_SECRET_RULES) {
      rx.lastIndex = 0;
      for (const match of text.matchAll(rx)) add(type, match.index, match.index + match[0].length, confidence);
    }

    GLOBAL_SSN.lastIndex = 0;
    for (const match of text.matchAll(GLOBAL_SSN)) {
      const start = match.index + match[0].lastIndexOf(match[1]);
      add("US_SSN", start, start + match[1].length, 0.99);
    }

    for (const finding of scanNative(text)) {
      const before = text.slice(Math.max(0, finding.start - 80), finding.start);
      const businessId = /\b(?:order|tracking|consignment|reference|ref|invoice|ticket|shipment|awb|waybill|parcel)\s*(?:id|no\.?|number|#)\s*[:#-]?\s*$/i.test(before);
      if (finding.type === "PHONE" && businessId) continue;
      add(finding.type, finding.start, finding.end, finding.confidence);
    }

    for (const [type, rx, confidence] of GLOBAL_CONTEXT_RULES) {
      rx.lastIndex = 0;
      for (const match of text.matchAll(rx)) add(type, match.index, match.index + match[0].length, confidence);
    }

    return findings.sort((a, b) => a.start - b.start || a.end - b.end);
  }

  function mask(text, findings, mode) {
    let out = text;
    for (const f of [...findings].sort((a, b) => b.start - a.start)) {
      let rep = `[${f.type}]`;
      if (mode === "partial" && ["AADHAAR", "CARD", "PHONE"].includes(f.type)) { const d = digits(text.slice(f.start, f.end)); rep = "X".repeat(Math.max(d.length - 4, 0)) + d.slice(-4); }
      out = out.slice(0, f.start) + rep + out.slice(f.end);
    }
    return out;
  }
  function risk(fs) { const score = Math.min(100, fs.reduce((a, f) => a + (WEIGHT[f.type] || 5), 0)); return { score, level: score >= 40 ? "high" : score >= 15 ? "medium" : score ? "low" : "none" }; }

  // ---- policy: allow < warn < mask < block, strictest finding wins ----
  // AADHAAR_POSSIBLE (warn tier) now has its own policy row and defaults to "warn",
  // so a downgraded look-alike is no longer blocked just because Aadhaar is set to Block.
  const ORDER = { allow: 0, warn: 1, mask: 2, block: 3 };
  const DEFAULT_POLICY = { EMAIL: "warn", IFSC: "allow", AADHAAR_POSSIBLE: "warn" };
  const key = (t) => t;
  function decide(findings, policy) {
    const items = []; let action = "allow";
    for (const f of findings) {
      const a = (policy && policy[key(f.type)]) || DEFAULT_POLICY[key(f.type)] || "warn";
      if (a === "allow") continue;
      items.push(f); if (ORDER[a] > ORDER[action]) action = a;
    }
    return { action, items };
  }
  const api = { scan, scanNative, mask, risk, decide, TYPES: Object.keys(WEIGHT) };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Kavach = api;
})(typeof self !== "undefined" ? self : globalThis);
