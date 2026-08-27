"""Offline-Tests fuer das Dashboard-Rendering. python tests/test_render.py

Schwerpunkt: Faellt eine Quelle aus, muss das auf der Seite stehen. Ein gruener
Lauf mit halber Datenmenge ist der gefaehrlichste Zustand - genau der ist am
27.08.2026 eingetreten (BILLA und PENNY lieferten aus der GitHub-Cloud nichts,
der Lauf war trotzdem gruen und die Seite sah normal aus).
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render import render_html  # noqa: E402

_fail = 0
_ok = 0


def check(cond, label):
    global _fail, _ok
    if cond:
        _ok += 1
    else:
        _fail += 1
        print("  FAIL:", label)


ROW = {
    "store": "BILLA", "product": "Testbutter", "brand": "Testmarke",
    "category": "Milch, Käse & Eier", "subcategory": "Butter",
    "category_detail": "Butter", "amount": "250 g", "effective_pct": 40.0,
    "price": 1.19, "old_price": 1.99, "base_price": "4,76 €/kg",
    "base_price_num": 4.76, "action_text": "-40 %", "requires_qty": 1,
    "needs_card": False, "size_varies": False, "is_new": True,
    "starts_in_future": False, "valid_from": "2026-08-27",
    "valid_to": date(2099, 1, 1).isoformat(), "key": "billa|testbutter|0.25kg",
    "url": None, "source": "BILLA", "hist_warning": False, "hist_median_pct": None,
}
BASE_META = {"generated_at": "27.08.2026 16:53", "min_pct": 30, "zip": "4652"}

# --- alle Quellen ok: kein Warnbanner, aber Quellenzeile ---
html_ok = render_html([ROW], {**BASE_META,
                              "sources": {"BILLA": 358, "PENNY": 62, "marktguru": 273},
                              "problems": []})
check('class="alert"' not in html_ok, "kein Banner, wenn alle Quellen liefern")
check("Von den Quellen geholt" in html_ok, "Quellenzeile vorhanden")
check("BILLA 358" in html_ok, "Anzahl je Quelle in der Fusszeile")

# --- eine Quelle tot: Banner mit Namen ---
html_dead = render_html([ROW], {**BASE_META,
                                "sources": {"BILLA": 0, "PENNY": 0, "marktguru": 276},
                                "problems": ["Quelle BILLA lieferte 0 Treffer"]})
check('class="alert"' in html_dead, "Banner bei ausgefallener Quelle")
check("BILLA und PENNY" in html_dead, "beide toten Quellen benannt")
check("unvollst" in html_dead, "Banner sagt, dass die Liste unvollstaendig ist")
check("marktguru" in html_dead, "lebende Quelle bleibt in der Fusszeile")

# --- ohne sources-Angabe (alte meta): nichts kaputt ---
html_plain = render_html([ROW], BASE_META)
check('class="alert"' not in html_plain, "kein Banner ohne Quellenangabe")
check("Von den Quellen geholt" not in html_plain, "keine leere Quellenzeile")

# --- Grundgeruest muss immer stehen ---
for needle, label in [
    ("prospekt-radar:favoriten", "Favoriten-Speicher"),
    ("bandOf", "Rabattbaender"),
    ("fillSubs", "Unterkategorien"),
    ("min-width:780px", "Mobil/Desktop-Umschaltung"),
    ("Testbutter", "Produktname gerendert"),
    ("noindex", "Suchmaschinen ausgesperrt"),
]:
    check(needle in html_ok, label + " fehlt")

# --- Rasterspalten und Kopfzeile muessen zusammenpassen ---
# .otop hat display:contents -> Stern, Rabatt, Geschaeft zaehlen einzeln.
import re  # noqa: E402

kopf = html_ok.count("<span data-k=") + 1          # +1 fuer die Sternspalte
m = re.search(r"\.cols\s*\{[^}]*grid-template-columns:\s*([^;}]+)", html_ok)
check(m is not None, "Rasterdefinition .cols gefunden")
if m:
    spalten = len(m.group(1).split())
    check(kopf == spalten, f"Kopfspalten ({kopf}) != Rasterspalten ({spalten})")

# --- HTML-Escaping ---
evil = {**ROW, "product": '<script>alert(1)</script>', "key": "x|y|1kg"}
html_evil = render_html([evil], BASE_META)
check("<script>alert(1)</script>" not in html_evil.split("const DATA")[0],
      "Produktname wird nicht als HTML eingebettet")

print(f"\n{_ok} ok, {_fail} fehlgeschlagen")
sys.exit(1 if _fail else 0)
