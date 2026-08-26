"""Offline-Tests fuer die Kategorie-Gruppierung. python tests/test_categories.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.categories import group_for, all_groups  # noqa: E402

_fail = 0
_ok = 0


def eq(cat, want):
    global _fail, _ok
    got = group_for(cat)
    if got != want:
        _fail += 1
        print(f"  FAIL {cat!r}: {got!r} erwartet {want!r}")
    else:
        _ok += 1


# --- Stolperfallen, die beim echten Datensatz aufgefallen sind ---
eq("Zahnpasta & -pflege", "Drogerie & Haushalt")   # enthaelt "pasta"
eq("Beutel & Sonstige Folien", "Drogerie & Haushalt")  # "Folien" enthaelt "ol"
eq("Töpfe", "Drogerie & Haushalt")                 # nicht "Topfen" (Quark)
eq("Topfen", "Milch, Käse & Eier")
eq("Tiefkühlpizza & -flammkuchen", "Tiefkühl")     # nicht Vorrat
eq("Pizza", "Vorrat")
eq("Schokoaufstrich", "Süßes & Snacks")            # nicht "aufstrich" -> Molkerei
eq("herzhafte Aufstriche", "Milch, Käse & Eier")
eq("Eis", "Süßes & Snacks")
eq("Eistee", "Getränke")                           # nicht "eis" -> Suesses
eq("Weissweine", "Alkohol")                        # enthaelt "eis"
eq("Weißwein", "Alkohol")
eq("Dessertwein & Portwein", "Alkohol")            # nicht "dessert" -> Molkerei
eq("Desserts", "Milch, Käse & Eier")
eq("Alkoholfreies Bier", "Getränke")               # nicht Alkohol
eq("Alkoholfreie Alternativen", "Getränke")
eq("Frucht- & Gemüsesäfte", "Getränke")            # nicht "gemuse" -> Obst
eq("Öle und Fette", "Vorrat")
eq("Eier-Teigwaren", "Vorrat")                     # nicht "eier" -> Molkerei
eq("Rosé", "Alkohol")
eq("Pommes & Co", "Tiefkühl")

# --- Normalfaelle ---
eq("Hartkäse", "Milch, Käse & Eier")
eq("Frischkäse & Hüttenkäse", "Milch, Käse & Eier")
eq("Faschiertes", "Fleisch & Wurst")
eq("Räucherfisch", "Fisch")
eq("Fischkonserven", "Fisch")
eq("Gemüse", "Obst & Gemüse")
eq("Zwiebeln und Knoblauch", "Obst & Gemüse")
eq("Knäckebrot & Zwieback", "Brot & Gebäck")
eq("Tafelschokolade", "Süßes & Snacks")
eq("Ganze Bohne", "Kaffee & Tee")
eq("Mineralwasser mit Geschmack", "Getränke")
eq("Windeln", "Baby & Kind")
eq("Waschmittel", "Drogerie & Haushalt")
eq("Tiefkühlgemüse", "Tiefkühl")

# --- Randfaelle ---
eq(None, "Sonstiges")
eq("", "Sonstiges")
eq("Voellig unbekannte Warengruppe", "Sonstiges")

# Gruppenliste muss eindeutig sein und Sonstiges enthalten
groups = all_groups()
if len(groups) != len(set(groups)):
    _fail += 1
    print("  FAIL: all_groups enthaelt Duplikate:", groups)
else:
    _ok += 1
if "Sonstiges" not in groups:
    _fail += 1
    print("  FAIL: Sonstiges fehlt in all_groups")
else:
    _ok += 1
# jede Regel-Gruppe muss erreichbar sein
if len(groups) > 15:
    _fail += 1
    print(f"  FAIL: {len(groups)} Gruppen - zu viele fuer einen Filter")
else:
    _ok += 1

print(f"\n{len(groups)} Gruppen: {', '.join(groups)}")
print(f"\n{_ok} ok, {_fail} fehlgeschlagen")
sys.exit(1 if _fail else 0)
