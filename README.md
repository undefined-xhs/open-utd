# open-utd · Academic Journal Reviews

**English** · [简体中文](README-ZH.MD)

An open journal catalogue with searchable article metadata and discussions for journals and individual articles. Built with Python + SQLite, Astro + TypeScript + Tailwind CSS, Pagefind, and GitHub Actions / Pages. The interface supports English and Chinese; journal and article metadata remain in their original English.

Repository: [undefined-xhs/open-utd](https://github.com/undefined-xhs/open-utd) · Website: [www.open-utd-hot-take.xyz](https://www.open-utd-hot-take.xyz/).

## Interface languages

The **English / Chinese** switch covers navigation, buttons, filters, status messages, policies, and the comment interface. The preference is saved in the current browser's `localStorage` under `open-utd-language` and persists across reloads and navigation. Without a saved preference, browsers configured for Chinese use Chinese; other browsers use English. The static fallback is English when JavaScript is disabled.

**Journal names, article titles, and author names remain in the source English, without automatic translation. This site does not display or index article abstracts.** Switching languages does not change article or journal URLs, public IDs, search data, or discussion mappings. The giscus interface switches between `en` and `zh-CN`; existing comment text is unchanged.

## Coverage

| Journal | Print ISSN | Electronic ISSN | Start year |
| --- | --- | --- | ---: |
| Management Science | 0025-1909 | 1526-5501 | 2006 |
| Information Systems Research | 1047-7047 | 1526-5536 | 2006 |
| Marketing Science | 0732-2399 | 1526-548X | 2006 |
| Operations Research | 0030-364X | 1526-5463 | 2006 |
| The Accounting Review | 0001-4826 | 1558-7967 | 2006 |
| Journal of Accounting and Economics | 0165-4101 | 1879-1980 | 2006 |
| Journal of Accounting Research | 0021-8456 | 1475-679X | 2006 |
| The Journal of Finance | 0022-1082 | 1540-6261 | 2006 |
| Journal of Financial Economics | 0304-405X | 1879-2774 | 2006 |
| The Review of Financial Studies | 0893-9454 | 1465-7368 | 2006 |
| INFORMS Journal on Computing | 1091-9856 | 1526-5528 | 2006 |
| MIS Quarterly | 0276-7783 | 2162-9730 | 2006 |
| Journal of Consumer Research | 0093-5301 | 1537-5277 | 2006 |
| Journal of Marketing | 0022-2429 | 1547-7185 | 2006 |
| Journal of Marketing Research | 0022-2437 | 1547-7193 | 2006 |
| Journal of Operations Management | 0272-6963 | 1873-1317 | 2006 |
| Manufacturing & Service Operations Management | 1523-4614 | 1526-5498 | 2006 |
| Production and Operations Management | 1059-1478 | 1937-5956 | 2006 |
| Academy of Management Journal | 0001-4273 | 1948-0989 | 2006 |
| Academy of Management Review | 0363-7425 | 1930-3807 | 2006 |
| Administrative Science Quarterly | 0001-8392 | 1930-3815 | 2006 |
| Organization Science | 1047-7039 | 1526-5455 | 2006 |
| Journal of International Business Studies | 0047-2506 | 1478-6990 | 2006 |
| Strategic Management Journal | 0143-2095 | 1097-0266 | 2006 |

The journal registry is [`data/journal_registry.csv`](data/journal_registry.csv). An initial import covers records from 2006 through the data available in Crossref at the time of the run. Subsequent runs synchronize changes using Crossref's index timestamps. The website shows **metadata deposited with Crossref**. Deposit delays, missing issue information, and Online First records mean it cannot guarantee complete coverage of a publisher's latest issue. Consult the data sources page and synchronization report for coverage, and the publisher's journal website for its current table of contents. Synthetic demo data is clearly labelled and rejected by production validation.

Crossref's `journal-article` category can also include book reviews, errata, indexes, and code or data companion records; not every record is a research article. The source classification is preserved. Deduplication by DOI also does not automatically merge duplicate publisher deposits that have different DOIs.

The collection follows the [official UT Dallas list of 24 journals](https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/index.php). Verification sources for ISSNs and query endpoints are recorded in [`data/journal-registry-sources.md`](data/journal-registry-sources.md). Use the database and [`data/sync-report.md`](data/sync-report.md) for current issue and article counts and each journal's collection results.

## Browsing and discussions

Clicking a journal name on the homepage opens its catalogue. Each card also has a separate **Reviews & experiences** button and an archive link; journal discussions have their own pages. Browse records through **journal → year → issue → article**. Records without an assigned issue appear in a separate Online First list, with 30 records per page.

| Path, after the site's base path | Contents |
| --- | --- |
| `/journals/{slug}/` | Journal overview, discussion link, and year grid |
| `/journals/{slug}/reviews/` | Journal reviews and submission experiences |
| `/journals/{slug}/years/{year}/` | Issues in the selected year; missing years use `undated` |
| `/journals/{slug}/issues/{issueId}/` | Records in an issue; existing issue URLs are retained |
| `/journals/{slug}/online-first/{page}/` | Paginated Online First / Unassigned records, starting at page 1 |
| `/articles/{articleId}/` | Article metadata and its individual discussion; existing article URLs are retained |
| `/comments/` | Latest comments and replies across journal and article discussions, newest first, with source permalinks |

Navigation and comment controls support both interface languages; bibliographic metadata remains in English. Search can take visitors directly to an article. Year and pagination routes do not change existing article or issue public IDs.

## Run locally without API keys or comment configuration

Requirements: **Node.js 24**, **Python 3.12+**, and Git. Installing dependencies initially requires network access. The following demo, tests, and builds do not call Crossref or OpenAlex.

```bash
git clone https://github.com/undefined-xhs/open-utd.git
cd open-utd
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
npm ci

export AJR_ENV=demo
export AJR_DB_PATH=.local/demo.sqlite
export PUBLIC_SITE_URL=http://localhost:4321
export PUBLIC_BASE_PATH=/
python scripts/cli.py db-init
python scripts/cli.py seed-demo
python scripts/cli.py validate
python -m pytest -q
npm run check
npm run build
npm run test:site
npm run preview
```

Use the preview address printed in the terminal. `npm run build` exports the database, prepares an offline comment file if needed, builds the static Astro site, and creates the Pagefind index. The first local build creates an empty comment file explicitly marked as never synchronized; an existing comment snapshot is preserved. To reset to the offline empty state, run `python scripts/fetch_comments.py --empty`. Search requires a built index, so verify it with `preview`. Use `npm run dev` while editing pages; after changing the database, export it again or restart the development server.

[`.env.example`](.env.example) lists optional settings. Astro reads public configuration from a copied `.env` file, but the Python CLI reads shell environment variables, which must be set separately with `export`. Do not commit `.env`. Windows users can run these commands through WSL. The npm export script invokes `python3`, which must point to the Python environment with the project dependencies installed.

## Deploy with GitHub Actions

The repository has two workflows:

| Workflow / trigger | Behaviour |
| --- | --- |
| `ci.yml`: pull request targeting main / manual run | Read-only token, isolated temporary demo database, offline data tests, production snapshot validation when present, type checks, a subpath build, and static output checks |
| `site.yml`: push to main | Fetch comments and aggregate analytics, build from the committed production database, and deploy without calling Crossref |
| `site.yml`: comment created, edited, or deleted; discussion edited, deleted, transferred, or category changed | Compare complete comment and analytics snapshots with the published JSON; stop if both are unchanged, otherwise reuse cached HTML and Pagefind and replace both snapshots |
| `site.yml`: daily at 03:37 UTC, 11:37 in Asia/Shanghai | Refresh aggregate analytics and check comments, covering missed events and moderation changes; no Crossref requests or database commits |
| `site.yml`: Mondays at 02:23 UTC, 10:23 in Asia/Shanghai | Incremental Crossref synchronization → validation → tests → comment snapshot → build → database commit → upload → deployment in the same run |
| `site.yml`: manual run | Refresh comments and analytics, then deploy by default; Crossref runs only when metadata synchronization is enabled. Historical imports also require `initial_import`; `journal` can select one journal. Enable `comments_only` for the lightweight comment and analytics path |

### Current configuration and first deployment

The public `undefined-xhs/open-utd` repository is already configured to deploy Pages through Actions. `CROSSREF_MAILTO` is stored as an Actions Secret, the giscus App is installed, and Discussions plus the four public comment variables are configured. These steps do not need to be repeated when redeploying this repository. They also describe setup for a fork or a new repository.

The live site uses the custom domain above with HTTPS enforced; its Actions configuration is `PUBLIC_SITE_URL=https://www.open-utd-hot-take.xyz` and `PUBLIC_BASE_PATH=/`.

1. Use a public repository with `main` as its default branch. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
2. Allow the required Actions in **Settings → Actions → General**. The production build job declares `contents: write` to commit validated SQLite snapshots and `discussions: read` to collect public comments. Organization policies must permit these permissions.
3. Add `CROSSREF_MAILTO` under **Settings → Secrets and variables → Actions → Secrets**, using a real maintainer contact email. The contact is stored only as a Secret; no Crossref API key is required.
4. The default GitHub Pages address needs no additional variables. For a custom domain, set Actions Variables `PUBLIC_SITE_URL=https://your-domain.example` and `PUBLIC_BASE_PATH=/`, and configure the domain and DNS in Pages settings.
5. Open **Actions → Sync metadata and deploy Pages → Run workflow** and select `main`. For a new repository's first import, set `sync_metadata=true`, `initial_import=true`, and `from_year=2006`; leave `journal` blank to include every journal. This repository already has a production snapshot, so a redeployment can leave `sync_metadata=false`. Historical imports must finish all API pages, validation, and the static build. After synchronization, an Actions artifact containing SQLite and the sync report is retained for seven days, allowing recovery if a later build or capacity check fails. The production snapshot is committed only after all checks pass.
6. Review resource metrics and comment statistics in the run Summary, the committed [`data/sync-report.md`](data/sync-report.md), and the Pages environment link. Code pushes refresh comments during a full build; comment events and the daily fallback use the lightweight path. The weekly schedule synchronizes metadata incrementally.

An ordinary push deployment fails explicitly if a real production snapshot is missing. Run the manual historical import once before deploying a new installation. Workflows never substitute demo records for production data.

The manual `journal` input accepts one registry slug, such as `marketing-science`; blank selects all journals. `from_year` defaults to `2006` and is used only for historical imports. It must match every selected journal's `start_year`. Leave it blank to use each journal's registry year, which supports journals with different coverage windows.

Crossref synchronization uses a fixed `from-index-date` / `until-index-date` window with overlap to capture revisions. Incremental runs also check recently published records without a lower index-date bound, catching records registered in advance of their publication date. Watermarks advance only after complete success, and DOI updates preserve public IDs. Journals without an initial watermark require a historical import first. Collection errors, validation or test failures, build failures, capacity limits, and rejected bot commits all prevent deployment; the published site remains available. If the database commit succeeds but Pages deployment fails, rerun the default manual deployment without metadata synchronization.

Synchronization and deployment share one concurrency group. Database commits made with `GITHUB_TOKEN` do not trigger another push workflow, so deployment finishes in the same run. If main changes while the build is running, the bot's non-fast-forward push fails. Update to the latest code and rerun; do not force-push.

## Website analytics

Cloudflare Web Analytics can report aggregate page views, visits, popular pages, referring sites, countries, devices, and page performance. Visits are not a count of unique people; browser blocking and network failures can cause missing data. It does not identify visitors by name or GitHub account, use tracking cookies, or provide custom click/search events. See the site's bilingual `/privacy/` page and [Cloudflare's documentation](https://developers.cloudflare.com/web-analytics/).

1. In Cloudflare **Web Analytics → Add a site**, add the production hostname (currently `www.open-utd-hot-take.xyz`). Hosting stays on GitHub Pages; DNS changes are not required.
2. Choose manual JavaScript snippet installation. Copy the 32-character hexadecimal `token` from `data-cf-beacon` into the repository's Actions **Variable** `PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN`. This is a public beacon site ID, not a Cloudflare API token or account credential. Do not also enable automatic script injection.
3. Run `site.yml` with `comments_only=false` and `sync_metadata=false`. After successful deployment, visit the site and check **Web Analytics** in Cloudflare; reporting can take a few minutes.

Only production builds using production data and a non-empty token include the script; demo data and `astro dev` do not. An invalid token blocks the production build without printing its value. Clear the Actions Variable and run a full deployment to disable collection. Analytics configuration is included in the comment-refresh cache key, so a changed token cannot reuse HTML built with older settings. Local configuration uses the same optional variable in [`.env.example`](.env.example).

### Public statistics page

`/analytics/` shows aggregate page views over the last 7 and 30 complete UTC days, daily trends, country/region totals, and popular site paths. The footer links to this page. The snapshot's collection time uses the visitor's browser time zone; reporting dates use UTC. Collection starts when the beacon is enabled and does not recover earlier traffic. An unavailable snapshot is shown as pending, separately from a successful zero count. The counts may be sampled and omit blocked requests; they do not count unique people.

Cloudflare's [special country codes](https://developers.cloudflare.com/waf/tools/ip-access-rules/parameters/) `XX` (unknown) and `T1` (Tor), along with empty country codes, are combined into the existing Unknown category (`ZZ`), preserving their page-view counts.

For automatic publication, create an API token with **Account Analytics:Read** for the relevant Cloudflare account and save it as the repository Actions **Secret** `CLOUDFLARE_ANALYTICS_API_TOKEN`. Set Actions **Variables** `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_WEB_ANALYTICS_SITE_TAG` to that account ID and the Web Analytics site tag from its dashboard URL. The site tag is distinct from the public beacon token. The API credential stays in the collection step and never enters the static site.

[`scripts/fetch_analytics.py`](scripts/fetch_analytics.py) reads Cloudflare's RUM GraphQL dataset, limits results to this site's hostname and tag, and writes a validated aggregate `public/data/analytics.json`. Regular deployments and the existing daily snapshot check refresh it; `comments_only=true` can also refresh it manually. Changed analytics can trigger publication even when comments are unchanged. The lightweight path replaces both JSON snapshots while reusing HTML and Pagefind. API or validation failures stop publication and preserve the live snapshot. Local builds use `--ensure-empty` without network calls. Clearing all three server-side settings publishes an unavailable snapshot on the next run; removing only part of the configuration fails explicitly.

## Journal and article comments: giscus + GitHub Discussions

Every journal and article has its own public discussion, with GitHub sign-in, Markdown, replies, and reactions. Journal reviews and submission experiences live at `/journals/{slug}/reviews/`; article discussions remain on article detail pages. Comments are stored in GitHub Discussions. The site does not provide star rankings or unverified review statistics.

The current comment service uses the **Announcements** category in `undefined-xhs/open-utd`. These public configuration values identify the repository and category; they are not credentials:

| Actions Variable | Current value |
| --- | --- |
| `PUBLIC_GISCUS_REPO` | `undefined-xhs/open-utd` |
| `PUBLIC_GISCUS_REPO_ID` | `R_kgDOVMBvww` |
| `PUBLIC_GISCUS_CATEGORY` | `Announcements` |
| `PUBLIC_GISCUS_CATEGORY_ID` | `DIC_kwDOVMBvw84DIl2E` |

When migrating or using a separate comment repository, its administrator must authorize the giscus App:

1. Enable **Discussions** in the target public repository and choose an Announcements-type category. Use the default `Announcements` category or create `Journal Reviews`.
2. Install the GitHub App from [giscus](https://giscus.app/), authorize the repository, and obtain its actual repository and category IDs.
3. Set `PUBLIC_GISCUS_REPO`, `PUBLIC_GISCUS_REPO_ID`, `PUBLIC_GISCUS_CATEGORY`, and `PUBLIC_GISCUS_CATEGORY_ID` as Actions **Variables** in the website source repository. These IDs are public configuration, not Secrets.
4. Run `site.yml` manually with `sync_metadata=false`. After deployment, open two journal review pages and two article pages. Use a real account to check Markdown comments, replies, reactions, and isolation between discussions.

Mappings use `specific` and `strict=1`: `journal:<journal.public_id>` for journals and `article:<article.public_id>` for articles. Both can use the same Discussion category. Moving journal discussions from overview pages to dedicated review pages retains these mappings and existing conversations. giscus creates a Discussion when the first comment is posted; the project does not precreate thousands of empty threads. Renaming a journal, changing domains, or rebuilding does not change discussion identity. Do not delete and recreate a production journal to rename it, or casually change a public ID. Missing configuration produces an explanatory placeholder rather than an invalid iframe.

The editor themes are `public/giscus-light.css`, `public/giscus-dark.css`, and the shared `public/giscus-editor.css`. They follow the site's light/dark setting through giscus's supported custom theme interface. Absolute stylesheet URLs are derived from `PUBLIC_SITE_URL` and `PUBLIC_BASE_PATH`. The iframe must be able to access the CSS with cross-origin loading permitted; local preview URLs may be affected by browser or network restrictions, so verify the final appearance after deployment.

Comments or replies written by an AI Agent must include the exact label `written by AI Agent`. This applies to both journal and article discussions.

Maintainers remove, lock, and moderate content through GitHub Discussions; see `/guidelines/` and `/privacy/` for site policies. Report public corrections through a [GitHub Issue](https://github.com/undefined-xhs/open-utd/issues). Contact the maintainer for sensitive information or appeals, and avoid posting private information in public comments.

### Latest comments

`/comments/` collects public comments and replies from discussions for all catalogued journals and articles, ordered by **creation time**, newest first, with 20 entries shown at a time. Each entry links to the original GitHub comment and the corresponding discussion on this site. Comment text and author names remain unchanged. Comment and snapshot timestamps use the visitor's browser time zone, including daylight saving time, with the corresponding GMT offset. Date formatting follows the selected interface language. Visitors still post through the original discussion.

Both full builds and lightweight comment refreshes use [`scripts/fetch_comments.py`](scripts/fetch_comments.py) to read GitHub's GraphQL API. It includes discussions in the configured giscus category whose titles exactly match known `journal:<public_id>` or `article:<public_id>` mappings. It follows all comment and reply pages, including new replies to old comments. Automatically generated Discussion opening bodies are not treated as user comments. Deleted or moderator-minimized comment bodies are excluded. Each collection reflects edits, deletions, and moderation; removed content disappears from the website after the next successful deployment.

Comment events trigger a lightweight refresh, with a daily fallback at 03:37 UTC (11:37 in Asia/Shanghai). Discussion deletion, editing, transfer, and category changes also trigger a check. GitHub may delay events or scheduled runs, so this is not a real-time feed. These runs never synchronize Crossref or commit the database. GitHub's [`discussion_comment` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#discussion_comment) uses default-branch code; the official documentation currently marks Discussions webhooks as public preview.

[`scripts/comment_refresh.py`](scripts/comment_refresh.py) compares the complete fresh feed with the published JSON, ignoring only the collection timestamp. It also checks `data/site-build.json` against the current source/configuration, so a newer comment run cannot skip an unpublished code change when GitHub replaces a pending run. If both are unchanged, it skips Node.js, dependency installation, cache download, build, artifact upload, and deployment. Edits, deletions, new replies, and author or destination changes all count. The displayed snapshot time changes only when a snapshot is published; it is not the time of the last no-change check. A network failure fails the run rather than reporting a successful no-change check.

When comments change, the workflow restores a verified site archive from the Actions cache and replaces only `dist/data/comments.json`. It reuses all HTML and the search index without Astro, Pagefind, or a full link scan. The cache key includes the exact source commit and public site/giscus configuration, and is computed after any metadata commit. There is no fallback to a different source version. A missing or expired cache triggers a normal validated full build. The archive excludes comment JSON, so cached deleted comments cannot reappear. The two paths share the production concurrency group. GitHub allows discussion events to restore caches but not save them. Cache writes therefore remain limited to pushes, schedules, and manual runs. Daily/manual no-change checks use a metadata-only cache lookup (no archive download); if the cache is missing, they rebuild it. Comment events retain a full-build fallback until a trusted run restores the cache. This uses existing permissions and preserves GitHub's default cache restrictions.

GitHub Pages still requires a complete deployment artifact, so a changed feed uploads and deploys the assembled site package. Pages artifacts are retained for one day; the reusable archive uses the separate Actions cache allowance. Full builds remain necessary for source/metadata changes, ordinary manual deployments, and cache recovery. To test or manually refresh comments, run `site.yml` with `comments_only=true` and metadata options disabled. No additional secret, service, or browser token is needed.

The collection step uses `GITHUB_TOKEN` with `discussions: read` only inside Actions. The token is never written to JSON, HTML, or the browser. `public/data/comments.json` is an ignored build file containing public comment text, authors, timestamps, source links, and site destinations; comment copies are not committed to Git history. The workflow uses the source repository's token, so keeping source and comments in the same repository is the simplest migration path. A separate comment repository requires a separately configured token or GitHub App with read access to that repository.

API errors, partial responses, pagination failures, or exhausted request budgets stop deployment and preserve the published site; they are not converted into a successful empty feed. Each run allows up to 400 requests by default. The Summary reports request count and GraphQL cost. A JSON snapshot over 5 MiB warns; over 20 MiB fails. If these budgets are reached, split the feed or add incremental storage rather than silently truncating it. API and permission details are documented in the [GitHub Discussions GraphQL guide](https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions) and [official rate limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api).

## Maintain data and add journals

`data/journals.sqlite` is the production snapshot tracked in Git. `.generated/`, `dist/`, and `.local/` are ignored local or build outputs. Production uses `AJR_ENV=production`; demos always use a separate `AJR_DB_PATH`. Do not repair production data by seeding demo records, recreating an empty database, or reverting public IDs.

Example local production workflow:

```bash
export AJR_ENV=production
export AJR_DB_PATH=data/journals.sqlite
export CROSSREF_MAILTO=your-real-maintainer-email@example.org
python scripts/cli.py db-init
python scripts/cli.py seed --file data/journal_registry.csv
python scripts/cli.py sync --provider crossref --mode initial --from-year 2006
python scripts/cli.py validate --production
python scripts/cli.py report --out data/sync-report.md
python scripts/cli.py stats
npm run build
```

Replace the example email with a real contact before making network requests. For routine updates, use `sync --provider crossref --mode incremental`. `sync --help` lists `--journal`, `--from-date`, `--to-date`, `--dry-run`, and request-limit options. Persisted production imports must cover January 1 of each journal's registry `start_year` through the current UTC date. Other date windows are available only with `--dry-run`. `--limit` also requires a dry run, preventing truncated pagination or partial-year imports from being recorded as complete. To change a production coverage start, review and update the registry before performing a full historical import.

The optional registry field `crossref_issns` lists Crossref query endpoints, separated by semicolons. When blank, all registered ISSNs for that journal are queried. It may contain only actual ISSNs from the same row and does not alter the journal's complete displayed ISSN set or article-ownership checks. Restrict query endpoints only with clear source evidence: for example, the actual electronic ISSNs for JAE and JFE currently have no Crossref journal endpoint. Other query errors still stop synchronization. Changing the effective query set invalidates the watermark and requires a new full historical import.

To add a journal, verify its publisher and Crossref ISSNs, add a registry row, assign a stable slug, and set `start_year`. Commit the registry, then run `site.yml` manually with `sync_metadata=true`, `initial_import=true`, and `journal=new-journal-slug`. Set `from_year` to the journal's `start_year`, or leave it blank to read the registry. This imports only the new journal while preserving other journals' records and public IDs. If one commit adds several visible journals without data, leave `journal` blank to import all of them together. Also leave `from_year` blank if their start years differ.

Alternatively, import only the new journal locally:

```bash
python scripts/cli.py seed --file data/journal_registry.csv
python scripts/cli.py sync --provider crossref --journal new-journal-slug --mode initial
python scripts/cli.py validate --production
python scripts/cli.py report --out data/sync-report.md
npm run check
npm run build
npm run test:site
```

After verifying the local import, commit the registry, SQLite snapshot, and sync report together; the main push deploys them. Do not leave a new journal to the weekly incremental job: a missing watermark fails safely. Changing an existing journal's `start_year` or adding an ISSN also invalidates its watermark and requires another historical import, preventing older records in the new range from being missed. Existing records and public IDs are retained. Adding journals does not require template changes. Review source records before resolving incorrect ISSNs, DOI conflicts across journals, or ambiguous issue assignments.

## Data quality and reuse

- Titles, author order, DOIs, volume/issue information, and dates come from source deposits. A year-only date retains that precision rather than being presented as an exact day.
- Records without sufficient volume and issue information appear under Online First / Unassigned. Missing information remains missing rather than being inferred.
- Each normalized DOI identifies at most one article record. Updates retain its `public_id`; authors with the same name are not automatically merged without reliable identifiers.
- The site has no abstract displays, expandable abstracts, or missing-abstract notices. Abstracts are excluded from HTML, JSON-LD, and the search index, and article details lead directly to discussion. Use the original-source link for abstracts and full text. The collector does not request abstract fields; the public SQLite snapshot and exports retain strict rights checks that reject unauthorized abstracts.
- OpenAlex enrichment is not enabled as a production source. `OPENALEX_API_KEY` is reserved configuration; workflows do not call OpenAlex or incur additional API usage there.
- The MIT license covers project code and original documentation. It does not grant rights to third-party abstracts, publisher content, or user comments.

## Backups, recovery, and migrations

The metadata workflow commits the database and report only after synchronization, validation, tests, and the build all succeed, providing a history of verified snapshots. A completed synchronization followed by a build failure retains its seven-day recovery artifact but does not update main. Before maintenance, stop concurrent local writes and use SQLite's backup API for a consistent copy:

```bash
mkdir -p .local
python -c 'import sqlite3; source=sqlite3.connect("data/journals.sqlite"); target=sqlite3.connect(".local/journals-backup.sqlite"); source.backup(target); target.close(); source.close()'
```

Keep important backups outside the repository as well. To restore, first back up the current files, then choose a known-good commit:

```bash
git log --oneline -- data/journals.sqlite
git restore --source=KNOWN_GOOD_COMMIT -- data/journals.sqlite data/sync-report.md
AJR_ENV=production AJR_DB_PATH=data/journals.sqlite python scripts/cli.py validate --production
AJR_ENV=production AJR_DB_PATH=data/journals.sqlite npm run build
```

After validating the restored data, commit and push the recovery change rather than rewriting shared Git history. If restoring an older snapshot, check whether newer public IDs need to be preserved. Comments live in GitHub Discussions, so restoring the database does not delete them; changing journal public IDs can disconnect their embedded mappings.

Database migrations live in `data/migrations/`. `db-init` runs only unapplied migrations. Back up before introducing a migration and verify that existing snapshots upgrade while preserving IDs, slugs, and foreign-key relationships.

## Resource metrics and troubleshooting

`python scripts/build_metrics.py --db data/journals.sqlite --dist dist --build-seconds 120` generates ignored `build-metrics.json` and `.md` files. Actions adds the report to its run Summary, including database size, article/issue/author counts, HTML page count, site and Pagefind sizes, and build duration.

Before expanding the collection, run an offline scale check as needed. The largest fixture is not built on every pull request:

```bash
export AJR_ENV=demo
for count in 10 100 1000 10000; do
  export AJR_DB_PATH=".local/benchmark-${count}.sqlite"
  python scripts/cli.py db-init
  python scripts/cli.py seed-demo --count "$count"
  started=$SECONDS
  npm run build
  elapsed=$((SECONDS - started))
  npm run test:site
  python scripts/build_metrics.py --db "$AJR_DB_PATH" --dist dist --build-seconds "$elapsed" --out ".local/build-metrics-${count}.json"
done
```

This rebuilds local `.generated/` and `dist/` using separate synthetic databases. Afterwards, restore `AJR_DB_PATH` to the database you want to preview and rebuild.

| Metric | Engineering warning | Commit / deployment guard |
| --- | --- | --- |
| SQLite | 50 MB | 95 MB; migrate snapshot storage before reaching the limit |
| Static site | 500 MB | 900 MB, leaving headroom below the Pages limit |
| Pagefind | 50 MB | Governed by the total site-size limit |
| Build duration | 5 minutes | Jobs have explicit timeouts |

These are project engineering budgets. [GitHub Pages' official limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) include a 1 GB published-site limit and a 10-minute deployment timeout. When approaching a budget, inspect indexing and page costs before moving storage or introducing an API. Preserve existing URLs and comment IDs; do not silently drop article pages.

| Symptom | Action |
| --- | --- |
| `initial_import` / watermark error | Run a manual historical synchronization, select the affected `journal`, and match `from_year` to its registry start year or leave it blank |
| Crossref 429, timeout, or pagination failure | Review the non-sensitive error report and retry later; failed runs do not commit partial snapshots |
| Bot push rejected | Check Actions write permissions, concurrent main updates, and branch protection; do not force-push |
| Main prohibits direct bot pushes | Use a synchronization PR → human review and merge → main deployment flow, handling bot-PR test triggers explicitly; do not disable protection |
| Pages load but CSS or search returns 404 | Check `PUBLIC_SITE_URL` and `PUBLIC_BASE_PATH`; the default project Pages path is `/open-utd` |
| Search does not work in development mode | Use `npm run build && npm run preview` |
| Scheduled jobs have not run for a long time | Check that Actions is enabled; schedules may be disabled after 60 days without activity in a public repository, and scheduled runs can be delayed |
| Comments are not enabled | Complete giscus App authorization, configure the Discussions category and four public variables, then redeploy |

## Engineering notes

Data flows from Crossref → SQLite → JSON shards → Astro static HTML → Pagefind → GitHub Pages. Browsers receive static pages, the search index, and public comment JSON; the comment widget loads separately from giscus. SQLite is not published as a website asset. No self-hosted application server or user database is required; posting comments requires a GitHub account.

GitHub-hosted runners use Node 24 and Python 3.12. Official Actions are pinned to specific commits; review their versions and permissions when upgrading: [checkout](https://github.com/actions/checkout), [setup-node](https://github.com/actions/setup-node), [setup-python](https://github.com/actions/setup-python), [configure-pages](https://github.com/actions/configure-pages), [upload-pages-artifact](https://github.com/actions/upload-pages-artifact), and [deploy-pages](https://github.com/actions/deploy-pages). The current configuration uses Pages configuration v6 and upload/deployment v5. Some official examples show older versions, so do not copy version numbers without checking.

The [technical roadmap](academic-journal-reviews-technical-roadmap-github-actions.md) provides design background. The executable implementation and this README describe current behaviour. Manual acceptance checks still include posting and replying with a real giscus account and comparing Crossref coverage with the publisher's latest issue contents.
