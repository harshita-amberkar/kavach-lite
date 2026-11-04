// node extension/tests/policy_and_privacy.js
const fs = require("fs"), path = require("path"), assert = require("assert"), K = require("../detector.js");
// 1) policy decisions
const f = (t) => ({ type: t, start: 0, end: 1 });
assert.strictEqual(K.decide([f("EMAIL")], {}).action, "warn");
assert.strictEqual(K.decide([f("EMAIL"), f("PAN")], {}).action, "warn");
assert.strictEqual(K.decide([f("PAN"), f("CARD")], { CARD: "block" }).action, "block");
assert.strictEqual(K.decide([f("PAN")], { PAN: "mask" }).action, "mask");
assert.strictEqual(K.decide([f("AADHAAR_POSSIBLE")], { AADHAAR: "block" }).action, "warn");
assert.strictEqual(K.decide([f("AADHAAR_POSSIBLE")], { AADHAAR_POSSIBLE: "block" }).action, "block");
assert.strictEqual(K.decide([f("AADHAAR")], { AADHAAR: "block" }).action, "block");
assert.strictEqual(K.mask("pan ABCPE1234F ok", K.scan("pan ABCPE1234F ok")), "pan [PAN] ok");

// The native port keeps parity; the extension scan adds deterministic global rules.
const consistencyCases = require("./detection_consistency.json");
for (const c of consistencyCases) {
  assert.deepStrictEqual(K.scanNative(c.text).map((x) => x.type), c.native_types, c.name);
  assert.deepStrictEqual(K.scan(c.text).map((x) => x.type), c.extension_types, c.name);
}
assert.strictEqual(K.decide([f("US_SSN")], { US_SSN: "block" }).action, "block");
assert.strictEqual(K.decide([f("MEDICAL_INFO")], { MEDICAL_INFO: "mask" }).action, "mask");
assert.strictEqual(K.decide([f("CONFIDENTIAL_BUSINESS")], { CONFIDENTIAL_BUSINESS: "allow" }).action, "allow");
assert.strictEqual(K.decide([f("US_SSN")], {}).action, "warn");
for (const type of ["US_SSN", "MEDICAL_INFO", "CONFIDENTIAL_BUSINESS"]) {
  assert.ok(K.TYPES.includes(type), `${type} appears in extension options`);
}
// 2) privacy: no network-capable code or permissions anywhere in the extension
const dir = path.join(__dirname, "..");
const banned = /\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts)\b|https?:\/\/(?!chatgpt|claude|gemini|chat\.openai)/;
for (const file of fs.readdirSync(dir).filter((x) => /\.(js|html)$/.test(x))) {
  const src = fs.readFileSync(path.join(dir, file), "utf8").replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
  assert.ok(!banned.test(src), `network-capable code in ${file}`);
}
const m = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
assert.deepStrictEqual(m.permissions, ["storage"]);
assert.ok(!m.host_permissions && !m.background, "no host permissions or background worker");
console.log("policy + privacy checks passed");
