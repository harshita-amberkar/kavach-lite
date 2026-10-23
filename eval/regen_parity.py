import json, shutil
from kavach import scan
from eval.gold import load

P = "extension/tests/parity.json"
shutil.copy(P, P + ".bak")
cases = json.load(open(P, encoding="utf-8"))
have = {c["text"] for c in cases}

extra = [r["text"] for r in load()]
extra += [
    "my aadhaar is 4330-4064-4928",
    "aadhaar number: 726018159082",
    "order id 9876543210 shipped",
    "score 98765 43210 today",
    "call me on 98765 43210",
    "Order ID 726018159082 and aadhaar 4330-4064-4928",
    "ticket: 501661318603",
]
added = 0
for t in extra:
    if t not in have:
        cases.append({"text": t, "expected": []})
        have.add(t)
        added += 1

for c in cases:
    c["expected"] = [[f.type, f.start, f.end] for f in scan(c["text"])]

with open(P, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False)
print(len(cases), "cases written,", added, "added; backup at", P + ".bak")
