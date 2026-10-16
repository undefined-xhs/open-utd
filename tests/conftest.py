import json
from pathlib import Path

import pytest

from scripts import db


@pytest.fixture
def connection(tmp_path, monkeypatch):
    path = tmp_path / "catalog.sqlite"
    # Test databases have their own environment; do not inherit the surrounding
    # CI/demo build mode or the path of any real snapshot.
    monkeypatch.setenv("AJR_ENV", "production")
    monkeypatch.setenv("AJR_DB_PATH", str(path))
    db.initialize(path, "production")
    conn = db.connect(path)
    conn.execute("INSERT INTO journals (public_id,slug,name,start_year,created_at,updated_at) VALUES ('j_one','test-journal','Test Journal',2006,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    conn.execute("INSERT INTO journal_issns VALUES (1,'1234-5679','print')")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def record():
    return json.loads((Path(__file__).parent / "fixtures/crossref-journal-article.json").read_text())
