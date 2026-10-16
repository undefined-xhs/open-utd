# Academic Journal Reviews — 完整技术路线与 Codex 工程规格

> 版本：v1.1 · 2026-10-16（GitHub Actions 自动化版）  
> 状态：可交付 Codex 执行的 MVP 实施规格（不是现成源码）  
> 项目暂定名：**Academic Journal Reviews（AJR）**  
> 首要原则：**数据存储与网站生成分离；先做可运行的静态 MVP，保留未来迁移至在线 API 的空间。**

---

## 0. 给 Codex 的简短任务说明

请在一个全新的 GitHub 仓库中实现学术期刊目录与公开评论网站。按本文件的架构、数据模型、接口、目录结构、测试、CI/CD 和验收条件完整交付，不要只生成漂亮的前端演示。必须保证**没有真实 API 密钥、没有已配置的 giscus 仓库时，也能凭内置合成测试数据完成本地构建**。

- 网站：Astro（静态输出）+ TypeScript + Tailwind CSS 4。
- 数据：Python + SQLite；构建时从 SQLite 导出分片 JSON，Astro 根据 JSON 生成静态页面。
- 学术元数据：Crossref 为首选数据源，OpenAlex 为可选补充源。
- 搜索：Pagefind（在 Astro 构建之后索引 HTML）。
- 评论：giscus + GitHub Discussions，**MVP 每本期刊一个 Discussion**，支持 GitHub 登录、Markdown、回复、Reaction。
- 托管：GitHub Pages + GitHub Actions（PR 测试、每周元数据同步、构建和自动部署）。
- 生产页面：期刊目录 → 期刊页 → 期次页 → 论文页；作者、DOI、摘要、刊期关系可浏览/检索。
- 英文作为第一版默认 UI 语言，文本集中管理，未来便于添加中文；简洁、可信、学术风格、移动端适配。
- 不要引入在线服务器、SSR、用户账户数据库、Supabase、React 全站水合等不必要的依赖。

**交付不等于“只有页面”。** 必须实现从种子数据 → SQLite → 规范化 → 静态导出 → HTML → 搜索索引 → Pages 部署的可复现流水线，以及测试、文档和错误处理。

---

## 1. 产品定位与 MVP 范围

### 1.1 产品定位

一个可以检索学术期刊、浏览每期期刊及论文元数据、并对**期刊整体发表/审稿体验**进行公开讨论的网站。论文信息是发现、导航及背景信息；用户生成内容由 GitHub Discussions 保管。

数据层级：

```text
Journal（期刊）
  ├── Issue（期次：Volume / Issue / Year）
  │     ├── Article（论文：Title / Abstract / DOI / Authors）
  │     └── Article
  ├── Issue
  └── Online First / Unassigned（未分配期次的论文）

Author（作者）与 Article 是多对多关系。

Journal ──> one stable GitHub Discussion（MVP）
```

### 1.2 第一版必须实现

1. 首页：网站介绍、检索入口、期刊列表、最近更新的期刊。
2. `/journals/`：所有已收录期刊，可按名称/学科查找。
3. 期刊详情页：名称、出版社、ISSN、所收录的 Volume/Issue、Online First，以及**期刊评论区**。
4. 期次详情页：该期的论文列表，显示题目、作者、发表日期、摘要状态、DOI 链接。
5. 论文详情页：标题、作者（顺序准确）、摘要（仅在允许展示时）、DOI、所属期刊/期次、来源与外部链接。
6. `/search/`：按期刊名、论文名、作者、DOI 关键词搜索，并提供必要筛选。
7. giscus：每本期刊的评论映射到固定的 Discussion，不随页面 URL/期刊更名改变。
8. 数据导入：可配置期刊 ISSN 列表，批量获取 Crossref 论文，重复导入不产生重复论文。
9. 增量同步：仅更新变更过的元数据；部分失败可恢复。
10. GitHub Actions 全自动流水线：PR 离线测试；push 到 `main` 自动构建部署；每周 Crossref 增量同步、更新 SQLite 快照并在**同一次工作流运行中**部署；支持手动首次历史导入。
11. 自动化测试、异常处理、数据来源标注、评论规范/隐私说明。

### 1.3 明确不在 MVP 范围内

- 不做匿名评论、站内注册、邮箱密码、独立用户资料。
- 不做星级评分、综合排名、接受率/审稿速度统计（除非来自可验证数据）。
- 不做论文全文/PDF 镜像、爬取付费页面或绕过出版社访问限制。
- 不做真实在线 SQLite 查询，也不做面向每个访客的动态 API。
- 不做论文级和期次级评论；数据模型预留将来扩展。
- 不做全部学术期刊的全库抓取；先以少量已配置期刊验证。

**重要：** 第一版评论讨论对象是 *Journal*，而不是每篇 *Article*。如果未来增加论文级讨论，使用独立且稳定的 `article:<public_id>` 映射词，不复用期刊 Discussion。

---

## 2. 技术选型与责任边界

| 层 | 选择 | 工作内容 | 部署时是否运行 |
|---|---|---|---|
| 数据采集 | Python 3.12+，HTTP 客户端 | Crossref/OpenAlex 同步 | 否，仅本地或 Actions |
| 数据存储 | SQLite | 关系、约束、数据去重、同步状态 | 否，仅构建时 |
| 数据导出 | Python CLI | SQLite → 分片、只读 JSON | 否，仅构建时 |
| 静态生成 | Astro + TypeScript | 页面模板、路由、SEO | 否，仅构建时 |
| 样式 | Tailwind CSS 4 | 响应式页面、主题 | CSS 在浏览器中运行 |
| 全文搜索 | Pagefind | 构建静态索引，浏览器搜索 | 浏览器运行其 JS |
| 评论 | giscus | 嵌入 GitHub Discussions | 浏览器中通过 GitHub 服务运行 |
| CI/CD | GitHub Actions | 检查、构建、部署、定期同步 | 仅 Actions |
| 网站托管 | GitHub Pages | 提供静态 HTML/CSS/JS/索引 | 是，仅提供文件 |

统一约束：

- Astro 保持 `output: 'static'`；不依赖 Astro SSR adapter。
- 所有页面在构建时预渲染，评论通过第三方 iframe 动态加载。
- 使用 Node.js 当前稳定且被 Astro 支持的版本（初期建议 Node 22；以实际最新版支持矩阵及 lockfile 为准）。
- **不要**把 SQLite 数据库下载到浏览器，也不要暴露内部管理接口。
- GitHub 仓库的 `data/journals.sqlite` 是 MVP 的持久化数据快照；`src/generated/` 或 `.generated/` 是一次性构建产物，不是另一份数据库。

### 2.1 运行数据流

```text
Crossref REST API ──┐
                   ├──> Python import/normalize ──> SQLite
OpenAlex API ──────┘                            (data/journals.sqlite)
                                                     │
                                             python export
                                                     │
                                         .generated/*.json
                                                     │
                                         Astro static build
                                                     │
                                            dist/*.html
                                                     │
                                           Pagefind index
                                                     │
                                      GitHub Actions deploy
                                                     │
                                          GitHub Pages
                                                     │
                 visitor ─────────────────────────────┤
                                                     │
                                giscus iframe ──> GitHub Discussions
```

**数据存储和网站生成分离的具体含义**：学术事实只保存/维护在 SQLite，Astro 页面只是其只读呈现；更新数据不需要修改页面模板，改造 UI 不需要改动数据库。将来更换托管或增加 API，也不必重建期刊标识与评论关联。

---

## 3. 仓库结构（建议遵循）

