"""Offline-Parser-Test fuer den marktguru-Adapter. python tests/test_marktguru.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.marktguru import parse_offers  # noqa: E402
from core.discount import qualifies  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "marktguru_offers.json")
_fail = 0


def fail(m):
    global _fail
    _fail += 1
    print("  FAIL:", m)


payload = json.load(open(FIX, encoding="utf-8"))
offers = parse_offers(payload)
print(f"{len(offers)} Offers aus {len(payload['results'])} rohen geparst")

if not offers:
    fail("keine Offers")

for o in offers:
    if not o.product:
        fail("leeres Produkt")
    if not o.store:
        fail("leerer Store")
    if o.amount is None:
        fail(f"keine Menge: {o.product}")
    if o.effective_pct is None or o.effective_pct < 0:
        fail(f"Rabatt fehlt: {o.product}")
    if o.valid_to is None:
        fail(f"valid_to fehlt: {o.product}")
    if o.price is not None and o.old_price is not None and o.old_price < o.price:
        fail(f"old < price: {o.product}")

# Grundpreis: referencePrice sollte oft uebernommen sein
with_bp = sum(1 for o in offers if o.base_price_label)
print(f"davon mit Grundpreis: {with_bp}")

# ueber 30% gefiltert
good = [o for o in offers if o.effective_pct >= 30]
print(f"davon >= 30%: {len(good)}")

print("\nBeispiele (>=30%):")
for o in sorted(good, key=lambda x: -x.effective_pct)[:6]:
    print(f"  −{o.effective_pct:.0f}% | {o.store} | {o.product} | {o.menge_label} | "
          f"{o.price}€ statt {o.old_price}€ | {o.base_price_label or '-'} | bis {o.valid_to}"
          f"{' | jö/App' if o.needs_card else ''}")

print(f"\n{'FEHLER' if _fail else 'OK'}: {_fail} Fehler")
sys.exit(1 if _fail else 0)
