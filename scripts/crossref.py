"""Crossref HTTP client with bounded retries and fixed-window cursor pagination."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class CrossrefError(RuntimeError):
    pass


class CrossrefClient:
    def __init__(self, mailto: str, *, rows=1000, retries=5, timeout=90,
                 request_budget=1000, opener=urlopen, sleep=time.sleep, interval=0.25):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", mailto or "") or mailto.endswith("example.com"):
            raise ValueError("Set CROSSREF_MAILTO to a real maintainer contact email")
        if not 1 <= rows <= 1000:
            raise ValueError("Crossref rows must be 1..1000")
        self.mailto, self.rows, self.retries, self.timeout = mailto, rows, retries, timeout
        self.request_budget, self.requests = request_budget, 0
        self.opener, self.sleep, self.interval = opener, sleep, interval

    def _retry_delay(self, value, attempt):
        if value:
            try:
                return min(300, max(0, float(value)))
            except ValueError:
                try:
                    return min(300, max(0, (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()))
                except (ValueError, TypeError):
                    pass
        return min(60, 2 ** attempt)

    def get(self, path: str, params: dict) -> dict:
        url = "https://api.crossref.org" + path + "?" + urlencode({**params, "mailto": self.mailto})
        for attempt in range(self.retries+1):
            if self.requests >= self.request_budget:
                raise CrossrefError("Crossref request budget exhausted; no data promoted")
            self.requests += 1
            if self.interval:
                self.sleep(self.interval)
            request = Request(url, headers={"User-Agent": f"OpenUTD/0.1 (https://github.com/allenz-me/open-utd; mailto:{self.mailto})", "Accept": "application/json"})
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                if payload.get("status") != "ok" or not isinstance(payload.get("message"), dict):
                    raise CrossrefError("Malformed Crossref response envelope")
                return payload["message"]
            except HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == self.retries:
                    raise CrossrefError(f"Crossref HTTP {error.code}; request failed after {attempt+1} attempt(s)") from None
                self.sleep(self._retry_delay(error.headers.get("Retry-After"), attempt))
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
                if attempt == self.retries:
                    raise CrossrefError(f"Crossref transport/JSON failure ({type(error).__name__}) after {attempt+1} attempts") from None
                self.sleep(self._retry_delay(None, attempt))
        raise CrossrefError("Crossref retries exhausted")

    def works(self, issn: str, *, from_date: str, to_date: str,
              indexed_until: str, indexed_from: str | None = None):
        def api_timestamp(value):
            # Crossref's filter parser accepts UTC timestamps without a zone suffix.
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo:
                parsed = parsed.astimezone(timezone.utc)
            return parsed.strftime("%Y-%m-%dT%H:%M:%S")
        indexed_until = api_timestamp(indexed_until)
        indexed_from = api_timestamp(indexed_from) if indexed_from else None
        filters = ["type:journal-article", f"from-pub-date:{from_date}", f"until-pub-date:{to_date}", f"until-index-date:{indexed_until}"]
        if indexed_from:
            filters.append(f"from-index-date:{indexed_from}")
        params = {"filter": ",".join(filters), "rows": self.rows, "cursor": "*",
                  "select": "DOI,title,author,ISSN,volume,issue,published-print,published-online,published,issued,URL,type,page,indexed"}
        previous_fingerprint = None
        while True:
            message = self.get(f"/journals/{issn}/works", params)
            items = message.get("items")
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise CrossrefError("Crossref page lacks an items array")
            # Crossref may legitimately reuse the same opaque cursor. Detect repeated pages,
            # not repeated cursors, to avoid both infinite loops and false failures.
            fingerprint = tuple(item.get("DOI") or json.dumps(item, sort_keys=True) for item in items)
            if items and fingerprint == previous_fingerprint:
                raise CrossrefError("Crossref returned a repeated page; refusing an incomplete sync")
            previous_fingerprint = fingerprint
            yield items
            if len(items) < self.rows:
                break
            next_cursor = message.get("next-cursor")
            if not next_cursor:
                raise CrossrefError("Crossref omitted cursor before the final page")
            params["cursor"] = next_cursor
