import copy
import io
import json
from urllib.error import HTTPError, URLError

import pytest

from scripts import comment_refresh as refresh


def snapshot(comments=None, **overrides):
    return dict(schema_version=1, repository="example/catalog",
                updated_at="2026-10-16T00:00:00Z", comments=comments or [], **overrides)


def test_collection_time_alone_does_not_require_a_deployment():
    previous = snapshot([{"id": "one", "body_text": "Same comment"}])
    fresh = copy.deepcopy(previous)
    fresh["updated_at"] = "2026-10-16T01:00:00Z"
    assert not refresh.changed(fresh, previous)
    assert not refresh.changed(snapshot(), snapshot())


@pytest.mark.parametrize("field,value", [("body_text", "Edited"), ("author", None),
                                         ("site_path", "articles/a_new/"), ("updated_at", "new time")])
def test_comment_changes_are_not_ignored(field, value):
    previous = snapshot([{"id": "one", "body_text": "Original", "author": "reader"}])
    fresh = copy.deepcopy(previous)
    fresh["comments"][0][field] = value
    assert refresh.changed(fresh, previous)


def test_removals_additions_and_empty_first_sync_require_publication():
    populated = snapshot([{"id": "one"}])
    assert refresh.changed(snapshot(), populated)
    assert refresh.changed(populated, snapshot())
    assert refresh.changed(snapshot(), None)
    bootstrap = snapshot()
    bootstrap["updated_at"] = None
    assert refresh.changed(snapshot(), bootstrap)
    with pytest.raises(refresh.FeedError, match="placeholder"):
        refresh.changed(bootstrap, snapshot())


@pytest.mark.parametrize("failure", [URLError("offline"), HTTPError("https://site", 500, "server error", {}, None)])
def test_network_failure_never_becomes_a_successful_noop(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(refresh, "urlopen", fail)
    with pytest.raises(refresh.FeedError, match="compare"):
        refresh.published_feed("https://site.example", "/open-utd/")


def test_missing_or_invalid_published_feed_is_repaired(monkeypatch):
    def missing(*args, **kwargs):
        raise HTTPError("https://site", 404, "missing", {}, None)
    monkeypatch.setattr(refresh, "urlopen", missing)
    assert refresh.published_feed("https://site.example", "/") is None
    monkeypatch.setattr(refresh, "urlopen", lambda *args, **kwargs: io.BytesIO(b"<html>invalid</html>"))
    assert refresh.published_feed("https://site.example", "/") is None


def test_comparison_uses_base_path_and_no_cache_request(monkeypatch):
    def respond(request, **kwargs):
        assert request.full_url.startswith("https://site.example/open-utd/data/comments.json?refresh=")
        assert request.get_header("Cache-control") == "no-cache"
        return io.BytesIO(json.dumps(snapshot()).encode())
    monkeypatch.setattr(refresh, "urlopen", respond)
    assert refresh.published_feed("https://site.example/", "/open-utd/") == snapshot()


def test_cache_reuse_requires_same_commit_and_public_configuration():
    config = {key: "configured" for key in refresh.CONFIG_KEYS}
    original = refresh.cache_key("first", config)
    assert refresh.cache_key("second", config) != original
    for key in refresh.CONFIG_KEYS:
        assert refresh.cache_key("first", dict(config, **{key: "changed"})) != original
    assert refresh.cache_key("first", dict(config, GITHUB_RUN_ID="next")) == original


@pytest.mark.parametrize("published", [None, {}, {"schema_version": 1, "cache_key": "older-commit"}])
def test_unchanged_comments_do_not_skip_an_unpublished_source_update(monkeypatch, published):
    monkeypatch.setattr(refresh, "published_feed", lambda *args: snapshot())
    monkeypatch.setattr(refresh, "published_json", lambda *args: published)
    assert refresh.needs_publication(snapshot(), "https://site.example", "/", "current-commit")


def test_same_site_and_comments_skip_publication(monkeypatch):
    monkeypatch.setattr(refresh, "published_feed", lambda *args: snapshot())
    monkeypatch.setattr(refresh, "published_json", lambda *args: {"schema_version": 1, "cache_key": "current-commit"})
    assert not refresh.needs_publication(snapshot(), "https://site.example", "/", "current-commit")


def test_patch_preserves_every_other_file_and_publishes_deletion(tmp_path):
    files = {"index.html": "home", "comments/index.html": "feed page",
             "pagefind/pagefind.js": "search", "articles/a_one/index.html": "paper"}
    for relative, text in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    output = tmp_path / "data/comments.json"
    output.parent.mkdir()
    output.write_text(json.dumps(snapshot([{"id": "deleted"}])))
    refresh.patch_site(tmp_path, snapshot())
    assert json.loads(output.read_text()) == snapshot()
    for relative, text in files.items():
        assert (tmp_path / relative).read_text() == text


def test_incomplete_cache_does_not_publish(tmp_path):
    with pytest.raises(refresh.FeedError, match="incomplete"):
        refresh.patch_site(tmp_path, snapshot())
    assert not (tmp_path / "data/comments.json").exists()