```text
academic-journal-reviews/
├── .github/
│   └── workflows/
│       ├── ci.yml                # pull_request: 测试 + 静态构建
│       └── site.yml              # main push / weekly cron / manual: 同步 + 构建 + 部署
├── data/
│   ├── journals.sqlite          # SQLite 持久化快照（小规模时 Git 跟踪）
│   ├── sync-report.md           # 自动同步后的人类可读变更报告
│   ├── journal_registry.csv     # 人工维护的期刊白名单 / ISSN
│   └── migrations/
│       ├── 001_init.sql
│       └── ...
├── scripts/
│   ├── cli.py                   # init / seed / sync / export / validate / stats
│   ├── db.py
│   ├── crossref.py
│   ├── openalex.py
│   ├── normalize.py
│   ├── reconcile.py
│   └── export.py
├── tests/
│   ├── fixtures/                # 合成测试数据 + 小份真实 API 响应 fixture
│   ├── test_schema.py
│   ├── test_ingest.py
│   ├── test_normalize.py
│   ├── test_export.py
│   └── test_urls.py
├── .generated/                  # Python 导出的 JSON；不提交 Git
│   ├── manifest.json
│   ├── journals-index.json
│   ├── journals/
│   ├── issues/
│   └── articles-by-journal/
├── public/
│   ├── favicon.svg
│   └── robots.txt
├── src/
│   ├── components/
│   │   ├── Header.astro
│   │   ├── SearchBox.astro
│   │   ├── JournalCard.astro
│   │   ├── IssueCard.astro
│   │   ├── ArticleCard.astro
│   │   ├── GiscusComments.astro
│   │   └── Breadcrumbs.astro
│   ├── layouts/
│   │   └── BaseLayout.astro
│   ├── lib/
│   │   ├── catalog.ts           # 只读 .generated 数据
│   │   ├── urls.ts              # 统一处理 base path
│   │   └── formatting.ts
│   ├── pages/
│   │   ├── index.astro
│   │   ├── journals/
│   │   │   ├── index.astro
│   │   │   └── [slug]/
│   │   │       ├── index.astro
│   │   │       └── issues/[issueId].astro
│   │   ├── articles/[articleId].astro
│   │   ├── search.astro
│   │   ├── about.astro
│   │   ├── guidelines.astro
│   │   ├── privacy.astro
│   │   └── data-sources.astro
│   └── styles/global.css
├── astro.config.mjs
├── package.json
├── package-lock.json             # 或 pnpm-lock.yaml；固定一种管理器
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

注意：真实项目可在不破坏以上职责边界的条件下调整细节；**不允许在 HTML 模板中写采集逻辑、不允许在 Python 导入模块中拼接网页 HTML**。

---

## 4. 数据库设计

### 4.1 标识符政策（最高优先级）

网站内部同时保留三个维度：

- **数据库 ID**：SQLite 自增 `id`，用于表关联，不出现在评论映射中。
- **公开稳定 ID**：`public_id`，首次创建时分配 UUID 等全局唯一标识，**永不因标题、URL、ISSN、DOI 更新而重置**。例如 `j_9a...`、`i_b3...`、`a_e2...`。
- **展示 slug**：例如 `marketing-science`，用于可读 URL；一经公开，原则上不变。期刊更名时采用别名/重定向策略，不能因此丢失 Discussion。

ISSN / ISSN-L 用于识别期刊、DOI 用于识别论文，但**都不是所有记录必有且永不变化的内部主键**。不要把 DOI 直接嵌入文件路径（含 `/`、大小写和转义问题）。

### 4.2 SQLite Schema（最小可落地设计）

下方 SQL 是基准结构；实现时可补充 CHECK、迁移版本、索引，但不能删除核心约束。

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE journals (
    id              INTEGER PRIMARY KEY,
    public_id       TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    abbreviation    TEXT,
    issn_l          TEXT,
    publisher       TEXT,
    subject         TEXT,
    homepage_url    TEXT,
    is_visible      INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE journal_issns (
    journal_id      INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    issn            TEXT NOT NULL UNIQUE,
    medium          TEXT, -- print / electronic / unknown
    PRIMARY KEY (journal_id, issn)
);

CREATE TABLE issues (
    id              INTEGER PRIMARY KEY,
    public_id       TEXT NOT NULL UNIQUE,
    journal_id      INTEGER NOT NULL REFERENCES journals(id),
    issue_key       TEXT NOT NULL,
    volume          TEXT,
    issue_number    TEXT,
    issue_title     TEXT,
    publication_year INTEGER,
    publication_date TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE (journal_id, issue_key)
);

CREATE TABLE articles (
    id                  INTEGER PRIMARY KEY,
    public_id           TEXT NOT NULL UNIQUE,
    journal_id          INTEGER NOT NULL REFERENCES journals(id),
    issue_id            INTEGER REFERENCES issues(id),
    doi                 TEXT COLLATE NOCASE UNIQUE,
    openalex_id         TEXT UNIQUE,
    title               TEXT NOT NULL,
    abstract_text       TEXT,
    abstract_source     TEXT,
    abstract_license_url TEXT,
    abstract_display_status TEXT NOT NULL DEFAULT 'unknown'
       CHECK (abstract_display_status IN ('permitted', 'unknown', 'restricted')),
    publication_date    TEXT,
    date_precision      TEXT,  -- year / month / day
    publication_year    INTEGER,
    pages               TEXT,
    article_type        TEXT,
    landing_url         TEXT,
    metadata_source     TEXT,
    source_modified_at  TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE authors (
    id              INTEGER PRIMARY KEY,
    public_id       TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    orcid           TEXT UNIQUE,
    openalex_id     TEXT UNIQUE
);

CREATE TABLE article_authors (
    article_id      INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    author_id       INTEGER NOT NULL REFERENCES authors(id),
    author_position INTEGER NOT NULL,
    byline_name     TEXT NOT NULL,
    affiliation_text TEXT,
    PRIMARY KEY (article_id, author_position)
);

CREATE TABLE sync_state (
    journal_id      INTEGER NOT NULL REFERENCES journals(id),
    provider        TEXT NOT NULL,
    last_successful_indexed_at TEXT,
    last_run_at     TEXT,
    last_status     TEXT,
    last_error      TEXT,
    PRIMARY KEY (journal_id, provider)
);

CREATE TABLE ingest_runs (
    id              INTEGER PRIMARY KEY,
    provider        TEXT NOT NULL,
    journal_id      INTEGER REFERENCES journals(id),
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,
    fetched_count   INTEGER NOT NULL DEFAULT 0,
    inserted_count  INTEGER NOT NULL DEFAULT 0,
    updated_count   INTEGER NOT NULL DEFAULT 0,
    skipped_count   INTEGER NOT NULL DEFAULT 0,
    error_text      TEXT
);

CREATE INDEX idx_issues_journal_year
    ON issues(journal_id, publication_year, volume, issue_number);
CREATE INDEX idx_articles_journal_year
    ON articles(journal_id, publication_year);
CREATE INDEX idx_articles_issue ON articles(issue_id);
CREATE INDEX idx_article_authors_author ON article_authors(author_id);
```

**补充约束（必须在应用逻辑或触发器中保证）：** `articles.issue_id` 对应的 `issues.journal_id` 必须等于 `articles.journal_id`；除非人工审核，禁止将同一 DOI 的文章移动到不相关期刊。

### 4.3 关键数据问题

**1. DOI 规范化**

- 接受 `10.xxxx/...`、`doi:10.xxxx/...`、`https://doi.org/10.xxxx/...` 等形式。
- 去掉前缀、空白，标准化大小写与安全的 URL 解码；去重基于规范化 DOI。
- 原始 DOI 保留在来源记录/日志中以备审计；不允许使用仅标题相似度来自动合并不同 DOI。
- 无 DOI 的记录优先用可靠的 OpenAlex ID 匹配；若也没有可靠标识符，不做跨数据源自动合并，交人工审核或保留单独记录。

**2. Authors**

- 保留论文署名顺序。
- 只在可靠 ORCID/OpenAlex Author ID 可用时做跨论文作者实体合并。
- 同名作者**不能**默认是同一人；无身份标识时允许建立各自的作者记录。
- 论文页面使用 `article_authors.byline_name` 展示原始署名。

**3. Issue**

- `volume`、`issue_number` 是**字符串**（可能为 `1-2`、`S1` 等），不能强行转整数。
- `issue_key` 在创建时由清洗后的期次标识生成；必须在同一期刊内唯一。历史记录的 `issue_key/public_id` 不因来源字段的小修改随意重建。
- 仅在有足够信息能唯一识别期次时创建 Issue。缺失期次或仅有模糊年份的 Article 保持 `issue_id = NULL`，在期刊页归为 Online First / Unassigned。
- DOI 后续补充了 Volume/Issue 时，应把原论文关联到相应 Issue，而不是新建论文。
- 兼容特殊期、合刊、期刊更名，遇到歧义时记录异常而非猜测。

**4. Dates**

- 区分在线发表、纸质发表、最终卷期等来源日期，MVP 选择一个用于展示的 `publication_date`，记录优先级和精度。
- 日期只有年份时，存 `2026` + `date_precision='year'`，不能伪造成 `2026-01-01` 并对用户显示为精确日期。

**5. Abstracts / 版权**

