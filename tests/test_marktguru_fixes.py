"""Regressionstests fuer die beim HOFER-Abgleich gefundenen Fehler.
python tests/test_marktguru_fixes.py   (offline)
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.marktguru import _parse_dt, _amount_from, _size_varies, parse_offers  # noqa: E402
from core.quantity import format_base_price  # noqa: E402

_fail = 0
_ok = 0


def eq(got, want, label):
    global _fail, _ok
    if got != want:
        _fail += 1
        print(f"  FAIL {label}: {got!r} != {want!r}")
    else:
        _ok += 1


# --- Bug 1: Zeitzone. Gegen hofer.at verifiziert. ---
# "Mo. 17.8. bis Do. 20.8." (Wochenstart-Aktion)
eq(_parse_dt("2026-08-16T22:00:00Z"), date(2026, 8, 17), "valid_from Wochenstart")
eq(_parse_dt("2026-08-20T21:59:00Z"), date(2026, 8, 20), "valid_to Wochenstart")
# "Verfuegbar seit 20.08" (Do-Aktion, Crofton Pfanne)
eq(_parse_dt("2026-08-19T22:00:00Z"), date(2026, 8, 20), "valid_from Do-Aktion")
# Winterzeit (UTC+1): 23:00Z ist der Folgetag
eq(_parse_dt("2026-01-14T23:00:00Z"), date(2026, 1, 15), "valid_from Winterzeit")
eq(_parse_dt("2026-01-20T22:59:00Z"), date(2026, 1, 20), "valid_to Winterzeit")
eq(_parse_dt("kaputt"), None, "ungueltiges Datum")

# --- Bug 2: Grundpreis-Formatierung immer 2 Nachkommastellen ---
eq(format_base_price((13.0, "kg")), "13,00 €/kg", "Grundpreis ganze Zahl")
eq(format_base_price((2.5, "l")), "2,50 €/l", "Grundpreis eine Stelle")
eq(format_base_price((0.04, "Stk")), "0,04 €/Stk", "Grundpreis klein")

# --- Bug 3: Einheit aus Beschreibung korrigieren (Ayran: kg -> ml) ---
ayran = {"volume": 0.25, "quantity": 1.0,
         "unit": {"shortName": "kg"}, "description": "250 ml"}
a = _amount_from(ayran)
eq(a.unit, "ml", "Ayran Einheit aus Beschreibung")
eq(a.label(), "250 ml", "Ayran Label")

# Gegenprobe: passt die Beschreibung zur Einheit, wird NICHT geaendert
kaffee = {"volume": 1.0, "quantity": 1.0,
          "unit": {"shortName": "kg"}, "description": "ganze Bohne 1 kg"}
eq(_amount_from(kaffee).unit, "kg", "Kaffee bleibt kg")

# Gegenprobe: abweichende Groesse in der Beschreibung darf nicht ueberschreiben
misc = {"volume": 0.5, "quantity": 1.0,
        "unit": {"shortName": "kg"}, "description": "Beilage 250 ml dazu"}
eq(_amount_from(misc).unit, "kg", "abweichende Groesse ignoriert")

# Mehrstueck bleibt erhalten (Familienjoghurt 6 x 120 g)
joghurt = {"volume": 0.12, "quantity": 6.0,
           "unit": {"shortName": "kg"}, "description": "6 x 120 g"}
a = _amount_from(joghurt)
eq((a.count, a.unit), (6, "kg"), "Familienjoghurt Stueckzahl")
eq(a.label(), "6 × 120 g", "Familienjoghurt Label")

# --- Bug 4: mehrere Gebindegroessen erkennen ---
eq(_size_varies({"isMultiProduct": True,
                 "description": "verschiedene Sorten 522 g/425 g/352 g"}), True, "Storck size_varies")
eq(_size_varies({"isMultiProduct": True,
                 "description": "Wild Rose, Sensitive, etc. Waschgänge 130/126"}), True, "Silan size_varies")
eq(_size_varies({"isMultiProduct": True, "description": "verschiedene Sorten 250 g"}), False,
   "eine Groesse -> kein Flag")
eq(_size_varies({"isMultiProduct": False, "description": "522 g/425 g"}), False,
   "kein MultiProduct -> kein Flag")

# --- Bug 5: Platzhalter-Marke nicht in den Produktnamen ---
payload = {"results": [{
    "id": 1,
    "advertisers": [{"name": "HOFER"}],
    "brand": {"name": "thisisnobrand123"},
    "product": {"name": "W-Wein"},
    "description": "11 % Vol. 1 l",
    "volume": 1.0, "quantity": 1.0, "unit": {"shortName": "l"},
    "price": 1.99, "oldPrice": 2.99, "referencePrice": 1.99,
    "validityDates": [{"from": "2026-08-19T22:00:00Z", "to": "2026-09-17T21:59:00Z"}],
}]}
offers = parse_offers(payload)
eq(len(offers), 1, "Wein geparst")
if offers:
    o = offers[0]
    eq(o.product, "W-Wein", "Platzhalter-Marke entfernt")
    eq(o.brand, None, "brand auf None")
    eq(o.valid_from, date(2026, 8, 20), "Wein valid_from mit TZ")
    # 11 % aus "11 % Vol." darf den Rabatt NICHT setzen (nur Preisdifferenz zaehlt)
    eq(round(o.effective_pct, 1), 33.4, "Rabatt aus Preisdifferenz, nicht aus '11 % Vol.'")
    eq(o.requires_qty, 1, "kein Mehrfachkauf")


# --- Bug 6: Grundpreis-Einheit muss zur (korrigierten) Menge passen ---
ayran_payload = {"results": [{
    "id": 2, "advertisers": [{"name": "HOFER"}], "brand": {"name": "Milsani"},
    "product": {"name": "Ayran"}, "description": "250 ml",
    "volume": 0.25, "quantity": 1.0, "unit": {"shortName": "kg"},
    "price": 0.29, "oldPrice": 0.49, "referencePrice": 1.16,
    "validityDates": [{"from": "2026-08-23T22:00:00Z", "to": "2026-08-27T21:59:00Z"}],
}]}
o = parse_offers(ayran_payload)[0]
eq(o.menge_label, "250 ml", "Ayran Menge")
eq(o.base_price_label, "1,16 €/l", "Ayran Grundpreis in €/l statt €/kg")

# Gegenprobe: passende Einheit -> referencePrice wird uebernommen
kaffee_payload = {"results": [{
    "id": 3, "advertisers": [{"name": "HOFER"}], "brand": {"name": "Barissimo"},
    "product": {"name": "Espresso Classico"}, "description": "ganze Bohne 1 kg",
    "volume": 1.0, "quantity": 1.0, "unit": {"shortName": "kg"},
    "price": 8.99, "oldPrice": 12.99, "referencePrice": 8.99,
    "validityDates": [{"from": "2026-08-20T22:00:00Z", "to": "2026-08-22T21:59:00Z"}],
}]}
o = parse_offers(kaffee_payload)[0]
eq(o.base_price_label, "8,99 €/kg", "Kaffee Grundpreis bleibt €/kg")
eq(o.valid_from, date(2026, 8, 21), "Kaffee valid_from mit TZ")

print(f"\n{_ok} ok, {_fail} fehlgeschlagen")
sys.exit(1 if _fail else 0)
