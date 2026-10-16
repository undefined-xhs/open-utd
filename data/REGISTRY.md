# Journal registry

The initial scope starts in 2006 and follows the latest metadata available from Crossref. Article pages are bibliographic records, not full-text copies. Publisher deposits may lag a published issue; an indexed catalogue is not a guarantee of complete coverage.

| Journal | Print ISSN | Online ISSN | Publisher source |
| --- | --- | --- | --- |
| Management Science | 0025-1909 | 1526-5501 | [INFORMS](https://pubsonline.informs.org/journal/mnsc) |
| Information Systems Research | 1047-7047 | 1526-5536 | [INFORMS](https://pubsonline.informs.org/journal/isre) |
| Marketing Science | 0732-2399 | 1526-548X | [INFORMS](https://pubsonline.informs.org/journal/mksc) |
| Operations Research | 0030-364X | 1526-5463 | [INFORMS](https://pubsonline.informs.org/journal/opre) |

These identifiers were checked against the publisher's journal pages on 2026-10-16. Print and electronic ISSNs belong to the same journal. The importer deduplicates articles by normalized DOI.

Edit `journal_registry.csv` to add journals. Keep `public_id` and `slug` unchanged after publication: the public ID links the journal to its Markdown discussion and the slug appears in public URLs. `start_year` controls each journal's earliest intended coverage. After adding a journal, run a manual initial import; a weekly incremental run requires a completed initial import.

Records registered as `journal-article` may include editorials and corrections. Crossref does not reliably distinguish all research articles from other journal content, so the site does not label every record a research paper.

Unlicensed abstracts are excluded from the public database snapshot, JSON exports, HTML, and search index. Visit the publisher via the DOI to read the abstract or full text. This rule matters because the SQLite snapshot is also public in the Git repository.
