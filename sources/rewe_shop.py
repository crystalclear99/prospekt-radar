"""Gemeinsamer Parser fuer die REWE-Shops Oesterreich (BILLA und PENNY).

Beide betreiben dieselbe Software: unter /api/product-discovery/products
liefern sie identisch aufgebaute JSON-Antworten inkl. exaktem Rabatt
(discountPercentage), Streichpreis (crossed) und Grundpreis
(perStandardizedQuantity). robots.txt erlaubt bei beiden alles.

Zwei Eigenheiten, die hier abgefangen werden:
  * Geblaettert wird ueber `page` (0-basiert); `offset` wird ignoriert.
  * Es gibt kein Aktions-Enddatum -> die Gueltigkeit wird als Wochenfenster
    modelliert (bis kommenden Samstag).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from core.http import PoliteClient
from core.models import Offer, build_offer
from core.quantity import Amount

_PT_TAG = re.compile(r"pt-(\d+)plus(\d+)")
_UNIT_MAP = {"gr": "g", "g": "g", "kg": "kg", "dag": "dag", "ml": "ml",
             "cl": "cl", "l": "l", "liter": "l", "stk": "Stk", "st": "Stk",
             "stueck": "Stk", "m": "m", "rolle": "Stk", "rollen": "Stk"}

PAGE_SIZE = 20        # beide Shops cappen count faktisch bei 20
MAX_PAGES = 80        # Sicherheitskappe gegen Endlosschleifen


def week_end(today: Optional[date] = None) -> date:
    """Kommender Samstag (inkl. heute, falls Samstag) = Ende der Aktionswoche."""
    today = today or date.today()
    return today + timedelta(days=(5 - today.weekday()) % 7)


def _iso_date(s) -> Optional[date]:
    """"2026-09-02" -> date. None bei fehlendem/kaputtem Wert."""
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _amount_from(p: dict) -> Optional[Amount]:
    unit = (p.get("volumeLabelShort") or "").strip().lower()
    unit = _UNIT_MAP.get(unit, unit)
    try:
        val = float(str(p.get("amount")).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if val <= 0 or not unit:
        return None            # ohne Menge nicht vergleichbar -> verwerfen
    return Amount(1, val, unit)


def _action_text(reg: dict, pct: float) -> str:
    for t in reg.get("tags", []):
        m = _PT_TAG.match(t)
        if m:
            return f"{m.group(1)}+{m.group(2)} gratis"
    txt = (reg.get("promotionText") or "").strip()
    if txt and txt.lower() not in ("aktion", "so"):
        return txt
    return f"-{abs(pct):.0f} %"


def _thumb(url):
    """Kleine Bildvariante des commercetools-CDN.

    Das Original wiegt rund 176 KB, "-small" nur etwa 5 KB - fuer Miniaturen
    in einer Liste mit hunderten Eintraegen ist das der Unterschied zwischen
    brauchbar und unbenutzbar. Faellt die Variante aus, blendet die Seite das
    Bild einfach aus (onerror im Dashboard).
    """
    if not url or not isinstance(url, str):
        return None
    return url[:-4] + "-small.jpg" if url.endswith(".jpg") else url


def _needs_card(reg: dict) -> bool:
    blob = " ".join(reg.get("tags", [])) + " " + (reg.get("promotionText") or "")
    return bool(re.search(r"jö|joe|bonus club|karte|app", blob, re.IGNORECASE))


def parse_products(payload: dict, store: str, valid_to: date,
                   valid_from: Optional[date] = None,
                   url_for: Optional[Callable[[str], str]] = None) -> list[Offer]:
    """Reines Parsen einer product-discovery Antwort -> Offers (offline testbar)."""
    offers: list[Offer] = []
    for p in payload.get("results", []):
        price = p.get("price") or {}
        reg = price.get("regular") or {}
        pct = price.get("discountPercentage")
        value = reg.get("value")
        # Nicht auf p["inPromotion"] verlassen: PENNY liefert dort auch bei
        # echten Aktionen False. discountPercentage ist das verlaessliche
        # Merkmal und bei beiden Shops gesetzt.
        if pct is None or value is None or float(pct) == 0:
            continue

        amount = _amount_from(p)
        if amount is None:
            continue

        ptype = reg.get("promotionType")
        pqty = reg.get("promotionQuantity") or 1
        requires_qty = int(pqty) if ptype == "PER_SET_OF" and pqty and pqty > 1 else 1

        slug = p.get("slug")
        crossed = price.get("crossed")
        # PENNY liefert echte Aktionsdaten mit; BILLA nicht -> Wochenfenster.
        o_from = _iso_date(price.get("validityStart")) or valid_from
        o_to = _iso_date(price.get("validityEnd")) or valid_to
        offer = build_offer(
            source=store,
            store=store,
            product=p.get("name") or "",
            brand=(p.get("brand") or {}).get("name"),
            category=p.get("category"),
            amount=amount,
            action_text=_action_text(reg, float(pct)),
            effective_pct=abs(float(pct)),
            price=round(value / 100.0, 2),
            old_price=round(crossed / 100.0, 2) if crossed else None,
            valid_to=o_to,
            valid_from=o_from,
            requires_qty=requires_qty,
            needs_card=_needs_card(reg),
            is_multi=requires_qty > 1,
            url=url_for(slug) if (url_for and slug) else None,
            image_url=_thumb((p.get("images") or [None])[0]),
        )
        if offer is not None:
            offers.append(offer)
    return offers


def fetch_shop(api: str, store: str, headers: dict,
               url_for: Optional[Callable[[str], str]] = None) -> list[Offer]:
    """Alle Aktionsprodukte eines REWE-Shops holen (seitenweise, hoeflich)."""
    valid_to = week_end()
    valid_from = date.today()
    offers: list[Offer] = []
    seen_sku: set[str] = set()
    with PoliteClient(ttl=6 * 3600, extra_headers=headers) as client:
        for page in range(MAX_PAGES):
            payload = client.get_json(api, params={
                "inPromotion": "true", "count": PAGE_SIZE, "page": page,
            })
            if not payload:
                break
            results = payload.get("results", [])
            if not results:
                break
            fresh = [p for p in results if p.get("sku") not in seen_sku]
            for p in fresh:
                seen_sku.add(p.get("sku"))
            offers.extend(parse_products({"results": fresh}, store, valid_to,
                                         valid_from, url_for))
            if (page + 1) * PAGE_SIZE >= (payload.get("total") or 0):
                break
    return offers
