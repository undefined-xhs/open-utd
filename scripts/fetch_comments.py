"""Build a public, read-only GitHub Discussions comment snapshot for the static site.

Only exact giscus terms found in the local catalogue and the configured category
are included. Pagination is exhaustive; failed/partial API responses never replace
the previous output. No third-party Python package is required.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

PAGE_INFO = "pageInfo { hasNextPage endCursor }"
COMMENT_FIELDS = """id bodyText createdAt updatedAt url deletedAt isMinimized
author { login url avatarUrl(size: 80) }"""
RATE_LIMIT = "rateLimit { cost remaining resetAt }"
DISCUSSIONS_QUERY = """
query Discussions($owner: String!, $name: String!, $category: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    isPrivate
    discussionCategories(first: 100) { nodes { id } }
    discussions(first: 100, after: $cursor, categoryId: $category,
      orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { id title category { id } }
      PAGE_INFO
    }
  }
  RATE_LIMIT
}
""".replace("PAGE_INFO", PAGE_INFO).replace("RATE_LIMIT", RATE_LIMIT)
COMMENTS_QUERY = """
query Comments($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on Discussion {
      comments(first: 100, after: $cursor) {
        nodes { COMMENT_FIELDS replies(first: 100) { nodes { COMMENT_FIELDS } PAGE_INFO } }
        PAGE_INFO
      }
    }
  }
  RATE_LIMIT
}
""".replace("COMMENT_FIELDS", COMMENT_FIELDS).replace("PAGE_INFO", PAGE_INFO).replace("RATE_LIMIT", RATE_LIMIT)
REPLIES_QUERY = """
query Replies($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on DiscussionComment {
      replies(first: 100, after: $cursor) { nodes { COMMENT_FIELDS } PAGE_INFO }
    }
  }
  RATE_LIMIT
}
""".replace("COMMENT_FIELDS", COMMENT_FIELDS).replace("PAGE_INFO", PAGE_INFO).replace("RATE_LIMIT", RATE_LIMIT)


class FeedError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str, max_requests: int = 400):
        self.token = token
        self.max_requests = max_requests
        self.requests = 0
        self.cost = 0
        self.remaining = None

    def query(self, query: str, variables: dict) -> dict:
        request = Request("https://api.github.com/graphql", method="POST",
                          data=json.dumps({"query": query, "variables": variables}).encode(),
                          headers={"Authorization": f"Bearer {self.token}",
                                   "Content-Type": "application/json", "Accept": "application/vnd.github+json",
                                   "User-Agent": "open-utd-comment-feed/1.0"})
        for attempt in range(3):
            if self.requests >= self.max_requests or (self.remaining is not None and self.remaining < 5):
                raise FeedError("GitHub query budget exhausted; previous published snapshot is retained")
            self.requests += 1
            try:
                with urlopen(request, timeout=45) as response:
                    result = json.load(response)
                break
            except HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise FeedError(f"GitHub GraphQL HTTP {error.code}; no feed was published") from error
            except (URLError, TimeoutError) as error:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise FeedError("GitHub GraphQL network request failed; no feed was published") from error
            except (ValueError, UnicodeError) as error:
                raise FeedError("GitHub returned invalid JSON; no feed was published") from error
        if not isinstance(result, dict) or result.get("errors") or not isinstance(result.get("data"), dict):
            # Never accept partial GraphQL data, even with a successful HTTP status.
            raise FeedError("GitHub GraphQL returned errors or incomplete data; check token permissions and API limits")
        data = result["data"]
        limits = data.get("rateLimit")
        if not isinstance(limits, dict) or not isinstance(limits.get("remaining"), int):
            raise FeedError("GitHub response is missing rate-limit accounting")
        self.remaining = limits["remaining"]
        self.cost += int(limits.get("cost", 0))
        return data


def paginate(fetch, initial=None):
    """Yield complete connection nodes, rejecting malformed or cyclic cursors."""
    cursor, seen = None, set()
    connection = initial
    while True:
        if connection is None:
            connection = fetch(cursor)
        if not isinstance(connection, dict) or not isinstance(connection.get("nodes"), list):
            raise FeedError("Missing GitHub connection; refusing an incomplete snapshot")
        info = connection.get("pageInfo")
        if not isinstance(info, dict) or not isinstance(info.get("hasNextPage"), bool):
            raise FeedError("Missing GitHub pagination metadata")
        for node in connection["nodes"]:
            if not isinstance(node, dict):
                raise FeedError("Missing GitHub node; retry after concurrent changes settle")
            yield node
        if not info["hasNextPage"]:
            return
        cursor = info.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            raise FeedError("GitHub pagination did not advance")
        seen.add(cursor)
        connection = None


def catalogue_entities(database: Path) -> dict:
    entities = {}
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT public_id,slug,name FROM journals WHERE is_visible=1"):
            entities[f"journal:{row['public_id']}"] = {
                "entity_type": "journal", "entity_id": row["public_id"], "title": row["name"],
                "journal_name": row["name"], "journal_slug": row["slug"],
                "site_path": f"journals/{quote(row['slug'], safe='')}/reviews/"}
        for row in conn.execute("SELECT a.public_id,a.title,j.slug,j.name FROM articles a JOIN journals j ON j.id=a.journal_id WHERE j.is_visible=1"):
            entities[f"article:{row['public_id']}"] = {
                "entity_type": "article", "entity_id": row["public_id"], "title": row["title"],
                "journal_name": row["name"], "journal_slug": row["slug"],
                "site_path": f"articles/{quote(row['public_id'], safe='')}/"}
    return entities


def timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timezone required")
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (AttributeError, TypeError, ValueError) as error:
        raise FeedError("Invalid comment timestamp") from error


def public_comment(node: dict, entity: dict, repository: str, is_reply: bool):
    if "isMinimized" not in node or "deletedAt" not in node:
        raise FeedError("Missing comment visibility fields")
    if node["isMinimized"] or node["deletedAt"]:
        return None
    if not isinstance(node.get("id"), str) or not isinstance(node.get("bodyText"), str):
        raise FeedError("Invalid comment content")
    url = urlsplit(node.get("url", ""))
    prefix = f"/{repository}/discussions/"
    if url.scheme != "https" or url.netloc != "github.com" or not url.path.lower().startswith(prefix.lower()) or not url.fragment:
        raise FeedError("Comment is missing its original GitHub permalink")
    author = node.get("author")
    if author is not None:
        if not isinstance(author, dict) or not isinstance(author.get("login"), str):
            raise FeedError("Invalid comment author")
        author = {"login": author["login"], "url": author.get("url"), "avatar_url": author.get("avatarUrl")}
    return dict(entity, id=node["id"], author=author, body_text=node["bodyText"],
                created_at=timestamp(node.get("createdAt")), updated_at=timestamp(node.get("updatedAt")),
                url=node["url"], is_reply=is_reply)


def fetch_feed(client, repository: str, category: str, entities: dict) -> dict:
    owner, name = repository.split("/")
    comments = {}
    seen_discussions = set()

    def discussions(cursor):
        data = client.query(DISCUSSIONS_QUERY, {"owner": owner, "name": name, "category": category, "cursor": cursor})
        repo = data.get("repository")
        if not isinstance(repo, dict) or repo.get("isPrivate") is not False:
            raise FeedError("Comments can only be exported from an accessible public repository")
        categories = repo.get("discussionCategories", {}).get("nodes", [])
        if category not in {item.get("id") for item in categories if isinstance(item, dict)}:
            raise FeedError("Configured giscus category does not belong to this repository")
        return repo.get("discussions")

    def connection(query, identifier, field, cursor):
        node = client.query(query, {"id": identifier, "cursor": cursor}).get("node")
        if not isinstance(node, dict):
            raise FeedError("Discussion disappeared during collection; retry the run")
        return node.get(field)

    def include(node, entity, is_reply):
        value = public_comment(node, entity, repository, is_reply)
        if value and (value["id"] not in comments or value["updated_at"] > comments[value["id"]]["updated_at"]):
            comments[value["id"]] = value

    for discussion in paginate(discussions):
        entity = entities.get(discussion.get("title"))
        if not entity:
            continue
        if discussion.get("category", {}).get("id") != category:
            raise FeedError("GitHub returned a discussion outside the configured category")
        identifier = discussion.get("id")
        if not isinstance(identifier, str):
            raise FeedError("Discussion has no stable ID")
        if identifier in seen_discussions:
            continue
        seen_discussions.add(identifier)
        for comment in paginate(lambda cursor: connection(COMMENTS_QUERY, identifier, "comments", cursor)):
            include(comment, entity, False)
            # A removed/minimized parent can still contain public replies.
            for reply in paginate(lambda cursor: connection(REPLIES_QUERY, comment["id"], "replies", cursor), initial=comment.get("replies")):
                include(reply, entity, True)
    return {"schema_version": 1, "repository": repository,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "comments": sorted(comments.values(), key=lambda item: (item["created_at"], item["id"]), reverse=True)}


def write_feed(output: Path, feed: dict, max_bytes: int = 20 * 1024 * 1024) -> int:
    payload = (json.dumps(feed, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > max_bytes:
        raise FeedError("Comment feed exceeds 20 MiB; split or archive the feed before increasing this limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".comments-", suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return len(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("PUBLIC_GISCUS_REPO") or os.getenv("GITHUB_REPOSITORY") or "allenz-me/open-utd")
    parser.add_argument("--category-id", default=os.getenv("PUBLIC_GISCUS_CATEGORY_ID"))
    parser.add_argument("--db", type=Path, default=Path(os.getenv("AJR_DB_PATH") or "data/journals.sqlite"))
    parser.add_argument("--out", type=Path, default=Path("public/data/comments.json"))
    parser.add_argument("--max-requests", type=int, default=400)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--empty", action="store_true", help="Write an offline, never-synchronized empty snapshot")
    mode.add_argument("--ensure-empty", action="store_true", help="Offline bootstrap only when no snapshot exists")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("repo must be owner/repository")
    if args.ensure_empty and args.out.exists():
        return
    if args.empty or args.ensure_empty:
        write_feed(args.out, {"schema_version": 1, "repository": args.repo, "updated_at": None, "comments": []})
        print("Prepared offline comment feed (not synchronized).")
        return
    token = os.getenv("GITHUB_TOKEN")
    if not token or not args.category_id:
        parser.error("GITHUB_TOKEN and PUBLIC_GISCUS_CATEGORY_ID are required for live collection; use --empty offline")
    if not 1 <= args.max_requests <= 800:
        parser.error("max-requests must be between 1 and 800")
    client = GitHubClient(token, args.max_requests)
    feed = fetch_feed(client, args.repo, args.category_id, catalogue_entities(args.db))
    size = write_feed(args.out, feed)
    summary = f"Comments: {len(feed['comments']):,}; snapshot: {size / 1024:.1f} KiB; GitHub requests: {client.requests}; GraphQL cost: {client.cost}; remaining: {client.remaining}."
    print(summary)
    if size > 5 * 1024 * 1024:
        print("::warning::Comment feed exceeds 5 MiB; consider splitting the static feed.")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("\n### Latest comments snapshot\n\n" + summary + "\n")


if __name__ == "__main__":
    try:
        main()
    except (FeedError, OSError, sqlite3.Error) as error:
        raise SystemExit(f"Comment feed failed: {error}") from error
