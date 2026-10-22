import io
import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError

import pytest

from scripts import fetch_analytics as analytics


NOW = datetime(2026, 10, 17, 3, 4, 5, tzinfo=timezone.utc)
ACCOUNT = "a" * 32
SITE = "b" * 32
SCHEMA = ("AccountFilter!", "RumFilter!")


def group(count, **dimensions):
    return {"count": count, "dimensions": dimensions}


def response(daily=None, countries=None, pages=None):
    account = {"countries": countries or [], "pages": pages or []}
    if daily is not None:
        account["daily"] = daily
    return {"viewer": {"accounts": [account]}}


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def query(self, query, variables):
        self.calls.append((query, variables))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


def fetch(monkeypatch, responses=None, **kwargs):
    monkeypatch.setattr(analytics, "discover_schema", lambda client: SCHEMA)
    client = FakeClient(responses or [response(daily=[]), response()])
    result = analytics.fetch_snapshot(client, ACCOUNT, SITE, "https://www.open-utd-hot-take.xyz", now=NOW, **kwargs)
    return result, client


def test_complete_utc_windows_share_daily_series_and_queries_are_aggregate_only(monkeypatch):
    payload, client = fetch(monkeypatch, [
        response(daily=[group(3, date="2026-09-17"), group(12, date="2026-10-09"), group(5, date="2026-10-16")],
                 countries=[group(8, countryName="US"), group(12, countryName="CN")],
                 pages=[group(7, requestPath="/"), group(5, requestPath="/search/?q=private+search#results")]),
        response(countries=[group(5, countryName="CN")], pages=[group(5, requestPath="/")]),
    ])
    assert payload["status"] == "ready"
    assert payload["updated_at"] == "2026-10-17T03:04:05Z"
    month, week = payload["periods"]["30"], payload["periods"]["7"]
    assert (month["start_date"], month["end_date"], month["page_views"]) == ("2026-09-17", "2026-10-16", 20)
    assert (week["start_date"], week["end_date"], week["page_views"]) == ("2026-10-10", "2026-10-16", 5)
    assert len(month["daily"]) == 30
    assert month["daily"][-7:] == week["daily"]
    assert week["daily"][0] == {"date": "2026-10-10", "page_views": 0, "visits": None}
    assert month["countries"] == [{"country_code": "CN", "page_views": 12}, {"country_code": "US", "page_views": 8}]
    assert month["pages"][-1] == {"path": "/search/", "page_views": 5}
    assert "private" not in json.dumps(payload)
    assert len(client.calls) == 2
    for index, (query, variables) in enumerate(client.calls):
        assert "rumPageloadEventsAdaptiveGroups" in query
        assert "httpRequests" not in query and "referer" not in query and "userAgent" not in query
        assert ("daily:" in query) == (index == 0)
        assert "limit: 10" in query and "limit: 300" in query
        assert variables == {"account": {"accountTag": ACCOUNT}, "filter": {
            "siteTag": SITE, "requestHost": "www.open-utd-hot-take.xyz",
            "datetime_geq": "2026-09-17T00:00:00Z" if index == 0 else "2026-10-10T00:00:00Z",
            "datetime_lt": "2026-10-17T00:00:00Z"}}


def test_empty_success_is_real_zero_but_offline_placeholder_is_not(monkeypatch):
    payload, _ = fetch(monkeypatch)
    assert payload["periods"]["30"]["page_views"] == 0
    assert analytics.empty_snapshot() == {"schema_version": 1, "status": "unavailable", "source": analytics.SOURCE,
                                          "updated_at": None, "timezone": "UTC", "periods": {}}


def test_clock_is_converted_to_utc_before_selecting_window(monkeypatch):
    monkeypatch.setattr(analytics, "discover_schema", lambda client: SCHEMA)
    client = FakeClient([response(daily=[]), response()])
    payload = analytics.fetch_snapshot(client, ACCOUNT, SITE, "https://www.open-utd-hot-take.xyz",
                                      now=datetime(2026, 10, 17, 2, 0, tzinfo=timezone(timedelta(hours=8))))
    assert payload["periods"]["7"]["end_date"] == "2026-10-15"
    assert payload["updated_at"] == "2026-10-16T18:00:00Z"


