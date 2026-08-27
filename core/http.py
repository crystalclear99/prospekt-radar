"""Hoeflicher HTTP-Client: identifizierbarer UA, max 1 Request/s pro Domain,
Retry mit exponentiellem Backoff, On-Disk-Cache mit TTL + ETag/If-Modified-Since.

Fairness laut Prompt Abschnitt 4. Kein Umgehen von Login/Bezahlung.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import httpx

USER_AGENT = (
    "ProspektRadar/0.1 (+privater Einkaufs-Preisvergleich, laeuft lokal; "
    "Kontakt: tomtom001xd@gmail.com)"
)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
_MIN_INTERVAL = 1.0          # Sekunden pro Domain
_last_request: dict[str, float] = {}


def _cache_key(method: str, url: str, params: Optional[dict]) -> Path:
    raw = json.dumps([method, url, params or {}], sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return _CACHE_DIR / f"{h}.json"


def _throttle(url: str) -> None:
    host = urlsplit(url).netloc
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_request.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.monotonic()


class PoliteClient:
    def __init__(self, ttl: float = 6 * 3600, timeout: float = 30.0,
                 extra_headers: Optional[dict] = None):
        self.ttl = ttl
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        self.last_error: Optional[str] = None
        self._client = httpx.Client(headers=headers, timeout=timeout,
                                    follow_redirects=True)
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._client.close()

    def get_json(self, url: str, params: Optional[dict] = None,
                 headers: Optional[dict] = None, retries: int = 3):
        """GET mit Cache/Conditional/Retry. Rueckgabe: geparstes JSON oder None."""
        text = self.get_text(url, params=params, headers=headers, retries=retries)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def get_text(self, url: str, params: Optional[dict] = None,
                 headers: Optional[dict] = None, retries: int = 3) -> Optional[str]:
        cache_path = _cache_key("GET", url, params)
        cached = None
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                cached = None
            if cached and (time.time() - cached.get("fetched_at", 0)) < self.ttl:
                return cached.get("body")

        cond = {}
        if cached:
            if cached.get("etag"):
                cond["If-None-Match"] = cached["etag"]
            if cached.get("last_modified"):
                cond["If-Modified-Since"] = cached["last_modified"]

        req_headers = dict(headers or {})
        req_headers.update(cond)

        backoff = 1.0
        for attempt in range(retries):
            _throttle(url)
            try:
                r = self._client.get(url, params=params, headers=req_headers)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                self.last_error = type(e).__name__
                time.sleep(backoff)
                backoff *= 2
                continue

            if r.status_code == 304 and cached:
                cached["fetched_at"] = time.time()
                cache_path.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
                return cached.get("body")

            if r.status_code == 200:
                entry = {
                    "body": r.text,
                    "etag": r.headers.get("ETag"),
                    "last_modified": r.headers.get("Last-Modified"),
                    "fetched_at": time.time(),
                }
                cache_path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
                return r.text

            if r.status_code in (429, 500, 502, 503, 504):
                self.last_error = f"HTTP {r.status_code}"
                time.sleep(backoff)
                backoff *= 2
                continue

            # 4xx (ausser 429): nicht wiederholen. Ursache protokollieren -
            # ein stilles None macht spaeter nicht nachvollziehbar, warum eine
            # Quelle nichts geliefert hat (z.B. Bot-Sperre gegen Rechenzentren).
            self.last_error = f"HTTP {r.status_code}"
            print(f"    ! {url.split('/')[2]}: HTTP {r.status_code} "
                  f"({r.headers.get('server', '?')})", file=sys.stderr)
            return None

        if self.last_error:
            print(f"    ! {url.split('/')[2]}: aufgegeben nach {retries} Versuchen "
                  f"({self.last_error})", file=sys.stderr)
        return None
