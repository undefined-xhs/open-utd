import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.crossref import CrossrefClient, CrossrefError


def response(items, cursor=None):
    message = {"items":items}
    if cursor:
        message["next-cursor"] = cursor
    return io.BytesIO(json.dumps({"status":"ok","message":message}).encode())


def test_retries_fixed_window_and_reused_cursor(record):
    requests, delays = [], []
    responses = [HTTPError("hidden",429,"rate limited",{"Retry-After":"2"},None), response([record], "opaque"), response([record|{"DOI":"10.5555/second"}],"opaque"), response([])]
    def opener(request,**kwargs):
        requests.append(request)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    client = CrossrefClient("maintainer@real.org",rows=1,opener=opener,sleep=delays.append,interval=0)
    pages = list(client.works("1234-5679",from_date="2006-01-01",to_date="2026-10-16",indexed_until="2026-10-16T09:00:18Z",indexed_from="2026-10-14T17:00:18+08:00"))
    assert len(pages) == 3 and delays == [2]
    filters = [parse_qs(urlsplit(r.full_url).query)["filter"][0] for r in requests]
    assert len(set(filters)) == 1
    assert "until-index-date:2026-10-16T09:00:18" in filters[0]
    assert "from-index-date:2026-10-14T09:00:18" in filters[0]
    assert "Z" not in filters[0] and "+08" not in filters[0]
    assert parse_qs(urlsplit(requests[-1].full_url).query)["cursor"] == ["opaque"]


def test_missing_cursor_is_failure(record):
    client = CrossrefClient("maintainer@real.org",rows=1,opener=lambda *a,**k: response([record]),interval=0)
    with pytest.raises(CrossrefError,match="omitted cursor"):
        list(client.works("1234-5679",from_date="2006-01-01",to_date="2026-10-16",indexed_until="2026-10-16T09:00:00Z"))


def test_repeated_pages_are_rejected(record):
    client = CrossrefClient("maintainer@real.org",rows=1,opener=lambda *a,**k: response([record],"same"),interval=0)
    with pytest.raises(CrossrefError,match="repeated page"):
        list(client.works("1234-5679",from_date="2006-01-01",to_date="2026-10-16",indexed_until="2026-10-16T09:00:00Z"))


def test_bounded_5xx_retries():
    calls = []
    def opener(*args,**kwargs):
        calls.append(True)
        raise HTTPError("hidden",503,"unavailable",{},None)
    client = CrossrefClient("maintainer@real.org",retries=2,opener=opener,sleep=lambda _:None,interval=0)
    with pytest.raises(CrossrefError,match="HTTP 503"):
        client.get("/test",{})
    assert len(calls)==3
