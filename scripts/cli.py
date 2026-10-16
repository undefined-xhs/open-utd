#!/usr/bin/env python3
"""Explicit, reproducible commands for the Open UTD data pipeline."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import db
from scripts.crossref import CrossrefClient
from scripts.demo import seed_demo
from scripts.export import export_catalog
from scripts.reconcile import ingest_record, prune_orphan_authors


def sync_database(path: Path, args, *, client=None, progress=print) -> dict:
    """Work only on a backup; promote atomically after every journal succeeds."""
    if args.limit and not args.dry_run:
        raise ValueError("--limit requires --dry-run: partial imports cannot advance production watermarks")
    today = datetime.now(timezone.utc).date()
    until = args.to_date or today.isoformat()
    date.fromisoformat(until)
    fixed_indexed_until = db.now()
    client = client or CrossrefClient(os.environ.get("CROSSREF_MAILTO", ""), rows=args.rows, request_budget=args.request_budget)
    descriptor, stage_name = tempfile.mkstemp(prefix=".sync-", suffix=".sqlite", dir=path.parent)
    os.close(descriptor)
    stage = Path(stage_name)
    conn = None
    try:
        source = db.connect(path, readonly=True)
        stored_environment = source.execute("SELECT value FROM settings WHERE key='environment'").fetchone()[0]
        if stored_environment != db.environment():
            source.close()
            raise ValueError(f"Database environment {stored_environment} does not match AJR_ENV={db.environment()}")
        conn = db.connect(stage)
        source.backup(conn)
        source.close()
        selected = set(part for value in (args.journal or []) for part in value.split(","))
        journals = list(conn.execute("SELECT * FROM journals ORDER BY slug"))
        if selected:
            unknown = selected - {row["slug"] for row in journals}
            if unknown:
                raise ValueError("Unknown journal slug: "+", ".join(sorted(unknown)))
            journals = [row for row in journals if row["slug"] in selected]
        if not journals:
            raise ValueError("No registered journals; run seed --file first")
        if any(row["is_synthetic"] for row in journals):
            raise ValueError("Live sync refuses synthetic journals")
        totals = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}
        for journal in journals:
            start_year = args.from_year or journal["start_year"]
            since = args.from_date or f"{start_year}-01-01"
            date.fromisoformat(since)
            if since>until:
                raise ValueError("from-date is after to-date")
            if not args.dry_run and (since != f"{journal['start_year']}-01-01" or until != today.isoformat()):
                raise ValueError("A persisted sync must cover the registry start_year through today. Use --dry-run for partial date windows, or update the registry start_year before an initial import.")
            indexed_from = None
            catchup_from = None
            if args.mode == "incremental":
                state = conn.execute("SELECT last_successful_indexed_at FROM sync_state WHERE journal_id=? AND provider='crossref'", (journal["id"],)).fetchone()
                if not state or not state[0]:
                    raise ValueError(f"No successful watermark for {journal['slug']}; run --mode initial first")
                indexed_from = (datetime.fromisoformat(state[0].replace("Z", "+00:00"))-timedelta(hours=48)).isoformat(timespec="seconds").replace("+00:00", "Z")
                catchup_from = max(since, indexed_from[:10])
            started = db.now()
            run_id = conn.execute("INSERT INTO ingest_runs (provider,journal_id,started_at,status,from_date,to_date,indexed_until) VALUES ('crossref',?,?,'running',?,?,?)", (journal["id"], started, since, until, fixed_indexed_until)).lastrowid
            counts = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}
            seen = set()
            issns = [r[0] for r in conn.execute("SELECT issn FROM journal_issns WHERE journal_id=? ORDER BY CASE medium WHEN 'print' THEN 0 ELSE 1 END,issn", (journal["id"],))]
            progress(f"{journal['slug']}: {args.mode}, publication {since}..{until}, fixed index through {fixed_indexed_until}", flush=True)
            limited = False
            windows = [(since, indexed_from)]
            if catchup_from:
                # Previously indexed future publications enter scope as time advances,
                # even when the publisher has not re-deposited their metadata.
                windows.append((catchup_from, None))
            for issn in issns:
                for window_from, window_indexed_from in windows:
                    for page_number, items in enumerate(client.works(issn, from_date=window_from, to_date=until, indexed_until=fixed_indexed_until, indexed_from=window_indexed_from), 1):
                        for record in items:
                            # ISSNs and catch-up windows may return the same work.
                            identifier = record.get("DOI")
                            if identifier and identifier.lower() in seen:
                                continue
                            if identifier:
                                seen.add(identifier.lower())
                            result = ingest_record(conn, journal["id"], record)
                            counts["fetched"] += 1
                            counts[result] += 1
                            if args.limit and counts["fetched"] >= args.limit:
                                limited = True
                                break
                        conn.commit()  # Checkpoint staging only; the production file is untouched.
                        progress(f"  {issn} page {page_number}: {len(items)} records; unique {counts['fetched']}", flush=True)
                        if limited:
                            break
                    if limited:
                        break
                if limited:
                    break
            finished = db.now()
            conn.execute("UPDATE ingest_runs SET finished_at=?,status=?,fetched_count=?,inserted_count=?,updated_count=?,skipped_count=? WHERE id=?", (finished, "dry-run" if args.dry_run else "success", counts["fetched"], counts["inserted"], counts["updated"], counts["skipped"], run_id))
            if not args.dry_run:
                conn.execute("INSERT INTO sync_state VALUES (?,'crossref',?,?,'success',NULL) ON CONFLICT(journal_id,provider) DO UPDATE SET last_successful_indexed_at=excluded.last_successful_indexed_at,last_run_at=excluded.last_run_at,last_status='success',last_error=NULL", (journal["id"], fixed_indexed_until, finished))
            conn.commit()
            for key in totals:
                totals[key] += counts[key]
        prune_orphan_authors(conn)
        conn.commit()
        db.validate(conn, production=stored_environment == "production" and not args.dry_run)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.close()
        conn = None
        if not args.dry_run:
            stage.replace(path)
        return totals | {"dry_run": args.dry_run, "indexed_until": fixed_indexed_until}
    finally:
        if conn:
            conn.close()
        stage.unlink(missing_ok=True)


def report(conn: sqlite3.Connection, output: Path) -> None:
    runs = conn.execute("SELECT r.*,j.name,j.slug FROM ingest_runs r LEFT JOIN journals j ON j.id=r.journal_id WHERE r.id IN (SELECT MAX(id) FROM ingest_runs GROUP BY journal_id,provider) ORDER BY j.name").fetchall()
    lines = ["# Metadata sync report", "", "Source: Crossref. This report records the latest completed run for each journal.", "", "| Journal | Status | Publication range | Indexed through (UTC) | Fetched | Added | Updated | Unchanged |", "|---|---|---|---|---:|---:|---:|---:|"]
    for run in runs:
        lines.append(f"| {run['name']} | {run['status']} | {run['from_date']} – {run['to_date']} | {run['indexed_until']} | {run['fetched_count']} | {run['inserted_count']} | {run['updated_count']} | {run['skipped_count']} |")
    lines.extend(["", "## Catalog quality", "", "| Journal | Articles | No assigned issue | No authors | No redistributable abstract |", "|---|---:|---:|---:|---:|"])
    for journal in conn.execute("SELECT * FROM journals ORDER BY name"):
        counts = conn.execute("SELECT COUNT(*),SUM(issue_id IS NULL),SUM(abstract_text IS NULL) FROM articles WHERE journal_id=?", (journal["id"],)).fetchone()
        no_authors = conn.execute("SELECT COUNT(*) FROM articles a WHERE journal_id=? AND NOT EXISTS (SELECT 1 FROM article_authors aa WHERE aa.article_id=a.id)", (journal["id"],)).fetchone()[0]
        denominator = counts[0] or 1
        lines.append(f"| {journal['name']} | {counts[0]} | {counts[1] or 0} ({(counts[1] or 0)/denominator:.1%}) | {no_authors} ({no_authors/denominator:.1%}) | {counts[2] or 0} ({(counts[2] or 0)/denominator:.1%}) |")
    lines.extend(["", "Only journal-article records matching the ISSN registry are included. Crossref does not reliably distinguish research articles from editorials or corrections; supplied titles and type labels are preserved.", "", "The date shown is print publication when present, then published, online publication, or issued. Partial dates retain their original precision. Online First includes records without both volume and issue; it is not a claim about publisher status.", "", "Work-level licenses do not establish abstract redistribution rights. Unverified abstracts are omitted from both the public SQLite snapshot and static exports.", "", "A successful indexed window confirms that all requested API pages completed; it does not prove publisher-archive completeness. Failed syncs never replace the published snapshot. Rerun the same command to retry from the last successful watermark.", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("db-init")
    seed = commands.add_parser("seed")
    seed.add_argument("--file", type=Path, default=db.ROOT / "data/journal_registry.csv")
    demo = commands.add_parser("seed-demo")
    demo.add_argument("--count", type=int, default=13, help="Synthetic article count for build scaling checks")
    sync = commands.add_parser("sync")
    sync.add_argument("--provider", choices=["crossref"], default="crossref")
    sync.add_argument("--journal", action="append", help="Registered slug; repeat or comma-separate to select multiple")
    sync.add_argument("--mode", choices=["initial", "incremental"], default="incremental")
    sync.add_argument("--from-year", type=int)
    sync.add_argument("--from-date")
    sync.add_argument("--to-date")
    sync.add_argument("--rows", type=int, default=1000)
    sync.add_argument("--limit", type=int)
    sync.add_argument("--request-budget", type=int, default=1000)
    sync.add_argument("--dry-run", action="store_true")
    validate = commands.add_parser("validate")
    validate.add_argument("--production", action="store_true")
    commands.add_parser("stats")
    export = commands.add_parser("export")
    export.add_argument("--out", type=Path, default=Path(".generated"))
    report_parser = commands.add_parser("report")
    report_parser.add_argument("--out", type=Path, default=Path("data/sync-report.md"))
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    path = db.db_path()
    try:
        if args.command == "db-init":
            db.initialize(path)
            print(f"Initialized {path} ({db.environment()})")
            return 0
        if not path.exists():
            raise ValueError(f"Database does not exist: {path}. Run db-init first.")
        if args.command == "sync":
            print(json.dumps(sync_database(path, args), indent=2))
            return 0
        if args.command == "seed-demo" and (path == db.DEFAULT_DB.resolve() or db.environment() != "demo"):
            raise ValueError("seed-demo requires AJR_ENV=demo and AJR_DB_PATH pointing outside data/journals.sqlite")
        with db.connect(path, readonly=args.command in {"validate", "stats", "export", "report"}) as conn:
            stored = conn.execute("SELECT value FROM settings WHERE key='environment'").fetchone()
            if stored[0] != db.environment():
                raise ValueError(f"Database environment {stored[0]} does not match AJR_ENV={db.environment()}")
            if args.command == "seed":
                print(f"Registered {db.seed_registry(conn, args.file)} journals")
            elif args.command == "seed-demo":
                print(f"Loaded {seed_demo(conn, count=args.count)} synthetic articles")
            elif args.command == "validate":
                print(json.dumps(db.validate(conn, production=args.production), indent=2))
            elif args.command == "stats":
                print(json.dumps(db.statistics(conn), indent=2))
            elif args.command == "export":
                print(json.dumps(export_catalog(conn, args.out, production=db.environment()=="production"), indent=2))
            elif args.command == "report":
                report(conn, args.out)
                print(f"Report written to {args.out}")
        conn.close()
        if path.stat().st_size >= 50_000_000:
            print("WARNING: SQLite snapshot exceeds 50 MB; evaluate external snapshot storage", file=sys.stderr)
        return 0
    except (ValueError, RuntimeError, sqlite3.Error, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
