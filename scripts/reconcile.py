"""Conservative identity matching and idempotent relational ingestion."""
from __future__ import annotations

import hashlib
import json
import sqlite3

from scripts.db import now, public_id
from scripts.normalize import normalize_issn, normalize_record, plain_text


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def ingest_record(conn: sqlite3.Connection, journal_id: int, record: dict, *, synthetic=False) -> str:
    if record.get("type") != "journal-article":
        return "skipped"
    article = normalize_record(record)
    whitelist = {r[0] for r in conn.execute("SELECT issn FROM journal_issns WHERE journal_id=?", (journal_id,))}
    source_issns = {normalize_issn(value) for value in record.get("ISSN", [])}
    if not source_issns or not source_issns.intersection(whitelist):
        raise ValueError("Crossref record does not match the requested journal ISSN whitelist")
    # A DOI must never silently migrate between journals.
    existing = conn.execute("SELECT * FROM articles WHERE doi=?", (article["doi"],)).fetchone() if article["doi"] else None
    source_key = "crossref:" + (article["doi"] or str(record.get("_source_id") or digest(record)))
    if not existing:
        existing = conn.execute("SELECT * FROM articles WHERE source_record_key=?", (source_key,)).fetchone()
    if existing and existing["journal_id"] != journal_id:
        raise ValueError(f"DOI journal conflict requires review: {article['doi']}")
    source_hash = digest(record)
    if existing and existing["source_hash"] == source_hash:
        return "skipped"
    if synthetic:
        article["metadata_source"] = "Synthetic demo"
        if record.get("_abstract_permitted") and record.get("abstract"):
            article.update(abstract_text=plain_text(record["abstract"]), abstract_source="Synthetic demo",
                           abstract_license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                           abstract_display_status="permitted", abstract_rights_verified=1)
    authors = article.pop("authors")
    issue = article.pop("issue")
    stamp = now()
    issue_id = None
    if issue:
        issue_key, volume, issue_number = issue
        old_issue = conn.execute("SELECT * FROM issues WHERE journal_id=? AND issue_key=?", (journal_id, issue_key)).fetchone()
        if old_issue:
            issue_id = old_issue["id"]
            # Once created, the issue's identity is independent of corrected dates.
        else:
            cursor = conn.execute("INSERT INTO issues (public_id,journal_id,issue_key,volume,issue_number,publication_year,publication_date,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (public_id("i"), journal_id, issue_key, volume, issue_number, article["publication_year"], article["publication_date"], stamp, stamp))
            issue_id = cursor.lastrowid
    elif existing:
        # An upstream partial deposit must not remove an established issue relationship.
        issue_id = existing["issue_id"]
    article.update(journal_id=journal_id, issue_id=issue_id, source_record_key=source_key,
                   source_hash=source_hash, is_synthetic=int(synthetic), updated_at=stamp)
    if existing:
        # Keep independently verified abstract rights only while the source stays unchanged.
        conn.execute("UPDATE articles SET "+",".join(f"{key}=?" for key in article)+" WHERE id=?", (*article.values(), existing["id"]))
        article_id = existing["id"]
    else:
        article.update(public_id=public_id("a"), created_at=stamp)
        cursor = conn.execute("INSERT INTO articles ("+",".join(article)+") VALUES ("+",".join("?" for _ in article)+")", tuple(article.values()))
        article_id = cursor.lastrowid
    prior_byline = {r["author_position"]: r for r in conn.execute("SELECT aa.*,a.orcid FROM article_authors aa JOIN authors a ON a.id=aa.author_id WHERE article_id=?", (article_id,))}
    conn.execute("DELETE FROM article_authors WHERE article_id=?", (article_id,))
    for position, author in enumerate(authors, 1):
        match = conn.execute("SELECT id FROM authors WHERE orcid=?", (author["orcid"],)).fetchone() if author["orcid"] else None
        previous = prior_byline.get(position)
        if not match and previous and previous["byline_name"] == author["byline_name"] and previous["orcid"] == author["orcid"]:
            author_id = previous["author_id"]
        elif match:
            author_id = match[0]
        else:
            author_id = conn.execute("INSERT INTO authors (public_id,display_name,orcid) VALUES (?,?,?)", (public_id("p"), author["byline_name"], author["orcid"])).lastrowid
        conn.execute("INSERT INTO article_authors VALUES (?,?,?,?,?)", (article_id, author_id, position, author["byline_name"], author["affiliation_text"]))
    source_dates = {key: record[key] for key in ("published-print", "published-online", "published", "issued") if key in record}
    conn.execute("INSERT INTO source_records VALUES (?,?,?,?,?) ON CONFLICT(article_id) DO UPDATE SET original_identifier=excluded.original_identifier,source_dates_json=excluded.source_dates_json,metadata_hash=excluded.metadata_hash", (article_id, "Synthetic demo" if synthetic else "Crossref", record.get("DOI"), json.dumps(source_dates, sort_keys=True), source_hash))
    return "updated" if existing else "inserted"


def prune_orphan_authors(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM authors WHERE NOT EXISTS (SELECT 1 FROM article_authors aa WHERE aa.author_id=authors.id)")
