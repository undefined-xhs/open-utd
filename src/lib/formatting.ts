import type { IssueBrief } from './types';
export const number = (value: number | undefined) => new Intl.NumberFormat('en').format(value || 0);
export function date(value?: string | null): string {
  if (!value) return 'Not recorded';
  if (/^\d{4}$/.test(value)) return value;
  if (/^\d{4}-\d{2}$/.test(value)) return new Intl.DateTimeFormat('en', {month:'long', year:'numeric', timeZone:'UTC'}).format(new Date(`${value}-01T00:00:00Z`));
  const parsed = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('en', {day:'numeric', month:'short', year:'numeric', timeZone:'UTC'}).format(parsed);
}
export function issueTitle(issue: IssueBrief): string {
  return [issue.volume && `Volume ${issue.volume}`, issue.issue_number && `Issue ${issue.issue_number}`].filter(Boolean).join(' · ') || 'Unspecified issue';
}
export function jsonLd(value: unknown): string {
  return JSON.stringify(value).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
}
