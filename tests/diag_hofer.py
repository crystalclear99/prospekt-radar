"""HOFER-Angebote aus dem letzten Lauf auflisten (fuer den Abgleich mit hofer.at)."""
import json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(os.path.join(ROOT, "out", "angebote.json"), encoding="utf-8"))
hofer = [r for r in rows if "hofer" in r["store"].lower()]
print(f"{len(hofer)} HOFER-Angebote von {len(rows)} gesamt\n")

print("Gueltigkeitsfenster:", Counter((r["valid_from"], r["valid_to"]) for r in hofer).most_common())
print("Quellen:", Counter(r["source"] for r in hofer))
print("Kategorien:", Counter(r.get("category") for r in hofer).most_common(8))
print()
for r in sorted(hofer, key=lambda x: -x["effective_pct"]):
    calc = None
    if r.get("price") and r.get("old_price"):
        calc = round(100 * (r["old_price"] - r["price"]) / r["old_price"], 1)
    flag = "" if calc is None or abs(calc - r["effective_pct"]) < 0.6 else f"  <-- PCT-ABWEICHUNG (rechnerisch {calc})"
    print(f"−{r['effective_pct']:5.1f}% | {r['product'][:42]:42} | {r['amount']:12} | "
          f"{r.get('price')}€ statt {r.get('old_price')}€ | {r.get('base_price')} | "
          f"{r['valid_from']}→{r['valid_to']}{flag}")
