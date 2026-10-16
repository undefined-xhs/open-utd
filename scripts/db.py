"""SQLite lifecycle, registry loading, and invariant validation."""
from __future__ import annotations

import csv
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from scripts.normalize import normalize_doi, normalize_issn, normalize_orcid, safe_url

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/journals.sqlite"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def public_id(prefix: str) -> str:
    return prefix + "_" + uuid4().hex


def db_path() -> Path:
    return Path(os.environ.get("AJR_DB_PATH") or DEFAULT_DB).expanduser().resolve()


def environment() -> str:
    value = os.environ.get("AJR_ENV", "production")
    if value not in {"demo", "production"}:
        raise ValueError("AJR_ENV must be demo or production")
    return value


def connect(path: Path | str, *, readonly=False) -> sqlite3.Connection:
    path = Path(path)
    if readonly:
        connection = sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def initialize(path: Path | str, env: str | None = None) -> None:
    env = env or environment()
    with connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for migration in sorted((ROOT / "data/migrations").glob("*.sql")):
            if migration.stem not in applied:
                script = migration.read_text()
                conn.executescript("BEGIN IMMEDIATE;\n" + script)
                conn.execute("INSERT INTO schema_migrations VALUES (?,?)", (migration.stem, now()))
                conn.commit()
        prior = conn.execute("SELECT value FROM settings WHERE key='environment'").fetchone()
        if prior and prior[0] != env:
            raise ValueError(f"Database environment is {prior[0]}, requested {env}")
        conn.execute("INSERT OR IGNORE INTO settings VALUES ('environment',?)", (env,))
    conn.close()


def registry_rows(file: Path | str) -> list[dict]:
    with open(file, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Journal registry is empty")
    slugs, ids, issns = set(), set(), set()
    for row in rows:
        for required in ("slug", "name"):
            if not row.get(required):
                raise ValueError(f"Registry lacks {required}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", row["slug"]):
            raise ValueError("Journal slug must contain lowercase words separated by hyphens")
        if row["slug"] in slugs:
            raise ValueError("Duplicate registry slug")
        slugs.add(row["slug"])
        if row.get("public_id"):
            if not re.fullmatch(r"j_[A-Za-z0-9_-]+", row["public_id"]):
                raise ValueError("Invalid journal public_id")
            if row["public_id"] in ids:
                raise ValueError("Duplicate registry public_id")
            ids.add(row["public_id"])
        mapped = {}
        for field, medium in (("issn_l", "unknown"), ("issn_print", "print"), ("issn_electronic", "electronic")):
            if row.get(field):
                mapped[normalize_issn(row[field])] = medium
        for value in (row.get("issns") or "").split(";"):
            if value.strip():
                mapped.setdefault(normalize_issn(value), "unknown")
        if not mapped:
            raise ValueError(f"No ISSN for {row['slug']}")
        if issns.intersection(mapped):
            raise ValueError("ISSN belongs to multiple registry journals")
        issns.update(mapped)
        row["_issns"] = mapped
        if row.get("homepage_url") and not safe_url(row["homepage_url"]):
            raise ValueError("Unsafe journal homepage URL")
        row["start_year"] = int(row.get("start_year") or 2006)
        if not 1600 <= row["start_year"] <= 2100:
            raise ValueError("Invalid registry start_year")
    return rows


def seed_registry(conn: sqlite3.Connection, file: Path | str) -> int:
    rows = registry_rows(file)
    stamp = now()
    for row in rows:
        existing = conn.execute("SELECT * FROM journals WHERE slug=? OR public_id=?", (row["slug"], row.get("public_id"))).fetchall()
        if len(existing)>1:
            raise ValueError("Registry ID and slug refer to different journals")
        old = existing[0] if existing else None
        if old and row.get("public_id") and old["public_id"] != row["public_id"]:
            raise ValueError("Registry cannot replace a stable public_id")
        if old and old["slug"] != row["slug"]:
            raise ValueError("Published slug changes require an explicit redirect migration")
        for issn in row["_issns"]:
            owner = conn.execute("SELECT journal_id FROM journal_issns WHERE issn=?", (issn,)).fetchone()
            if owner and (not old or owner[0] != old["id"]):
                raise ValueError(f"ISSN {issn} is assigned to another journal")
        fields = ("name", "abbreviation", "issn_l", "publisher", "subject", "homepage_url", "start_year")
        values = {key: row.get(key) or None for key in fields}
        if values["issn_l"]:
            values["issn_l"] = normalize_issn(values["issn_l"])
        values["is_visible"] = int(row.get("is_visible") or 1)
        if old:
            prior_issns = {r[0] for r in conn.execute("SELECT issn FROM journal_issns WHERE journal_id=?", (old["id"],))}
            if old["start_year"] != values["start_year"] or set(row["_issns"]) - prior_issns:
                conn.execute("UPDATE sync_state SET last_successful_indexed_at=NULL,last_status='scope_changed',last_error='Registry coverage changed; run a complete initial import' WHERE journal_id=?", (old["id"],))
            if any(old[k] != v for k,v in values.items()):
                conn.execute("UPDATE journals SET "+",".join(f"{k}=?" for k in values)+",updated_at=? WHERE id=?", (*values.values(), stamp, old["id"]))
            journal_id = old["id"]
        else:
            values.update(public_id=row.get("public_id") or public_id("j"), slug=row["slug"], created_at=stamp, updated_at=stamp)
            cursor = conn.execute("INSERT INTO journals ("+",".join(values)+") VALUES ("+",".join("?" for _ in values)+")", tuple(values.values()))
            journal_id = cursor.lastrowid
        # Preserve historic ISSNs; removal should be an explicit, reviewed migration.
        for issn, medium in row["_issns"].items():
            conn.execute("INSERT INTO journal_issns VALUES (?,?,?) ON CONFLICT(journal_id,issn) DO UPDATE SET medium=excluded.medium", (journal_id, issn, medium))
    return len(rows)


def statistics(conn: sqlite3.Connection) -> dict:
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("journals", "issues", "articles", "authors")}


