"""Export aggregate Cloudflare Web Analytics data for the public statistics page.

Only daily totals, country totals and the ten most viewed public paths are read.
This never reads individual events, IPs, referrers, or search queries. Cloudflare's
GraphQL schema is dynamic, so required fields and argument types are discovered
before querying. See the official schema and pagination documentation:
https://developers.cloudflare.com/analytics/graphql-api/features/discovery/introspection/
https://developers.cloudflare.com/analytics/graphql-api/features/pagination/

Every window ends at the latest complete UTC day. API and validation failures
leave the previous snapshot intact. --ensure-empty is an offline bootstrap only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ENDPOINT = "https://api.cloudflare.com/client/v4/graphql"
DATASET = "rumPageloadEventsAdaptiveGroups"
SOURCE = "Cloudflare Web Analytics"
MAX_SAFE_INTEGER = 2**53 - 1
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
COUNTRY_LIMIT = 300
TOP_LIMIT = 10
TYPE_REF = "kind name ofType { kind name ofType { kind name ofType { kind name } } }"
FIELD_INFO = "name type { " + TYPE_REF + " } args { name type { " + TYPE_REF + " } }"
ROOT_QUERY = "query AnalyticsRoot { __schema { queryType { fields { " + FIELD_INFO + " } } } }"
TYPE_QUERY = """query AnalyticsType($name: String!) {
  __type(name: $name) {
    fields { FIELD_INFO }
    inputFields { name }
    enumValues { name }
  }
}""".replace("FIELD_INFO", FIELD_INFO)
STATIC_PATHS = {"/", "/journals/", "/comments/", "/search/", "/analytics/",
                "/about/", "/data-sources/", "/guidelines/", "/privacy/"}
PUBLIC_ROUTE = re.compile(
    r"(?:/articles/a_[A-Za-z0-9_-]+/|/journals/[a-z0-9]+(?:-[a-z0-9]+)*/"
    r"(?:(?:reviews/)|(?:years/(?:[0-9]{4}|undated)/)|(?:online-first/[1-9][0-9]*/)|"
    r"(?:issues/i_[A-Za-z0-9_-]+/))?)"
)


class AnalyticsError(RuntimeError):
    pass


class CloudflareClient:
    def __init__(self, token: str, max_requests: int = 30):
        self.token = token
        self.max_requests = max_requests
        self.requests = 0

    def query(self, query: str, variables: dict) -> dict:
        request = Request(ENDPOINT, method="POST",
                          data=json.dumps({"query": query, "variables": variables}).encode(),
                          headers={"Authorization": f"Bearer {self.token}",
                                   "Content-Type": "application/json", "Accept": "application/json",
                                   "User-Agent": "open-utd-analytics/1.0"})
        for attempt in range(3):
            if self.requests >= self.max_requests:
                raise AnalyticsError("Cloudflare query budget exhausted; previous snapshot retained")
            self.requests += 1
            try:
                with urlopen(request, timeout=45) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise AnalyticsError("Cloudflare response exceeds the aggregate response limit")
                result = json.loads(raw)
                break
            except HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise AnalyticsError(f"Cloudflare GraphQL HTTP {error.code}; previous snapshot retained") from error
            except (URLError, TimeoutError) as error:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise AnalyticsError("Cloudflare network request failed; previous snapshot retained") from error
            except (ValueError, UnicodeError) as error:
                raise AnalyticsError("Cloudflare returned invalid JSON; previous snapshot retained") from error
        if not isinstance(result, dict) or result.get("errors") or not isinstance(result.get("data"), dict):
            # Print only bounded, token-redacted diagnostic messages, never data.
            messages = []
            errors = result.get("errors") if isinstance(result, dict) else None
            if isinstance(errors, list):
                for error in errors[:3]:
                    message = error.get("message") if isinstance(error, dict) else None
                    if isinstance(message, str):
                        message = message.replace(self.token, "[redacted]") if self.token else message
                        messages.append(re.sub(r"[\x00-\x20\x7f]+", " ", message).strip()[:240])
            detail = ": " + "; ".join(messages) if messages else ""
            raise AnalyticsError("Cloudflare GraphQL returned errors or incomplete data; check permissions, schema and limits" + detail)
        return result["data"]


def _named_type(reference: dict) -> str:
    while isinstance(reference, dict):
        name = reference.get("name")
        if isinstance(name, str) and re.fullmatch(r"[_A-Za-z][_0-9A-Za-z]*", name):
            return name
        reference = reference.get("ofType")
    raise AnalyticsError("Cloudflare schema is missing a type name")


def _type_expression(reference: dict) -> str:
    if not isinstance(reference, dict):
        raise AnalyticsError("Cloudflare schema is missing an argument type")
    if reference.get("kind") == "NON_NULL":
        return _type_expression(reference.get("ofType")) + "!"
    if reference.get("kind") == "LIST":
        return "[" + _type_expression(reference.get("ofType")) + "]"
    return _named_type(reference)


def _fields(value: dict, key: str) -> dict:
    rows = value.get(key) if isinstance(value, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in rows):
        raise AnalyticsError("Cloudflare schema discovery returned incomplete fields")
    return {row["name"]: row for row in rows}


def discover_schema(client) -> tuple[str, str]:
    """Resolve types from Cloudflare itself; never assume undocumented type names."""
    cache = {}

    def inspect(reference):
        name = _named_type(reference)
        if name not in cache:
            result = client.query(TYPE_QUERY, {"name": name}).get("__type")
            if not isinstance(result, dict):
                raise AnalyticsError("Required Cloudflare analytics type is unavailable")
            cache[name] = result
        return cache[name]

    try:
        root = client.query(ROOT_QUERY, {})["__schema"]["queryType"]
        viewer = _fields(root, "fields")["viewer"]
        accounts = _fields(inspect(viewer["type"]), "fields")["accounts"]
        account_filter = _fields(accounts, "args")["filter"]["type"]
        if "accountTag" not in _fields(inspect(account_filter), "inputFields"):
            raise AnalyticsError("Cloudflare account filtering is unavailable")
        dataset = _fields(inspect(accounts["type"]), "fields")[DATASET]
        args = _fields(dataset, "args")
        if not {"filter", "limit", "orderBy"} <= args.keys():
            raise AnalyticsError("Cloudflare aggregate query arguments changed")
        filter_type = args["filter"]["type"]
        filter_fields = _fields(inspect(filter_type), "inputFields")
        if not {"siteTag", "requestHost", "datetime_geq", "datetime_lt"} <= filter_fields.keys():
            raise AnalyticsError("Cloudflare RUM site, host or time filtering is unavailable")
        group = _fields(inspect(dataset["type"]), "fields")
        if not {"count", "dimensions"} <= group.keys():
            raise AnalyticsError("Cloudflare RUM page-view fields are unavailable")
        dimensions = _fields(inspect(group["dimensions"]["type"]), "fields")
        if not {"date", "countryName", "requestPath"} <= dimensions.keys():
            raise AnalyticsError("Cloudflare RUM public aggregate dimensions are unavailable")
        orders = _fields(inspect(args["orderBy"]["type"]), "enumValues")
        if not {"date_ASC", "count_DESC"} <= orders.keys():
            raise AnalyticsError("Cloudflare RUM sorting fields are unavailable")
        return _type_expression(account_filter), _type_expression(filter_type)
    except (KeyError, TypeError, AttributeError) as error:
        raise AnalyticsError("Cloudflare RUM schema is incomplete or changed") from error


def aggregate_query(schema: tuple[str, str], include_daily: bool) -> str:
    daily = f"""daily: {DATASET}(filter: $filter, limit: 30, orderBy: [date_ASC]) {{
        count dimensions {{ date }}
      }}""" if include_daily else ""
    return f"""query PublicAnalytics($account: {schema[0]}, $filter: {schema[1]}) {{
  viewer {{ accounts(filter: $account) {{
      {daily}
      countries: {DATASET}(filter: $filter, limit: {COUNTRY_LIMIT}, orderBy: [count_DESC]) {{
        count dimensions {{ countryName }}
      }}
      pages: {DATASET}(filter: $filter, limit: {TOP_LIMIT}, orderBy: [count_DESC]) {{
        count dimensions {{ requestPath }}
      }}
  }} }}
}}"""


def _integer(value, label: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
        raise AnalyticsError(f"Invalid {label}; expected a nonnegative safe integer")
    return value


def _date(value) -> date:
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError as error:
        raise AnalyticsError("Invalid analytics UTC date") from error


def _timestamp(value) -> datetime:
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
            raise ValueError
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AnalyticsError("Invalid analytics UTC timestamp") from error


def public_path(raw, base_path: str = "") -> str | None:
    """Keep only known route shapes; discard queries, fragments and unsafe paths."""
    if not isinstance(raw, str) or len(raw) > 2048 or re.search(r"[\x00-\x20\x7f\\]", raw):
        return None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or raw.startswith("//"):
        return None
    path = parsed.path
    # Percent escapes and dot segments are unnecessary for the public route IDs.
    if "%" in path or any(part in {".", ".."} for part in path.split("/")) or "//" in path:
        return None
    base = "/" + base_path.strip("/") if base_path.strip("/") else ""
    if base:
        if path == base:
            path = "/"
        elif path.startswith(base + "/"):
            path = path[len(base):]
        else:
            return None
    path = path.rstrip("/") + "/"
    return path if path in STATIC_PATHS or PUBLIC_ROUTE.fullmatch(path) else None


def _rows(account: dict, name: str, limit: int, *, complete: bool = False) -> list:
    rows = account.get(name)
    if not isinstance(rows, list) or len(rows) > limit or (complete and len(rows) == limit):
        raise AnalyticsError(f"Cloudflare {name} groups are missing, truncated or exceed their limit")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("dimensions"), dict):
            raise AnalyticsError(f"Cloudflare {name} group is incomplete")
        _integer(row.get("count"), "page-view count")
    return rows


def _account(data: dict) -> dict:
    viewer = data.get("viewer")
    accounts = viewer.get("accounts") if isinstance(viewer, dict) else None
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        raise AnalyticsError("Cloudflare account is unavailable or ambiguous")
    return accounts[0]


def fetch_snapshot(client, account_id: str, site_tag: str, site_url: str,
                   base_path: str = "", now: datetime | None = None) -> dict:
    if not all(isinstance(value, str) and re.fullmatch(r"[a-fA-F0-9]{32}", value) for value in (account_id, site_tag)):
        raise AnalyticsError("Cloudflare account ID and Web Analytics site tag must be 32 hexadecimal characters")
    try:
        site = urlsplit(site_url)
        if site.scheme != "https" or not site.hostname or site.username or site.password or site.port or site.query or site.fragment:
            raise ValueError
    except ValueError as error:
        raise AnalyticsError("PUBLIC_SITE_URL must be the HTTPS website URL") from error
    if base_path and not re.fullmatch(r"/?[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?", base_path) and base_path != "/":
        raise AnalyticsError("Invalid PUBLIC_BASE_PATH")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise AnalyticsError("Analytics collection time must include a timezone")
    now = now.astimezone(timezone.utc)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    schema = discover_schema(client)
    periods, daily = {}, []
    for days in (30, 7):
        start = end - timedelta(days=days)
        filters = {"siteTag": site_tag, "requestHost": site.hostname,
                   "datetime_geq": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "datetime_lt": end.strftime("%Y-%m-%dT%H:%M:%SZ")}
        result = _account(client.query(aggregate_query(schema, days == 30),
                                      {"account": {"accountTag": account_id}, "filter": filters}))
        if days == 30:
            by_date = {}
            for row in _rows(result, "daily", 30):
                key = _date(row["dimensions"].get("date"))
                if not start.date() <= key < end.date() or key in by_date:
                    raise AnalyticsError("Cloudflare daily dates are duplicated or outside the requested UTC window")
                by_date[key] = row["count"]
            # Missing groups in a successful complete response mean no recorded views.
            daily = [{"date": (start.date() + timedelta(days=index)).isoformat(),
                      "page_views": by_date.get(start.date() + timedelta(days=index), 0), "visits": None}
                     for index in range(30)]
        countries, pages, seen_countries = {}, {}, set()
        for row in _rows(result, "countries", COUNTRY_LIMIT, complete=True):
            code = row["dimensions"].get("countryName")
            if not isinstance(code, str) or (code not in {"", "T1"} and not re.fullmatch(r"[A-Z]{2}", code)):
                raise AnalyticsError("Cloudflare returned an invalid country code")
            if code in seen_countries:
                raise AnalyticsError("Cloudflare returned duplicate country groups")
            seen_countries.add(code)
            # Cloudflare also emits XX (unknown) and T1 (Tor), neither a location.
            # https://developers.cloudflare.com/waf/tools/ip-access-rules/parameters/
            code = "ZZ" if code in {"", "XX", "T1"} else code
            countries[code] = countries.get(code, 0) + row["count"]
        seen_paths = set()
        for row in _rows(result, "pages", TOP_LIMIT):
            raw = row["dimensions"].get("requestPath")
            if not isinstance(raw, str) or raw in seen_paths:
                raise AnalyticsError("Cloudflare returned invalid or duplicate page groups")
            seen_paths.add(raw)
            path = public_path(raw, base_path)
            if path:
                pages[path] = pages.get(path, 0) + row["count"]
        period_daily = daily[-days:]
        periods[str(days)] = {
            "start_date": start.date().isoformat(), "end_date": (end.date() - timedelta(days=1)).isoformat(),
            "page_views": sum(row["page_views"] for row in period_daily), "visits": None,
            "daily": period_daily,
            "countries": [{"country_code": code, "page_views": count} for code, count in
                          sorted(countries.items(), key=lambda pair: (-pair[1], pair[0]))[:TOP_LIMIT]],
            "pages": [{"path": path, "page_views": count} for path, count in
                      sorted(pages.items(), key=lambda pair: (-pair[1], pair[0]))[:TOP_LIMIT]],
        }
    return validate_snapshot({"schema_version": 1, "status": "ready", "source": SOURCE,
                              "updated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                              "timezone": "UTC", "periods": periods})


def empty_snapshot() -> dict:
    return {"schema_version": 1, "status": "unavailable", "source": SOURCE,
            "updated_at": None, "timezone": "UTC", "periods": {}}


def _keys(value, expected: set[str], label: str):
    if not isinstance(value, dict) or set(value) != expected:
        raise AnalyticsError(f"Invalid {label} fields; only public aggregate fields are allowed")


def validate_snapshot(payload: dict) -> dict:
    """Strict public schema validator, shared by fetch, compare and artifact patch."""
    _keys(payload, {"schema_version", "status", "source", "updated_at", "timezone", "periods"}, "snapshot")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["source"] != SOURCE or payload["timezone"] != "UTC":
        raise AnalyticsError("Unsupported analytics snapshot schema or source")
    if payload["status"] == "unavailable":
        if payload["updated_at"] is not None or payload["periods"] != {}:
            raise AnalyticsError("Unavailable analytics must not claim a successful timestamp or zero traffic")
        return payload
    if payload["status"] != "ready":
        raise AnalyticsError("Invalid analytics snapshot status")
    updated = _timestamp(payload["updated_at"])
    _keys(payload["periods"], {"7", "30"}, "periods")
    for days in (7, 30):
        period = payload["periods"][str(days)]
        _keys(period, {"start_date", "end_date", "page_views", "visits", "daily", "countries", "pages"}, "period")
        start, end = _date(period["start_date"]), _date(period["end_date"])
        if (end - start).days != days - 1 or end != updated.date() - timedelta(days=1):
            raise AnalyticsError("Analytics window must contain the most recent complete UTC days")
        _integer(period["page_views"], "period page views")
        if period["visits"] is not None:
            raise AnalyticsError("Visits are not collected by this snapshot version")
        if not isinstance(period["daily"], list) or len(period["daily"]) != days:
            raise AnalyticsError("Analytics daily series is incomplete")
        for index, row in enumerate(period["daily"]):
            _keys(row, {"date", "page_views", "visits"}, "daily row")
            if _date(row["date"]) != start + timedelta(days=index) or row["visits"] is not None:
                raise AnalyticsError("Analytics daily series is unordered or invalid")
            _integer(row["page_views"], "daily page views")
        if sum(row["page_views"] for row in period["daily"]) != period["page_views"]:
            raise AnalyticsError("Analytics period total does not match its daily series")
        for field, key in (("countries", "country_code"), ("pages", "path")):
            rows = period[field]
            if not isinstance(rows, list) or len(rows) > TOP_LIMIT:
                raise AnalyticsError("Public analytics ranking exceeds its limit")
            seen = set()
            for row in rows:
                _keys(row, {key, "page_views"}, "ranking row")
                value = row[key]
                _integer(row["page_views"], "ranking page views")
                if not isinstance(value, str) or value in seen:
                    raise AnalyticsError("Invalid or duplicate public analytics dimension")
                seen.add(value)
                if key == "country_code" and not re.fullmatch(r"[A-Z]{2}", value):
                    raise AnalyticsError("Invalid public country code")
                if key == "path" and public_path(value) != value:
                    raise AnalyticsError("Invalid public page path")
            if rows != sorted(rows, key=lambda row: (-row["page_views"], row[key])):
                raise AnalyticsError("Public analytics ranking is not sorted")
    if payload["periods"]["7"]["daily"] != payload["periods"]["30"]["daily"][-7:]:
        raise AnalyticsError("Analytics windows disagree on overlapping days")
    return payload


def write_snapshot(output: Path, payload: dict, max_bytes: int = 64 * 1024) -> int:
    validate_snapshot(payload)
    encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(encoded) > max_bytes:
        raise AnalyticsError("Public analytics snapshot exceeds 64 KiB")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".analytics-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
        os.replace(temporary, output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return len(encoded)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", default=os.getenv("CLOUDFLARE_ACCOUNT_ID"))
    parser.add_argument("--site-tag", default=os.getenv("CLOUDFLARE_WEB_ANALYTICS_SITE_TAG"))
    parser.add_argument("--site-url", default=os.getenv("PUBLIC_SITE_URL") or "https://www.open-utd-hot-take.xyz")
    parser.add_argument("--base-path", default=os.getenv("PUBLIC_BASE_PATH", ""))
    parser.add_argument("--out", type=Path, default=Path("public/data/analytics.json"))
    parser.add_argument("--ensure-empty", action="store_true", help="Create an unavailable placeholder only if no file exists; never calls the API")
    args = parser.parse_args(argv)
    if args.ensure_empty:
        if not args.out.exists():
            write_snapshot(args.out, empty_snapshot())
        return
    token = os.getenv("CLOUDFLARE_ANALYTICS_API_TOKEN", "").strip()
    if not token and not args.account_id and not args.site_tag:
        write_snapshot(args.out, empty_snapshot())
        print("Cloudflare public analytics is unconfigured; published an unavailable placeholder")
        return
    if not token or not args.account_id or not args.site_tag:
        parser.error("CLOUDFLARE_ANALYTICS_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_WEB_ANALYTICS_SITE_TAG are required; use --ensure-empty only for offline setup")
    try:
        snapshot = fetch_snapshot(CloudflareClient(token), args.account_id, args.site_tag, args.site_url, args.base_path)
        size = write_snapshot(args.out, snapshot)
    except AnalyticsError as error:
        parser.exit(1, f"Analytics refresh failed: {error}\n")
    print(f"Published aggregate analytics snapshot ({size} bytes), through {snapshot['periods']['30']['end_date']} UTC")


if __name__ == "__main__":
    main()
