"""Synthetic labelled prompt generator (en, hi, mr, hinglish, mr-en) with hard negatives.
Only synthetic values are produced: never use real personal data."""
import json, random, re
from kavach.detectors import verhoeff_check_digit, gstin_check_char, luhn_valid

DEVA = str.maketrans("0123456789", "०१२३४५६७८९")
T = {
 "en": ["My Aadhaar number is {AADHAAR}, please verify it.", "Call me on {PHONE} and pay at {UPI_ID}.",
        "Client PAN is {PAN} and GSTIN is {GSTIN}.", "Card {CARD} was declined, email {EMAIL}."],
 "hi": ["मेरा आधार नंबर {AADHAAR} है, कृपया वेरिफाई करें।", "इस नंबर {PHONE} पर कॉल करें और {UPI_ID} पर पैसे भेजें।",
        "क्लाइंट का PAN {PAN} और GSTIN {GSTIN} है।", "कार्ड {CARD} से पेमेंट फेल हुआ, मेल {EMAIL} पर भेजें।"],
 "mr": ["माझा आधार क्रमांक {AADHAAR} आहे, कृपया तपासा.", "{PHONE} वर कॉल करा आणि {UPI_ID} वर पेमेंट पाठवा.",
        "ग्राहकाचा PAN {PAN} आणि GSTIN {GSTIN} फॉर्ममध्ये भरा.", "कार्ड {CARD} ची मुदत संपली, ईमेल {EMAIL} वर कळवा."],
 "hinglish": ["bhai mera aadhaar {AADHAAR} hai, loan form bhar do", "payment {UPI_ID} pe bhejo aur {PHONE} pe call karo",
              "client ka PAN {PAN} aur GSTIN {GSTIN} hai", "card {CARD} decline ho raha hai, mail {EMAIL} pe bhejna"],
 "mr_en": ["Customer cha aadhaar {AADHAAR} aahe, please verify kar", "{UPI_ID} var payment pathva ani {PHONE} la call kara",
           "PAN {PAN} ani GSTIN {GSTIN} form madhe taka", "card {CARD} expire zala, {EMAIL} var mail kara"],
}
NEG = ["Order ID {N12} was dispatched today.", "ticket {N10} escalate karo", "Reference {N16} is invalid.",
       "Meeting on 12-08-2026 at 10:30, budget 1,45,00,000 rupees.", "Please summarise this report in five points.",
       "कृपया यह रिपोर्ट पांच बिंदुओं में समझाएं।", "कृपया हा अहवाल पाच मुद्द्यांत सांगा.", "is code ko optimize karo please",
       "Version 3.11.4 released; roll no {N8}."]

class G:
    def __init__(s, seed): s.r = random.Random(seed)
    def d(s, n): return "".join(s.r.choice("0123456789") for _ in range(n))
    def u(s, n): return "".join(s.r.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))
    def AADHAAR(s):
        b = s.r.choice("23456789") + s.d(10); a = b + verhoeff_check_digit(b)
        return s.r.choice([a, f"{a[:4]} {a[4:8]} {a[8:]}", f"{a[:4]}-{a[4:8]}-{a[8:]}"])
    def PAN(s):
        v = s.u(3) + s.r.choice("PCFHAT") + s.u(1) + s.d(4) + s.u(1)
        return v.lower() if s.r.random() < .12 else v           # lowercase: realistic hard case
    def PHONE(s):
        n = s.r.choice("6789") + s.d(9)
        return s.r.choice([n, "+91 " + n[:5] + " " + n[5:], "+91-" + n, n[:5] + "-" + n[5:], "0" + n])
    def CARD(s):
        b = "4" + s.d(14); c = next(c for c in "0123456789" if luhn_valid(b + c)); n = b + c
        return s.r.choice([n, " ".join(n[i:i + 4] for i in range(0, 16, 4))])
    def UPI_ID(s): return s.u(s.r.randint(4, 8)).lower() + s.r.choice(["", ".", "_"]) + s.d(s.r.randint(0, 3)) + "@" + s.r.choice(["ybl", "okaxis", "paytm", "oksbi", "ibl"])
    def GSTIN(s):
        b = f"{s.r.randint(1, 37):02d}" + s.u(3) + "P" + s.u(1) + s.d(4) + s.u(1) + "1Z"; return b + gstin_check_char(b)
    def EMAIL(s): return s.u(5).lower() + s.r.choice([".", "_"]) + s.u(4).lower() + "@" + s.r.choice(["gmail.com", "acme.in", "corp.co.in"])
    def N(s, k): return s.d(k) if k != 12 else str(s.r.randint(1, 1)) + s.d(11)  # starts with 1: never a valid Aadhaar

def fill(tpl, g, lang):
    out, ents, pos = "", [], 0
    for m in re.finditer(r"\{([A-Z_0-9]+)\}", tpl):
        out += tpl[pos:m.start()]; k = m.group(1)
        if k.startswith("N") and k[1:].isdigit(): v = g.N(int(k[1:])); typ = None
        else:
            v = getattr(g, k)(); typ = k
            if lang in ("hi", "mr", "hinglish") and typ in ("AADHAAR", "PHONE", "CARD") and g.r.random() < .3: v = v.translate(DEVA)
        if typ: ents.append({"type": typ, "start": len(out), "end": len(out) + len(v)})
        out += v; pos = m.end()
    return out + tpl[pos:], ents

def generate(n=600, seed=42, neg_ratio=.3):
    g, rows = G(seed), []
    for i in range(n):
        if g.r.random() < neg_ratio:
            lang, tpl = "neg", g.r.choice(NEG)
        else:
            lang = g.r.choice(list(T)); tpl = g.r.choice(T[lang])
        text, ents = fill(tpl, g, lang)
        rows.append({"id": i, "lang": lang, "text": text, "entities": ents, "split": "test" if g.r.random() < .3 else "dev"})
    return rows

if __name__ == "__main__":
    import sys
    rows = generate(); open(sys.argv[1] if len(sys.argv) > 1 else "dataset.jsonl", "w", encoding="utf-8").write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    print(len(rows), "rows")
