"""Adapter: PENNY (penny.at) - dieselbe product-discovery JSON-API wie BILLA.

PENNY gehoert wie BILLA zur REWE-Gruppe und betreibt dieselbe Shop-Software.
robots.txt von penny.at enthaelt nur einen Sitemap-Verweis, erlaubt also alles.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from core.models import Offer
from sources import rewe_shop

NAME = "PENNY"
API = "https://www.penny.at/api/product-discovery/products"
_HEADERS = {"Referer": "https://www.penny.at/", "Origin": "https://www.penny.at"}


def _url_for(slug: str) -> str:
    return f"https://www.penny.at/produkte/{slug}"


def parse_products(payload: dict, valid_to: date,
                   valid_from: Optional[date] = None) -> list[Offer]:
    """Reines Parsen (offline testbar)."""
    return rewe_shop.parse_products(payload, NAME, valid_to, valid_from, _url_for)


def fetch(zip_code: str = "1010") -> list[Offer]:
    """Adapter-Vertrag. zip_code wird ignoriert: PENNY-Aktionen sind national."""
    return rewe_shop.fetch_shop(API, NAME, _HEADERS, _url_for)
