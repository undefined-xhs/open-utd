from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import db
from scripts.cli import parser, sync_database


def args(*extra):
    return parser().parse_args(["sync","--mode","initial",*extra])


class FakeClient:
    def __init__(self, record, fail=False):
        self.record,self.fail,self.calls = record,fail,[]
    def works(self,issn,**kwargs):
        self.calls.append((issn,kwargs))
        yield [self.record]
        if self.fail:
            raise RuntimeError("Simulated interruption after a successful page")


def path_for(connection):
    return Path(connection.execute("PRAGMA database_list").fetchone()[2])


def test_failed_page_keeps_original_database_byte_for_byte(connection,record):
    path = path_for(connection)
    before = path.read_bytes()
    with pytest.raises(RuntimeError,match="interruption"):
        sync_database(path,args(),client=FakeClient(record,fail=True),progress=lambda *a,**k:None)
    assert path.read_bytes()==before
    assert not list(path.parent.glob(".sync-*.sqlite"))


def test_complete_window_promotes_and_is_idempotent(connection,record):
    path = path_for(connection)
    first = sync_database(path,args(),client=FakeClient(record),progress=lambda *a,**k:None)
    assert first["inserted"]==1
    with db.connect(path) as current:
        public_id = current.execute("SELECT public_id FROM articles").fetchone()[0]
    client = FakeClient(record)
    second = sync_database(path,args("--mode","incremental"),client=client,progress=lambda *a,**k:None)
    assert second["inserted"]==0 and second["skipped"]==1
    assert len(client.calls)==2
    assert client.calls[0][1]["indexed_from"]
    assert client.calls[1][1]["indexed_from"] is None  # Publication catch-up for pre-indexed future works.
    with db.connect(path) as current:
        assert current.execute("SELECT public_id FROM articles").fetchone()[0]==public_id
        assert current.execute("SELECT COUNT(*) FROM ingest_runs WHERE status='success'").fetchone()[0]==2


def test_dry_run_leaves_no_checkpoint_or_mutation(connection,record):
    path=path_for(connection)
    before=path.read_bytes()
    result=sync_database(path,args("--dry-run","--limit","1"),client=FakeClient(record),progress=lambda *a,**k:None)
    assert result["dry_run"] and path.read_bytes()==before


def test_partial_window_cannot_advance_watermark(connection,record):
    path=path_for(connection)
    before=path.read_bytes()
    with pytest.raises(ValueError,match="registry start_year"):
        sync_database(path,args("--from-year","2020"),client=FakeClient(record),progress=lambda *a,**k:None)
    assert path.read_bytes()==before


def test_incremental_needs_initial_import(connection,record):
    with pytest.raises(ValueError,match="No successful watermark"):
        sync_database(path_for(connection),args("--mode","incremental"),client=FakeClient(record),progress=lambda *a,**k:None)
