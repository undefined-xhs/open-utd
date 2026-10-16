import io
import json

import pytest

from scripts import fetch_comments as feed


def page(nodes, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor}}


def comment(identifier, day=1, **extra):
    return dict(id=identifier, bodyText=f"Text {identifier}", createdAt=f"2026-10-{day:02}T12:00:00Z",
                updatedAt=f"2026-10-{day:02}T12:00:00Z", deletedAt=None, isMinimized=False,
                url=f"https://github.com/example/catalog/discussions/1#discussioncomment-{day}",
                author={"login": "reader", "url": "https://github.com/reader", "avatarUrl": "https://avatars.githubusercontent.com/u/1"},
                **extra)


ENTITY = {"entity_type": "journal", "entity_id": "j_one", "title": "Test Journal", "journal_name": "Test Journal",
          "journal_slug": "test-journal", "site_path": "journals/test-journal/reviews/"}


class FakeClient:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def query(self, query, variables):
        expected_query, expected_variables, result = next(self.replies)
        assert query == expected_query
        assert variables == expected_variables
        self.calls.append(variables)
        return result


def repository_page(nodes, cursor=None, **extra):
    return {"repository": dict(isPrivate=False, discussionCategories={"nodes": [{"id": "category"}]},
                               discussions=page(nodes, cursor), **extra)}


def test_every_connection_paginated_and_new_reply_to_old_parent_is_latest():
    first = comment("old-parent", 1, replies=page([comment("reply-1", 2)], "reply-next"))
    first["isMinimized"] = True
    second = comment("second-parent", 3, replies=page([]))
    second["author"] = None
    discussion = {"id": "discussion", "title": "journal:j_one", "category": {"id": "category"}}
    unrelated = {"id": "ignore", "title": "journal:j_one extra text", "category": {"id": "category"}}
    client = FakeClient([
        (feed.DISCUSSIONS_QUERY, {"owner": "example", "name": "catalog", "category": "category", "cursor": None}, repository_page([unrelated], "discussion-next")),
        (feed.DISCUSSIONS_QUERY, {"owner": "example", "name": "catalog", "category": "category", "cursor": "discussion-next"}, repository_page([discussion])),
        (feed.COMMENTS_QUERY, {"id": "discussion", "cursor": None}, {"node": {"comments": page([first], "comment-next")}}),
        (feed.REPLIES_QUERY, {"id": "old-parent", "cursor": "reply-next"}, {"node": {"replies": page([comment("reply-newest", 16)])}}),
        (feed.COMMENTS_QUERY, {"id": "discussion", "cursor": "comment-next"}, {"node": {"comments": page([second])}}),
    ])
    result = feed.fetch_feed(client, "example/catalog", "category", {"journal:j_one": ENTITY})
    assert [item["id"] for item in result["comments"]] == ["reply-newest", "second-parent", "reply-1"]
    assert result["comments"][0]["is_reply"] is True
    assert result["comments"][1]["author"] is None
    assert result["comments"][1]["site_path"] == ENTITY["site_path"]
    assert len(client.calls) == 5
    assert result["updated_at"]


def test_deleted_comment_body_is_not_published_and_original_permalink_is_required():
    deleted = comment("deleted")
    deleted["deletedAt"] = "2026-10-02T00:00:00Z"
    assert feed.public_comment(deleted, ENTITY, "example/catalog", False) is None
    invalid = comment("invalid")
    invalid["url"] = "https://github.com/example/catalog/discussions/1"
    with pytest.raises(feed.FeedError, match="permalink"):
        feed.public_comment(invalid, ENTITY, "example/catalog", False)


@pytest.mark.parametrize("bad_page", [page([], "repeat"), {"nodes": [], "pageInfo": {}}, {"pageInfo": {"hasNextPage": False}}])
def test_invalid_or_repeating_pagination_fails(bad_page):
    with pytest.raises(feed.FeedError):
        list(feed.paginate(lambda cursor: bad_page))


