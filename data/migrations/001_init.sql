CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE journals (
 id INTEGER PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
 slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, abbreviation TEXT,
 issn_l TEXT, publisher TEXT, subject TEXT, homepage_url TEXT,
 start_year INTEGER NOT NULL DEFAULT 2006,
 is_visible INTEGER NOT NULL DEFAULT 1 CHECK(is_visible IN (0,1)),
 is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE journal_issns (
 journal_id INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
 issn TEXT NOT NULL UNIQUE, medium TEXT NOT NULL DEFAULT 'unknown',
 PRIMARY KEY(journal_id, issn)
);
CREATE TABLE issues (
 id INTEGER PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
 journal_id INTEGER NOT NULL REFERENCES journals(id), issue_key TEXT NOT NULL,
 volume TEXT, issue_number TEXT, issue_title TEXT,
 publication_year INTEGER, publication_date TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(journal_id, issue_key)
);
CREATE TABLE articles (
 id INTEGER PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
 journal_id INTEGER NOT NULL REFERENCES journals(id), issue_id INTEGER REFERENCES issues(id),
 doi TEXT COLLATE NOCASE UNIQUE, openalex_id TEXT UNIQUE,
 title TEXT NOT NULL, abstract_text TEXT, abstract_source TEXT,
 abstract_license_url TEXT, abstract_display_status TEXT NOT NULL DEFAULT 'unknown'
 CHECK(abstract_display_status IN ('permitted','unknown','restricted')),
 abstract_rights_verified INTEGER NOT NULL DEFAULT 0 CHECK(abstract_rights_verified IN (0,1)),
 publication_date TEXT, date_precision TEXT CHECK(date_precision IN ('year','month','day')),
 publication_year INTEGER, pages TEXT, article_type TEXT, landing_url TEXT,
 metadata_source TEXT, source_modified_at TEXT, source_record_key TEXT UNIQUE,
 source_hash TEXT, is_synthetic INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE authors (
 id INTEGER PRIMARY KEY, public_id TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
 orcid TEXT UNIQUE, openalex_id TEXT UNIQUE
);
CREATE TABLE article_authors (
 article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES authors(id), author_position INTEGER NOT NULL,
 byline_name TEXT NOT NULL, affiliation_text TEXT,
 PRIMARY KEY(article_id,author_position)
);
CREATE TABLE sync_state (
 journal_id INTEGER NOT NULL REFERENCES journals(id), provider TEXT NOT NULL,
 last_successful_indexed_at TEXT, last_run_at TEXT, last_status TEXT, last_error TEXT,
 PRIMARY KEY(journal_id,provider)
);
CREATE TABLE ingest_runs (
 id INTEGER PRIMARY KEY, provider TEXT NOT NULL,
 journal_id INTEGER REFERENCES journals(id), started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL, fetched_count INTEGER NOT NULL DEFAULT 0,
 inserted_count INTEGER NOT NULL DEFAULT 0, updated_count INTEGER NOT NULL DEFAULT 0,
 skipped_count INTEGER NOT NULL DEFAULT 0, error_text TEXT,
 from_date TEXT, to_date TEXT, indexed_until TEXT
);
CREATE TABLE source_records (
 article_id INTEGER PRIMARY KEY REFERENCES articles(id), provider TEXT NOT NULL,
 original_identifier TEXT, source_dates_json TEXT, metadata_hash TEXT NOT NULL
);
CREATE INDEX idx_issues_journal_year ON issues(journal_id,publication_year,volume,issue_number);
CREATE INDEX idx_articles_journal_year ON articles(journal_id,publication_year);
CREATE INDEX idx_articles_issue ON articles(issue_id);
CREATE INDEX idx_article_authors_author ON article_authors(author_id);
CREATE TRIGGER article_issue_insert BEFORE INSERT ON articles
WHEN NEW.issue_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM issues WHERE id=NEW.issue_id AND journal_id=NEW.journal_id
)
BEGIN SELECT RAISE(ABORT,'article and issue must belong to the same journal'); END;
CREATE TRIGGER article_issue_update BEFORE UPDATE OF issue_id,journal_id ON articles
WHEN NEW.issue_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM issues WHERE id=NEW.issue_id AND journal_id=NEW.journal_id
)
BEGIN SELECT RAISE(ABORT,'article and issue must belong to the same journal'); END;
CREATE TRIGGER issue_journal_update BEFORE UPDATE OF journal_id ON issues
WHEN EXISTS (SELECT 1 FROM articles WHERE issue_id=OLD.id AND journal_id!=NEW.journal_id)
BEGIN SELECT RAISE(ABORT,'cannot move an assigned issue to another journal'); END;
