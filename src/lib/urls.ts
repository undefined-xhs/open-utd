import type { JournalBrief, IssueBrief } from './types';
export const basePath = `/${import.meta.env.BASE_URL.replace(/^\/+|\/+$/g, '')}/`.replace('//', '/');
export const href = (path = '') => basePath + path.replace(/^\/+/, '');
export const journalUrl = (journal: Pick<JournalBrief,'slug'>) => href(`journals/${encodeURIComponent(journal.slug)}/`);
export const issueUrl = (journal: Pick<JournalBrief,'slug'>, issue: Pick<IssueBrief,'public_id'>) => href(`journals/${encodeURIComponent(journal.slug)}/issues/${encodeURIComponent(issue.public_id)}/`);
export const articleUrl = (id: string) => href(`articles/${encodeURIComponent(id)}/`);
export function safeExternal(value?: string | null): string | undefined {
  if (!value) return undefined;
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined; }
  catch { return undefined; }
}
export function doiUrl(doi?: string | null): string | undefined {
  if (!doi || !/^10\.\d{4,9}\/\S+$/i.test(doi)) return undefined;
  return `https://doi.org/${doi.split('/').map(encodeURIComponent).join('/')}`;
}
export function orcidUrl(orcid?: string | null): string | undefined {
  const id = orcid?.replace(/^https?:\/\/orcid.org\//, '');
  return id && /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/i.test(id) ? `https://orcid.org/${id}` : undefined;
}
export const repositoryUrl = 'https://github.com/allenz-me/open-utd';
