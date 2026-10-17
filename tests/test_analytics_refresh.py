import copy
from datetime import date, timedelta
import io
import json
from pathlib import Path
import tarfile

import pytest

from scripts import analytics_refresh as refresh
from scripts.fetch_analytics import AnalyticsError
from scripts.fetch_comments import FeedError


def snapshot():
    end = date(2026, 10, 16)
    periods = {}
    for days in (7, 30):
        start = end - timedelta(days=days - 1)
        periods[str(days)] = {
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "page_views": days * 2, "visits": None,
            "daily": [{"date": (start + timedelta(days=index)).isoformat(), "page_views": 2, "visits": None}
                      for index in range(days)],
            "countries": [{"country_code": "CN", "page_views": days * 2}],
            "pages": [{"path": "/", "page_views": days * 2}],
        }
    return {"schema_version": 1, "status": "ready", "source": "Cloudflare Web Analytics",
            "updated_at": "2026-10-17T00:00:00Z", "timezone": "UTC", "periods": periods}


def write_feed(path, value=None):
    path.write_text(json.dumps(snapshot() if value is None else value))
    return path


def entry(name, content=b"", kind=tarfile.REGTYPE):
    member = tarfile.TarInfo(name)
    member.type = kind
    member.size = len(content)
    member.mode = 0o644
    member.mtime = 123456789
    if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
        member.linkname = "index.html"
    return member, content


def write_archive(path, extras=(), analytics=None):
    with tarfile.open(path, "w", format=tarfile.GNU_FORMAT) as archive:
        files = [entry("./", kind=tarfile.DIRTYPE), entry("./index.html", b"home"),
                 entry("./data/", kind=tarfile.DIRTYPE), entry("./data/comments.json", b"existing comments"),
                 entry("./pagefind/pagefind.js", b"existing search index")]
        if analytics is not None:
            files.append(entry("./data/analytics.json", json.dumps(analytics).encode()))
        for member, payload in files + list(extras):
            archive.addfile(member, io.BytesIO(payload))


def contents(path):
    with tarfile.open(path, "r:") as archive:
        return {member.name.removeprefix("./"): archive.extractfile(member).read()
                for member in archive if member.isfile()}


def test_comparison_ignores_only_collection_time():
    old = snapshot()
    fresh = copy.deepcopy(old)
    fresh["updated_at"] = "2026-10-17T01:00:00Z"
    assert not refresh.changed(fresh, old)
    fresh["periods"]["7"]["pages"][0]["path"] = "/journals/"
    assert refresh.changed(fresh, old)
    assert refresh.changed(old, None)


@pytest.mark.parametrize("fresh,published", [({}, snapshot()), (snapshot(), {}),
                                           ({**snapshot(), "private_ip": "192.0.2.1"}, snapshot())])
def test_comparison_rejects_invalid_schema(fresh, published):
    with pytest.raises(AnalyticsError):
        refresh.changed(fresh, published)


@pytest.mark.parametrize("different", [False, True])
def test_compare_cli_reports_change_after_success(tmp_path, monkeypatch, different):
    feed = write_feed(tmp_path / "analytics.json")
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("PUBLIC_SITE_URL", "https://site.example")
    monkeypatch.setenv("PUBLIC_BASE_PATH", "/catalog/")
    calls = []
    def published(*args):
        calls.append(args)
        return None if different else snapshot()
    monkeypatch.setattr(refresh, "published_json", published)
    refresh.main(["compare", "--feed", str(feed)])
    assert output.read_text() == f"changed={str(different).lower()}\n"
    assert calls == [("https://site.example", "/catalog/", "data/analytics.json")]


def test_compare_network_error_does_not_report_no_change(tmp_path, monkeypatch):
    feed = write_feed(tmp_path / "analytics.json")
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    def failed(*args):
        raise FeedError("Network unavailable")
    monkeypatch.setattr(refresh, "published_json", failed)
    with pytest.raises(FeedError):
        refresh.main(["compare", "--feed", str(feed)])
    assert not output.exists()


