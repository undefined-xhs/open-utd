export interface JournalBrief { public_id: string; slug: string; name: string }
export interface Journal extends JournalBrief {
  abbreviation: string | null; publisher: string | null; subject: string | null;
  issn_l: string | null; issns: string[]; homepage_url: string | null;
  article_count: number; issue_count: number; start_year?: number;
  last_synced_at: string | null; updated_at: string;
}
export interface IssueBrief {
  public_id: string; volume: string | null; issue_number: string | null;
  publication_year: number | null;
}
export interface Issue extends IssueBrief {
  issue_title: string | null; publication_date: string | null; article_count: number;
}
export interface Author {
  display_name: string; byline_name: string; orcid: string | null; affiliation_text: string | null;
}
export interface Article {
  public_id: string; title: string; doi: string | null; authors: Author[];
  journal: JournalBrief; issue: IssueBrief | null;
  abstract_text: string | null; abstract_source: string | null;
  abstract_license_url: string | null;
  abstract_display_status: 'permitted' | 'unknown' | 'restricted';
  publication_date: string | null; date_precision: string | null;
  publication_year: number | null; pages: string | null; article_type: string | null;
  landing_url: string | null; metadata_source: string | null; updated_at: string;
}
export interface JournalDetail extends Journal { issues: Issue[]; online_first: Article[] }
export interface IssueDetail extends Issue { journal: JournalBrief; articles: Article[] }
export interface Manifest {
  schema_version: 1; environment: 'demo' | 'production';
  journals: {public_id: string; slug: string}[];
  issues: {public_id: string; journal_slug: string}[];
  articles: {public_id: string; journal_public_id: string}[];
  stats: {journals: number; issues: number; articles: number; authors: number};
  updated_at: string | null;
}
