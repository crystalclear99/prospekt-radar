"""Offline-Tests fuer Mengen-Normalisierung + Grundpreis. python tests/test_quantity.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.quantity import parse_amount, base_price, format_base_price  # noqa: E402

_fail = 0
_ok = 0


def check(text, count, value, unit, base_val=None, base_unit=None):
    global _fail, _ok
    a = parse_amount(text)
    if a is None:
        _fail += 1
        print(f"  FAIL [{text!r}] -> None")
        return
    probs = []
    if a.count != count:
        probs.append(f"count={a.count}!={count}")
    if abs(a.value - value) > 1e-6:
        probs.append(f"value={a.value}!={value}")
    if a.unit != unit:
        probs.append(f"unit={a.unit!r}!={unit!r}")
    if base_val is not None:
        bv, bu = a.base()
        if abs(bv - base_val) > 1e-6 or bu != base_unit:
            probs.append(f"base=({bv},{bu})!=({base_val},{base_unit})")
    if probs:
        _fail += 1
        print(f"  FAIL [{text!r}]: " + "; ".join(probs))
    else:
        _ok += 1


def check_none(text):
    global _fail, _ok
    a = parse_amount(text)
    if a is not None:
        _fail += 1
        print(f"  FAIL [{text!r}] -> {a}, erwartet None")
    else:
        _ok += 1


def check_bp(price, text, expected_val, expected_unit):
    global _fail, _ok
    bp = base_price(price, parse_amount(text))
    if bp is None:
        _fail += 1
        print(f"  FAIL base_price({price},{text!r}) -> None")
        return
    v, u = bp
    if abs(v - expected_val) > 0.01 or u != expected_unit:
        _fail += 1
        print(f"  FAIL base_price({price},{text!r}) = {v} €/{u}, erwartet {expected_val} €/{expected_unit}")
    else:
        _ok += 1


check("200 g", 1, 200, "g", 0.2, "kg")
check("1,5 l", 1, 1.5, "l", 1.5, "l")
check("1,5l", 1, 1.5, "l", 1.5, "l")
check("1500 ml", 1, 1500, "ml", 1.5, "l")
check("6 x 1,5 l", 6, 1.5, "l", 9.0, "l")
check("6x1,5l", 6, 1.5, "l", 9.0, "l")
check("6 × 1.5 L", 6, 1.5, "l", 9.0, "l")
check("16 Rollen", 16, 1.0, "Stk", 16.0, "Stk")
check("10 Stück", 10, 1.0, "Stk", 10.0, "Stk")
check("500 g Packung", 1, 500, "g", 0.5, "kg")
check("250g", 1, 250, "g", 0.25, "kg")
check("0,75 l", 1, 0.75, "l", 0.75, "l")
check("1 kg", 1, 1, "kg", 1.0, "kg")

check_none("")
check_none("Aktion der Woche")
check_none("Bio-Bergkäse")

# Grundpreis
check_bp(2.99, "200 g", 14.95, "kg")     # aus dem Prompt
check_bp(5.99, "6 x 1,5 l", 0.67, "l")   # 5,99 / 9 l
check_bp(1.00, "500 g", 2.0, "kg")
check_bp(4.80, "16 Rollen", 0.30, "Stk")

print(f"\n{_ok} ok, {_fail} fehlgeschlagen")
sys.exit(1 if _fail else 0)