@pytest.mark.parametrize("payload", [b"not json", b"[]", b"{}", b"\xff", b'{"schema_version":true}'])
def test_invalid_json_never_reaches_artifact(tmp_path, monkeypatch, payload):
    feed = tmp_path / "analytics.json"
    feed.write_bytes(payload)
    def unexpected(*args):
        pytest.fail("Invalid JSON must be rejected before artifact handling")
    monkeypatch.setattr(refresh, "patch", unexpected)
    with pytest.raises(AnalyticsError):
        refresh.main(["patch", "--feed", str(feed)])


def test_read_snapshot_enforces_size_limit(tmp_path, monkeypatch):
    feed = write_feed(tmp_path / "analytics.json")
    monkeypatch.setattr(refresh, "MAX_SNAPSHOT_BYTES", 10)
    with pytest.raises(AnalyticsError, match="1 MiB"):
        refresh.read_snapshot(feed)


def test_dist_patch_only_changes_analytics_and_takes_precedence(tmp_path):
    dist = tmp_path / "dist"
    (dist / "data").mkdir(parents=True)
    (dist / "index.html").write_bytes(b"home")
    (dist / "data/comments.json").write_bytes(b"comments")
    (dist / refresh.ANALYTICS_PATH).write_bytes(b"old analytics")
    archive = tmp_path / "artifact.tar"
    write_archive(archive)
    archive_before = archive.read_bytes()
    refresh.patch(snapshot(), dist, archive)
    assert (dist / "index.html").read_bytes() == b"home"
    assert (dist / "data/comments.json").read_bytes() == b"comments"
    assert json.loads((dist / refresh.ANALYTICS_PATH).read_text()) == snapshot()
    assert archive.read_bytes() == archive_before
    assert not list(dist.rglob(".analytics-*"))


def test_dist_patch_is_atomic_on_replace_failure(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "data").mkdir(parents=True)
    (dist / "index.html").write_bytes(b"home")
    target = dist / refresh.ANALYTICS_PATH
    target.write_bytes(b"old analytics")
    def failed(*args):
        raise OSError("Replace failed")
    monkeypatch.setattr(refresh.os, "replace", failed)
    with pytest.raises(OSError):
        refresh.patch_dist(dist, snapshot())
    assert target.read_bytes() == b"old analytics"
    assert not list(dist.rglob(".analytics-*"))


def test_dist_rejects_links_and_site_size_overflow(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_bytes(b"home")
    (dist / "linked").symlink_to(tmp_path)
    with pytest.raises(AnalyticsError, match="link"):
        refresh.patch_dist(dist, snapshot())
    (dist / "linked").unlink()
    monkeypatch.setattr(refresh, "MAX_SITE_BYTES", 4 + len(refresh._payload(snapshot())))
    with pytest.raises(AnalyticsError, match="900 MB"):
        refresh.patch_dist(dist, snapshot())
    assert not (dist / refresh.ANALYTICS_PATH).exists()


def test_patch_without_artifact_fails(tmp_path):
    with pytest.raises(AnalyticsError, match="No built site"):
        refresh.patch(snapshot(), tmp_path / "dist", tmp_path / "artifact.tar")


@pytest.mark.parametrize("has_previous", [False, True])
def test_archive_replaces_analytics_once_and_preserves_other_content(tmp_path, has_previous):
    path = tmp_path / "artifact.tar"
    write_archive(path, analytics=snapshot() if has_previous else None,
                  extras=[entry("articles/a_one/index.html", b"paper" * 500_000)])
    old = contents(path)
    old.pop(refresh.ANALYTICS_PATH, None)
    with tarfile.open(path) as archive:
        metadata = {item.name: (item.mode, item.mtime) for item in archive if not item.name.endswith("analytics.json")}
    fresh = snapshot()
    fresh["updated_at"] = "2026-10-17T01:00:00Z"
    refresh.patch(fresh, tmp_path / "missing-dist", path)
    result = contents(path)
    assert json.loads(result.pop(refresh.ANALYTICS_PATH)) == fresh
    assert result == old
    with tarfile.open(path) as archive:
        members = list(archive)
        assert sum(item.name.removeprefix("./") == refresh.ANALYTICS_PATH for item in members) == 1
        assert {item.name: (item.mode, item.mtime) for item in members if not item.name.endswith("analytics.json")} == metadata
    assert not list(tmp_path.glob(".analytics-*"))


@pytest.mark.parametrize("name", ["/absolute", "../escape", "./../escape", "a/../escape", "a//file",
                                  "a/./file", ".env", ".git/config", "C:/file", "a\\file", "a\nfile"])
def test_unsafe_archive_paths_preserve_original(tmp_path, name):
    path = tmp_path / "artifact.tar"
    write_archive(path, extras=[entry(name)])
    before = path.read_bytes()
    with pytest.raises(AnalyticsError, match="path"):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".analytics-*"))


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE,
                                  tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.GNUTYPE_SPARSE])