@pytest.mark.parametrize("private,category", [(True, "category"), (False, "wrong-category")])
def test_private_repo_and_wrong_category_fail(private, category):
    result = repository_page([])
    result["repository"]["isPrivate"] = private
    client = FakeClient([(feed.DISCUSSIONS_QUERY, {"owner": "example", "name": "catalog", "category": category, "cursor": None}, result)])
    with pytest.raises(feed.FeedError):
        feed.fetch_feed(client, "example/catalog", category, {})


def test_graphql_http_200_partial_errors_never_succeed(monkeypatch):
    monkeypatch.setattr(feed, "urlopen", lambda *args, **kwargs: io.StringIO(json.dumps({"data": {"repository": {}}, "errors": [{"message": "Limit exceeded"}]})))
    with pytest.raises(feed.FeedError, match="incomplete data"):
        feed.GitHubClient("test-token").query("query { viewer { login } }", {})


def test_request_budget_checked_before_next_network_request(monkeypatch):
    monkeypatch.setattr(feed, "urlopen", lambda *args, **kwargs: io.StringIO(json.dumps({"data": {"rateLimit": {"cost": 1, "remaining": 999}}})))
    client = feed.GitHubClient("test-token", max_requests=1)
    client.query("query { rateLimit { cost remaining } }", {})
    with pytest.raises(feed.FeedError, match="budget"):
        client.query("query { rateLimit { cost remaining } }", {})
    assert client.requests == 1


def test_size_failure_preserves_existing_snapshot(tmp_path):
    output = tmp_path / "comments.json"
    output.write_text("previous snapshot")
    with pytest.raises(feed.FeedError, match="exceeds"):
        feed.write_feed(output, {"comments": ["large content"]}, max_bytes=5)
    assert output.read_text() == "previous snapshot"
    assert list(tmp_path.iterdir()) == [output]


def test_empty_bootstrap_has_no_fake_sync_date_and_preserves_live_snapshot(tmp_path, monkeypatch):
    output = tmp_path / "comments.json"
    monkeypatch.setattr("sys.argv", ["fetch_comments.py", "--ensure-empty", "--out", str(output)])
    feed.main()
    assert json.loads(output.read_text())["updated_at"] is None
    output.write_text("live snapshot")
    feed.main()
    assert output.read_text() == "live snapshot"


def test_catalogue_mapping_is_exact_and_read_only(connection):
    connection.execute("INSERT INTO articles(public_id,journal_id,title,created_at,updated_at) VALUES ('a_one',1,'Original English paper title','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    connection.commit()
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    from pathlib import Path
    before = Path(path).read_bytes()
    entities = feed.catalogue_entities(Path(path))
    article_entity = dict(ENTITY, entity_type="article", entity_id="a_one", title="Original English paper title", site_path="articles/a_one/")
    assert entities == {"journal:j_one": ENTITY, "article:a_one": article_entity}
    assert Path(path).read_bytes() == before
    discussions = [{"id": term, "title": term, "category": {"id": "category"}} for term in entities]
    client = FakeClient([
        (feed.DISCUSSIONS_QUERY, {"owner": "example", "name": "catalog", "category": "category", "cursor": None}, repository_page(discussions)),
        (feed.COMMENTS_QUERY, {"id": "journal:j_one", "cursor": None}, {"node": {"comments": page([comment("journal-comment", 1, replies=page([]))])}}),
        (feed.COMMENTS_QUERY, {"id": "article:a_one", "cursor": None}, {"node": {"comments": page([comment("article-comment", 2, replies=page([]))])}}),
    ])
    result = feed.fetch_feed(client, "example/catalog", "category", entities)
    assert [item["entity_type"] for item in result["comments"]] == ["article", "journal"]
    assert result["comments"][0]["title"] == "Original English paper title"
    assert result["comments"][0]["site_path"] == "articles/a_one/"