@pytest.mark.parametrize("bad_rows", [
    [group(1, date="2026-10-17")], [group(1, date="2026-09-16")],
    [group(1, date="2026-10-16"), group(2, date="2026-10-16")],
    [group(1, date="2026-02-30")], [group(-1, date="2026-10-16")],
    [group(True, date="2026-10-16")], [group(1.5, date="2026-10-16")],
    [group(2**53, date="2026-10-16")], [group(1, date="2026-10-16")] * 31,
])
def test_bad_or_truncated_daily_groups_fail(monkeypatch, bad_rows):
    with pytest.raises(analytics.AnalyticsError):
        fetch(monkeypatch, [response(daily=bad_rows)])


@pytest.mark.parametrize("field,rows", [
    ("countries", [group(1, countryName="US")] * 300),
    ("countries", [group(1, countryName="person@example.org")]),
    ("countries", [group(1, countryName="US"), group(2, countryName="US")]),
    ("pages", [group(1, requestPath="/")] * 11),
    ("pages", [group(1, requestPath="/"), group(2, requestPath="/")]),
    ("pages", [group(1, requestPath=None)]),
])
def test_malformed_rankings_and_country_limit_fail(monkeypatch, field, rows):
    args = {field: rows, "daily": []}
    with pytest.raises(analytics.AnalyticsError):
        fetch(monkeypatch, [response(**args)])


def test_country_ranking_is_bounded_and_unknown_is_normalized(monkeypatch):
    countries = [group(index, countryName="A" + chr(65 + index)) for index in range(12)]
    countries += [group(15, countryName="")]
    payload, _ = fetch(monkeypatch, [response(daily=[], countries=countries), response()])
    rows = payload["periods"]["30"]["countries"]
    assert len(rows) == 10
    assert rows[0] == {"country_code": "ZZ", "page_views": 15}


def test_cloudflare_special_country_codes_merge_without_losing_views(monkeypatch):
    countries = [group(2, countryName=""), group(3, countryName="XX"),
                 group(5, countryName="T1"), group(7, countryName="ZZ"),
                 group(11, countryName="CN")]
    payload, _ = fetch(monkeypatch, [
        response(daily=[group(28, date="2026-10-16")], countries=countries),
        response(countries=countries),
    ])
    for period in payload["periods"].values():
        assert period["page_views"] == 28
        assert period["countries"] == [{"country_code": "ZZ", "page_views": 17},
                                       {"country_code": "CN", "page_views": 11}]


@pytest.mark.parametrize("code", [None, 1, [], {}, "T2", "us", "Unknown", "United States"])
def test_unsupported_country_values_still_fail(monkeypatch, code):
    with pytest.raises(analytics.AnalyticsError, match="invalid country code"):
        fetch(monkeypatch, [response(daily=[], countries=[group(1, countryName=code)])])


@pytest.mark.parametrize("code", ["", "XX", "T1", "ZZ"])
def test_duplicate_special_country_groups_still_fail(monkeypatch, code):
    with pytest.raises(analytics.AnalyticsError, match="duplicate country groups"):
        fetch(monkeypatch, [response(daily=[], countries=[group(1, countryName=code),
                                                       group(2, countryName=code)])])


@pytest.mark.parametrize("raw,expected", [
    ("/", "/"), ("/search?q=secret#result", "/search/"),
    ("/articles/a_one", "/articles/a_one/"), ("/journals/test-journal/years/2026/", "/journals/test-journal/years/2026/"),
    ("/journals/test-journal/issues/i_123/", "/journals/test-journal/issues/i_123/"),
    ("/journals/test-journal/online-first/2/", "/journals/test-journal/online-first/2/"),
    ("https://example.org/search/", None), ("https://www.open-utd-hot-take.xyz/search/", None),
    ("//example.org/search/", None), ("/\\evil/search/", None), ("/search/../privacy/", None),
    ("/search/%2e%2e/privacy/", None), ("/%2f%2fevil.org/", None), ("/search/\n", None),
    ("/private/person@example.org/", None), ("/404/", None), ("/arbitrary-path/", None),
    ("/journals/test/online-first/0/", None), ("javascript:alert(1)", None),
])
def test_only_safe_public_route_shapes_are_published(raw, expected):
    assert analytics.public_path(raw) == expected