- 标题、作者、DOI 等书目信息与摘要的再使用权限**不能混为一谈**。Crossref 明确提醒：摘要版权通常归作者或出版社所有。
- 保存 `abstract_text`（规范化后的纯文本）、`abstract_source`、`abstract_license_url`、`abstract_display_status`。
- 在网站上**仅当再发布权限经过验证**（例如适用的许可明确允许）时全文展示摘要。许可不明时显示 `Abstract not available for redistribution` 与论文官方来源链接，不在网页源码或 Pagefind 索引中泄漏全文摘要。
- Crossref 常见摘要为 JATS/XML，必须安全提取为纯文本；禁用对外部摘要 HTML 的原样渲染。允许安全的数学/上标呈现作为后续增强。
- OpenAlex 补充摘要同样需要审核适用权限，不要推定 OpenAlex 返回字段就意味着任何用途均可再发布。

### 4.4 SQLite 数据库存储策略

- MVP：`data/journals.sqlite` 受 Git 跟踪；同步生成 `data/sync-report.md`；不提交 `.sqlite-wal` / `.sqlite-shm` 或 `.generated/`。定期由 GitHub Actions 在数据校验、测试和构建成功后提交数据快照。
- 导入使用事务、`PRAGMA foreign_keys=ON`；退出前关闭连接并检查完整性；如使用 WAL 模式，提交前 checkpoint、切回可移植的 journal 模式并关闭所有连接，确保 Git 跟踪的 `.sqlite` 文件完整。
- 对数据库变更使用有版本号的 SQL migration；不要每次重建数据库。
- 提供数据库备份/恢复脚本或明确操作文档。上线后**严禁以 `seed --reset` 覆盖生产数据**。
- SQLite 文件接近 **50 MB** 时提醒评估外部快照/对象存储；超过 GitHub 常规单文件限制前必须迁移保存方式。此阈值是工程预警，而非 SQLite 能力上限。
- 每次自动同步附带 `sync-report.md` 变更摘要（新增、更新、失败、缺失字段比例、同步范围），避免只看到不可读的二进制 DB 差异。即使没有新论文，也要保留本次成功执行的可追踪记录。

---

## 5. 数据源与 ETL（抽取、规范化、写入）

### 5.1 来源优先级

**Crossref（主源）**

- 用人工维护的 ISSN 白名单限定收录范围，不根据模糊名称自动认定期刊。
- 主要字段：`DOI`、`title`、`author`、`container-title`、`ISSN`、`volume`、`issue`、`published-*`、`abstract`、`URL`、`type`。
- 仅收录适用的 `journal-article` 记录；是否包含 Editorial/Correction 等，应允许配置，不可默默当作 Research Article。
- 优先使用 `/journals/{ISSN}/works` 或经官方文档验证的 ISSN filter。
- 使用真实 `CROSSREF_MAILTO` / User-Agent 联系方式，遵守请求限流。

**OpenAlex（可选补充）**

- 按 DOI / OpenAlex ID 做谨慎匹配，用于补充作者标识、部分缺失元数据；不得覆盖更可信的字段而不留痕迹。
- 正式或大规模使用时通过 `OPENALEX_API_KEY`（GitHub Actions Secrets）控制调用；没有 key 时系统仍可只用 Crossref 正常工作。
- API 配额和计费政策可能变化，先做 `--dry-run` / 请求预算上限；发生 429 时退避并停止或延后。

### 5.2 数据同步策略

**初始化 / 历史导入**

1. 从 `data/journal_registry.csv` 载入期刊清单，验证 ISSN 格式和重复记录。
2. 每本期刊按时间窗口导入论文（例：最近 5–10 年，作为可配置参数；不要写死实际年份）。
3. Crossref 使用 cursor 分页，不依赖超过 API 限制的大 offset。
4. 每批执行规范化、DOI 去重、Issue 关联、作者关联，然后事务提交。
5. 输出导入总数、新增数、更新数、跳过数、错误数和缺失摘要/期次比例。

**增量同步（推荐每周；可改每日）**

1. 读取各期刊的 `sync_state.last_successful_indexed_at`。
2. 使用 Crossref `from-index-date` 和**固定的** `until-index-date`；这是捕捉后续元数据修订的重要机制。不能只用文章发布日期。
3. 采用约 24–48 小时安全重叠窗口（包含边界）；由于 DOI upsert 幂等，不会产生重复数据。
4. 只在**该期刊该时间窗口的所有分页成功完成**后推进同步水位；中断后允许重跑。
5. 请求重试必须有上限：429/5xx 指数退避、超时、`Retry-After`；失败时保留上次成功数据、不得推送半成品替换站点。
6. 每批限制请求数、支持 `--limit`、`--dry-run`、`--journal`、`--mode`、`--from-date`、`--to-date`。

**字段变更处理：** 同一 DOI 再导入时更新已更正的标题、作者、期次等，但保留 `public_id`。若元数据冲突、期刊归属发生变化或来源存在明显异常，记录供审核，不要静默覆盖。

### 5.3 导入模块职责

```text
scripts/crossref.py    -> HTTP / 重试 / 分页 / 原始响应解析
scripts/openalex.py    -> 可选补充、限额、身份匹配
scripts/normalize.py   -> DOI、ISSN、日期、JATS 摘要、作者顺序
scripts/reconcile.py   -> 识别/分配 Journal、Issue、Article、Author
scripts/db.py          -> migrations、事务、SQL、upsert、同步状态
scripts/export.py      -> 输出只读、可构建 JSON
scripts/cli.py         -> 命令行统一入口
```

测试必须使用录制或合成 fixture，不能每次测试都联网到真实 API。

---

## 6. Python CLI 与本地开发工作流

Codex 应实现可运行的、语义明确的命令（可采用 `argparse` 或 Typer，但命令名保持统一）。推荐：

```bash
# 1) 准备环境
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
npm ci

# 2) 初始化空数据库并执行 migrations
python3 scripts/cli.py db-init

# 3) 导入人工维护的期刊白名单
python3 scripts/cli.py seed --file data/journal_registry.csv

# 4) 可离线运行：加载合成演示 fixture（不得与生产数据混淆）
python3 scripts/cli.py seed-demo

# 5) 有真实网络时：对指定期刊导入/更新论文
python3 scripts/cli.py sync --provider crossref --journal marketing-science --mode initial --from-year 2020
python3 scripts/cli.py sync --provider crossref --journal marketing-science --mode incremental

# 6) 数据质量与统计
python3 scripts/cli.py validate
python3 scripts/cli.py validate --production   # 对生产快照禁用合成数据，要求真实有效数据
python3 scripts/cli.py stats
python3 scripts/cli.py report --out data/sync-report.md

# 7) SQLite -> 构建只读数据
python3 scripts/cli.py export --out .generated

# 8) 本地预览与生产构建
npm run dev
npm run build
npm run preview
```

`--journal marketing-science` 仅为示意；期刊注册表中的 slug 由用户配置，**不强制要求这本期刊一定已经注册**。

**CLI 补充契约（Actions 必须实现）：**

- `AJR_DB_PATH` 环境变量可以切换 SQLite 路径，CI 使用临时数据库，生产默认 `data/journals.sqlite`。所有命令必须遵守该路径，不允许 `seed-demo` 修改生产快照。
- `AJR_ENV=demo|production` 区分演示与正式环境；`validate --production` 必须拒绝合成 fixture、无真实论文的生产数据、数据库结构错误与未经许可公开的摘要。
- `db-init`、`seed`、`sync` 都应幂等；`seed` 更新期刊白名单，但不能清空历史论文或变更稳定 `public_id`。
- `report --out data/sync-report.md` 读取最近一次同步结果，生成可追溯、无密钥的 Markdown 变更统计。
- `sync --mode initial --from-year YYYY` 为首次历史导入；`sync --mode incremental` 为后续补充与元数据修订。
- 导入过程中任一严重错误应返回非零退出码；绝不可静默发布部分完成的同步结果。

### 6.1 `package.json` 中必须提供的脚本

```json
{
  "scripts": {
    "data:export": "python3 scripts/cli.py export --out .generated",
    "dev": "npm run data:export && astro dev",
    "build": "npm run data:export && astro build && pagefind --site dist",
    "preview": "astro preview",
    "check": "astro check"
  }
}
```

说明：上面是关键 scripts 片段，**不是完整的 package.json**。`pagefind` 必须作为开发依赖固定在 lockfile 中。若在不提供 `python3` 命令的系统运行，README 说明如何替换。开发模式下更新 DB 后需再次导出或重启 dev；不要让 Astro dev 直接修改 SQLite。

### 6.2 `.env.example`

