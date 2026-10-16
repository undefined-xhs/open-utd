"""Synthetic offline fixture data; never imported into the production database."""
from scripts.db import now
from scripts.reconcile import ingest_record, prune_orphan_authors


def seed_demo(conn, *, count=13):
    env = conn.execute("SELECT value FROM settings WHERE key='environment'").fetchone()
    if not env or env[0] != "demo":
        raise ValueError("seed-demo requires an isolated demo database")
    if conn.execute("SELECT 1 FROM journals WHERE is_synthetic=0 LIMIT 1").fetchone():
        raise ValueError("Do not mix production registry journals and demo records")
    if count < 13:
        count = max(1, count)
    for j, name in enumerate(("Synthetic Journal of Decisions", "Synthetic Information Research"), 1):
        slug = ("synthetic-decisions", "synthetic-information")[j-1]
        conn.execute("INSERT OR IGNORE INTO journals (public_id,slug,name,abbreviation,publisher,subject,start_year,is_synthetic,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (f"j_synthetic_{j}", slug, name, f"DEMO {j}", "Synthetic Demonstration Press", "Synthetic / Demo", 2006, 1, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
        journal_id = conn.execute("SELECT id FROM journals WHERE slug=?", (slug,)).fetchone()[0]
        issn = ("1234-5679", "2049-3630")[j-1]
        conn.execute("INSERT OR IGNORE INTO journal_issns VALUES (?,?,'unknown')", (journal_id, issn))
    journal_ids = [r[0] for r in conn.execute("SELECT id FROM journals ORDER BY public_id")]
    for index in range(count):
        j = 0 if index<6 or index>=12 and index%2==0 else 1
        record = {"_source_id": f"demo-{index}", "type": "journal-article", "ISSN": [("1234-5679", "2049-3630")[j]],
                  "title": [f"Synthetic study {index+1}: {(('Decisions under uncertainty','Information and collaboration','Markets and learning')[index%3])}"],
                  "published": {"date-parts": [[2025, index%12+1]]}, "volume": "1", "issue": str((index//3)%2+1),
                  "author": [{"given": "Alex", "family": "Example", "affiliation": [{"name": "Synthetic University"}]}, {"given": "Morgan", "family": f"Demo {index%3+1}"}],
                  "abstract": "<jats:p>This is a synthetic example, created solely to demonstrate the catalogue. It is not a published research paper.</jats:p>", "_abstract_permitted": index%3==0}
        if index>=12:
            record.pop("issue")
            record.pop("volume")
        ingest_record(conn, journal_ids[j], record, synthetic=True)
    prune_orphan_authors(conn)
    return count
