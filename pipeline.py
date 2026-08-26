#!/usr/bin/env python3
"""Prospekt-Radar Pipeline: Adapter -> Dedupe -> Filter -> Historie -> Render.

Fehlertolerant: ein kaputter Adapter darf den Lauf nie abbrechen.

CLI:
  python pipeline.py --plz 4020 --min-pct 30 --stores BILLA,SPAR,HOFER
  python pipeline.py                       # Defaults: PLZ 1010, min 30%, alle Quellen

Exit-Code != 0, wenn eine Quelle 0 Treffer liefert oder der Lauf < 50% der
Vorwoche findet (stillschweigend leere Ergebnisse sind der schlimmste Fehler).
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from core.categories import group_for
from core.models import Offer
from render import render_html
from sources import billa, marktguru, penny

# Alle Zeitangaben in Wiener Zeit. Der GitHub-Runner laeuft in UTC; ohne das
# steht auf der Seite ein falsches Datum und abgelaufene Angebote bleiben
# zwischen 00:00 und 02:00 Wiener Zeit einen Tag zu lang stehen.
VIENNA = ZoneInfo("Europe/Vienna")


def now_vienna() -> datetime:
    return datetime.now(VIENNA)


def today_vienna() -> date:
    return now_vienna().date()


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "out"
HISTORY = DATA / "history.jsonl"
LAST_RUN = DATA / "last_run.json"

# Reihenfolge = Prioritaet beim Dedupe (erste Quelle gewinnt bei Duplikaten)
ADAPTERS = [
    ("BILLA", billa.fetch),
    ("PENNY", penny.fetch),
    ("marktguru", marktguru.fetch),
]


def log(msg: str) -> None:
    print(f"[{now_vienna():%H:%M:%S}] {msg}", file=sys.stderr)


# --- Dedupe ---------------------------------------------------------------
def dedupe(offers: list[Offer]) -> list[Offer]:
    """Exakter Key zuerst; danach konservatives Fuzzy (gleicher Store + gleiche
    Basismenge + identische Wort-Menge im Namen). Lieber ein Duplikat zu viel."""
    out: list[Offer] = []
    seen_keys: set[str] = set()
    seen_fuzzy: set[tuple] = set()
    for o in offers:
        if o.key in seen_keys:
            continue
        bv, bu = o.amount.base()
        from core.models import _slug_name
        tokens = frozenset(_slug_name(o.product).split())
        fuzzy = (o.store.strip().lower(), round(bv, 3), bu, tokens)
        if fuzzy in seen_fuzzy:
            continue
        seen_keys.add(o.key)
        seen_fuzzy.add(fuzzy)
        out.append(o)
    return out


# --- Preishistorie / Scheinrabatt -----------------------------------------
def load_history() -> dict[str, list[dict]]:
    hist: dict[str, list[dict]] = {}
    if not HISTORY.exists():
        return hist
    cutoff = (today_vienna() - timedelta(days=90)).isoformat()
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("date", "") >= cutoff:
            hist.setdefault(rec["key"], []).append(rec)
    return hist


def apply_history(offers: list[Offer], hist: dict[str, list[dict]]) -> None:
    """Rabatt zusaetzlich gegen Median der letzten 90 Tage pruefen (>=4 Beob.)."""
    for o in offers:
        obs = hist.get(o.key, [])
        pcts = [r["pct"] for r in obs if isinstance(r.get("pct"), (int, float))]
        if len(pcts) >= 4:
            med = statistics.median(pcts)
            o.hist_median_pct = round(med, 1)
            if abs(o.effective_pct - med) > 10:
                o.hist_warning = True


def append_history(offers: list[Offer]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    today = today_vienna().isoformat()
    with HISTORY.open("a", encoding="utf-8") as f:
        for o in offers:
            f.write(json.dumps({
                "date": today, "key": o.key, "store": o.store,
                "pct": round(o.effective_pct, 1), "price": o.price,
            }, ensure_ascii=False) + "\n")


# --- Fetch (fehlertolerant) -----------------------------------------------
def run_adapters(zip_code: str, only: set[str] | None) -> tuple[list[Offer], dict[str, int]]:
    all_offers: list[Offer] = []
    counts: dict[str, int] = {}
    for name, fetch in ADAPTERS:
        if only and name.lower() not in only:
            continue
        try:
            offers = fetch(zip_code)
        except Exception as e:                      # noqa: BLE001 - Adapter darf Lauf nie killen
            log(f"  ⚠ Adapter {name} FEHLER: {type(e).__name__}: {e}")
            counts[name] = 0
            continue
        counts[name] = len(offers)
        all_offers.extend(offers)
        log(f"  {name}: {len(offers)} rohe Angebote")
    return all_offers, counts


# --- Rows fuer Render/Export ----------------------------------------------
def to_rows(offers: list[Offer], prev_keys: set[str]) -> list[dict]:
    rows = []
    for o in offers:
        r = o.to_row()
        r["is_new"] = o.key not in prev_keys if prev_keys else False
        # Feine Quell-Kategorie als Detail behalten, im Filter aber die Gruppe
        # zeigen (die Quellen liefern ~145 Kategorien, das ist unbrauchbar).
        r["category_detail"] = r.get("category")
        r["category"] = group_for(r.get("category"))
        r["starts_in_future"] = o.starts_in_future
        r["base_price_num"] = o.base_price_val
        rows.append(r)
    return rows


def write_outputs(rows: list[dict], meta: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "angebote.html").write_text(render_html(rows, meta), encoding="utf-8")
    (OUT / "angebote.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["store", "product", "brand", "category", "effective_pct", "price",
            "old_price", "base_price", "amount", "action_text", "requires_qty",
            "needs_card", "size_varies", "category_detail", "valid_from",
            "valid_to", "is_new",
            "source", "url"]
    with (OUT / "angebote.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prospekt-Radar")
    ap.add_argument("plz_pos", nargs="?", default=None, help="PLZ (positional, optional)")
    ap.add_argument("--plz", "--zip", dest="plz", default=None)
    ap.add_argument("--min-pct", type=float, default=30.0)
    ap.add_argument("--stores", default="", help="Komma-Liste, filtert nach Geschaeft")
    ap.add_argument("--sources", default="", help="Komma-Liste der Adapter (default alle)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    zip_code = args.plz or args.plz_pos or "1010"
    min_pct = args.min_pct
    store_filter = {s.strip().lower() for s in args.stores.split(",") if s.strip()}
    only_sources = {s.strip().lower() for s in args.sources.split(",") if s.strip()} or None
    global OUT
    if args.out:
        OUT = Path(args.out)

    log(f"Prospekt-Radar Lauf — PLZ {zip_code}, min −{min_pct:.0f}%")
    raw, counts = run_adapters(zip_code, only_sources)

    problems: list[str] = []
    for name, n in counts.items():
        if n == 0:
            problems.append(f"Quelle {name} lieferte 0 Treffer")

    # Dedupe
    offers = dedupe(raw)
    log(f"  nach Dedupe: {len(offers)} (von {len(raw)})")

    # Filter: Rabattschwelle, Gueltigkeit, optional Store
    today = today_vienna()
    kept: list[Offer] = []
    for o in offers:
        if o.effective_pct + 1e-9 < min_pct:
            continue
        if o.valid_to < today:                      # abgelaufen raus
            continue
        if store_filter and not any(sf in o.store.lower() for sf in store_filter):
            continue
        kept.append(o)
    kept.sort(key=lambda o: -o.effective_pct)
    log(f"  nach Filter (≥{min_pct:.0f}%, gültig, Store): {len(kept)}")

    # Historie: erst warnen (alte Daten), dann aktuelle Beobachtungen anhaengen
    hist = load_history()
    apply_history(kept, hist)
    append_history(kept)
    warned = sum(1 for o in kept if o.hist_warning)
    if warned:
        log(f"  ⚠ {warned} moegliche Scheinrabatte (Abweichung >10pp vom 90-Tage-Median)")

    # NEU-Diff + Monitoring gegen letzten Lauf
    prev_keys: set[str] = set()
    prev_count = None
    if LAST_RUN.exists():
        try:
            prev = json.loads(LAST_RUN.read_text(encoding="utf-8"))
            prev_keys = set(prev.get("keys", []))
            prev_count = prev.get("count")
        except Exception:
            pass

    if prev_count and len(kept) < prev_count * 0.5:
        problems.append(f"nur {len(kept)} Angebote — < 50% der Vorwoche ({prev_count})")

    meta = {
        "generated_at": now_vienna().strftime("%d.%m.%Y %H:%M"),
        "min_pct": int(min_pct), "zip": zip_code,
    }
    rows = to_rows(kept, prev_keys)
    write_outputs(rows, meta)
    n_new = sum(1 for r in rows if r["is_new"])
    log(f"  geschrieben: {OUT/'angebote.html'} ({len(rows)} Angebote, {n_new} NEU)")

    DATA.mkdir(parents=True, exist_ok=True)
    LAST_RUN.write_text(json.dumps({
        "generated_at": today_vienna().isoformat(), "count": len(kept),
        "keys": [o.key for o in kept],
    }, ensure_ascii=False), encoding="utf-8")

    if problems:
        for p in problems:
            log(f"  ✖ PROBLEM: {p}")
        return 2
    log("  ✓ Lauf ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
