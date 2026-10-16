import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
const manifest = JSON.parse(readFileSync('.generated/manifest.json','utf8'));
assert(existsSync('dist/pagefind/pagefind.js'), 'Pagefind search bundle missing');
const terms = new Set();
function assertDiscussion(html, term) {
  // Client code may mention giscus even when no repository is configured.
  // Inspect the rendered host element, not URL strings inside JavaScript.
  const hosts = [...html.matchAll(/<div\b[^>]*\bdata-giscus-host(?=[\s=>])[^>]*>/g)];
  if (hosts.length) {
    assert.equal(hosts.length, 1, 'Each page must render exactly one configured discussion host');
    const host = hosts[0][0];
    assert(host.includes(`data-term="${term}"`), `Configured discussion has wrong stable term: ${term}`);
    assert(host.includes('data-mapping="specific"') && host.includes('data-strict="1"'), 'giscus must use strict stable-ID matching');
  } else {
    assert(html.includes(`data-discussion-term="${term}"`), `Unconfigured discussion must retain its stable placeholder term: ${term}`);
  }
}
for (const journal of manifest.journals) {
  const html=readFileSync(`dist/journals/${journal.slug}/index.html`,'utf8');
  assert(/<h1[^>]*data-original/.test(html),'Journal names must be protected from UI translation');
  assert(html.includes('data-set-language="en"') && html.includes('data-set-language="zh-CN"'),'Language switch must be present');
  const term=`journal:${journal.public_id}`;
  assertDiscussion(html, term);
  assert(html.includes('data-pagefind-filter="journal"'),'Journal must be searchable by filter');
  terms.add(term);
}
for (const article of manifest.articles) {
  const html=readFileSync(`dist/articles/${article.public_id}/index.html`,'utf8');
  assert(/<h1[^>]*data-original/.test(html),'Article titles must be protected from UI translation');
  assert(/class="byline"[^>]*data-original/.test(html),'Author names must be protected from UI translation');
  const term=`article:${article.public_id}`;
  assertDiscussion(html, term);
  assert(html.includes('data-pagefind-body'),'Article must be indexed by Pagefind');
  assert(html.includes('data-pagefind-filter="journal"'),'Article must have journal filter');
  assert(!terms.has(term),'Discussion terms must be globally unique');terms.add(term);
}
console.log(`Verified Pagefind and ${terms.size} independent stable discussions.`);
const check=spawnSync('python3',['scripts/check_site.py'],{stdio:'inherit',env:process.env});
process.exit(check.status ?? 1);