def test_base_path_is_removed_and_mismatched_paths_are_excluded(monkeypatch):
    payload, _ = fetch(monkeypatch, [response(daily=[], pages=[
        group(9, requestPath="/catalog/search/?q=secret"),
        group(8, requestPath="/search/"), group(7, requestPath="/catalog/404/")]), response()], base_path="/catalog/")
    assert payload["periods"]["30"]["pages"] == [{"path": "/search/", "page_views": 9}]


@pytest.mark.parametrize("data", [{}, {"viewer": {}}, {"viewer": {"accounts": []}}, {"viewer": {"accounts": [{}, {}]}},
                                   {"viewer": {"accounts": [{"daily": [], "pages": []}]}}])
def test_missing_or_ambiguous_account_and_missing_groups_fail(monkeypatch, data):
    with pytest.raises(analytics.AnalyticsError):
        fetch(monkeypatch, [data])


def type_ref(name, kind="OBJECT"):
    return {"kind": kind, "name": name}


def schema_fixture():
    def field(name, typename, args=None):
        return {"name": name, "type": type_ref(typename), "args": args or []}

    def arg(name, typename):
        return {"name": name, "type": {"kind": "NON_NULL", "name": None, "ofType": type_ref(typename, "INPUT_OBJECT")}}

    def names(*values):
        return [{"name": value} for value in values]

    root = {"__schema": {"queryType": {"fields": [field("viewer", "Viewer")]}}}
    types = {
        "Viewer": {"fields": [field("accounts", "Account", [arg("filter", "AccountFilter")])]},
        "AccountFilter": {"inputFields": names("accountTag")},
        "Account": {"fields": [field(analytics.DATASET, "RumGroup", [arg("filter", "RumFilter"), arg("limit", "Int"), arg("orderBy", "RumOrder")])]},
        "RumFilter": {"inputFields": names("siteTag", "requestHost", "datetime_geq", "datetime_lt")},
        "RumGroup": {"fields": [field("count", "UInt64"), field("dimensions", "RumDimensions")]},
        "RumDimensions": {"fields": [field("date", "Date"), field("countryName", "String"), field("requestPath", "String")]},
        "RumOrder": {"enumValues": names("date_ASC", "count_DESC")},
    }
    return root, types


def test_schema_types_and_required_fields_are_discovered_from_api():
    root, types = schema_fixture()

    class SchemaClient:
        def query(self, query, variables):
            if query == analytics.ROOT_QUERY:
                return root
            assert query == analytics.TYPE_QUERY
            return {"__type": types[variables["name"]]}

    assert analytics.discover_schema(SchemaClient()) == SCHEMA
    types["RumFilter"]["inputFields"] = [{"name": "siteTag"}]
    with pytest.raises(analytics.AnalyticsError, match="filtering"):
        analytics.discover_schema(SchemaClient())


def test_graphql_errors_with_http_200_fail_without_exposing_response(monkeypatch):
    secret = "sensitive-test-token"
    raw = json.dumps({"data": {"private": "must-not-appear"}, "errors": [
        {"message": "Unknown field requestPath: " + secret + "\n" + "x" * 1000, "private": "must-not-appear"}]}).encode()
    monkeypatch.setattr(analytics, "urlopen", lambda *args, **kwargs: io.BytesIO(raw))
    with pytest.raises(analytics.AnalyticsError, match="errors") as error:
        analytics.CloudflareClient(secret).query("query {}", {})
    assert secret not in str(error.value)
    assert "must-not-appear" not in str(error.value)
    assert "Unknown field requestPath" in str(error.value)
    assert "[redacted]" in str(error.value)
    assert "\n" not in str(error.value)
    assert len(str(error.value)) < 400


def test_network_failure_retries_and_http_permission_failure_does_not(monkeypatch):
    calls, sleeps = [], []

    def fail(*args, **kwargs):
        calls.append(1)
        raise URLError("sensitive connection details")

    monkeypatch.setattr(analytics, "urlopen", fail)
    monkeypatch.setattr(analytics.time, "sleep", sleeps.append)
    with pytest.raises(analytics.AnalyticsError, match="network"):
        analytics.CloudflareClient("test-token").query("query {}", {})
    assert len(calls) == 3 and sleeps == [1, 2]
    monkeypatch.setattr(analytics, "urlopen", lambda *a, **k: (_ for _ in ()).throw(HTTPError(analytics.ENDPOINT, 403, "forbidden", {}, None)))
    with pytest.raises(analytics.AnalyticsError, match="HTTP 403"):
        analytics.CloudflareClient("test-token").query("query {}", {})
    assert sleeps == [1, 2]


