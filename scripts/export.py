"""Deterministic public JSON shards consumed by the static site."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

from scripts.db import validate


def _natural(value):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold()) for part in re.split(r"(\d+)", str(value or "")))


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))+"\n", encoding="utf-8")


def export_catalog(conn: sqlite3.Connection, output: Path | str, *, production=False) -> dict:
    validate(conn, production=production)
    output = Path(output).resolve()
    if output == Path.cwd().resolve() or output.parent == output:
        raise ValueError("Export output must be a dedicated generated directory")
    allowed = {"manifest.json", "journals-index.json", "journals", "issues", "articles-by-journal", ".ajr-generated", ".DS_Store"}
    if output.exists() and (not output.is_dir() or any(child.name not in allowed for child in output.iterdir())):
        raise ValueError("Refusing to replace a directory containing non-generated files")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".ajr-export-", dir=output.parent))
    env = conn.execute("SELECT value FROM settings WHERE key='environment'").fetchone()[0]
    manifest = {"schema_version": 1, "environment": env, "journals": [], "issues": [], "articles": [],
                "stats": {"journals": 0, "issues": 0, "articles": 0, "authors": 0}, "updated_at": None}
    index = []
    author_ids, timestamps = set(), []
    try:
        for journal_row in conn.execute("SELECT * FROM journals WHERE is_visible=1 ORDER BY name COLLATE NOCASE,public_id"):
            journal = {key: journal_row[key] for key in ("public_id", "slug", "name", "abbreviation", "issn_l", "publisher", "subject", "homepage_url", "start_year", "created_at", "updated_at")}
            journal["issns"] = [row[0] for row in conn.execute("SELECT issn FROM journal_issns WHERE journal_id=? ORDER BY issn", (journal_row["id"],))]
            state = conn.execute("SELECT MAX(last_run_at) FROM sync_state WHERE journal_id=? AND last_status='success'", (journal_row["id"],)).fetchone()[0]
            journal["last_synced_at"] = state
            journal["is_synthetic"] = bool(journal_row["is_synthetic"])
            brief = {key: journal[key] for key in ("public_id", "slug", "name")}
            issue_rows = list(conn.execute("SELECT * FROM issues WHERE journal_id=?", (journal_row["id"],)))
            issue_rows.sort(key=lambda row: (row["publication_year"] or 0, _natural(row["volume"]), _natural(row["issue_number"]), row["public_id"]), reverse=True)
            issues = {}
            for row in issue_rows:
                issue = {key: row[key] for key in ("public_id", "volume", "issue_number", "issue_title", "publication_year", "publication_date", "created_at", "updated_at")}
                issue.update(journal=brief, articles=[])
                issues[row["id"]] = issue
            articles = []
            for row in conn.execute("SELECT * FROM articles WHERE journal_id=? ORDER BY publication_date DESC,title COLLATE NOCASE,public_id", (journal_row["id"],)):
                article = {key: row[key] for key in ("public_id", "doi", "openalex_id", "title", "abstract_source", "abstract_license_url", "abstract_display_status", "publication_date", "date_precision", "publication_year", "pages", "article_type", "landing_url", "metadata_source", "source_modified_at", "created_at", "updated_at")}
                article["abstract_text"] = row["abstract_text"] if row["abstract_display_status"] == "permitted" and row["abstract_rights_verified"] else None
                article["journal"] = brief
                issue = issues.get(row["issue_id"])
                article["issue"] = {key: issue[key] for key in ("public_id", "volume", "issue_number", "publication_year")} if issue else None
                article["authors"] = []
                for author in conn.execute("SELECT a.id,a.display_name,a.orcid,aa.byline_name,aa.affiliation_text FROM article_authors aa JOIN authors a ON a.id=aa.author_id WHERE aa.article_id=? ORDER BY aa.author_position", (row["id"],)):
                    author_ids.add(author["id"])
                    article["authors"].append({key: author[key] for key in ("display_name", "byline_name", "orcid", "affiliation_text")})
                articles.append(article)
                if issue:
                    issue["articles"].append(article)
                manifest["articles"].append({"public_id": article["public_id"], "journal_public_id": journal["public_id"]})
                timestamps.append(row["updated_at"])
            journal["article_count"] = len(articles)
            journal["issue_count"] = len(issues)
            index.append(dict(journal))
            journal["issues"] = []
            for issue in issues.values():
                issue["article_count"] = len(issue["articles"])
                journal["issues"].append({key:value for key,value in issue.items() if key not in {"articles", "journal"}})
                manifest["issues"].append({"public_id": issue["public_id"], "journal_slug": journal["slug"]})
                _dump(stage / "issues" / (issue["public_id"]+".json"), issue)
            journal["online_first"] = [article for article in articles if not article["issue"]]
            _dump(stage / "journals" / (journal["public_id"]+".json"), journal)
            _dump(stage / "articles-by-journal" / (journal["public_id"]+".json"), articles)
            manifest["journals"].append(brief | {"slug": journal["slug"]})
            timestamps.extend(filter(None, [journal["updated_at"], state]))
        manifest["stats"] = {"journals": len(index), "issues": len(manifest["issues"]), "articles": len(manifest["articles"]), "authors": len(author_ids)}
        manifest["updated_at"] = max(timestamps, default=None)
        _dump(stage / "manifest.json", manifest)
        _dump(stage / "journals-index.json", index)
        (stage / ".ajr-generated").write_text("Open UTD generated catalog, safe to replace.\n")
        if output.exists():
            shutil.rmtree(output)
        stage.rename(output)
        return manifest["stats"]
    finally:
        if stage.exists():
            shutil.rmtree(stage)
