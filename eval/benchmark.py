"""Precision / recall on synthetic labelled data. Run: python -m eval.benchmark"""
import random
from kavach import scan
from kavach.detectors import verhoeff_check_digit, gstin_check_char, luhn_valid

random.seed(7)
rd = lambda n: "".join(random.choice("0123456789") for _ in range(n))
up = lambda n: "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))


def aadhaar():
    b = random.choice("23456789") + rd(10)
    a = b + verhoeff_check_digit(b)
    return f"{a[:4]} {a[4:8]} {a[8:]}"


def gstin():
    b = f"{random.randint(1, 37):02d}" + up(3) + "P" + up(1) + rd(4) + up(1) + "1Z"
    return b + gstin_check_char(b)


def card():
    b = "4" + rd(14)
    return next(b + c for c in "0123456789" if luhn_valid(b + c))


GEN = {
    "AADHAAR": (aadhaar, "my aadhaar is {}, please verify"),
    "GSTIN": (gstin, "invoice for GSTIN {} attached"),
    "CARD": (card, "card number {} expiry 09/28"),
    "PAN": (lambda: up(3) + "P" + up(1) + rd(4) + up(1), "PAN {} of the client"),
    "PHONE": (lambda: "+91 " + random.choice("6789") + rd(4) + " " + rd(5), "call me on {} tomorrow"),
    "UPI_ID": (lambda: up(6).lower() + "@" + random.choice(["ybl", "okaxis", "paytm"]), "send to {} today"),
    "IFSC": (lambda: up(4) + "0" + rd(6), "IFSC code {}"),
}
NEG = [f"Order ID {rd(12)} was delivered", f"Ticket #{rd(9)} escalated",
       "Meeting at 10:30 on 12-08-2026", "Total revenue was 1,45,00,000 rupees",
       "Please summarise the attached report", "Version 3.11.4 released", f"Roll no {rd(8)}"]


def run(n=200):
    print(f"{'type':10} {'precision':>9} {'recall':>7}")
    for typ, (gen, tpl) in GEN.items():
        tp = fn = fp = 0
        for _ in range(n):
            found = [f.type for f in scan(tpl.format(gen()))]
            tp += typ in found
            fn += typ not in found
            fp += sum(1 for x in found if x != typ)
        print(f"{typ:10} {tp / max(tp + fp, 1):9.3f} {tp / max(tp + fn, 1):7.3f}")
    neg_fp = sum(len(scan(t)) for t in NEG * 30)
    print(f"false alarms on {len(NEG) * 30} clean sentences: {neg_fp}")


if __name__ == "__main__":
    run()