```dotenv
# 用真实的维护者邮箱配置 Crossref polite pool；不要填占位邮箱去发正式请求
CROSSREF_MAILTO=

# 可选：OpenAlex API key；绝对不能放入 PUBLIC_ 前缀变量
OPENALEX_API_KEY=

# giscus 是公开配置，来自 https://giscus.app/ 配置页面
PUBLIC_GISCUS_REPO=
PUBLIC_GISCUS_REPO_ID=
PUBLIC_GISCUS_CATEGORY=Journal Reviews
PUBLIC_GISCUS_CATEGORY_ID=

# GitHub Pages 的网站根 URL 和仓库子路径
PUBLIC_SITE_URL=
PUBLIC_BASE_PATH=

# 在 CI/Actions 中区分合成数据和生产快照；正常用户本地开发可设为 demo
AJR_ENV=demo
# 可选，CI 指向隔离的临时 DB 文件；生产无需设置
AJR_DB_PATH=
```

对必需但未配置的项给出明确提示；不能在没有 `OPENALEX_API_KEY` 时让 Crossref/本地构建整体失败。giscus 未配置时显示非交互式说明，而非嵌入坏掉的评论 iframe。

---

## 7. SQLite → Astro 的构建时数据接口

### 7.1 导出层的契约

`python3 scripts/cli.py export --out .generated` 做如下工作：

- 校验数据库可读取，并且没有重复 DOI / 断裂的 FK / 非法 URL。
- 使用明确的排序（期刊名称；期次按年、卷、期倒序；作者按位置）。
- 生成 JSON，所有日期采用稳定字符串表示，保留精度。
- 按 Journal / Issue 分片，不输出一个包含全部文章、全部摘要的巨大 JSON。
- 导出只允许公开的信息，**未经许可的摘要文本绝不进入 `.generated/` 或 `dist/`**。
- 生成 `manifest.json`，其中列出可构建的 Journal、Issue、Article ID/route，以及规模统计；再次导出同一数据应有稳定输出。

示意：

```text
.generated/
├── manifest.json
├── journals-index.json             # 轻量目录信息
├── journals/j_<public-id>.json     # 期刊元信息 + issue 列表
├── issues/i_<public-id>.json       # 单一期次 + article 摘要记录
└── articles-by-journal/
    └── j_<public-id>.json          # 单期刊文章详情分片
```

所有 JSON 类型在 TypeScript 中明确定义；在导出端用 Python Schema 验证，在读取端用轻量校验/断言。不得在 Astro 中写 SQL 采集或维护数据库。

### 7.2 页面生成策略

- **MVP：** 为所有可见 Journal、Issue，以及被收录的 Article 各生成静态页面。这样每篇文章有独立 URL，搜索结果可以直达论文。
- Article 页面只存**合法可公开的元数据**；不嵌入论文 PDF。
- 对大量文章按需分片导出，`getStaticPaths()` 从 manifest 构建路径，避免一次把无关的原始 API payload 全放内存。
- 必须生成实际的 `404.html`，并让不存在的 Journal/Issue/Article 在生产站点返回静态 404 体验。
- **不要为了应付大规模数据静默删掉已经公开的论文 URL。** 如果超出静态方案可承受范围，进入第 14 节的 API/SSR 迁移，而不是随机跳过文章。

---

## 8. 网站页面、路由与交互

> 下方路径是站点内部相对路径。GitHub Pages 项目站点可能还有 `/repo-name` 前缀，必须统一经 `src/lib/urls.ts` 处理。

| 路由 | 页面内容 | 评论 |
|---|---|---|
| `/` | 介绍、搜索、期刊发现、最近更新 | 无 |
| `/journals/` | 可搜索的期刊列表/筛选 | 无 |
| `/journals/{slug}/` | 期刊详情、全部期次、Online First | **有：Journal Discussion** |
| `/journals/{slug}/issues/{issueId}/` | 该期的论文列表 | MVP 无 |
| `/articles/{articleId}/` | 论文详情、署名、摘要许可状态、外部链接 | MVP 无 |
| `/search/` | 全文检索与结果过滤 | 无 |
| `/about/` | 项目定位和维护方法 | 无 |
| `/data-sources/` | 来源、最后同步时间、缺失数据说明 | 无 |
| `/guidelines/` | 期刊评论规范、纠错方式 | 无 |
| `/privacy/` | GitHub 登录及第三方评论说明 | 无 |

### 8.1 Journal 页面（信息层次）

```text
[期刊名]  [缩写]
Publisher · ISSN(s) · Academic field
[Visit publisher site]

Issues
- Volume 45 · Issue 2 · 2026 · 8 articles
- Volume 45 · Issue 1 · 2026 · 9 articles
...

Online First / Unassigned
- Article A
- Article B

Journal Reviews & Submission Experiences
[解释：这是公开评论，不代表网站官方对期刊的评级]
[giscus iframe]
```

### 8.2 Issue 页面

每篇论文展示：

- 标题（链接到论文详情）
- 作者（原始署名顺序）
- DOI（跳转 `https://doi.org/{encoded-doi}`）
- 年份/发表日期
- 摘要：许可允许时展示纯文本，可折叠；否则只显示来源链接/许可状态
- 返回期刊/期次的面包屑导航

如论文尚未分配 Issue，期刊页面的 Online First 分组中可以直达论文页。

### 8.3 Article 页面

- H1 为准确论文标题，不使用全大写等错误处理。
- 作者列表保留顺序；ORCID 有值才链接。
- 期刊、Volume、Issue、页码、发表日期、DOI（值缺失时不渲染空字段）。
- 摘要仅在展示许可明确时输出，保存段落换行但转义危险字符。
- 论文站点/DOI 链接，数据来源、最后更新日期。
- 可加 DOI citation copy 按钮，但不必开发复杂文献管理工具。

### 8.4 外观和可访问性

- 英文界面、简洁学术风格、浅色/深色模式、移动端优先。
- 内容可读性优先于炫目动画；宽屏下正文合理限宽。
- 标题层级正确（单一 H1），键盘可操作搜索和导航。
- 空状态（无期次、无摘要、无结果）、加载状态和错误提示完整。
- 外链显式标注，禁止用户提交内容直接进入页面 HTML。

---

## 9. 评论系统：giscus + GitHub Discussions

### 9.1 单独评论仓库（推荐）

建议：

- 网站源码仓库：`academic-journal-reviews`。
- 公开评论仓库：`academic-journal-reviews-discussions`（也可第一版使用同仓库）。

将评论放到单独仓库可以减少源码仓库噪音，也方便将来更换静态网站托管；如果维护成本优先，使用同一仓库也完全可行。

配置步骤：

1. 创建**公开** GitHub 仓库，并启用 Discussions。
2. 创建类别 `Journal Reviews`，推荐使用 Announcements 类别，以限制创建新 Discussion 的权限。
3. 在该仓库安装 giscus GitHub App，并赋予必要权限。
4. 到 https://giscus.app/ 生成正确的 `repo`、`repo-id`、`category`、`category-id`。
5. 将公开配置写到 Astro 对应环境变量或配置中。
6. 使用真实 GitHub 账户在部署后的页面完成一次提交/回复/刷新测试。

**giscus 不是自建评论数据库**：评论内容保存在 GitHub Discussions 中，用户必须用 GitHub 登录并授权；Markdown 由 GitHub 支持。静态站点自身不存评论和用户身份。

### 9.2 映射规则：**必须使用稳定 ID**

不要用 URL、pathname、网页 title 作为主要映射；它们会因域名、slug 或标题变化而变。

对每本期刊：

```text
Discussion mapping mode: specific
Discussion term: journal:<journal.public_id>
Strict title matching: enabled
Example term: journal:j_9a1b2c3d
```

对应 giscus 关键参数如下（其他 repo/category ID **由用户的真实 GitHub 仓库配置产生，不要编造**）：

```html
<script src="https://giscus.app/client.js"
  data-repo="OWNER/REPOSITORY"
  data-repo-id="ACTUAL_REPO_ID"
  data-category="Journal Reviews"
  data-category-id="ACTUAL_CATEGORY_ID"
  data-mapping="specific"
  data-term="journal:j_9a1b2c3d"
  data-strict="1"
  data-reactions-enabled="1"
  data-emit-metadata="0"
  data-input-position="top"
  data-theme="preferred_color_scheme"
  data-lang="en"
  crossorigin="anonymous"
  async>
</script>
```

这是**参数示例**而非生产可直接使用的真实配置。Codex 要实现 `GiscusComments.astro`，把 `data-term` 作为 props 从数据库公开 ID 动态注入；Astro 外部脚本应按其官方 inline/script 规则处理，防止构建器改写第三方嵌入代码。

