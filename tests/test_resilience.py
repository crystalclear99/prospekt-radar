"""Abnahmekriterium 6: ein kaputter Adapter darf den Lauf nicht abbrechen.
python tests/test_resilience.py  (offline, ohne Netzwerk)
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pipeline  # noqa: E402
from core.models import build_offer  # noqa: E402
from core.quantity import Amount  # noqa: E402

_fail = 0


def fail(m):
    global _fail
    _fail += 1
    print("  FAIL:", m)


def boom(zip_code="1010"):
    raise RuntimeError("absichtlich kaputt (URL verbogen)")


def fake_marktguru(zip_code="1010"):
    o = build_offer(source="marktguru", store="SPAR", product="Testbutter",
                    amount=Amount(1, 250, "g"), action_text="-40 %",
                    effective_pct=40.0, price=1.19, old_price=1.99,
                    valid_to=date(2099, 1, 1))
    return [o]


# Adapter-Registry so verbiegen, dass BILLA kracht, marktguru liefert
pipeline.ADAPTERS = [("BILLA", boom), ("marktguru", fake_marktguru)]

offers, counts = pipeline.run_adapters("1010", None)

if counts.get("BILLA") != 0:
    fail(f"BILLA sollte 0 sein, ist {counts.get('BILLA')}")
if counts.get("marktguru", 0) < 1:
    fail("marktguru sollte trotz BILLA-Absturz liefern")
if not any(o.store == "SPAR" for o in offers):
    fail("marktguru-Angebot fehlt im Ergebnis")

print(f"counts={counts}, offers={len(offers)} -> Lauf lief trotz Absturz weiter")
print(f"\n{'FEHLER' if _fail else 'OK'}: {_fail} Fehler")
sys.exit(1 if _fail else 0)
