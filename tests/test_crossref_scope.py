import pytest

from scripts import db
from scripts.reconcile import ingest_record


PRINT = "1234-5679"
ELECTRONIC = "2049-3630"
STAMP = "2026-10-16T09:00:00Z"


def registry(tmp_path, policy=None, *, electronic=True):
    path = tmp_path / "registry.csv"
    path.write_text(
        "public_id,slug,name,issn_print,issn_electronic,start_year,crossref_issns\n"
        f"j_one,test-journal,Test Journal,{PRINT},{ELECTRONIC if electronic else ''},2006,{policy or ''}\n"
    )
    return path


def mark_success(conn):
    conn.execute("INSERT OR REPLACE INTO sync_state VALUES (1,'crossref',?,?,'success',NULL)", (STAMP, STAMP))


def test_optional_policy_is_normalized_without_changing_bibliographic_issns(connection, tmp_path):
    path = registry(tmp_path, " 20493630 ;12345679;2049-3630 ")
    row = db.registry_rows(path)[0]
    assert row["crossref_issns"] == f"{PRINT};{ELECTRONIC}"
    assert set(row["_issns"]) == {PRINT, ELECTRONIC}
    db.seed_registry(connection, path)
    journal = connection.execute("SELECT * FROM journals").fetchone()
    assert journal["crossref_issns"] == f"{PRINT};{ELECTRONIC}"
    assert db.crossref_query_issns(connection, journal) == [PRINT, ELECTRONIC]
    path.write_text("public_id,slug,name,issn_print\nj_one,test-journal,Test Journal,1234-5679\n")
    assert db.registry_rows(path)[0]["crossref_issns"] is None


@pytest.mark.parametrize("policy", ["1234-5678", "not-an-issn", "0165-4101", "1234-5679;"])
def test_invalid_or_unregistered_query_issn_is_rejected(tmp_path, policy):
    with pytest.raises(ValueError, match="ISSN|crossref_issns"):
        db.registry_rows(registry(tmp_path, policy))


def test_another_journals_query_issn_is_rejected(tmp_path):
    path = registry(tmp_path, "0165-4101")
    with path.open("a") as handle:
        handle.write("j_other,other,Other Journal,0165-4101,,2006,\n")
    with pytest.raises(ValueError, match="same journal"):
        db.registry_rows(path)


@pytest.mark.parametrize("old_policy,new_policy", [
    (None, PRINT), (PRINT, None), (PRINT, ELECTRONIC),
    (PRINT, f"{PRINT};{ELECTRONIC}"), (f"{PRINT};{ELECTRONIC}", PRINT),
])
def test_changed_query_set_invalidates_watermark(connection, tmp_path, old_policy, new_policy):
    db.seed_registry(connection, registry(tmp_path, old_policy))
    mark_success(connection)
    db.seed_registry(connection, registry(tmp_path, new_policy))
    assert connection.execute("SELECT last_successful_indexed_at,last_status FROM sync_state").fetchone()[:] == (None, "scope_changed")
    assert connection.execute("SELECT public_id FROM journals").fetchone()[0] == "j_one"


@pytest.mark.parametrize("old_policy,new_policy", [
    (None, f"{ELECTRONIC};{PRINT}"), (f"{PRINT};{ELECTRONIC}", None),
    (PRINT, "12345679;1234-5679"),
])
def test_unchanged_effective_query_set_retains_watermark(connection, tmp_path, old_policy, new_policy):
    db.seed_registry(connection, registry(tmp_path, old_policy))
    mark_success(connection)
    db.seed_registry(connection, registry(tmp_path, new_policy))
    assert connection.execute("SELECT last_successful_indexed_at,last_status FROM sync_state").fetchone()[:] == (STAMP, "success")


def test_default_policy_includes_historic_issns_removed_from_csv(connection, tmp_path):
    db.seed_registry(connection, registry(tmp_path, PRINT))
    mark_success(connection)
    db.seed_registry(connection, registry(tmp_path, electronic=False))
    assert connection.execute("SELECT last_successful_indexed_at FROM sync_state").fetchone()[0] is None
    journal = connection.execute("SELECT * FROM journals").fetchone()
    assert db.crossref_query_issns(connection, journal) == [PRINT, ELECTRONIC]
    mark_success(connection)
    db.seed_registry(connection, registry(tmp_path, electronic=False))
    assert connection.execute("SELECT last_successful_indexed_at FROM sync_state").fetchone()[0] == STAMP


@pytest.mark.parametrize("policy", ["0165-4101", "12345679", " "])
def test_database_validation_rejects_invalid_or_noncanonical_policy(connection, policy):
    connection.execute("UPDATE journals SET crossref_issns=?", (policy,))
    with pytest.raises(ValueError, match="crossref_issns"):
        db.validate(connection)


def test_legacy_snapshot_migrates_without_changing_ids_or_metadata(tmp_path, record):
    path = tmp_path / "legacy.sqlite"
    tables = ("journals", "journal_issns", "issues", "articles", "authors", "article_authors", "source_records", "sync_state")
    with db.connect(path) as conn:
        conn.executescript((db.ROOT / "data/migrations/001_init.sql").read_text())
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_migrations VALUES ('001_init',?)", (STAMP,))
        conn.execute("INSERT INTO settings VALUES ('environment','production')")
        conn.execute("INSERT INTO journals (id,public_id,slug,name,created_at,updated_at) VALUES (1,'j_one','test-journal','Test Journal',?,?)", (STAMP, STAMP))
        conn.execute("INSERT INTO journal_issns VALUES (1,?,'print')", (PRINT,))
        ingest_record(conn, 1, record)
        mark_success(conn)
        assert db.validate(conn, production=True)["articles"] == 1
        columns = {table: [r[1] for r in conn.execute(f"PRAGMA table_info({table})")] for table in tables}
        before = {table: [tuple(r) for r in conn.execute(f"SELECT * FROM {table}")] for table in tables}
    db.initialize(path, "production")
    db.initialize(path, "production")
    with db.connect(path) as conn:
        for table in tables:
            assert [tuple(r) for r in conn.execute(f"SELECT {','.join(columns[table])} FROM {table}")] == before[table]
        assert conn.execute("SELECT crossref_issns FROM journals").fetchone()[0] is None
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 2
        assert db.validate(conn, production=True)["articles"] == 1
