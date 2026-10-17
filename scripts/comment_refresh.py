"""Compare public comment snapshots and reuse a verified static site without rebuilding."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from scripts.fetch_comments import FeedError, timestamp, write_feed

MAX_BYTES = 20 * 1024 * 1024
CONFIG_KEYS = (
    "PUBLIC_SITE_URL", "PUBLIC_BASE_PATH", "PUBLIC_GISCUS_REPO",
    "PUBLIC_GISCUS_REPO_ID", "PUBLIC_GISCUS_CATEGORY", "PUBLIC_GISCUS_CATEGORY_ID",
    "PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN",
)


def content(feed: dict) -> dict:
    """Ignore collection time only; edits, removals, authors and destinations matter."""
    if (not isinstance(feed, dict) or feed.get("schema_version") != 1
            or not isinstance(feed.get("repository"), str)
            or not isinstance(feed.get("comments"), list)
            or "updated_at" not in feed):
        raise FeedError("Invalid comment snapshot")
    if feed["updated_at"] is not None:
        timestamp(feed["updated_at"])
    elif feed["comments"]:
        raise FeedError("Unsynchronized snapshot contains comments")
    return {key: value for key, value in feed.items() if key != "updated_at"}


def changed(fresh: dict, published: dict | None) -> bool:
    current = content(fresh)
    if fresh["updated_at"] is None:
        raise FeedError("A live refresh must not publish an offline placeholder")
    return (published is None or published["updated_at"] is None
            or current != content(published))


def published_json(site: str, base: str, relative: str) -> dict | None:
    parsed = urlsplit(site)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise FeedError("Invalid public site URL")
    path = "/".join(part.strip("/") for part in (site, base, relative) if part.strip("/"))
    # Bypass an older CDN response when checking immediately after another deployment.
    query = urlencode({"refresh": f"{os.getenv('GITHUB_RUN_ID', 'local')}-{os.getenv('GITHUB_RUN_ATTEMPT', '1')}"})
    request = Request(f"{path}?{query}", headers={"Cache-Control": "no-cache", "User-Agent": "open-utd-comment-refresh/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(MAX_BYTES + 1)
    except HTTPError as error:
        if error.code == 404:
            return None  # First deployment or a missing feed needs publication.
        raise FeedError(f"Could not compare published comments: HTTP {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise FeedError("Could not compare published comments; no deployment attempted") from error
    if len(payload) > MAX_BYTES:
        raise FeedError("Published comment snapshot exceeds 20 MiB")
    try:
        result = json.loads(payload)
        return result if isinstance(result, dict) else None
    except (ValueError, UnicodeError):
        return None  # Repair an invalid/legacy published file using a complete fresh feed.


def published_feed(site: str, base: str) -> dict | None:
    result = published_json(site, base, "data/comments.json")
    try:
        content(result)
        return result
    except FeedError:
        return None


def cache_key(revision: str, environ: dict) -> str:
    configuration = {key: environ.get(key, "") for key in CONFIG_KEYS}
    digest = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()[:20]
    return f"pages-shell-v1-{revision}-{digest}"


def current_key() -> str:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    return cache_key(revision, os.environ)


def needs_publication(fresh: dict, site: str, base: str, key: str) -> bool:
    if changed(fresh, published_feed(site, base)):
        return True
    # GitHub may replace a pending push run with a newer comment run in the
    # concurrency group. Never skip an unpublished code/configuration update.
    build = published_json(site, base, "data/site-build.json")
    return build != {"schema_version": 1, "cache_key": key}


def patch_site(dist: Path, fresh: dict) -> None:
    content(fresh)
    if fresh["updated_at"] is None:
        raise FeedError("Cannot publish an offline placeholder")
    for relative in ("index.html", "comments/index.html", "pagefind/pagefind.js"):
        if not (dist / relative).is_file():
            raise FeedError(f"Cached site is incomplete: {relative}")
    write_feed(dist / "data/comments.json", fresh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["compare", "cache-key", "record-build", "patch"])
    parser.add_argument("--feed", type=Path, default=Path("public/data/comments.json"))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    if args.action == "cache-key":
        print(f"key={current_key()}")
        return
    if args.action == "record-build":
        write_feed(args.dist / "data/site-build.json", {"schema_version": 1, "cache_key": current_key()})
        return
    fresh = json.loads(args.feed.read_text(encoding="utf-8"))
    if args.action == "patch":
        patch_site(args.dist, fresh)
        print("Replaced only data/comments.json; existing HTML and search index reused.")
        return
    needs_publish = needs_publication(fresh, os.environ["PUBLIC_SITE_URL"], os.environ["PUBLIC_BASE_PATH"], current_key())
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(f"changed={str(needs_publish).lower()}\n")
    message = "Comments or site version changed; publication required." if needs_publish else "Comments and site version unchanged. Scheduled/manual checks will also verify cache availability."
    print(message)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(f"\n{message}\n")


if __name__ == "__main__":
    try:
        main()
    except (FeedError, OSError, ValueError) as error:
        raise SystemExit(f"Comment refresh failed: {error}") from error
