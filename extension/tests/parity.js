// This fixture checks only the native Python rules, not Presidio/global additions.
const K = require("../detector.js"), cases = require("./parity.json");
let bad = 0;
for (const c of cases) {
  const got = K.scanNative(c.text).map((f) => [f.type, f.start, f.end]);
  if (JSON.stringify(got) !== JSON.stringify(c.expected)) { if (bad++ < 5) console.log("MISMATCH", JSON.stringify(c.text), "\n  py:", JSON.stringify(c.expected), "\n  js:", JSON.stringify(got)); }
}
console.log(`${cases.length - bad}/${cases.length} identical to Python`);
process.exit(bad ? 1 : 0);
