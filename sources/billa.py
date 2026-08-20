"""Adapter: BILLA product-discovery API (offiziell, JSON, robots erlaubt alles).

Endpoint:  GET https://shop.billa.at/api/product-discovery/products?inPromotion=true
Paginierung via count/offset. Beste Qualitaet fuer BILLA inkl. exaktem Rabatt.

Einzige Luecke: die API liefert KEIN Aktions-Enddatum -> BILLA-Online-Aktionen
sind rollierende Wochenpreise. valid_to wird als Wochenfenster (kommender
Samstag) modelliert; das ist konfigurierbar.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.http import PoliteClient
from core.models import Offer, build_offer
from core.quantity import Amount

NAME = "BILLA"
API = "https://shop.billa.at/api/product-discovery/products"
_HEADERS = {"Referer": "https://shop.billa.at/", "Origin": "https://shop.billa.at"}

_PT_TAG = re.compile(r"pt-(\d+)plus(\d+)")
_UNIT_MAP = {"gr": "g", "g": "g", "kg": "kg", "dag": "dag", "ml": "ml",
             "cl": "cl", "l": "l", "liter": "l", "stk": "Stk", "st": "Stk"}


def _week_end(today: Optional[date] = None) -> date:
    """Kommender Samstag (inkl. heute, falls Samstag) = Ende der BILLA-Aktionswoche."""
    today = today or date.today()
    return today + timedelta(days=(5 - today.weekday()) % 7)


def _amount_from(p: dict) -> Optional[Amount]:
    raw_amount = p.get("amount")
    unit = (p.get("volumeLabelShort") or "").strip().lower()
    unit = _UNIT_MAP.get(unit, unit)
    try:
        val = float(str(raw_amount).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if val <= 0 or not unit:
        # Stueckware ohne Menge -> nicht vergleichbar, verwerfen
        return None
    return Amount(1, val, unit)


def _action_text(reg: dict, pct: int) -> str:
    for t in reg.get("tags", []):
        m = _PT_TAG.match(t)
        if m:
            return f"{m.group(1)}+{m.group(2)} gratis"
    txt = (reg.get("promotionText") or "").strip()
    if txt and txt.lower() not in ("aktion",):
        return txt
    return f"-{abs(pct)} %"


def _needs_card(reg: dict) -> bool:
    blob = " ".join(reg.get("tags", [])) + " " + (reg.get("promotionText") or "")
    return bool(re.search(r"jö|joe|bonus club|karte", blob, re.IGNORECASE))


def parse_products(payload: dict, valid_to: date, valid_from: Optional[date] = None) -> list[Offer]:
    """Reines Parsen einer product-discovery Antwort -> Offers (offline testbar)."""
    offers: list[Offer] = []
    for p in payload.get("results", []):
        if not p.get("inPromotion"):
            continue
        price = p.get("price") or {}
        reg = price.get("regular") or {}
        pct = price.get("discountPercentage")
        crossed = price.get("crossed")
        value = reg.get("value")
        if pct is None or value is None:
            continue

        amount = _amount_from(p)
        if amount is None:
            continue

        ptype = reg.get("promotionType")
        pqty = reg.get("promotionQuantity") or 1
        requires_qty = int(pqty) if ptype == "PER_SET_OF" and pqty and pqty > 1 else 1

        slug = p.get("slug")
        url = f"https://shop.billa.at/produkte/{slug}" if slug else None
        brand = (p.get("brand") or {}).get("name")

        offer = build_offer(
            source=NAME,
            store=NAME,
            product=p.get("name") or "",
            brand=brand,
            category=p.get("category"),
            amount=amount,
            action_text=_action_text(reg, pct),
            effective_pct=abs(float(pct)),
            price=round(value / 100.0, 2),
            old_price=round(crossed / 100.0, 2) if crossed else None,
            valid_to=valid_to,
            valid_from=valid_from,
            requires_qty=requires_qty,
            needs_card=_needs_card(reg),
            is_multi=requires_qty > 1,
            url=url,
            image_url=(p.get("images") or [None])[0],
        )
        if offer is not None:
            offers.append(offer)
    return offers


def fetch(zip_code: str = "1010") -> list[Offer]:
    """Adapter-Vertrag. zip_code wird ignoriert (BILLA-Online-Aktionen sind national)."""
    valid_to = _week_end()
    valid_from = date.today()
    offers: list[Offer] = []
    seen_sku: set[str] = set()
    page_size = 20            # BILLA cappt count faktisch bei 20; geblaettert wird per page (0-basiert)
    max_pages = 80            # Sicherheitskappe (80*20 = 1600 > aktuell ~1009 Aktionen)
    with PoliteClient(ttl=6 * 3600, extra_headers=_HEADERS) as client:
        for page in range(max_pages):
            payload = client.get_json(API, params={
                "inPromotion": "true", "count": page_size, "page": page,
            })
            if not payload:
                break
            results = payload.get("results", [])
            if not results:
                break
            # Duplikate ueber Seiten hinweg per SKU vermeiden
            fresh = [p for p in results if p.get("sku") not in seen_sku]
            for p in fresh:
                seen_sku.add(p.get("sku"))
            offers.extend(parse_products({"results": fresh}, valid_to, valid_from))
            if (page + 1) * page_size >= (payload.get("total") or 0):
                break
    return offers
