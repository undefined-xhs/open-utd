import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Article, IssueDetail, Journal, JournalDetail, Manifest } from './types';
const root = resolve(process.cwd(), '.generated');
function read<T>(file: string): T {
  try { return JSON.parse(readFileSync(resolve(root, file), 'utf8')) as T; }
  catch (error) { throw new Error(`Cannot read .generated/${file}. Run npm run data:export first.`, {cause: error}); }
}
function publicId(value: string): string {
  if (!/^[a-zA-Z0-9_-]+$/.test(value)) throw new Error('Invalid public ID in catalog');
  return value;
}
// Exports are immutable during a build. Layouts render once per page, so parsing
// the complete manifest for each layout would make catalogue builds quadratic.
let manifestCache: Manifest | undefined;
let journalsCache: Journal[] | undefined;
export function getManifest(): Manifest {
  if (manifestCache) return manifestCache;
  const manifest = read<Manifest>('manifest.json');
  if (manifest.schema_version !== 1 || !Array.isArray(manifest.articles) || !Array.isArray(manifest.journals) || !['demo','production'].includes(manifest.environment)) {
    throw new Error('Unsupported catalog export schema');
  }
  manifestCache = manifest;
  return manifestCache;
}
export function getJournals(): Journal[] {
  if (journalsCache) return journalsCache;
  const journals = read<Journal[]>('journals-index.json');
  if (!Array.isArray(journals) || journals.some(j => !j.public_id || !j.slug || !j.name || !Array.isArray(j.issns))) throw new Error('Invalid journal catalog');
  journalsCache = journals;
  return journalsCache;
}
export function getJournal(id: string): JournalDetail { return read(`journals/${publicId(id)}.json`); }
export function getIssue(id: string): IssueDetail { return read(`issues/${publicId(id)}.json`); }
const articles = new Map<string, Map<string, Article>>();
export function getArticle(journalId: string, articleId: string): Article {
  if (!articles.has(journalId)) {
    const shard = read<Article[]>(`articles-by-journal/${publicId(journalId)}.json`);
    if (!Array.isArray(shard)) throw new Error('Invalid article shard');
    for (const article of shard) {
      if (article.abstract_display_status !== 'permitted' && article.abstract_text) throw new Error('Export contains an abstract without redistribution permission');
      if (!Array.isArray(article.authors) || !article.title || !article.journal) throw new Error('Invalid article record');
    }
    articles.set(journalId, new Map(shard.map(article => [article.public_id, article])));
  }
  const article = articles.get(journalId)!.get(articleId);
  if (!article) throw new Error(`Article ${articleId} missing from journal shard`);
  return article;
}
