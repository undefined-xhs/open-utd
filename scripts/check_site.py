"""Check the built site, including links when deployed beneath a repository path."""

import argparse
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.headings += 1
        for attribute in ("href", "src"):
            if attribute in attrs:
                self.links.append(attrs[attribute])


def check_site(dist: Path, generated: Path, base: str) -> list[str]:
    errors = []
    base = "/" + base.strip("/") + "/" if base.strip("/") else "/"
    manifest = json.loads((generated / "manifest.json").read_text())
    expected = ["index.html", "404.html", "search/index.html", "journals/index.html", "pagefind/pagefind.js"]
    expected += [f"journals/{j['slug']}/index.html" for j in manifest["journals"]]
    expected += [f"journals/{i['journal_slug']}/issues/{i['public_id']}/index.html" for i in manifest["issues"]]
    expected += [f"articles/{a['public_id']}/index.html" for a in manifest["articles"]]
    for filename in expected:
        if not (dist / filename).is_file():
            errors.append(f"Missing output: {filename}")
    pages = list(dist.rglob("*.html"))
    for page in pages:
        parser = Links()
        parser.feed(page.read_text())
        if parser.headings != 1:
            errors.append(f"{page}: expected one h1, found {parser.headings}")
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            if path.startswith("/"):
                if not path.startswith(base):
                    errors.append(f"{page}: link escapes base {base}: {path}")
                    continue
                target = dist / path[len(base):]
            else:
                target = page.parent / path
            if not target.resolve().is_relative_to(dist.resolve()):
                errors.append(f"{page}: link escapes output directory: {path}")
                continue
            if not target.is_file() and not (target / "index.html").is_file():
                errors.append(f"{page}: broken local link: {link}")
    for file in dist.rglob("*"):
        if file.suffix in {".sqlite", ".db", ".sqlite3"}:
            errors.append(f"Private database in site output: {file}")
    # The export is the only data boundary the frontend is allowed to consume.
    for shard in (generated / "articles-by-journal").glob("*.json"):
        for article in json.loads(shard.read_text()):
            if article.get("abstract_display_status") != "permitted" and article.get("abstract_text"):
                errors.append(f"Unlicensed abstract exported: {article['public_id']}")
    print(f"Checked {len(pages):,} HTML pages, {len(manifest['articles']):,} article routes; base={base}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--generated", type=Path, default=Path(".generated"))
    parser.add_argument("--base", default=os.getenv("PUBLIC_BASE_PATH", "/"))
    args = parser.parse_args()
    errors = check_site(args.dist, args.generated, args.base)
    for error in errors[:30]:
        print(error)
    if errors:
        raise SystemExit(f"Static site validation failed: {len(errors)} errors")
    print("Static routes, links, headings, and export rights checks passed.")


if __name__ == "__main__":
    main()