- 同一 `public_id` 在任何情况下只能对应一个期刊评论话题。
- 初次有人评论时，giscus 可以自动创建对应 Discussion（需要仓库/类别/app 配置正确）。
- 管理者可以从 GitHub Discussions 删除/锁定评论；评论区显示“View discussion on GitHub”等官方入口（若能可靠取得 Discussion URL）。
- 改名/迁移域名、重新构建后，旧评论仍在原 Discussion。
- 缺少配置时显示“Comments are not configured yet”，但**构建和其他页面必须照常成功**。

### 9.3 评论政策与隐私

在 `/guidelines/` 明确：

- 欢迎讨论具体投稿流程、审稿速度、编辑沟通、建设性建议。
- 鼓励提供时间线，但不能冒充官方统计；读者要区分个人经历与客观事实。
- 禁止人身攻击、泄露匿名审稿人身份、发布私人联系方式、威胁、仇恨、垃圾广告和无法核验的严重指控。
- 网站管理员保留按规则移除/锁定讨论的权利；提供纠错与申诉联系路径。

在 `/privacy/` 明确：评论使用第三方 GitHub/giscus，访问者发表评论需要 GitHub 账户，用户名和评论在公开仓库可见；网站不提供匿名保证。

---

## 10. 搜索：Pagefind

### 10.1 搜索目标

支持用户通过以下文本找到对应页面：

- Journal name / abbreviation / ISSN
- Article title / DOI / author
- Year / journal 的条件过滤（最基本）

为每篇 Article 生成页面后，Pagefind 能直接返回论文详情 URL；避免所有搜索都跳到某个很长的 Issue 页。

### 10.2 构建顺序（不可颠倒）

```bash
python3 scripts/cli.py export --out .generated
npx astro build
npx pagefind --site dist
```

上述操作打包为 `npm run build`。Pagefind 读取已生成的 HTML 并将搜索索引写入 `dist/pagefind/`，因此**不能在 Astro build 前运行**。

### 10.3 索引要求

- 用 `data-pagefind-body` 只索引主内容；导航、页脚、giscus 评论 iframe 不纳入索引。
- 为 Article/Journal 页面添加 `page_type`、`journal`、`year` 等元数据或过滤属性。
- Issue 页的论文列表与 Article 详情内容存在重复；可以降低 Issue 页索引权重或排除冗余区块，减少重复命中。
- 避免把每位作者都做独立过滤 facet（高基数会膨胀索引）；作者名先做全文检索。
- Pagefind JS/CSS 的路径必须兼容 GitHub Pages 的 `/repo-name/` base path。
- `astro dev` 不能天然提供最终的 Pagefind 索引；检验搜索时用 `npm run build && npm run preview`。
- 对未获摘要再分发许可的论文，确保摘要文本**不进入静态页面或搜索索引**。

示意：

```html
<main data-pagefind-body>
  <h1 data-pagefind-meta="title">Paper title</h1>
  <span data-pagefind-filter="page_type:article"></span>
  <span data-pagefind-filter="year:2026"></span>
  <!-- 作者、标题、DOI 等允许公开的数据 -->
</main>
```

具体 API 以 https://pagefind.app/docs/ 为准。

---

## 11. GitHub Pages + GitHub Actions：**唯一自动化/部署入口**

### 11.1 核心架构与触发语义

采用 **2 个工作流，不要再单独创建会与它们竞争部署的 `deploy.yml` / `sync.yml`**：

| 工作流 | GitHub 事件 | 数据采集 | 持久化 DB | 构建/部署 |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | `pull_request` → `main`，手动 | 不联网，用合成 fixtures | 不改生产 DB | 测试 + 构建，不部署 |
| `.github/workflows/site.yml` | `push` → `main` | 无 | 不写 DB | 读取正式快照，构建 + 部署 |
| `.github/workflows/site.yml` | `schedule` 每周一 | Crossref 增量同步 | 校验通过后自动 commit/push | **同一次运行**构建 + 部署 |
| `.github/workflows/site.yml` | `workflow_dispatch` | 默认不采集；可选择增量或历史导入 | 启用同步时持久化 | 构建 + 部署 |

运行流程：

```text
PR ───────────► CI: pytest → synthetic fixture → Astro check → build → Pagefind

push main ─────┐
schedule ──────┼──► site.yml: checkout → [可选 sync → report]
manual run ───┘                          ↓
                             production validate + tests
                                       ↓
                              Astro build → Pagefind
                                       ↓
                                 artifact 检查
                                       ↓
                              upload Pages artifact
                                       ↓
                         [同步时 commit SQLite → push]
                                       ↓
                                deploy Pages
                                       ↓
                                在线静态站点更新
```