def validate(conn: sqlite3.Connection, *, production=False) -> dict:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise ValueError(f"SQLite integrity check failed: {integrity}")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Foreign key check failed")
    if conn.execute("SELECT 1 FROM articles a JOIN issues i ON i.id=a.issue_id WHERE i.journal_id!=a.journal_id LIMIT 1").fetchone():
        raise ValueError("Article points to an issue in a different journal")
    env = conn.execute("SELECT value FROM settings WHERE key='environment'").fetchone()
    if not env or env[0] not in {"demo", "production"}:
        raise ValueError("Database has no valid environment marker")
    for table, prefix in (("journals", "j"), ("issues", "i"), ("articles", "a")):
        for row in conn.execute(f"SELECT public_id FROM {table}"):
            if not re.fullmatch(prefix+r"_[A-Za-z0-9_-]+", row[0]):
                raise ValueError("Unsafe public_id")
    for row in conn.execute("SELECT issn FROM journal_issns"):
        if normalize_issn(row[0]) != row[0]:
            raise ValueError("ISSN is not normalized")
    for row in conn.execute("SELECT doi,landing_url,abstract_display_status,abstract_rights_verified,abstract_license_url,abstract_text FROM articles"):
        if row[0] and normalize_doi(row[0]) != row[0]:
            raise ValueError("DOI is not normalized")
        if row[1] and not safe_url(row[1]):
            raise ValueError("Unsafe article URL")
        if row[2] == "permitted" and (not row[3] or not safe_url(row[4])):
            raise ValueError("Permitted abstract lacks verified redistribution evidence")
        if row[2] != "permitted" and row[5]:
            raise ValueError("Unlicensed abstract must not be persisted in the public database")
    for row in conn.execute("SELECT homepage_url FROM journals WHERE homepage_url IS NOT NULL"):
        if not safe_url(row[0]):
            raise ValueError("Unsafe journal URL")
    for row in conn.execute("SELECT orcid FROM authors WHERE orcid IS NOT NULL"):
        normalize_orcid(row[0])
    counts = statistics(conn)
    if production:
        if env[0] != "production":
            raise ValueError("Production validation refuses a demo database")
        for table in ("journals", "articles"):
            if conn.execute(f"SELECT 1 FROM {table} WHERE is_synthetic!=0 LIMIT 1").fetchone():
                raise ValueError("Production validation refuses synthetic data")
        if not counts["articles"]:
            raise ValueError("Production database contains no real articles")
        missing = conn.execute("SELECT slug FROM journals j WHERE is_visible=1 AND NOT EXISTS (SELECT 1 FROM articles a WHERE a.journal_id=j.id)").fetchall()
        if missing:
            raise ValueError("Visible journals without articles: "+", ".join(r[0] for r in missing))
        if conn.execute("SELECT 1 FROM articles WHERE metadata_source NOT IN ('Crossref','OpenAlex') OR metadata_source IS NULL LIMIT 1").fetchone():
            raise ValueError("Production article lacks a recognized metadata source")
    return counts
