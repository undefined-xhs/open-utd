import copy
import sqlite3

import pytest

from scripts.db import statistics, validate
from scripts.reconcile import ingest_record, prune_orphan_authors


def test_upsert_retains_public_identity_and_author_order(connection, record):
    assert ingest_record(connection, 1, record) == "inserted"
    identity = connection.execute("SELECT public_id FROM articles").fetchone()[0]
    assert ingest_record(connection, 1, record) == "skipped"
    record["DOI"] = "https://doi.org/10.5555/synthetic.001"
    record["title"] = ["Corrected synthetic title"]
    record["author"].reverse()
    assert ingest_record(connection, 1, record) == "updated"
    assert connection.execute("SELECT public_id,title FROM articles").fetchone()[:] == (identity,"Corrected synthetic title")
    bylines = list(connection.execute("SELECT byline_name FROM article_authors ORDER BY author_position"))
    assert [row[0] for row in bylines] == ["Morgan Example", "Alex Example"]
    prune_orphan_authors(connection)
    assert statistics(connection)["articles"] == 1


def test_later_issue_assignment_retains_article(connection, record):
    record.pop("issue")
    ingest_record(connection, 1, record)
    first = connection.execute("SELECT public_id,issue_id FROM articles").fetchone()
    assert first[1] is None
    record["issue"] = "1-2"
    ingest_record(connection, 1, record)
    second = connection.execute("SELECT public_id,issue_id FROM articles").fetchone()
    assert first[0] == second[0] and second[1]


def test_different_orcids_and_unidentified_same_names_are_distinct(connection, record):
    record["author"] = [{"given":"Alex","family":"Example"}]
    ingest_record(connection,1,record)
    record["DOI"] = "10.5555/synthetic.002"
    ingest_record(connection,1,record)
    assert statistics(connection)["authors"] == 2
    record["DOI"] = "10.5555/synthetic.003"
    record["author"][0]["ORCID"] = "0000-0002-1825-0097"
    ingest_record(connection,1,record)
    record["DOI"] = "10.5555/synthetic.004"
    record["author"][0]["ORCID"] = "0000-0001-5109-3700"
    ingest_record(connection,1,record)
    assert statistics(connection)["authors"] == 4


def test_rights_do_not_follow_work_level_license(connection,record):
    ingest_record(connection,1,record)
    row = connection.execute("SELECT abstract_text,abstract_display_status FROM articles").fetchone()
    assert row[:] == (None,"unknown")
    assert "PRIVATE-ABSTRACT-SENTINEL" not in " ".join(connection.iterdump())
    assert validate(connection,production=True)["articles"] == 1


def test_missing_doi_does_not_merge_by_title(connection,record):
    record.pop("DOI")
    ingest_record(connection,1,record)
    ingest_record(connection,1,record)
    assert statistics(connection)["articles"] == 1
    record["_source_id"] = "separate-source-record"
    ingest_record(connection,1,record)
    assert statistics(connection)["articles"] == 2


def test_doi_cannot_move_to_other_journal(connection,record):
    ingest_record(connection,1,record)
    connection.execute("INSERT INTO journals (id,public_id,slug,name,created_at,updated_at) VALUES (2,'j_two','other','Other','2026','2026')")
    connection.execute("INSERT INTO journal_issns VALUES (2,'2049-3630','unknown')")
    record["ISSN"] = ["2049-3630"]
    with pytest.raises(ValueError, match="journal conflict"):
        ingest_record(connection,2,record)


def test_issue_journal_constraint(connection,record):
    ingest_record(connection,1,record)
    connection.execute("INSERT INTO journals (id,public_id,slug,name,created_at,updated_at) VALUES (2,'j_two','other','Other','2026','2026')")
    with pytest.raises(sqlite3.IntegrityError,match="same journal"):
        connection.execute("UPDATE articles SET journal_id=2")
    with pytest.raises(sqlite3.IntegrityError,match="another journal"):
        connection.execute("UPDATE issues SET journal_id=2")