> **特别注意 GitHub Actions 的触发限制：** `GITHUB_TOKEN` 产生的普通 `git push` **不会触发另一个 `push` 工作流，也不会自动触发 GitHub Pages 构建**。因此，同步数据后必须在 **当前 `site.yml` 的同一次运行里直接上传产物并部署**，不能依赖机器人提交后再唤醒一个独立的部署 workflow。官方说明：[GITHUB_TOKEN 文档](https://docs.github.com/en/actions/concepts/security/github_token)。

### 11.2 GitHub Pages URL 与 Astro 配置

项目站点（`https://OWNER.github.io/REPO/`）和自定义域名的 base path 不同。不要在任何代码里写死 `/REPO`。

```js
// astro.config.mjs（示意，正式项目可继续添加 integrations）
import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',
  site: process.env.PUBLIC_SITE_URL || 'http://localhost:4321',
  base: process.env.PUBLIC_BASE_PATH || '/',
  trailingSlash: 'always',
});
```

- `site.yml` 未配置 Variables 时，自动推导 `https://OWNER.github.io` + `/REPO`；仓库名为 `OWNER.github.io` 时使用 `/`。
- 设置自定义域名时，在 Repository Variables 指定 `PUBLIC_SITE_URL=https://your-domain.example`、`PUBLIC_BASE_PATH=/`。
- 所有站内链接、资源、Pagefind 路径、sitemap、canonical URL 都必须统一处理 `import.meta.env.BASE_URL`。
- `npm run build` 必须执行 `data:export → astro build → pagefind --site dist`，不能只构建 Astro 而漏掉搜索索引。

### 11.3 PR CI：`.github/workflows/ci.yml`

此工作流故意**不提供任何 Secrets**；不执行 Crossref/OpenAlex 在线同步，也不写回 Git。即使 PR 来自外部 fork，代码也不应获得写入令牌或生产密钥。

**下述内容已同时作为独立 `ci.yml` 文件交付；以它为准创建实际工作流。**

```yaml
# No network metadata fetches, credentials, or write permissions in pull-request CI.
name: CI - validate and build

on:
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    env:
      AJR_ENV: demo
      AJR_DB_PATH: /tmp/ajr-ci-demo.sqlite
      PUBLIC_SITE_URL: https://example.invalid
      PUBLIC_BASE_PATH: /academic-journal-reviews
    steps:
      - name: Checkout
        uses: actions/checkout@v7

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Set up Node.js
        uses: actions/setup-node@v7
        with:
          node-version: '24'
          cache: npm

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e '.[dev]'
          npm ci

      - name: Unit tests
        run: python3 -m pytest -q

      - name: Check production snapshot when present
        shell: bash
        run: |
          if [[ -s data/journals.sqlite ]]; then
            AJR_DB_PATH=data/journals.sqlite AJR_ENV=production \
              python3 scripts/cli.py validate --production
          fi

      - name: Prepare isolated synthetic dataset
        run: |
          python3 scripts/cli.py db-init
          python3 scripts/cli.py seed-demo
          python3 scripts/cli.py validate

      - name: Astro types, build, and Pagefind
        run: |
          npm run check
          npm run build

      - name: Check generated static site
        shell: bash
        run: |
          test -f dist/index.html
          test -f dist/404.html
          test -d dist/pagefind
          echo "Generated $(find dist -type f | wc -l) files"
```

### 11.4 自动同步、构建及部署：`.github/workflows/site.yml`

运行时规则：

1. 普通 `push main` 仅从受 Git 追踪的生产 `data/journals.sqlite` 读取数据，验证并部署；不会访问元数据 API。
2. 周一 `02:23 UTC` 自动增量同步（韩国时间周一 `11:23`）；非整点运行减少高峰拥堵。时间是计划触发时间，GitHub 不承诺准点执行。
3. 手动 `Run workflow` 可指定 `sync_metadata=true`；**第一次**选择 `initial_import=true`、`from_year=2020`（年份根据实际需求修改）。首次历史导入应限制在期刊白名单中、按窗口分页，避免超量请求。
4. 数据同步出错、生产校验失败、测试不通过、构建失败、产物超出阈值或提交失败时，workflow 非零退出，**不得继续部署**；已经成功部署的旧站点保持不变。
5. 在**成功完成校验、构建和产物检查以后**再提交数据库和 `sync-report.md`，减少坏数据进入 `main` 的风险。GitHub Bot 的提交不会循环触发另一个工作流。
6. 同步与部署串行（`concurrency`）；若外部提交使 push 产生冲突，不强行覆盖 `main`，应失败并人工重跑。
7. `OPENALEX_API_KEY` 是预留的可选配置；本版定时同步默认只调用 Crossref。Codex 实现可选 OpenAlex enrichment 后必须另设明确开关、请求配额和失败策略，不能偷偷造成 API 费用。

**下述内容已同时作为独立 `site.yml` 文件交付；以它为准创建实际工作流。**

```yaml
# Production pipeline for Academic Journal Reviews.
# Requires scripts/cli.py and package.json commands defined in the roadmap.
name: Sync metadata and deploy Pages

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      sync_metadata:
        description: 'Fetch and persist Crossref metadata before deployment'
        required: true
        type: boolean
        default: false
      initial_import:
        description: 'Run historical import instead of incremental sync (requires sync_metadata)'
        required: true
        type: boolean
        default: false
      from_year:
        description: 'First publication year for historical import'
        required: true
        type: string
        default: '2020'
  schedule:
    # Monday 02:23 UTC (11:23 Asia/Seoul); avoid top-of-hour congestion.
    - cron: '23 2 * * 1'

concurrency:
  group: ajr-production-pages
  cancel-in-progress: false

jobs:
  build:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 50
    permissions:
      contents: write  # Needed only when scheduled/manual sync commits its SQLite snapshot.
      pages: write     # Needed by configure-pages.
    env:
      AJR_ENV: production
      CROSSREF_MAILTO: ${{ secrets.CROSSREF_MAILTO }}
      OPENALEX_API_KEY: ${{ secrets.OPENALEX_API_KEY }}
      PUBLIC_SITE_URL: ${{ vars.PUBLIC_SITE_URL }}
      PUBLIC_BASE_PATH: ${{ vars.PUBLIC_BASE_PATH }}
      PUBLIC_GISCUS_REPO: ${{ vars.PUBLIC_GISCUS_REPO }}
      PUBLIC_GISCUS_REPO_ID: ${{ vars.PUBLIC_GISCUS_REPO_ID }}
      PUBLIC_GISCUS_CATEGORY: ${{ vars.PUBLIC_GISCUS_CATEGORY }}
      PUBLIC_GISCUS_CATEGORY_ID: ${{ vars.PUBLIC_GISCUS_CATEGORY_ID }}
      INPUT_SYNC_METADATA: ${{ inputs.sync_metadata || false }}
      INPUT_INITIAL_IMPORT: ${{ inputs.initial_import || false }}
      INPUT_FROM_YEAR: ${{ inputs.from_year || '2020' }}

    steps:
      - name: Checkout main branch
        uses: actions/checkout@v7
        with:
          ref: main
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Set up Node.js
        uses: actions/setup-node@v7
        with:
          node-version: '24'
          cache: npm

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e '.[dev]'
          npm ci

      - name: Resolve GitHub Pages site URL and base path
        shell: bash
        run: |
          set -euo pipefail
          owner="${GITHUB_REPOSITORY%%/*}"
          repo="${GITHUB_REPOSITORY#*/}"
          site="${PUBLIC_SITE_URL:-https://${owner}.github.io}"
          base="${PUBLIC_BASE_PATH:-/${repo}}"
          if [[ "$repo" == "${owner}.github.io" && -z "${PUBLIC_BASE_PATH:-}" ]]; then
            base='/'
          fi
          echo "PUBLIC_SITE_URL=$site" >> "$GITHUB_ENV"
          echo "PUBLIC_BASE_PATH=$base" >> "$GITHUB_ENV"
          echo "Site: $site ; base: $base"

      - name: Guard manual import options
        if: github.event_name == 'workflow_dispatch'
        shell: bash
        run: |
          if [[ "$INPUT_INITIAL_IMPORT" == 'true' && "$INPUT_SYNC_METADATA" != 'true' ]]; then
            echo 'initial_import requires sync_metadata=true' >&2
            exit 1
          fi

      - name: Synchronize academic metadata
        if: github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.sync_metadata == true)
        shell: bash
        run: |
          set -euo pipefail
          if [[ -z "${CROSSREF_MAILTO:-}" ]]; then
            echo 'Missing GitHub Actions secret: CROSSREF_MAILTO' >&2
            exit 1
          fi
          python3 scripts/cli.py db-init
          python3 scripts/cli.py seed --file data/journal_registry.csv

          if [[ "$INPUT_INITIAL_IMPORT" == 'true' ]]; then
            if ! [[ "$INPUT_FROM_YEAR" =~ ^[0-9]{4}$ ]]; then
              echo 'from_year must be a four-digit year' >&2
              exit 1
            fi
            python3 scripts/cli.py sync --provider crossref --mode initial --from-year "$INPUT_FROM_YEAR"
          else
            python3 scripts/cli.py sync --provider crossref --mode incremental
          fi

          # This command must produce a human-readable report after successful sync.
          python3 scripts/cli.py report --out data/sync-report.md

      - name: Validate production snapshot and run tests
        shell: bash
        run: |
          set -euo pipefail
          test -s data/journals.sqlite || { echo 'Production SQLite snapshot is missing'; exit 1; }
          python3 scripts/cli.py validate --production
          python3 -m pytest -q
          npm run check

      - name: Build static HTML and Pagefind index
        run: npm run build

      - name: Smoke-test and enforce site size guard
        shell: bash
        run: |
          set -euo pipefail
          test -f dist/index.html
          test -f dist/404.html
          test -d dist/pagefind
          size=$(du -sb dist | cut -f1)
          echo "Static site size: ${size} bytes"
          if (( size > 900000000 )); then
            echo 'Static site exceeds 900 MB engineering warning threshold' >&2
            exit 1
          fi

      - name: Configure GitHub Pages
        uses: actions/configure-pages@v5

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: dist

      - name: Commit validated metadata snapshot
        if: github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.sync_metadata == true)
        shell: bash
        run: |
          set -euo pipefail
          git add -- data/journals.sqlite data/sync-report.md
          if git diff --cached --quiet; then
            echo 'No database/report change; nothing to commit.'
          else
            git config user.name 'github-actions[bot]'
            git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
            git commit -m 'data: update academic journal metadata'
            git push origin HEAD:main
          fi

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy GitHub Pages artifact
        id: deployment
        uses: actions/deploy-pages@v5
```

### 11.5 GitHub 仓库初始化清单（必须人工执行）

1. 创建 GitHub 公共仓库，默认分支为 `main`。在仓库 `Settings → Pages → Build and deployment → Source` 选择 **GitHub Actions**（不选择 `Deploy from a branch`）。
2. 在 `Settings → Actions → General → Workflow permissions` 确保 workflow 被允许写入本仓库。`site.yml` 的 `contents: write` 仅用于生产数据快照的 Bot commit；部署作业仅有 `pages: write` 和 `id-token: write`。组织政策可能限制写入权限，需要仓库管理员协调。
3. 在 **Settings → Secrets and variables → Actions → Secrets** 添加 `CROSSREF_MAILTO`（真实联系邮箱）；需要 OpenAlex enrichment 时才添加 `OPENALEX_API_KEY`。
4. 在 **Settings → Secrets and variables → Actions → Variables** 可添加 `PUBLIC_SITE_URL`、`PUBLIC_BASE_PATH`（不填时按 GitHub Pages 项目仓库推断）；评论就绪后添加 `PUBLIC_GISCUS_REPO`、`PUBLIC_GISCUS_REPO_ID`、`PUBLIC_GISCUS_CATEGORY`、`PUBLIC_GISCUS_CATEGORY_ID`。这些是**公开配置值**，不应把 API 密钥放进去。
5. 确保 `data/journal_registry.csv` 包含真实且校验过的 ISSN。不要把 Synthetic demo 数据作为生产快照提交。
6. 在 `Actions → Sync metadata and deploy Pages → Run workflow` 选择 `main`，第一次运行设置 `sync_metadata=true`、`initial_import=true` 及合适的 `from_year`。工作流成功后检查站点和 `data/sync-report.md`；后续由 cron 增量更新。
7. 评论仓库必须启用 Discussions、安装 giscus GitHub App；从 https://giscus.app/ 获取真实 repo/category ID，并手动在两个不同期刊页面测试映射与 Markdown 评论。

**关于分支保护**：上述 direct-commit 方案适合个人维护的 MVP。如果 `main` 启用禁止 Bot 直推的保护规则，`git push origin HEAD:main` 将失败，这是正常的安全限制。应改成 `sync PR → 管理员审核/合并 → push main 自动部署` 的审核型工作流，**不要简单关闭保护或放宽所有权限**。Bot 创建的 PR 测试存在单独的触发/审批机制；Codex 切换到 PR 模式时须按官方文档处理，并写明审核过程。本次交付默认使用 direct-commit 方案。

### 11.6 故障排查、费用与持续运营

| 场景 | 排查与处置 |
|---|---|
| `Permission denied` / Bot push rejected | 检查 Actions 写入权限及 main 分支保护；按需切换 PR 模式 |
| Pages `404` 或 CSS / 搜索失效 | 检查 `PUBLIC_SITE_URL`、`PUBLIC_BASE_PATH` 以及 Pagefind 的 base URL |
| 周一没有定时更新 | 检查 workflow 是否禁用、Actions 日志、cron；公开仓库连续 **60 天无活动**可能自动禁用计划任务 |
| Crossref 429 / 网络超时 | 指数退避、请求限额、分页断点；校验失败不提交新 DB、不部署 |
| OpenAlex 配额问题 | enrichment 默认关闭；开通时用 Secret、控制预算并记录限额 |
| SQLite 被覆盖/损坏 | 用最近正常的 Git 快照恢复并重建；单元测试验证 DOI、外键和摘要许可 |
| Pages 上传过大 | 查看 `dist` 与 Pagefind 索引体积，接近 1 GB 官方限制前拆分架构 |
| `giscus` 不显示 | 检查 Discussions、giscus App、repo/category ID 及仓库 Public 状态 |

**安全要求：** 不使用 `pull_request_target` 执行外部 PR 源码；不把 Secrets 写入静态导出或日志；production 校验不能回退成 demo 模式；尽可能使用官方 Actions，生产可进一步 pin 到审核过的 commit SHA。对 SQLite 进行事务、完整性验证和备份。GitHub-hosted runner 运行时间与账户额度、Crossref/OpenAlex 使用条款按最新官方规则为准。

---

## 12. SEO、性能与可用性

- 每个 Journal、Issue、Article 都有 `title`、`description`、canonical URL、Open Graph 基本元数据。
- 添加 sitemap（例如 `@astrojs/sitemap`）和 `robots.txt`；仅可公开页面加入 sitemap。
- 合理生成 `schema.org/ScholarlyArticle` 的 JSON-LD（只用真实字段，不虚构 DOI/日期）。
- Article 页面用 `https://doi.org/...` 链接到权威原文。
- 建议记录页面元数据来源和最近同步时间；避免把“不完整数据”伪装成完整期刊目录。
- JS 尽量少：只有搜索和 giscus 等实际需要交互的部分加载脚本。
- 优先支持窄屏浏览和键盘导航；排除不必要的第三方埋点。
- 检查 404、重复页面、无摘要/无期次、外链安全（`rel` 等）。

---

## 13. 数据质量、安全与可运营性

### 13.1 不变式

- 一个规范化 DOI 至多一个 Article。
- 一个 `public_id` 永久对应同一实体；同步不得更换。
- 每个 Article 的 `issue_id` 为空或指向同一期刊的 Issue。
- `article_authors` 顺序不能因导入器排序方式改变。
- 重复运行 sync/export/build 不应产生重复数据或随机变化的 URL。
- 所有公开数据导出均不包括未经许可的摘要、密钥、原始私有响应或运行日志。
- 学术数据同步失败不能删除已存在的评论，也不能直接发布损坏数据库。

### 13.2 防御性措施

- 外部元数据一律视为不可信：SQL 参数绑定；页面 HTML 转义；JATS/XML 使用安全解析，禁用实体扩展和远程实体。
- 只允许 `http(s)` 形式的外部链接；对 DOI、ORCID、ISSN 做格式验证。
- GitHub Actions 版本固定且优先选官方 Action；生产凭据只存 Secrets。
- 日志不可打印 API key 和其他敏感配置。
- 对 429、500、超时、不完整分页、JSON 结构缺失作明确错误处理。
- DB 快照导出前运行 `PRAGMA integrity_check` 与 FK 检查。
- 给用户纠错入口（GitHub Issues 或维护邮箱），不要允许未审核用户直接写数据库。

### 13.3 数据许可与内容治理

- 在 `/data-sources/` 说明 Crossref/OpenAlex 的来源、更新时间及数据缺漏。
- 对受版权保护的摘要实施展示策略，不缓存或公开超出授权范围的内容。
- 评论遵守 GitHub 的公开讨论与处理规则；支持删除/锁定、举报/联系管理员。
- 不对个人投稿经验进行未经核实的统计泛化，不默认把评论数量当作期刊质量指标。

---

## 14. 扩容策略：什么时候不用纯静态？

GitHub Pages 官方说明：已发布站点**不超过 1 GB**，部署**超过 10 分钟会超时**，还有流量等软限制。因此应监控真实构建产物，而不是单纯按“期刊数量”判断。

### 14.1 第一阶段：纯静态（本方案）

适用：几十本期刊、几千到数万篇论文等可在可接受时间内完整构建的规模。规模只是经验区间，最终由 `dist` 大小、构建耗时和索引体积决定。

预警建议（不是官方硬性阈值）：

- `data/journals.sqlite` 接近 50 MB：评估 Git 仓库维护成本。
- `dist/` 超过 500 MB：分析 HTML/索引膨胀及 Pages 余量。
- CI 构建持续超过 5 分钟：做 profiler，考虑混合渲染。
- 搜索索引使首次搜索加载明显变慢：调整索引策略。

### 14.2 第二阶段：混合方案

数据仍由 ETL 管理，但改成：

```text
SQLite / PostgreSQL / 托管数据库
             ↓
         API / Serverless
             ↓
 Astro 静态首页与期刊页 + 动态论文查询 / 分页
             ↓
       用户浏览器

评论仍然是 giscus + GitHub Discussions
```

可选托管按实际预算和平台限制评估 Cloudflare Workers + D1、Turso、Supabase/PostgreSQL 等；**不是 MVP 必需选型**。若迁移，必须保持期刊、Issue、Article `public_id` 不变，原有 URL 做兼容或重定向，giscus 以稳定 ID 映射的评论继续可用。

### 14.3 重要工程决策

不要因为未来可能有百万篇论文，现在就引入数据库服务器。也不要在纯静态方案超过平台极限后偷偷舍弃已有论文页面。应以指标触发明确的迁移。

---

## 15. 测试计划（必须由 Codex 实施）

### 15.1 Python 数据测试

- DOI：大小写、`doi:` 前缀、URL 前缀、percent encoding、重复 upsert。
- Journal：多 ISSN 映射同一期刊；冲突 ISSN 不得误合并。
- Issue：正常 Volume/Issue、Supplement、合刊、无期次、后补期次。
- Article：无摘要、无 DOI、错误 DOI、后续修订标题与作者。
- Author：同名不同 ORCID 不合并；正确顺序和 affiliation。
- Date：只有年份、年月、完整日期；不得伪造精度。
- ETL：分页断点、429/5xx 重试、固定时间窗口、重复运行幂等。
- DB：foreign keys、`integrity_check`、migration 兼容性。
- Rights：`unknown/restricted` 摘要绝不出现在生成的 JSON 或 HTML。

### 15.2 Astro / 浏览器测试

- 首页、期刊页、Issue 页、Article 页、404 均可打开。
- 期刊 → 期次 → 论文 → DOI 外链可导航。
- 在线发表、无摘要、空期次有合理 UI。
- Pagefind 用论文标题或作者检索，得到可点击正确结果。
- `/REPO/` 子路径部署下，内部路由、CSS、Pagefind 文件全部有效。
- giscus 未配置时不崩溃；配置后每本期刊注入不同稳定 `data-term`。
- 通过人工验收确认提交评论、Markdown 渲染、回复及 GitHub Discussion 双向显示。
- 页面无明显控制台错误，移动端布局基本可用。

### 15.3 构建与规模测试

- 10、100、1,000、10,000 条合成论文记录的批量构建测试（可单独运行，不要求所有 PR 每次测最大规模）。
- 输出构建时间、HTML 页面数、`dist/` 字节数、Pagefind 字节数。
- 不允许用户打开 `/search/` 时下载完整 SQLite 或巨型全站 JSON。

---

## 16. 实施顺序（Codex 必须按阶段推进）

### Phase 0 — Scaffold & Offline Demo（首先完成）

**工作：**

- 创建 Astro + TypeScript + Tailwind 4 项目。
- 建立 Python CLI、SQLite migrations、合成测试 fixture。
- 完成 SQLite → `.generated` JSON → Astro 静态页面链路。
- 至少提供：2 本虚构示例期刊、每本 2 期、每期至少 3 篇虚构论文，作者署名齐全；再提供至少 1 篇无期次的 Online First 论文。
- 数据必须清楚标为 **Demo / Synthetic**，不能伪装为真实已发表学术论文。

**验收：** 离线执行 `db-init → seed-demo → npm run build → npm run preview` 后能浏览多层页面；没有 giscus/OpenAlex 配置也不报错。

### Phase 1 — Real Metadata Pipeline

**工作：**

- 实现 journal registry 和 ISSN 校验。
- 实现 Crossref 导入、分页、错误重试、DOI upsert、期次重建/关联、数据质量报告。
- 测试至少一种真实期刊（使用**验证过的** ISSN），可配置年份区间；对导入记录标注来源。
- 实现摘要许可控制，不误将所有 Crossref abstract 自动公开。

**验收：** 两次导入同一范围得到相同 DOI 记录数与稳定 URL；年份/Issue/作者关系正确。

### Phase 2 — Search, Comments & UX

**工作：**

- 完善期刊目录与详情、搜索、空状态、面包屑、主题。
- 集成 Pagefind，校验子路径。
- 集成 giscus（`specific` + `public_id` + strict）；提供仓库管理配置说明。
- 创建 `/about/`、`/privacy/`、`/guidelines/`、`/data-sources/`。

**验收：** 检索可以进入目标论文；不同期刊的 giscus term 不同；对真实配置完成评论验收。

### Phase 3 — CI/CD & Production Release

**工作：**

- 配置 CI、GitHub Pages 部署、`site/base`。
- 用生产期刊白名单导入正式数据；不得发布带有合成论文的“生产目录”。
- 配置站点元信息、sitemap、404、robots、安全链接。
- 编写安装、部署、数据更新、备份与故障恢复 README。

**验收：** `main` 提交后公开站点自动更新；数据更新时间清晰展示；CI 对错误数据能阻止构建。

### Phase 4 — Automated Sync & Maintenance

**工作：**

- 实现固定 `until-index-date` 的增量同步。
- 启用 `site.yml` 每周一次 `schedule`，按固定 `until-index-date` 窗口做增量同步，生成 `data/sync-report.md`。
- 同步通过校验、测试、构建以后使用 `GITHUB_TOKEN` 自动提交 SQLite 快照，并在**同一次 workflow run** 中部署到 Pages。
- 人工通过 `workflow_dispatch` 执行第一次历史导入、异常后的手动重跑。
- 加入批量增长情况下的大小/耗时监控和报警阈值；如果 main 不允许 Bot 直推，迁移为 PR 审核方案。

**验收：** API 失败不污染主数据；Bot 提交数据后无需二次触发即能看到最新站点；默认主分支受保护时有清晰失败/PR 迁移说明。

---

## 17. 最终验收清单（Definition of Done）

- [ ] 新机器按照 README 完成离线运行，不需要付费账户或 API key。
- [ ] SQLite Schema 有迁移机制、FK 校验、关键唯一性约束。
- [ ] Journal → Issue → Article → Author 的关系正确，Online First 可展示。
- [ ] DOI、ISSN 去重及期刊归属不会被模糊匹配破坏。
- [ ] 数据源变化不会重置公开 ID、URL 或期刊 Discussion 映射。
- [ ] 页面来自数据库构建输出，而不是手写每篇论文 HTML。
- [ ] 真实 Crossref 可配置导入，速率限制/分页/重试可控。
- [ ] Abstract 的版权展示规则在导出层生效；无许可不会被搜索索引泄漏。
- [ ] 搜索支持期刊、论文标题、作者、DOI；能直达论文页面。
- [ ] giscus 支持 Markdown、回复与 Reaction；期刊 stable ID 对应唯一 Discussion。
- [ ] 缺少 GitHub 评论配置或可选 OpenAlex key 时网站仍正常构建。
- [ ] `npm run build` 同时产出 Astro HTML 和 Pagefind 索引。
- [ ] GitHub Pages 的 `base`/自定义域名路径均能正确生成链接。
- [ ] `ci.yml` 对 PR 使用隔离 demo DB、最小只读权限，离线执行数据质量验证、测试和静态构建。
- [ ] `site.yml` 在 push main、schedule、workflow_dispatch 三种情境正确运行；首次历史导入仅在人工确认输入后进行。
- [ ] 每周同步数据通过校验后自动提交 SQLite 与变更报告，并在同次运行完成 Pages 部署；失败不发布坏数据。
- [ ] `main` 分支自动部署，正式版本不混入合成数据。
- [ ] README 说明配置、同步、迁移、备份、管理员审核和内容管理。

---

## 18. Codex 的执行指令（可以直接作为第一条任务）

> 请读取仓库根目录的 `academic-journal-reviews-technical-roadmap.md` 并据此**实施**整个 Academic Journal Reviews MVP。优先按照 Phase 0 → Phase 1 → Phase 2 → Phase 3 的顺序创建真实工程文件、运行测试、修复失败，再处理 Phase 4。必须实现 `.github/workflows/ci.yml` 和 `.github/workflows/site.yml`，严格遵守第 11 节 GitHub Actions 合并同步/部署、运行权限、生产校验及第一次手动导入契约。不要仅输出方案或伪代码；不要因为 giscus repo ID、OpenAlex key、GitHub 用户名等外部配置尚未提供而中止本地可运行的开发。缺省时用合成 fixture 和明确的环境变量占位，绝不伪造真实期刊数据/评论。每完成一个阶段运行相关命令并记录结果；最后提交清晰的 README、已完成/未完成项、以及需要维护者手动设置的 GitHub 项目配置。严格遵循稳定 public_id、摘要再发布权限、无后端纯静态部署和可重现构建等要求。如技术细节与最新版官方文档不符，以官方文档为准并在 README 说明偏差。

### 维护者后续需人工提供/设置的事项

1. GitHub 源码仓库路径、是否使用独立 Discussions 仓库。
2. GitHub Pages 网站正式域名（没有可先使用 `USERNAME.github.io/REPO`）。
3. 期刊白名单与准确 ISSN（建议先从 3–5 本期刊验证）。
4. giscus App 授权和真实 repo/category ID。
5. GitHub Actions 的 `CROSSREF_MAILTO` Secret、可选 `OPENALEX_API_KEY`，以及站点/giscus Variables；第一次通过手动 workflow_dispatch 导入正式数据。
6. 评论规则与纠错/联系渠道的最终内容。

---

## 19. 官方参考资料

- Astro 官方文档：https://docs.astro.build/
- Astro GitHub Pages：https://docs.astro.build/en/guides/deploy/github/
- GitHub Actions 运行与触发：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- `GITHUB_TOKEN` 触发限制：https://docs.github.com/en/actions/concepts/security/github_token
- GitHub Pages 自定义工作流：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- Actions checkout：https://github.com/actions/checkout
- Actions Pages 部署：https://github.com/actions/deploy-pages
- Astro Tailwind：https://docs.astro.build/en/guides/styling/
- Pagefind：https://pagefind.app/docs/
- Pagefind 搜索字段/过滤：https://pagefind.app/docs/filtering/
- giscus 配置：https://giscus.app/
- giscus GitHub 仓库：https://github.com/giscus/giscus
- GitHub Pages 官方限制：https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Crossref REST API：https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Crossref 同步建议：https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
- Crossref 元数据版权（尤其摘要）：https://www.crossref.org/documentation/retrieve-metadata/
- OpenAlex API：https://help.openalex.org/api/
- OpenAlex 身份验证/额度：https://help.openalex.org/api/authentication/

> 说明：这是**工程实施规格 + 可复制的 GitHub Actions YAML 模板**，而不是已部署网站或已经实现的所有应用源码。独立 `site.yml`、`ci.yml` 与本文一同交付；Codex 必须先实现本规格 CLI、Node scripts 与数据模式，才能使 Actions 成功。实际开发时应校验依赖的最新兼容版本、官方 Actions 配置及第三方 API 使用政策。