def test_archive_special_types_are_rejected(tmp_path, kind):
    path = tmp_path / "artifact.tar"
    write_archive(path, extras=[entry("special", kind=kind)])
    before = path.read_bytes()
    with pytest.raises(AnalyticsError):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["data/analytics.json", "./data/analytics.json", "./index.html"])
def test_duplicate_archive_entries_are_rejected(tmp_path, name):
    path = tmp_path / "artifact.tar"
    write_archive(path, analytics=snapshot(), extras=[entry(name, b"duplicate")])
    before = path.read_bytes()
    with pytest.raises(AnalyticsError, match="Duplicate"):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before


@pytest.mark.parametrize("child_first", [False, True])
def test_archive_file_directory_conflict_is_rejected(tmp_path, child_first):
    path = tmp_path / "artifact.tar"
    extras = [entry("conflict", b"file"), entry("conflict/child", b"child")]
    write_archive(path, extras=list(reversed(extras)) if child_first else extras)
    with pytest.raises(AnalyticsError, match="Conflicting"):
        refresh.patch_archive(path, snapshot())


def test_archive_requires_index_and_file_analytics(tmp_path):
    path = tmp_path / "artifact.tar"
    with tarfile.open(path, "w") as archive:
        info, payload = entry("data/comments.json", b"comments")
        archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(AnalyticsError, match="index.html"):
        refresh.patch_archive(path, snapshot())
    write_archive(path, extras=[entry(refresh.ANALYTICS_PATH, kind=tarfile.DIRTYPE)])
    with pytest.raises(AnalyticsError, match="regular file"):
        refresh.patch_archive(path, snapshot())


@pytest.mark.parametrize("trailing_bytes", [-1, 0, 512, 1023])
def test_archive_missing_content_or_trailer_is_rejected(tmp_path, trailing_bytes):
    path = tmp_path / "artifact.tar"
    write_archive(path)
    with tarfile.open(path) as archive:
        last = archive.getmembers()[-1]
        data_end = last.offset_data + ((last.size + 511) // 512) * 512
    path.write_bytes(path.read_bytes()[:data_end + trailing_bytes])
    before = path.read_bytes()
    with pytest.raises(AnalyticsError):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before


def test_archive_hidden_tail_and_size_overflow_are_rejected(tmp_path, monkeypatch):
    path = tmp_path / "artifact.tar"
    write_archive(path)
    with path.open("ab") as handle:
        handle.write(b"hidden".ljust(512, b"\0"))
    with pytest.raises(AnalyticsError, match="after"):
        refresh.patch_archive(path, snapshot())
    write_archive(path, analytics={"old": "x" * 1000})
    existing_bytes = sum(len(value) for key, value in contents(path).items() if key != refresh.ANALYTICS_PATH)
    monkeypatch.setattr(refresh, "MAX_SITE_BYTES", existing_bytes + len(refresh._payload(snapshot())))
    before = path.read_bytes()
    with pytest.raises(AnalyticsError, match="900 MB"):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before


def test_archive_replacement_failure_keeps_original(tmp_path, monkeypatch):
    path = tmp_path / "artifact.tar"
    write_archive(path)
    before = path.read_bytes()
    def failed(*args):
        raise OSError("Replace failed")
    monkeypatch.setattr(refresh.os, "replace", failed)
    with pytest.raises(OSError):
        refresh.patch_archive(path, snapshot())
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".analytics-*"))
