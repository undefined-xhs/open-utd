import json

import pytest

from scripts import db
from scripts.demo import seed_demo
from scripts.export import export_catalog
from scripts.reconcile import ingest_record


def test_stable_shards_without_unlicensed_abstract(connection,record,tmp_path):
    ingest_record(connection,1,record)
    connection.commit()
    output = tmp_path / "generated"
    export_catalog(connection,output,production=True)
    original = {p.relative_to(output):p.read_bytes() for p in output.rglob("*") if p.is_file()}
    export_catalog(connection,output,production=True)
    assert original == {p.relative_to(output):p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert all(b"PRIVATE-ABSTRACT-SENTINEL" not in content for content in original.values())
    manifest = json.loads((output/"manifest.json").read_text())
    article_id = manifest["articles"][0]["public_id"]
    assert "/" not in article_id
    article = json.loads((output/"articles-by-journal/j_one.json").read_text())[0]
    assert article["abstract_text"] is None
    assert article["authors"][0]["byline_name"] == "Alex Example"
    assert article["issue"]["issue_number"] == "S1"


def test_unsafe_snapshot_is_rejected_before_export(connection,record,tmp_path):
    ingest_record(connection,1,record)
    connection.execute("UPDATE articles SET abstract_text='PRIVATE-ABSTRACT-SENTINEL'")
    with pytest.raises(ValueError,match="Unlicensed abstract"):
        export_catalog(connection,tmp_path/"generated")
    assert not (tmp_path/"generated").exists()


def test_export_cannot_delete_source_directory(connection,tmp_path):
    output = tmp_path/"source"
    output.mkdir()
    (output/"important.py").write_text("print('keep me')")
    with pytest.raises(ValueError,match="non-generated"):
        export_catalog(connection,output)
    assert (output/"important.py").exists()


def test_demo_is_complete_and_production_rejects_it(tmp_path):
    path = tmp_path/"demo.sqlite"
    db.initialize(path,"demo")
    with db.connect(path) as conn:
        seed_demo(conn)
        first = db.statistics(conn)
        seed_demo(conn)
        assert first == db.statistics(conn) == {"journals":2,"issues":4,"articles":13,"authors":26}
        assert conn.execute("SELECT COUNT(*) FROM articles WHERE issue_id IS NULL").fetchone()[0] == 1
        with pytest.raises(ValueError,match="demo database"):
            db.validate(conn,production=True)
        export_catalog(conn,tmp_path/"demo-export")
    assert "synthetic example" in "".join(p.read_text() for p in (tmp_path/"demo-export").rglob("*.json"))
