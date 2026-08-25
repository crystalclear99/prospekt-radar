"""Offline-Parser-Test fuer den BILLA-Adapter (nutzt gespeicherte Fixture).
python tests/test_billa.py
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.billa import parse_products  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "billa_promo.json")

_fail = 0


def fail(msg):
    global _fail
    _fail += 1
    print("  FAIL:", msg)


payload = json.load(open(FIX, encoding="utf-8"))
valid_to = date(2026, 8, 22)
offers = parse_products(payload, valid_to)

print(f"{len(offers)} Offers aus {len(payload['results'])} Produkten geparst")

if not offers:
    fail("keine Offers geparst")

for o in offers:
    if not o.product:
        fail(f"leeres Produkt: {o}")
    if o.store != "BILLA":
        fail(f"falscher Store: {o.store}")
    if o.amount is None:
        fail(f"keine Menge: {o.product}")
    if o.effective_pct is None or o.effective_pct <= 0:
        fail(f"kein Rabatt: {o.product}")
    if o.valid_to != valid_to:
        fail(f"valid_to falsch: {o.product}")
    # Grundpreis muss berechnet sein, wenn Preis vorhanden
    if o.price is not None and o.base_price_label is None:
        fail(f"kein Grundpreis trotz Preis: {o.product}")
    # key nicht leer
    if not o.key or o.key.count("|") != 2:
        fail(f"key kaputt: {o.key}")

# Mehrfachkauf-Erkennung: mind. eines mit requires_qty>1 ODER keines (je nach Woche) ist ok,
# aber wenn requires_qty>1, muss is_multi True sein
for o in offers:
    if o.requires_qty > 1 and not o.is_multi:
        fail(f"is_multi nicht gesetzt bei requires_qty={o.requires_qty}: {o.product}")

# Beispielausgabe
print("\nBeispiele:")
for o in offers[:5]:
    print(f"  -{o.effective_pct:.0f}% | {o.store} | {o.product} | {o.menge_label} | "
          f"{o.price}€ statt {o.old_price}€ | {o.base_price_label} | '{o.action_text}'"
          f"{' | qty='+str(o.requires_qty) if o.requires_qty>1 else ''}")

print(f"\n{'FEHLER' if _fail else 'OK'}: {_fail} Fehler")
sys.exit(1 if _fail else 0)
