"""Mengen normalisieren und Grundpreis berechnen.

"6 x 1,5 l", "1,5l", "1500 ml", "16 Rollen", "6er Tray", "200 g" -> Amount
(Stueckzahl + Wert + Einheit) auf einer vergleichbaren Basis, damit Grundpreis
stimmt und Duplikate erkennbar sind.

Netzwerkfrei, offline testbar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Faktor -> Basiseinheit (kg bzw. l). Stueck bleibt Stueck.
_WEIGHT = {
    "mg": 1e-6, "g": 1e-3, "dag": 1e-2, "dkg": 1e-2, "kg": 1.0,
    "gramm": 1e-3, "kilogramm": 1.0, "kilo": 1.0,
}
_VOLUME = {
    "ml": 1e-3, "cl": 1e-2, "dl": 1e-1, "l": 1.0, "ltr": 1.0,
    "liter": 1.0,
}
# Stueck-Einheiten (Basis = Stk, Faktor 1)
_PIECE = {
    "stk", "stück", "stueck", "st", "stk.", "x", "er",
    "rolle", "rollen", "blatt", "beutel", "sackerl", "paar",
    "portion", "portionen", "kapsel", "kapseln", "tab", "tabs",
    "stück.", "packung", "packungen", "pkg", "dosen", "dose",
    "flasche", "flaschen", "waschgänge", "waschgang",
}

_UNIT_CANON = {
    "gramm": "g", "kilogramm": "kg", "kilo": "kg", "liter": "l", "ltr": "l",
    "stück": "Stk", "stueck": "Stk", "st": "Stk", "stk": "Stk", "stk.": "Stk",
}


@dataclass(frozen=True)
class Amount:
    count: int          # Stueckzahl im Gebinde (6 bei "6 x 1,5 l", 1 bei "200 g")
    value: float        # Wert je Einzelstueck (1.5 bei "6 x 1,5 l")
    unit: str           # kanonische Einheit der Einzelmenge ("l","g","kg","ml","Stk"...)

    @property
    def total(self) -> float:
        return self.count * self.value

    @property
    def kind(self) -> str:
        u = self.unit.lower()
        if u in _WEIGHT:
            return "weight"
        if u in _VOLUME:
            return "volume"
        return "piece"

    def base(self) -> tuple[float, str]:
        """Gesamtmenge in Basiseinheit (kg, l oder Stk)."""
        u = self.unit.lower()
        if u in _WEIGHT:
            return self.total * _WEIGHT[u], "kg"
        if u in _VOLUME:
            return self.total * _VOLUME[u], "l"
        return float(self.count) if self.value in (0, 1) else self.total, "Stk"

    def label(self) -> str:
        """Anzeige: "6 × 1,5 l", "200 g", "16 Rollen". Kleine Mengen huebscher."""
        if self.unit == "Stk":
            n = self.count if self.value in (0, 1) else int(self.total)
            return f"{n} Stk"
        val, unit = self.value, self.unit
        # kleine kg/l fuer die Anzeige in g/ml umrechnen
        if unit == "kg" and val < 1:
            val, unit = val * 1000, "g"
        elif unit == "l" and val < 1:
            val, unit = val * 1000, "ml"
        if self.count > 1:
            return f"{self.count} × {_fmt(val)} {unit}"
        return f"{_fmt(val)} {unit}"


def _fmt(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)


def _canon_unit(u: str) -> str:
    u = u.strip().lower().rstrip(".")
    return _UNIT_CANON.get(u, u)


# "6 x 1,5 l" / "6x1,5l" / "6 × 1.5 L"
_MULTI = re.compile(
    r"(?P<count>\d+)\s*(?:x|×|er[- ]?(?:tray|pack|packung)?)\s*"
    r"(?P<val>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-ZäöüÄÖÜ]+)",
    re.IGNORECASE,
)
# einzelne Menge "1,5 l" / "1500 ml" / "200 g" / "0,75l"
_SINGLE = re.compile(
    r"(?P<val>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|dag|dkg|g|mg|gramm|kilogramm|kilo|"
    r"ml|cl|dl|l|ltr|liter)\b",
    re.IGNORECASE,
)
# Stueckzahl "16 Rollen" / "10 Stück" / "6er"
_PIECE_RE = re.compile(
    r"(?P<count>\d+)\s*(?:er\b|(?P<unit>stück|stueck|stk\.?|rollen?|blatt|beutel|"
    r"paar|portionen?|kapseln?|tabs?|packungen?|dosen?|flaschen?|waschgänge?))",
    re.IGNORECASE,
)


def parse_amount(text: str) -> Amount | None:
    """Beste Mengen-Interpretation aus freiem Text. None, wenn keine erkennbar."""
    if not text:
        return None
    t = text.strip()

    m = _MULTI.search(t)
    if m:
        unit = _canon_unit(m.group("unit"))
        if unit.lower() in _WEIGHT or unit.lower() in _VOLUME:
            return Amount(int(m.group("count")), _num(m.group("val")), unit)

    m = _SINGLE.search(t)
    if m:
        return Amount(1, _num(m.group("val")), _canon_unit(m.group("unit")))

    m = _PIECE_RE.search(t)
    if m:
        return Amount(int(m.group("count")), 1.0, "Stk")

    return None


def base_price(total_price: float | None, amount: Amount | None) -> tuple[float, str] | None:
    """Grundpreis (Preis je kg / l / Stk). None, wenn nicht berechenbar."""
    if total_price is None or amount is None:
        return None
    base_val, base_unit = amount.base()
    if base_val <= 0:
        return None
    return round(total_price / base_val, 2), base_unit


def format_base_price(bp: tuple[float, str] | None) -> str | None:
    """Grundpreis als Geldbetrag: immer 2 Nachkommastellen ("13,00 €/kg")."""
    if bp is None:
        return None
    val, unit = bp
    return f"{val:.2f}".replace(".", ",") + f" €/{unit}"
