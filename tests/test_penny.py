"""Offline-Parser-Test fuer den PENNY-Adapter (gespeicherte Fixture).
python tests/test_penny.py
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.penny import parse_products  # noqa: E402
from sources.rewe_shop import _iso_date  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "penny_promo.json")
_fail = 0


def fail(m):
    global _fail
    _fail += 1
    print("  FAIL:", m)


payload = json.load(open(FIX, encoding="utf-8"))
valid_to = date(2026, 8, 29)
offers = parse_products(payload, valid_to)
print(f"{len(offers)} Offers aus {len(payload['results'])} Produkten geparst")

if not offers:
    fail("keine Offers geparst")

for o in offers:
    if not o.product:
        fail("leeres Produkt")
    if o.store != "PENNY":
        fail(f"falscher Store: {o.store}")
    if o.amount is None:
        fail(f"keine Menge: {o.product}")
    if o.effective_pct is None or o.effective_pct <= 0:
        fail(f"kein Rabatt: {o.product}")
    if o.valid_to is None:
        fail(f"valid_to fehlt: {o.product}")
    if o.price is not None and o.base_price_label is None:
        fail(f"kein Grundpreis trotz Preis: {o.product}")
    if o.url and not o.url.startswith("https://www.penny.at/"):
        fail(f"falsche URL: {o.url}")
    if o.requires_qty > 1 and not o.is_multi:
        fail(f"is_multi fehlt bei qty={o.requires_qty}: {o.product}")
    # Preis/Rabatt muessen zueinander passen
    if o.price and o.old_price:
        calc = 100 * (o.old_price - o.price) / o.old_price
        if abs(calc - o.effective_pct) > 1.5:
            fail(f"Rabatt inkonsistent: {o.product} {o.effective_pct}% vs {calc:.1f}%")


# PENNY liefert echte Aktionsdaten (validityStart/End) - die muessen gewinnen,
# das Wochenfenster ist nur der Rueckfall. Erwartung je Produkt nachrechnen.
expected = {}
for prod in payload["results"]:
    pr = prod.get("price") or {}
    if pr.get("discountPercentage"):
        expected[prod["name"]] = (_iso_date(pr.get("validityStart")),
                                  _iso_date(pr.get("validityEnd")))
n_real = 0
for o in offers:
    want_from, want_to = expected.get(o.product, (None, None))
    if want_to is not None:
        n_real += 1
        if o.valid_to != want_to:
            fail(f"echtes validityEnd ignoriert: {o.product} {o.valid_to} != {want_to}")
        if want_from is not None and o.valid_from != want_from:
            fail(f"echtes validityStart ignoriert: {o.product} {o.valid_from} != {want_from}")
    elif o.valid_to != valid_to:
        fail(f"Rueckfall aufs Wochenfenster fehlt: {o.product}")
print(f"davon mit echtem Aktionszeitraum von PENNY: {n_real}")
print("\nBeispiele:")
for o in sorted(offers, key=lambda x: -x.effective_pct)[:5]:
    print(f"  -{o.effective_pct:.0f}% | {o.product[:34]:34} | {o.menge_label:10} | "
          f"{o.price} statt {o.old_price} | {o.base_price_label}")

print(f"\n{'FEHLER' if _fail else 'OK'}: {_fail} Fehler")
sys.exit(1 if _fail else 0)
