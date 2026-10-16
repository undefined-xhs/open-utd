"""Inspect the final static artifact and fail before publishing unsafe size/state.

Uses only the Python standard library; can be run locally or in Actions.
Thresholds are engineering budgets, not a claim about SQLite capacity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys


def inspect(db: Path, dist: Path, build_seconds: float) -> tuple[dict, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = (dist / "index.html", dist / "404.html", dist / "pagefind" / "pagefind.js")
    for path in required:
        if not path.is_file():
            errors.append(f"Missing build artifact: {path}")
    if not db.is_file():
        errors.append(f"Missing SQLite snapshot: {db}")
    files = list(dist.rglob("*")) if dist.is_dir() else []
    for path in files:
        if path.is_symlink():
            errors.append(f"Static artifacts must not contain symbolic links: {path}")
        if path.suffix in {".sqlite", ".sqlite3", ".db"} or path.name.startswith(".env"):
            errors.append(f"Private/build-only file found in static artifact: {path}")
    regular_files = [p for p in files if p.is_file() and not p.is_symlink()]
    metrics: dict = {
        "database_bytes": db.stat().st_size if db.is_file() else 0,
        "static_site_bytes": sum(p.stat().st_size for p in regular_files),
        "pagefind_bytes": sum(p.stat().st_size for p in regular_files if "pagefind" in p.relative_to(dist).parts),
        "html_pages": sum(p.suffix == ".html" for p in regular_files),
        "artifact_files": len(regular_files),
        "build_seconds": round(build_seconds, 2),
    }
    if db.is_file():
        try:
            with sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True) as connection:
                metrics["records"] = {
                    table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("journals", "issues", "articles", "authors")
                }
        except sqlite3.Error as exc:
            errors.append(f"Cannot count validated database records: {exc}")
    budgets = (
        ("database_bytes", 50_000_000, "SQLite exceeds 50 MB; plan external snapshot storage before Git file limits."),
        ("static_site_bytes", 500_000_000, "Static site exceeds 500 MB; inspect HTML/index growth and Pages headroom."),
        ("pagefind_bytes", 50_000_000, "Pagefind exceeds 50 MB; measure first-search latency and review index scope."),
        ("build_seconds", 300, "Static build exceeds 5 minutes; profile before expanding the catalogue."),
    )
    warnings.extend(message for key, limit, message in budgets if metrics[key] >= limit)
    if metrics["static_site_bytes"] >= 900_000_000:
        errors.append("Static site reached the 900 MB deployment guard; no Pages publication is allowed.")
    if metrics["database_bytes"] >= 95_000_000:
        errors.append("SQLite reached the 95 MB Git snapshot guard; move storage before committing more data.")
    return metrics, warnings, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.getenv("AJR_DB_PATH", "data/journals.sqlite")))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--build-seconds", type=float, default=0)
    parser.add_argument("--out", type=Path, default=Path("build-metrics.json"))
    args = parser.parse_args()
    if args.build_seconds < 0:
        parser.error("--build-seconds cannot be negative")
    metrics, warnings, errors = inspect(args.db, args.dist, args.build_seconds)
    report = {**metrics, "warnings": warnings, "errors": errors}
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = ["## Build resources", "", "| Metric | Value |", "| --- | ---: |"]
    rows.extend(f"| {key} | {value:,} |" for key, value in metrics.items() if key != "records")
    rows.extend(f"| {key} records | {value:,} |" for key, value in metrics.get("records", {}).items())
    rows.extend(["", *[f"- Warning: {message}" for message in warnings], *[f"- Error: {message}" for message in errors]])
    markdown = "\n".join(rows) + "\n"
    Path("build-metrics.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    if summary_path := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    for level, messages in (("warning", warnings), ("error", errors)):
        for message in messages:
            print(f"::{level}::{message}" if os.getenv("GITHUB_ACTIONS") else f"{level}: {message}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
