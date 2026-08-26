"""Adapter: BILLA (shop.billa.at) - offizielle product-discovery JSON-API.

Die eigentliche Logik steckt in sources/rewe_shop.py, weil PENNY dieselbe
API-Struktur nutzt. robots.txt von shop.billa.at erlaubt alles.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from core.models import Offer
from sources import rewe_shop
from sources.rewe_shop import week_end as _week_end   # noqa: F401 (Test/Kompatibilitaet)

NAME = "BILLA"
API = "https://shop.billa.at/api/product-discovery/products"
_HEADERS = {"Referer": "https://shop.billa.at/", "Origin": "https://shop.billa.at"}


def _url_for(slug: str) -> str:
    return f"https://shop.billa.at/produkte/{slug}"


def parse_products(payload: dict, valid_to: date,
                   valid_from: Optional[date] = None) -> list[Offer]:
    """Reines Parsen (offline testbar)."""
    return rewe_shop.parse_products(payload, NAME, valid_to, valid_from, _url_for)


def fetch(zip_code: str = "1010") -> list[Offer]:
    """Adapter-Vertrag. zip_code wird ignoriert: BILLA-Onlineaktionen sind national."""
    return rewe_shop.fetch_shop(API, NAME, _HEADERS, _url_for)
