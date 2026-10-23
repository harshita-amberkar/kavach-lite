"""Print valid-looking FAKE values to paste into your gold file.  python -m eval.fake"""
import random, sys
from .gen import G
g = G(random.randrange(10**6))
for t in ("AADHAAR", "PAN", "PHONE", "CARD", "UPI_ID", "GSTIN", "EMAIL"):
    print(f"{t:8}", getattr(g, t)())
