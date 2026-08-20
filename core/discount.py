"""Aktionstext -> effektiver Rabatt in Prozent.

Der Kern des Tools: im Prospekt steht bei Mengenaktionen ("2+1 gratis") nie ein
Prozentwert. Hier wird der *zugesagte* effektive Rabatt berechnet. Unbestimmte
Obergrenzen ("bis zu -50%") gelten NICHT als zugesagter Rabatt.

Rueckgabe von effective_discount(): float in Prozent (positiv, z.B. 33.33) oder
None, wenn kein zugesagter Rabatt ableitbar ist.

Alle Funktionen sind rein und netzwerkfrei -> offline testbar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscountResult:
    pct: float | None          # effektiver Rabatt in Prozent, positiv; None = unbestimmt
    requires_qty: int          # Stueckzahl fuer den Rabatt (1 = kein Mehrfachkauf)
    needs_card: bool           # Rabatt nur mit Kundenkarte/App
    matched: str               # welches Muster gegriffen hat (fuer Debug/Tests)


# --- Kundenkarten-Erkennung ------------------------------------------------
_CARD_PATTERNS = [
    r"jö\s*bonus", r"\bjö\b", r"j[oö]\s*card",
    r"spar\s*app", r"penny\s*app", r"lidl\s*plus",
    r"mit\s+(?:der\s+)?app", r"kundenkarte", r"clubkarte", r"vorteilscard",
    r"nur\s+mit\s+karte", r"card\s*&\s*win",
]
_CARD_RE = re.compile("|".join(_CARD_PATTERNS), re.IGNORECASE)


def needs_card(text: str) -> bool:
    return bool(_CARD_RE.search(text or ""))


def _norm(text: str) -> str:
    t = (text or "").lower()
    t = t.replace(" ", " ")
    t = t.replace("prozent", "%")
    t = re.sub(r"\s+", " ", t).strip()
    return t


# --- Muster -> effektiver Rabatt -------------------------------------------
# Jedes Muster: (compiled_regex, handler) wobei handler(match) -> DiscountResult|None

def _r(pct, qty=1, card=False, name=""):
    return DiscountResult(pct=pct, requires_qty=qty, needs_card=card, matched=name)


def _handle_plus_gratis(m: re.Match) -> DiscountResult | None:
    # "N+M gratis": kaufe N, zahle N, bekomme M zusaetzlich -> Rabatt M/(N+M)
    n = int(m.group("buy"))
    k = int(m.group("free"))
    total = n + k
    pct = 100.0 * k / total
    return _r(round(pct, 4), qty=total, name=f"{n}+{k} gratis")


def _handle_x_fuer_y(m: re.Match) -> DiscountResult | None:
    # "X fuer Y" / "X um Y" : zahle Y Stueck, bekomme X -> Rabatt (X-Y)/X
    x = int(m.group("take"))
    y = int(m.group("pay"))
    if x <= y:
        return None
    pct = 100.0 * (x - y) / x
    return _r(round(pct, 4), qty=x, name=f"{x} fuer {y}")


def _handle_jeder_n_gratis(m: re.Match) -> DiscountResult | None:
    # "jeder N. gratis" / "jeder N. Artikel gratis": von N Stueck ist 1 gratis
    n = int(m.group("n"))
    if n < 2:
        return None
    pct = 100.0 / n
    return _r(round(pct, 4), qty=n, name=f"jeder {n}. gratis")


def _handle_jeder_n_halb(m: re.Match) -> DiscountResult | None:
    # "jeder N. Artikel zum halben Preis": Rabatt = 0.5/N
    n = int(m.group("n"))
    if n < 2:
        return None
    pct = 100.0 * 0.5 / n
    return _r(round(pct, 4), qty=n, name=f"jeder {n}. halber Preis")


def _handle_zweiter_halb(m: re.Match) -> DiscountResult | None:
    # "2. Artikel zum halben Preis" / "der zweite zum halben Preis" -> -25%
    return _r(25.0, qty=2, name="2. zum halben Preis")


def _handle_zweiter_gratis(m: re.Match) -> DiscountResult | None:
    # "jeder 2. Artikel gratis" / "2. gratis" -> -50%
    return _r(50.0, qty=2, name="2. gratis")


def _handle_minus_pct(m: re.Match) -> DiscountResult | None:
    # "-30%", "30% Rabatt", "minus 30%"
    val = float(m.group("pct").replace(",", "."))
    return _r(round(val, 4), name=f"-{val}%")


def _handle_halber_preis(m: re.Match) -> DiscountResult | None:
    # "zum halben Preis" (auf das ganze Produkt, ohne Mehrfachkauf) -> -50%
    return _r(50.0, name="halber Preis")


# "bis zu" ist eine Obergrenze -> KEIN zugesagter Rabatt
_BIS_ZU_RE = re.compile(r"bis\s+zu\s*[-–]?\s*\d", re.IGNORECASE)

_PATTERNS: list[tuple[re.Pattern, callable]] = [
    # N+M gratis  (1+1, 2+1, 3+1 ...)
    (re.compile(r"(?P<buy>\d+)\s*\+\s*(?P<free>\d+)\s*(?:gratis|geschenkt|gratis dazu)"), _handle_plus_gratis),
    # X fuer Y / X um Y (3 fuer 2, 3 um 2)
    (re.compile(r"(?P<take>\d+)\s*(?:für|fuer|um|zum preis von)\s*(?P<pay>\d+)\b"), _handle_x_fuer_y),
    # jeder 2. Artikel gratis  (Spezialfall vor "jeder N. gratis", da eigener Text)
    (re.compile(r"jede[rs]?\s*2\.?\s*(?:artikel|stück|stk|packung)?\s*gratis"), _handle_zweiter_gratis),
    # jeder N. Artikel zum halben Preis
    (re.compile(r"jede[rs]?\s*(?P<n>\d+)\.?\s*(?:artikel|stück|stk|packung)?\s*(?:zum\s*)?halben?\s*preis"), _handle_jeder_n_halb),
    # jeder N. (Artikel) gratis
    (re.compile(r"jede[rs]?\s*(?P<n>\d+)\.?\s*(?:artikel|stück|stk|packung)?\s*gratis"), _handle_jeder_n_gratis),
    # 2. Artikel zum halben Preis / der zweite zum halben preis
    (re.compile(r"(?:der\s*)?(?:2\.|zweite[rs]?)\s*(?:artikel|stück|stk|packung)?\s*(?:zum\s*)?halben?\s*preis"), _handle_zweiter_halb),
    # -30% / 30% Rabatt / minus 30 %
    (re.compile(r"(?:minus\s*)?[-–]?\s*(?P<pct>\d{1,2}(?:[.,]\d)?)\s*%(?:\s*(?:rabatt|ermäßigung|reduziert|billiger))?"), _handle_minus_pct),
    # ganzes Produkt zum halben Preis (ohne Mehrfachkauf)
    (re.compile(r"(?:zum\s*)?halben\s*preis"), _handle_halber_preis),
]


def effective_discount(text: str) -> DiscountResult:
    """Bestes zugesagtes Rabatt-Ergebnis fuer einen Aktionstext.

    Bei "bis zu" (Obergrenze) -> pct=None. Wenn nichts greift -> pct=None.
    Kundenkarten-Flag wird unabhaengig gesetzt.
    """
    raw = text or ""
    card = needs_card(raw)
    t = _norm(raw)

    if _BIS_ZU_RE.search(t):
        return DiscountResult(pct=None, requires_qty=1, needs_card=card, matched="bis-zu")

    # Priorisierter First-Match: spezifische Mengen-Muster vor generischen
    # Fallbacks (-X%, "halber Preis"). Kein Maximum ueber alle Treffer, sonst
    # wuerde "jeder 2. zum halben Preis" (=-25%) faelschlich das generische
    # "halber Preis" (=-50%) erben.
    for rx, handler in _PATTERNS:
        for m in rx.finditer(t):
            res = handler(m)
            if res is not None:
                return DiscountResult(pct=res.pct, requires_qty=res.requires_qty,
                                      needs_card=card or res.needs_card, matched=res.matched)

    return DiscountResult(pct=None, requires_qty=1, needs_card=card, matched="none")


def qualifies(text: str, min_pct: float) -> bool:
    """True, wenn der zugesagte effektive Rabatt >= min_pct ist."""
    res = effective_discount(text)
    return res.pct is not None and res.pct + 1e-9 >= min_pct
