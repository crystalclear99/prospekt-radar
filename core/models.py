"""Normalisiertes Datenmodell fuer ein Angebot (Offer) + Aufbau/Validierung."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

from core.quantity import Amount, base_price, format_base_price


def _slug_name(name: str) -> str:
    """Produktname fuer Dedupe-Key: klein, ohne Marke-Dopplung, ohne Mengen."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\d+(?:[.,]\d+)?\s*(?:x|kg|dag|dkg|g|mg|ml|cl|dl|l|stk|stueck|rollen?)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class Offer:
    source: str
    store: str
    product: str
    amount: Amount
    action_text: str
    effective_pct: float            # zugesagter effektiver Rabatt, positiv (33.3)
    valid_to: date
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None       # Aktionspreis in EUR
    old_price: Optional[float] = None   # Streichpreis in EUR
    base_price_val: Optional[float] = None
    base_price_unit: Optional[str] = None
    valid_from: Optional[date] = None
    requires_qty: int = 1
    needs_card: bool = False
    is_multi: bool = False
    size_varies: bool = False       # Angebot deckt mehrere Gebindegroessen ab
                                    # -> Grundpreis gilt nur fuer eine Variante
    url: Optional[str] = None
    image_url: Optional[str] = None
    # von der Pipeline gefuellt (Preishistorie):
    hist_median_pct: Optional[float] = None
    hist_warning: bool = False

    @property
    def key(self) -> str:
        bv, bu = self.amount.base()
        return f"{self.store.strip().lower()}|{_slug_name(self.product)}|{round(bv, 3)}{bu}"

    @property
    def menge_label(self) -> str:
        return self.amount.label()

    @property
    def base_price_label(self) -> Optional[str]:
        if self.base_price_val is not None and self.base_price_unit:
            return format_base_price((self.base_price_val, self.base_price_unit))
        return None

    @property
    def starts_in_future(self) -> bool:
        return self.valid_from is not None and self.valid_from > date.today()

    def to_row(self) -> dict:
        d = asdict(self)
        d["amount"] = self.menge_label
        d["valid_to"] = self.valid_to.isoformat()
        d["valid_from"] = self.valid_from.isoformat() if self.valid_from else None
        d["base_price"] = self.base_price_label
        d["key"] = self.key
        return d


def build_offer(**kw) -> Optional[Offer]:
    """Baut ein Offer, berechnet Grundpreis falls noetig, validiert Pflichtfelder.

    Gibt None zurueck, wenn Produkt/Store/Menge/Rabatt fehlen -> das Angebot
    wird dann verworfen (Abnahmekriterium 3: keine leeren Pflichtzellen).
    """
    product = (kw.get("product") or "").strip()
    store = (kw.get("store") or "").strip()
    amount: Optional[Amount] = kw.get("amount")
    pct = kw.get("effective_pct")
    valid_to = kw.get("valid_to")

    if not product or not store or amount is None or pct is None or valid_to is None:
        return None

    # Grundpreis selbst berechnen, wenn nicht geliefert
    if kw.get("base_price_val") is None and kw.get("price") is not None:
        bp = base_price(kw["price"], amount)
        if bp:
            kw["base_price_val"], kw["base_price_unit"] = bp

    allowed = set(Offer.__dataclass_fields__.keys())
    clean = {k: v for k, v in kw.items() if k in allowed}
    return Offer(**clean)
