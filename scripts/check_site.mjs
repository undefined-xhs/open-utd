import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
const manifest = JSON.parse(readFileSync('.generated/manifest.json','utf8'));
assert(existsSync('dist/pagefind/pagefind.js'), 'Pagefind search bundle missing');
const terms = new Set();
const links = html => [...html.matchAll(/<a\b[^>]*\bhref="([^"]+)"/g)].map(match=>match[1]);
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
  const data=JSON.parse(readFileSync(`.generated/journals/${journal.public_id}.json`,'utf8'));
  const rootLinks=links(html);
  assert(/<h1[^>]*data-original/.test(html),'Journal names must be protected from UI translation');
  assert(html.includes('data-set-language="en"') && html.includes('data-set-language="zh-CN"'),'Language switch must be present');
  const term=`journal:${journal.public_id}`;
  const reviews=readFileSync(`dist/journals/${journal.slug}/reviews/index.html`,'utf8');
  assertDiscussion(reviews, term);
  assert(!/<div\b[^>]*\bdata-giscus-host(?=[\s=>])/.test(html),'Journal archive must link to its separate review page');
  assert(rootLinks.some(link=>link.endsWith(`/journals/${journal.slug}/reviews/`)),'Archive must expose its journal reviews');
  assert(!rootLinks.some(link=>/\/articles\/[^/]+\/$/.test(link)),'Journal root must not render a bulk article list');
  assert(html.includes('data-pagefind-filter="journal"'),'Journal must be searchable by filter');
  assert(!reviews.includes('data-pagefind-body'),'Review pages must not duplicate the journal search record');
  const years=new Map();
  for (const issue of data.issues) {
    const year=String(issue.publication_year ?? 'undated');
    if(!years.has(year))years.set(year,[]);
    years.get(year).push(issue.public_id);
  }
  for (const [year, ids] of years) {
    assert(rootLinks.some(link=>link.endsWith(`/journals/${journal.slug}/years/${year}/`)),`Missing year navigation: ${journal.slug}/${year}`);
    const page=readFileSync(`dist/journals/${journal.slug}/years/${year}/index.html`,'utf8');
    const found=links(page).flatMap(link=>link.match(/\/issues\/([^/]+)\/$/)?.slice(1) ?? []);
    assert.deepEqual([...new Set(found)].sort(),ids.sort(),`Year must contain only its own issues: ${journal.slug}/${year}`);
    assert(!page.includes('data-pagefind-body'),'Year pages must not duplicate article search records');
  }
  const online=[];
  for(let page=1;page<=Math.max(1,Math.ceil(data.online_first.length/30));page++) {
    const content=readFileSync(`dist/journals/${journal.slug}/online-first/${page}/index.html`,'utf8');
    const ids=links(content).flatMap(link=>link.match(/\/articles\/([^/]+)\/$/)?.slice(1) ?? []);
    assert(ids.length<=30,'Online First pages must contain at most 30 articles');
    assert.deepEqual(ids,data.online_first.slice((page-1)*30,page*30).map(article=>article.public_id),'Online First pagination must preserve every article exactly once and in order');
    assert(!content.includes('data-pagefind-body'),'Online First pages must not duplicate article search records');
    online.push(...ids);
  }
  assert.equal(online.length,data.online_first.length,'Online First pagination must retain every source article');
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
