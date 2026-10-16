-- NULL preserves the original policy: query every registered (including historic)
-- ISSN. A non-null value is a normalized, semicolon-separated harvesting subset;
-- the full bibliographic identifiers remain in journal_issns.
ALTER TABLE journals ADD COLUMN crossref_issns TEXT;
