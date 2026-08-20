"""Adapter: marktguru.at interne JSON-API.

robots.txt von api.marktguru.at erlaubt /api/ ausdruecklich (auch fuer Bots).
Ablauf: apiKey + clientKey aus dem Homepage-HTML (Inline-JSON <config>), dann
GET /api/v1/offers/search je Suchbegriff. Deckt BILLA/SPAR/HOFER/PENNY/Lidl ab
und liefert echte Gueltigkeitsdaten + Grundpreis (referencePrice).

Enumeration ueber eine konfigurierbare Begriffsliste (data/search_terms.txt) —
so bekommt man gezielt die Staple-Produkte statt eines fragilen Voll-Crawls.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from core.http import PoliteClient
from core.discount import effective_discount
from core.models import Offer, build_offer
from core.quantity import Amount, parse_amount

VIENNA = ZoneInfo("Europe/Vienna")

# "522 g/425 g/352 g" oder "Waschgaenge 130/126" -> mehrere Gebindegroessen
_MULTISIZE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|stk|waschgänge|wg)?\s*/\s*\d+", re.IGNORECASE)

# marktguru-Platzhalter fuer "keine Marke" - darf nicht in den Produktnamen
_PLACEHOLDER_BRANDS = {"thisisnobrand123", "no-brand", "nobrand"}

NAME = "marktguru"
HOME = "https://www.marktguru.at/"
API = "https://api.marktguru.at/api/v1/offers/search"

_DEFAULT_TERMS = [
    "milch", "butter", "käse", "joghurt", "topfen", "obers", "eier",
    "brot", "semmel", "mehl", "zucker", "nudeln", "reis", "öl", "essig",
    "kaffee", "tee", "kakao", "schokolade", "kekse", "chips",
    "wurst", "schinken", "faschiertes", "hühnerfilet", "schnitzel", "speck",
    "lachs", "thunfisch", "fisch",
    "apfel", "banane", "tomaten", "gurke", "kartoffel", "zwiebel", "salat",
    "tiefkühl", "pizza", "eis", "waschmittel", "klopapier", "windeln",
    "bier", "wein", "wasser", "saft", "cola", "energy",
]

_UNIT_MAP = {"kg": "kg", "g": "g", "dag": "dag", "l": "l", "ml": "ml",
             "cl": "cl", "stk": "Stk", "stück": "Stk", "st": "Stk", "": ""}


def _load_terms() -> list[str]:
    p = Path(__file__).resolve().parent.parent / "data" / "search_terms.txt"
    if p.exists():
        terms = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
        if terms:
            return terms
    return _DEFAULT_TERMS


def get_config(client: PoliteClient) -> Optional[dict]:
    """apiKey/clientKey aus dem Inline-JSON der Homepage ziehen (kurzer Cache)."""
    html = client.get_text(HOME)
    if not html:
        return None
    i = html.find('"config"')
    if i < 0:
        return None
    start = html.rfind("{", 0, i)
    depth = 0
    for j in range(start, len(html)):
        if html[j] == "{":
            depth += 1
        elif html[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    cfg = json.loads(html[start:j + 1]).get("config", {})
                except json.JSONDecodeError:
                    return None
                if cfg.get("apiKey") and cfg.get("clientKey"):
                    return cfg
                return None
    return None


def _parse_dt(s: str) -> Optional[date]:
    """UTC-Zeitstempel -> oesterreichisches Kalenderdatum.

    marktguru liefert die Gueltigkeit als UTC ("2026-08-16T22:00:00Z" =
    17.08. 00:00 Wiener Zeit). Ohne Umrechnung ist valid_from einen Tag zu
    frueh - verifiziert gegen hofer.at ("Mo. 17.8. bis Do. 20.8." bzw.
    "Verfuegbar seit 20.08").
    """
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    try:
        return dt.astimezone(VIENNA).date()
    except Exception:
        return dt.date()


def _amount_from(o: dict) -> Optional[Amount]:
    """Menge aus volume/quantity/unit; Einheit ggf. aus der Beschreibung korrigieren.

    marktguru fuehrt manche Getraenke faelschlich in kg (z.B. Ayran: volume=0.25
    unit=kg, Beschreibung "250 ml"). Wenn die Beschreibung dieselbe Groesse in
    einer anderen Mengenart nennt, gewinnt die Beschreibung.
    """
    unit = ((o.get("unit") or {}).get("shortName") or "").strip().lower()
    unit = _UNIT_MAP.get(unit, unit)
    vol = o.get("volume")
    qty = o.get("quantity") or 1
    try:
        vol = float(vol)
        cnt = max(1, int(qty))
    except (TypeError, ValueError):
        return None
    if vol <= 0 or not unit:
        return None

    amount = Amount(cnt, vol, unit)

    desc_amt = parse_amount(o.get("description") or "")
    if desc_amt is not None and desc_amt.count == 1:
        same_size = abs(desc_amt.base()[0] - Amount(1, vol, unit).base()[0]) < 1e-6
        if same_size and desc_amt.kind != amount.kind:
            amount = Amount(cnt, desc_amt.value, desc_amt.unit)
    return amount


def _size_varies(o: dict) -> bool:
    """True, wenn das Angebot mehrere Gebindegroessen umfasst ("522 g/425 g/352 g").

    Dann gilt der Grundpreis nur fuer eine Variante -> im Dashboard kennzeichnen.
    """
    if not o.get("isMultiProduct"):
        return False
    desc = o.get("description") or ""
    return bool(_MULTISIZE_RE.search(desc))


def parse_offers(payload: dict, seen: Optional[set] = None) -> list[Offer]:
    """Reines Parsen einer offers/search-Antwort -> Offers (offline testbar)."""
    seen = seen if seen is not None else set()
    out: list[Offer] = []
    for o in payload.get("results", []):
        oid = o.get("id")
        if oid in seen:
            continue
        seen.add(oid)

        advertisers = o.get("advertisers") or []
        store = advertisers[0].get("name") if advertisers else None
        if not store:
            continue

        brand = (o.get("brand") or {}).get("name")
        if brand and brand.strip().lower() in _PLACEHOLDER_BRANDS:
            brand = None                      # Platzhalter nicht in den Namen uebernehmen
        pname = (o.get("product") or {}).get("name") or ""
        product = " ".join(x for x in (brand, pname) if x).strip() or (o.get("description") or "")[:60]

        amount = _amount_from(o)
        if amount is None:
            continue

        price = o.get("price")
        old = o.get("oldPrice")

        # effektiver Rabatt: numerisch (Preis vs Streichpreis) ODER Mengen-Aktion
        # aus dem Beschreibungstext (nur echte Mehrfachkauf-Muster, qty>1).
        numeric = None
        if price is not None and old and old > 0:
            numeric = round(100.0 * (old - price) / old, 2)
        dres = effective_discount(o.get("description") or "")
        text_pct = dres.pct if (dres.pct and dres.requires_qty > 1) else None

        cands = [p for p in (numeric, text_pct) if p is not None]
        if not cands:
            continue
        effective = max(cands)
        requires_qty = dres.requires_qty if text_pct == effective else 1

        vd = (o.get("validityDates") or [{}])[0]
        valid_to = _parse_dt(vd.get("to"))
        valid_from = _parse_dt(vd.get("from"))
        if valid_to is None:
            continue

        # Grundpreis: marktguru-referencePrice nur uebernehmen, wenn seine Einheit
        # zur (ggf. korrigierten) Menge passt - sonst rechnet build_offer selbst.
        # Sonst stuende bei Ayran "250 ml" ein Grundpreis "€/kg" daneben.
        ref = o.get("referencePrice")
        raw_unit = ((o.get("unit") or {}).get("shortName") or "").lower()
        raw_unit = _UNIT_MAP.get(raw_unit, raw_unit)
        amount_base_unit = amount.base()[1]
        if raw_unit.lower() != amount_base_unit.lower():
            ref = None
        base_unit = amount_base_unit

        # Aktionstext: bei Mengenaktionen das erkannte Muster, sonst der Prozentwert
        action = dres.matched if requires_qty > 1 else f"−{effective:.0f} %"

        offer = build_offer(
            source=NAME,
            store=store,
            product=product,
            brand=brand,
            category=(o.get("categories") or [{}])[0].get("name"),
            amount=amount,
            action_text=action,
            effective_pct=effective,
            price=price,
            old_price=old,
            base_price_val=round(float(ref), 2) if ref else None,
            base_price_unit=base_unit if ref else None,
            valid_to=valid_to,
            valid_from=valid_from,
            requires_qty=requires_qty,
            needs_card=bool(o.get("requiresLoyalityMembership")),
            is_multi=bool(o.get("isMultiProduct")) or requires_qty > 1,
            size_varies=_size_varies(o),
            url=o.get("externalUrl") or (f"https://www.marktguru.at/offers/{o.get('id')}" if o.get("id") else None),
        )
        if offer is not None:
            out.append(offer)
    return out


def fetch(zip_code: str = "1010") -> list[Offer]:
    offers: list[Offer] = []
    seen: set = set()
    with PoliteClient(ttl=3 * 3600) as client:
        cfg = get_config(client)
        if not cfg:
            return []
        headers = {"x-apikey": cfg["apiKey"], "x-clientkey": cfg["clientKey"],
                   "Origin": "https://www.marktguru.at", "Referer": HOME}
        for term in _load_terms():
            payload = client.get_json(API, params={
                "as": "web", "limit": 40, "offset": 0, "q": term, "zipCode": zip_code,
            }, headers=headers)
            if payload:
                offers.extend(parse_offers(payload, seen))
    return offers
