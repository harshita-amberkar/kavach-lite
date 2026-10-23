// node extension/tests/parity.js  -> the JS port must match the Python detector exactly
const K = require("../detector.js"), cases = require("./parity.json");
let bad = 0;
for (const c of cases) {
  const got = K.scan(c.text).map((f) => [f.type, f.start, f.end]);
  if (JSON.stringify(got) !== JSON.stringify(c.expected)) { if (bad++ < 5) console.log("MISMATCH", JSON.stringify(c.text), "\n  py:", JSON.stringify(c.expected), "\n  js:", JSON.stringify(got)); }
}
console.log(`${cases.length - bad}/${cases.length} identical to Python`);
process.exit(bad ? 1 : 0);
