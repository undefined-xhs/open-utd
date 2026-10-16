import pytest

from scripts import db


def test_migrations_are_idempotent_and_environment_is_sticky(tmp_path):
    path = tmp_path/"db.sqlite"
    db.initialize(path,"production")
    db.initialize(path,"production")
    with db.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]==1
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0]==1
        assert db.validate(conn)["articles"]==0
        with pytest.raises(ValueError,match="no real articles"):
            db.validate(conn,production=True)
    with pytest.raises(ValueError,match="environment"):
        db.initialize(path,"demo")


def test_registry_multiple_issns_and_stable_identity(connection,tmp_path):
    registry = tmp_path/"journals.csv"
    registry.write_text("public_id,slug,name,issn_print,issn_electronic,start_year\nj_one,test-journal,Renamed Journal,1234-5679,2049-3630,2006\n")
    db.seed_registry(connection,registry)
    db.seed_registry(connection,registry)
    assert connection.execute("SELECT COUNT(*) FROM journal_issns").fetchone()[0]==2
    assert connection.execute("SELECT public_id,name FROM journals").fetchone()[:]==("j_one","Renamed Journal")
    registry.write_text("public_id,slug,name,issn_print\nj_two,other,Other,1234-5679\n")
    with pytest.raises(ValueError,match="another journal"):
        db.seed_registry(connection,registry)


def test_expanded_registry_scope_invalidates_watermark(connection,tmp_path):
    connection.execute("INSERT INTO sync_state VALUES (1,'crossref','2026-10-16T09:00:00Z','2026-10-16T09:00:00Z','success',NULL)")
    registry = tmp_path/"journals.csv"
    registry.write_text("public_id,slug,name,issn_print,issn_electronic,start_year\nj_one,test-journal,Test Journal,1234-5679,2049-3630,2006\n")
    db.seed_registry(connection,registry)
    assert connection.execute("SELECT last_successful_indexed_at,last_status FROM sync_state").fetchone()[:] == (None,"scope_changed")
    connection.execute("UPDATE sync_state SET last_successful_indexed_at='2026-10-16T09:00:00Z',last_status='success'")
    registry.write_text("public_id,slug,name,issn_print,issn_electronic,start_year\nj_one,test-journal,Test Journal,1234-5679,2049-3630,2000\n")
    db.seed_registry(connection,registry)
    assert connection.execute("SELECT last_successful_indexed_at FROM sync_state").fetchone()[0] is None