def test_client_budget_and_response_size_are_bounded(monkeypatch):
    with pytest.raises(analytics.AnalyticsError, match="budget"):
        analytics.CloudflareClient("test-token", max_requests=0).query("query {}", {})
    monkeypatch.setattr(analytics, "urlopen", lambda *args, **kwargs: io.BytesIO(b" " * (analytics.MAX_RESPONSE_BYTES + 1)))
    with pytest.raises(analytics.AnalyticsError, match="response limit"):
        analytics.CloudflareClient("test-token").query("query {}", {})


@pytest.mark.parametrize("mutate", [
    lambda data: data.update(ip="192.0.2.1"),
    lambda data: data.update(updated_at="2026-10-17T03:04:05+08:00"),
    lambda data: data["periods"]["7"].update(end_date="2026-10-17"),
    lambda data: data["periods"]["7"].update(page_views=1),
    lambda data: data["periods"]["7"]["daily"].pop(),
    lambda data: data["periods"]["30"]["daily"][0].update(date="2026-09-18"),
    lambda data: data["periods"]["7"].update(pages=[{"path": "/search/?q=secret", "page_views": 1}]),
    lambda data: data["periods"]["7"].update(pages=[{"path": "https://evil.org/", "page_views": 1}]),
    lambda data: data["periods"]["7"].update(countries=[{"country_code": "US", "page_views": False}]),
])
def test_public_snapshot_rejects_private_fields_bad_dates_and_inconsistent_totals(monkeypatch, mutate):
    payload, _ = fetch(monkeypatch)
    mutate(payload)
    with pytest.raises(analytics.AnalyticsError):
        analytics.validate_snapshot(payload)


def test_failed_fetch_and_oversize_write_preserve_existing_snapshot(tmp_path, monkeypatch):
    output = tmp_path / "analytics.json"
    output.write_text("previous snapshot")
    monkeypatch.setenv("CLOUDFLARE_ANALYTICS_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT)
    monkeypatch.setenv("CLOUDFLARE_WEB_ANALYTICS_SITE_TAG", SITE)
    monkeypatch.setattr(analytics, "fetch_snapshot", lambda *args, **kwargs: (_ for _ in ()).throw(analytics.AnalyticsError("failed")))
    with pytest.raises(SystemExit) as error:
        analytics.main(["--out", str(output)])
    assert error.value.code == 1
    assert output.read_text() == "previous snapshot"
    with pytest.raises(analytics.AnalyticsError, match="exceeds"):
        analytics.write_snapshot(output, analytics.empty_snapshot(), max_bytes=1)
    assert output.read_text() == "previous snapshot"
    assert list(tmp_path.iterdir()) == [output]


def test_ensure_empty_is_offline_and_preserves_existing_snapshot(tmp_path, monkeypatch):
    output = tmp_path / "analytics.json"
    monkeypatch.setattr(analytics, "urlopen", lambda *args, **kwargs: pytest.fail("Offline bootstrap must not call Cloudflare"))
    analytics.main(["--ensure-empty", "--out", str(output)])
    assert json.loads(output.read_text()) == analytics.empty_snapshot()
    output.write_text("existing live snapshot")
    analytics.main(["--ensure-empty", "--out", str(output)])
    assert output.read_text() == "existing live snapshot"


def test_partial_configuration_fails_without_replacing_output(tmp_path, monkeypatch):
    output = tmp_path / "analytics.json"
    output.write_text("existing")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT)
    monkeypatch.delenv("CLOUDFLARE_WEB_ANALYTICS_SITE_TAG", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ANALYTICS_API_TOKEN", raising=False)
    with pytest.raises(SystemExit) as error:
        analytics.main(["--out", str(output)])
    assert error.value.code == 2
    assert output.read_text() == "existing"


def test_all_empty_configuration_writes_unavailable_without_network(tmp_path, monkeypatch):
    output = tmp_path / "analytics.json"
    output.write_text("existing published data")
    for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WEB_ANALYTICS_SITE_TAG", "CLOUDFLARE_ANALYTICS_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(analytics, "urlopen", lambda *args, **kwargs: pytest.fail("Unconfigured analytics must stay offline"))
    analytics.main(["--out", str(output)])
    assert json.loads(output.read_text()) == analytics.empty_snapshot()
