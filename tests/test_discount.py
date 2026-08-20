"""Offline-Tests fuer die Rabatt-Engine. Aufruf: python tests/test_discount.py

Jeder neue Aktionstext aus echten Prospekten bekommt hier einen Fall.
Kein Netzwerk, kein Framework noetig.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.discount import effective_discount, qualifies  # noqa: E402

_fail = 0
_ok = 0


def approx(a, b, tol=0.05):
    return a is not None and b is not None and abs(a - b) <= tol


def check_pct(text, expected, qty=None, card=None):
    global _fail, _ok
    res = effective_discount(text)
    problems = []
    if expected is None:
        if res.pct is not None:
            problems.append(f"pct={res.pct} erwartet None")
    else:
        if not approx(res.pct, expected):
            problems.append(f"pct={res.pct} erwartet ~{expected}")
    if qty is not None and res.requires_qty != qty:
        problems.append(f"qty={res.requires_qty} erwartet {qty}")
    if card is not None and res.needs_card != card:
        problems.append(f"card={res.needs_card} erwartet {card}")
    if problems:
        _fail += 1
        print(f"  FAIL [{text!r}] ({res.matched}): " + "; ".join(problems))
    else:
        _ok += 1


def check_qual(text, min_pct, expected):
    global _fail, _ok
    got = qualifies(text, min_pct)
    if got != expected:
        _fail += 1
        print(f"  FAIL qualifies({text!r}, {min_pct}) = {got}, erwartet {expected}")
    else:
        _ok += 1


# --- Prompt-Tabelle: was rein muss (>= 30%) ---
check_pct("1+1 gratis", 50.0, qty=2)
check_pct("jeder 2. Artikel gratis", 50.0, qty=2)
check_pct("2+1 gratis", 33.333, qty=3)
check_pct("3 für 2", 33.333, qty=3)
check_pct("3 um 2", 33.333, qty=3)
check_pct("jeder 3. gratis", 33.333, qty=3)
check_pct("-30%", 30.0)
check_pct("-30 %", 30.0)
check_pct("minus 30 %", 30.0)
check_pct("30% Rabatt", 30.0)

# --- Prompt-Tabelle: was raus muss (< 30%) ---
check_pct("3+1 gratis", 25.0, qty=4)
check_pct("jeder 2. Artikel zum halben Preis", 25.0, qty=2)
check_pct("-25% mit Kundenkarte", 25.0, card=True)
check_pct("bis zu -50%", None)
check_pct("bis zu 50% Rabatt", None)

# --- qualifies() an der Schwelle 30 ---
check_qual("1+1 gratis", 30.0, True)
check_qual("2+1 gratis", 30.0, True)
check_qual("jeder 3. gratis", 30.0, True)
check_qual("-30%", 30.0, True)
check_qual("3+1 gratis", 30.0, False)
check_qual("jeder 2. Artikel zum halben Preis", 30.0, False)
check_qual("-25% mit Kundenkarte", 30.0, False)
check_qual("bis zu -50%", 30.0, False)
# hoehere Schwelle
check_qual("2+1 gratis", 40.0, False)   # 33.3 < 40
check_qual("1+1 gratis", 40.0, True)    # 50 >= 40
check_qual("1+1 gratis", 50.0, True)    # 50 >= 50 (Gleichheit)

# --- weitere reale Muster (in freier Wildbahn gefunden) ---
check_pct("2+1 GRATIS", 33.333, qty=3)          # Grossschreibung
check_pct("4+2 gratis", 33.333, qty=6)          # 2/6
check_pct("5 für 3", 40.0, qty=5)               # (5-3)/5
check_pct("jeder 4. gratis", 25.0, qty=4)       # < 30
check_pct("der zweite Artikel zum halben Preis", 25.0, qty=2)
check_pct("2. Packung zum halben Preis", 25.0, qty=2)
check_pct("zum halben Preis", 50.0)             # ganzes Produkt
check_pct("-50%", 50.0)
check_pct("- 33 %", 33.0)
check_pct("jö Bonus: -20%", 20.0, card=True)    # Kundenkarte erkannt
check_pct("mit der Lidl Plus App -40%", 40.0, card=True)
check_pct("SPAR App: 2+1 gratis", 33.333, qty=3, card=True)
check_pct("kein Rabatt hier", None)
check_pct("", None)
check_pct("Aktion", None)
# "bis zu" darf spezifische Aktion nicht ueberschreiben, aber Vorsicht:
check_pct("2+1 gratis (bis zu -50% moeglich)", None)  # bis-zu-Guard greift zuerst

# --- Grenzfaelle Zahlenerkennung ---
check_pct("3 für 2026 Punkte", None)   # kein echtes X-fuer-Y (x<=y)
check_pct("Packung 200 g", None)       # keine Prozent/Menge-Aktion

print(f"\n{_ok} ok, {_fail} fehlgeschlagen")
sys.exit(1 if _fail else 0)
