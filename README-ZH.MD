# open-utd · Academic Journal Reviews

[English](README.md) · **简体中文**

开放的学术期刊目录，支持文献元数据搜索、期刊投稿经验交流和逐篇文献讨论。项目基于 Python + SQLite、Astro + TypeScript + Tailwind CSS、Pagefind，以及 GitHub Actions / Pages。界面支持 English / 中文，期刊和文献元数据保留来源英文原文。

项目仓库：[undefined-xhs/open-utd](https://github.com/undefined-xhs/open-utd) · 网站：[www.open-utd-hot-take.xyz](https://www.open-utd-hot-take.xyz/)。

## 界面语言

页面提供 **English / 中文** 切换，涵盖导航、按钮、筛选、状态提示、政策说明和评论组件界面。语言偏好保存在当前浏览器的 `localStorage`（`open-utd-language`），刷新和跨页面导航后仍然有效；没有保存偏好时，中文浏览器使用中文，其他浏览器使用英文。禁用 JavaScript 时显示英文静态页面。

**期刊名称、论文标题和作者署名始终保留来源英文原文，不作自动翻译。本站不展示或索引论文摘要。** 切换语言不会改变论文或期刊 URL、公开 ID、搜索数据或评论归属；giscus 界面对应切换为 `en` / `zh-CN`，已有评论内容保持原样。

## 收录范围

| Journal | Print ISSN | Electronic ISSN | 起始年份 |
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

期刊清单在 [`data/journal_registry.csv`](data/journal_registry.csv)。首次导入覆盖 2006 年起至运行时 Crossref 已收录的数据，之后按索引更新时间增量同步。网站显示的是 **Crossref 已登记的元数据**；登记延迟、缺失卷期和 Online First 记录意味着它不能保证与出版社“最新一期完整目录”同步。具体覆盖和同步结果见数据来源页及同步报告，最新期目录以出版社官方期刊页为准。合成演示数据有明确标记，生产校验拒绝演示数据。

Crossref 的 `journal-article` 分类也可能包含书评、勘误、索引及代码/数据附属记录，并非每条都是研究论文正文；本站保留来源分类。按 DOI 去重也不意味着能自动合并出版社以不同 DOI 重复登记的内容。

期刊范围采用 [UT Dallas 官方 24 刊名单](https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/index.php)。ISSN 与查询入口的核验依据见 [`data/journal-registry-sources.md`](data/journal-registry-sources.md)；当前期次、论文数量和各期刊采集结果以数据库及 [`data/sync-report.md`](data/sync-report.md) 为准。

## 浏览与讨论

首页点击期刊名称进入该刊的文献目录；卡片另有独立的**评论与投稿经验**按钮及浏览文献入口；期刊讨论集中在独立评论页。查找论文时，按“期刊 → 年份 → 期次 → 论文”逐层浏览；尚未分配期次的论文在单独的 Online First 列表中，每页 30 篇。

| 路径（站点 base path 之后） | 内容 |
| --- | --- |
| `/journals/{slug}/` | 期刊概况、评论入口、年份网格 |
| `/journals/{slug}/reviews/` | 该期刊的评论与投稿经验 |
| `/journals/{slug}/years/{year}/` | 所选年份的期次；缺失年份使用 `undated` |
| `/journals/{slug}/issues/{issueId}/` | 该期论文列表，沿用原期次 URL |
| `/journals/{slug}/online-first/{page}/` | Online First / Unassigned 分页列表，页码从 1 开始 |
| `/articles/{articleId}/` | 论文元数据及该论文的独立讨论，沿用原论文 URL |
| `/comments/` | 期刊和论文的最新评论与回复，按发表时间倒序，附原评论链接 |

页面导航和评论组件支持中英文切换，文献元数据保持英文原文。网站检索仍可直接进入论文；年份和分页导航不改变已有论文、期次的公开 ID。

## 本地运行：不需要 API key 或评论配置

需要 **Node.js 24**、**Python 3.12+**、Git。首次安装依赖需要网络；以下演示数据、测试和构建不会请求 Crossref/OpenAlex。

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

预览地址以终端输出为准。`npm run build` 顺序执行数据库导出、离线评论文件准备、Astro 静态构建、Pagefind 索引。首次本地构建会自动生成空评论文件，并明确显示“尚未同步”；已有评论快照不会被覆盖。需要恢复离线空状态时运行 `python scripts/fetch_comments.py --empty`。搜索需要构建产物，使用 `preview` 验证；`npm run dev` 适合修改页面，修改数据库后需重新导出或重启。

[`.env.example`](.env.example) 提供可选配置；复制为 `.env` 后 Astro 会读取公开配置，Python CLI 读取 shell 环境变量，需自行 `export`。不要将 `.env` 提交到 Git。Windows 可使用 WSL 运行以上命令；npm 数据导出脚本调用 `python3`，应确保它指向已安装依赖的 Python。

## GitHub Actions 部署

仓库只有两个工作流：

| 工作流 / 事件 | 行为 |
| --- | --- |
| `ci.yml`：向 main 提交 PR / 手动运行 | 只读令牌、独立临时演示 DB、离线数据测试、生产快照校验（若存在）、类型检查、子路径构建、静态产物检查 |
| `site.yml`：push main | 获取最新评论与汇总统计，使用已提交的生产数据库构建和部署，不请求 Crossref |
| `site.yml`：评论新增、编辑、删除；讨论编辑、删除、转移或更改类别 | 完整获取评论和统计后与线上 JSON 比较，两者均无变化直接结束；有变化则复用 HTML 和 Pagefind 缓存，替换两份快照 |
| `site.yml`：每天 03:37 UTC（北京时间 11:37） | 刷新汇总统计并补查评论，覆盖遗漏事件和管理操作；不请求 Crossref，不提交数据库 |
| `site.yml`：每周一 02:23 UTC（北京时间 10:23） | Crossref 增量同步 → 校验 → 测试 → 评论快照 → 构建 → 提交数据库 → 上传 → 同一次运行部署 |
| `site.yml`：手动运行 | 默认更新评论与统计并部署；显式启用元数据同步后才采集 Crossref，历史导入需再打开 `initial_import`，可用 `journal` 只更新指定期刊；打开 `comments_only` 可改为轻量评论与统计更新 |

### 当前配置与首次部署

公开仓库 `undefined-xhs/open-utd` 已创建，GitHub Pages 已选择 Actions 构建来源，`CROSSREF_MAILTO` 已保存为 Actions Secret；giscus App 已安装，Discussions 和四个公开评论变量已配置。重新部署此仓库无需重复这些设置。以下步骤也适用于 fork 或迁移到新仓库。

当前网站使用上述自定义域名，并已强制启用 HTTPS；Actions 配置为 `PUBLIC_SITE_URL=https://www.open-utd-hot-take.xyz` 和 `PUBLIC_BASE_PATH=/`。

1. 仓库使用公开可见性和 `main` 默认分支。在 **Settings → Pages → Build and deployment** 选择 **GitHub Actions**。
2. 在 **Settings → Actions → General** 允许所需 Actions。生产构建作业声明 `contents: write`，用于提交经过验证的 SQLite 快照；另需 `discussions: read` 读取公开评论。组织策略必须允许这些权限。
3. 在 **Settings → Secrets and variables → Actions → Secrets** 添加 `CROSSREF_MAILTO`，填写真实维护者联系邮箱。联系地址只保存在 Secret 中；无需 Crossref API key。
4. 默认 GitHub Pages 地址无需添加变量。自定义域名时同时设置 Actions Variables：`PUBLIC_SITE_URL=https://your-domain.example`、`PUBLIC_BASE_PATH=/`，并在 Pages 设置中配置域名和 DNS。
5. 打开 **Actions → Sync metadata and deploy Pages → Run workflow**，选 `main`。新仓库首次导入设置 `sync_metadata=true`、`initial_import=true`、`from_year=2006`，`journal` 留空以包含全部期刊。当前仓库已有正式快照，重新部署可保持 `sync_metadata=false`。历史导入需等待全部分页、校验及静态构建完成。同步成功后先保存一份保留 7 天的 Actions artifact（SQLite 与同步报告），后续构建或容量校验失败时仍可下载恢复，生产版本只在全部检查通过后更新。
6. 查看运行 Summary 的资源指标、评论快照统计、提交后的 [`data/sync-report.md`](data/sync-report.md)、Pages 环境链接。普通代码推送在完整构建中刷新评论；评论变动和每天补查走轻量流程，每周运行元数据增量同步。

如果仓库暂时没有真实生产快照，普通 push 部署会明确失败；运行一次手动历史导入后即可部署。工作流不会用演示论文填充正式站点。

手动参数 `journal` 接受 registry 中的单个 slug（如 `marketing-science`），留空选择全部期刊。`from_year` 默认 `2006`，只在历史导入时使用；其值必须与所选每本期刊的 `start_year` 一致。将 `from_year` 留空时，各期刊分别使用自己的 registry 起始年份，适合将来收录范围不同的期刊。

Actions 使用固定窗口的 Crossref `from-index-date` / `until-index-date` 和重叠区间捕获后续修订。增量同步还按新近发表日期补查一次，不限制起始索引日期，以补齐提前登记、后来才到发表日期的论文。只有完整成功才推进水位；同一 DOI 更新保留公开 ID。缺少初始水位的期刊必须先做历史导入。采集失败、数据校验失败、测试或构建失败、体积超限、Bot 提交失败都会阻止本次部署，已发布站点保留。若数据已提交但 Pages 服务部署失败，重新手动运行默认的“仅部署”即可。

同步和部署通过同一 concurrency group 串行执行。`GITHUB_TOKEN` 的数据提交不会触发另一个 push 工作流，因此部署就在当前运行完成。若有人在构建期间更新 main，Bot 的非快进推送会失败；拉取新代码后重跑，不进行 force push。

## 网站访问统计

Cloudflare Web Analytics 可提供浏览量、访问次数、热门页面、来源网站、国家、设备和页面性能的汇总统计。访问次数不等于去重人数；浏览器拦截和网络故障可能导致漏计。它不会显示访客姓名或 GitHub 账户，不使用追踪 Cookie，也不提供自定义点击或搜索事件统计。详见网站双语 `/privacy/` 页面及 [Cloudflare 文档](https://developers.cloudflare.com/web-analytics/)。

1. 在 Cloudflare 的 **Web Analytics → Add a site** 中添加正式域名（当前为 `www.open-utd-hot-take.xyz`）。网站继续由 GitHub Pages 托管，无需修改 DNS。
2. 选择手动安装 JavaScript 脚本，将 `data-cf-beacon` 中的 32 位十六进制 `token` 填入仓库 Actions **Variable** `PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN`。这是公开的统计站点标识，不是 Cloudflare API token 或账户凭据。不要同时开启自动脚本注入。
3. 运行 `site.yml`，保持 `comments_only=false`、`sync_metadata=false`。部署成功后访问网站，再到 Cloudflare 的 **Web Analytics** 查看数据；报告可能需要几分钟才出现。

只有使用正式数据、配置了非空 token 的生产构建才会加入脚本；演示数据和 `astro dev` 不加载。无效 token 会阻断生产构建，错误信息不会输出其值。停用时清空该 Actions Variable 并重新执行完整部署。统计配置纳入评论刷新缓存键，修改 token 后不会复用旧配置生成的 HTML。本地可使用 [`.env.example`](.env.example) 中的同名可选变量。

### 公开统计页

`/analytics/` 展示最近 7／30 个完整 UTC 日的浏览量、每日趋势、国家／地区汇总和热门站内路径，入口位于页脚。快照采集时间按访问者浏览器时区显示，统计日期按 UTC 划分。数据从启用统计脚本后开始，不补回之前的访问记录。尚无可用快照时显示等待状态，与成功同步后的真实零值区分。数据可能经过采样，也可能因请求被拦截而漏计，不代表去重人数。

自动发布需要为对应 Cloudflare 账户创建 **Account Analytics:Read** API token，将其保存为仓库 Actions **Secret** `CLOUDFLARE_ANALYTICS_API_TOKEN`。另设置 Actions **Variables** `CLOUDFLARE_ACCOUNT_ID` 和 `CLOUDFLARE_WEB_ANALYTICS_SITE_TAG`，分别填写账户 ID 及 Web Analytics 仪表盘 URL 中的站点 tag。该 tag 与公开 beacon token 不同。API 凭据仅在采集步骤中使用，不进入静态网站。

[`scripts/fetch_analytics.py`](scripts/fetch_analytics.py) 读取 Cloudflare 的 RUM GraphQL 数据集，以本站域名和 tag 限定范围，生成经过校验的汇总文件 `public/data/analytics.json`。普通部署和现有的每日快照检查都会刷新，也可用 `comments_only=true` 手动刷新。即使评论没有变化，统计变化仍会触发发布；轻量流程替换两份 JSON，复用 HTML 和 Pagefind。API 或数据校验失败会中止发布，保留线上旧快照。本地构建通过 `--ensure-empty` 准备空状态，不访问网络。清空三项后端配置后，下次运行会发布不可用状态；只删除部分配置则明确失败。

## 期刊和论文评论：giscus + GitHub Discussions

每本期刊和每篇论文都有各自的公开讨论，支持 GitHub 登录、Markdown、回复和 Reaction。期刊讨论位于 `/journals/{slug}/reviews/`，用于投稿和审稿经历；论文讨论仍位于论文详情页，用于研究内容。评论保存在 GitHub Discussions。不做星级排名或未经验证的审稿统计。

当前评论服务已配置在 `undefined-xhs/open-utd` 的 **Announcements** 类别。公开配置如下；这些值是仓库和类别标识，不是凭据：

| Actions Variable | 当前值 |
| --- | --- |
| `PUBLIC_GISCUS_REPO` | `undefined-xhs/open-utd` |
| `PUBLIC_GISCUS_REPO_ID` | `R_kgDOVMBvww` |
| `PUBLIC_GISCUS_CATEGORY` | `Announcements` |
| `PUBLIC_GISCUS_CATEGORY_ID` | `DIC_kwDOVMBvw84DIl2E` |

迁移或使用独立评论仓库时，需由仓库管理员完成新仓库的 giscus App 授权：

1. 在目标公开评论仓库启用 **Discussions**，选择 Announcements 类型类别；可使用默认的 `Announcements`，或创建 `Journal Reviews`。
2. 从 [giscus](https://giscus.app/) 安装 GitHub App，授权该仓库，取得真实 repo/category ID。
3. 在网站源码仓库的 Actions **Variables** 设置 `PUBLIC_GISCUS_REPO`、`PUBLIC_GISCUS_REPO_ID`、`PUBLIC_GISCUS_CATEGORY`、`PUBLIC_GISCUS_CATEGORY_ID`。这些 ID 是公开配置，不是 Secrets。
4. 手动运行 `site.yml`，保持 `sync_metadata=false`。部署后分别打开两本期刊的评论页和两篇论文详情页，使用真实账户确认 Markdown 评论、回复、Reaction，以及 Discussion 的隔离。

映射使用 `specific`、`strict=1`，期刊为 `journal:<journal.public_id>`，论文为 `article:<article.public_id>`，可以使用同一 Discussion 类别。期刊评论从概览页移到独立评论页后仍使用原映射，已有讨论继续保留。第一次评论时由 giscus 按需创建讨论，不预建数万条空 Discussion。期刊改名、域名调整或重新构建不改变讨论归属。不要删除再创建生产期刊来改名，也不要随意更换公开 `public_id`。配置缺失时显示评论尚未启用的说明，不加载无效 iframe。

评论编辑器主题位于 `public/giscus-light.css`、`public/giscus-dark.css` 和共用的 `public/giscus-editor.css`，随网站切换明暗模式。它们通过 giscus 官方自定义主题接口加载，绝对地址由 `PUBLIC_SITE_URL` 与 `PUBLIC_BASE_PATH` 生成。giscus iframe 需要能访问并跨域加载该 CSS；本地预览地址可能受浏览器跨域或网络限制，最终主题效果应在部署后验证。

由 AI Agent 撰写的评论或回复必须包含原样标注 `written by AI Agent`，适用于期刊和论文讨论。

管理员通过 GitHub Discussions 删除、锁定和管理违规内容；以网站 `/guidelines/`、`/privacy/` 为准。公共纠错可提交 [GitHub Issue](https://github.com/undefined-xhs/open-utd/issues)，敏感信息和申诉请联系维护者，避免在公开评论中发布私人资料。

### 最新评论页

`/comments/` 汇总所有已收录期刊、论文讨论中的公开评论与回复，按**发表时间**倒序排列，每次显示 20 条。每条记录提供 GitHub 原评论永久链接及返回本站讨论区的入口；评论和作者名称保持原文。评论时间和快照更新时间按访问者浏览器所在时区显示（包含夏令时），并标注对应 GMT 偏移；日期格式随中英文界面切换。评论提交仍通过原讨论区进行。

完整构建和轻量评论更新均通过 [`scripts/fetch_comments.py`](scripts/fetch_comments.py) 只读访问 GitHub GraphQL API，读取当前 giscus 类别中标题精确匹配已知 `journal:<public_id>` / `article:<public_id>` 的讨论。脚本完整翻页获取评论和回复，老评论下的新回复也会出现；自动生成的 Discussion 开头正文不作为用户评论。已删除或被管理员折叠的评论正文不进入快照。每次重新采集会反映编辑、删除和管理操作，删除内容在网站上的消失时间取决于下次成功部署。

评论事件触发轻量刷新，每天 03:37 UTC（北京时间 11:37）补查一次；讨论删除、编辑、转移或更改类别也会触发检查。GitHub 可能延迟事件或计划运行，因此这不是实时动态流。这些运行不会触发 Crossref 同步或数据库提交。GitHub 的 [`discussion_comment` 事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#discussion_comment)使用默认分支代码；当前官方文档仍将 Discussions webhook 标为公开预览。

[`scripts/comment_refresh.py`](scripts/comment_refresh.py) 将新采集的完整评论与已发布 JSON 比较，仅忽略采集时间。同时核对 `data/site-build.json` 的源码及配置标识，避免 GitHub 用较新的评论运行替换排队任务时，跳过尚未发布的代码更新。两者均无变化且可复用缓存可用时，跳过 Node.js、依赖安装、缓存下载、构建、产物上传和部署。编辑、删除、新回复、作者或目标链接变化都会触发发布。页面显示的快照时间只在发布快照后更新，不代表最近一次“没有变化”的检查时间。网络请求失败会使运行失败，不会被当成“没有变化”。

评论有变化时，从 Actions 缓存恢复经过验证的站点归档，只替换 `dist/data/comments.json`。HTML 和搜索索引直接复用，不运行 Astro、Pagefind 或全站链接扫描。缓存键包含准确的源码提交及公开站点/giscus 配置，并在元数据提交后计算，不会回退使用另一源码版本。缓存缺失或过期时自动回退到经过完整校验的正常构建。归档不含评论 JSON，避免恢复缓存时带回已删除评论。两种流程共用生产部署的串行队列。GitHub 允许讨论事件读取缓存，但不允许保存；缓存写入因此仅由代码推送、定时和手动任务负责。每天补查或手动检查发现内容未变化时，仅查询缓存是否存在，不下载归档；缓存缺失则重建。可信任务修复缓存前，评论事件保留完整构建兜底。整个方案使用现有权限，保留 GitHub 默认缓存权限限制。

GitHub Pages 仍要求完整部署包，因此评论有变化时仍会上传并发布组装好的站点。Pages 产物保留 1 天；可复用归档使用单独的 Actions 缓存额度。源码/元数据更新、普通手动部署和缓存恢复仍需完整构建。手动刷新或验证评论流程时，运行 `site.yml`，设置 `comments_only=true`，关闭元数据选项即可。无需新增 Secret、外部服务或浏览器令牌。

访问令牌仅在 Actions 采集步骤通过 `GITHUB_TOKEN` 使用，声明 `discussions: read`，不写入 JSON、HTML 或浏览器。`public/data/comments.json` 是忽略的构建文件，包含公开评论纯文本、作者、时间、原链接和本站目标；不提交评论副本到 Git 历史。当前工作流使用源码仓库自带令牌，迁移时优先保持评论与源码在同一仓库；独立评论仓库需另行配置具有该仓库只读权限的令牌或 GitHub App。

API 错误、部分响应、分页异常或预算耗尽会阻止本次部署，保留已发布站点，不以空评论伪装成功。默认每轮最多 400 次请求，运行 Summary 显示请求数和 GraphQL 消耗；JSON 超过 5 MiB 预警、20 MiB 失败。达到预算时应拆分评论文件或引入增量存储，不能截断后声称完整。接口和权限依据 [GitHub Discussions GraphQL 文档](https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions)及[官方速率限制](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)。

## 数据维护与增加期刊

`data/journals.sqlite` 是受 Git 跟踪的正式快照；`.generated/`、`dist/`、`.local/` 是忽略的本地或构建文件。正式环境使用 `AJR_ENV=production`，演示始终使用独立 `AJR_DB_PATH`。不要以演示 seed、重建空库或回退 public ID 的方式修复正式数据。

生产数据的本地操作示例：

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

请将示例邮箱替换为真实地址再联网。日常更新使用 `sync --provider crossref --mode incremental`。`sync --help` 列出 `--journal`、`--from-date`、`--to-date`、`--dry-run` 和请求限制选项。正式持久化导入必须覆盖每本期刊 registry 中 `start_year` 的 1 月 1 日至当前 UTC 日期；不同范围只能使用 `--dry-run` 检查。`--limit` 也仅用于 dry run，避免截断分页或局部年份导入被误记为完整成功。如果要调整正式起始年份，请先审核并修改 registry，再执行完整历史导入。

注册表中的 `crossref_issns` 是可选的 Crossref 查询入口集合，用分号分隔；留空时查询该刊全部已登记 ISSN。该字段只能包含该行的真实 ISSN，不改变完整的期刊 ISSN 展示或文章归属校验。仅在有明确来源证据时限制查询入口，例如 JAE、JFE 的真实电子 ISSN 尚无 Crossref journal endpoint；其他查询错误仍会中止同步。修改实际查询集合会使水位失效，必须重新执行完整历史导入。

添加期刊时，先核实出版社和 Crossref ISSN，向 registry 增加一行，分配稳定 slug 并设置 `start_year`。提交注册表后，手动运行 `site.yml`，设置 `sync_metadata=true`、`initial_import=true`、`journal=new-journal-slug`，并将 `from_year` 改为该期刊的 `start_year`（或留空读取 registry）。这样只导入新增期刊，其他期刊的已有论文和公开 ID 保留。如果同一提交新增多本尚无数据的可见期刊，应将 `journal` 留空一并完成首次导入；不同期刊起始年份不一致时，`from_year` 也留空。

也可以在本地只导入新增期刊：

```bash
python scripts/cli.py seed --file data/journal_registry.csv
python scripts/cli.py sync --provider crossref --journal new-journal-slug --mode initial
python scripts/cli.py validate --production
python scripts/cli.py report --out data/sync-report.md
npm run check
npm run build
npm run test:site
```

本地导入确认后一起提交 registry、SQLite 和同步报告，再由 main push 部署。不要直接把新期刊交给每周增量任务，缺少水位会安全失败。已有期刊修改 `start_year` 或增加 ISSN 后，旧水位也会失效，要求重新执行该期刊的历史导入，避免漏掉新范围内的旧论文；历史数据及公开 ID 保留。日后扩展不需要修改页面模板；如果发现错误 ISSN、跨期刊 DOI 冲突或期次歧义，应先审核源记录。

## 数据质量与再使用

- 标题、作者顺序、DOI、卷期和日期来自源数据；只有年份的日期保持年份精度，不伪装成具体某天。
- 没有足够卷期信息的论文列入 Online First / Unassigned。缺失信息保留缺失状态，不推测补全。
- 同一规范化 DOI 至多一篇论文，记录更新保留 `public_id`；同名作者不在缺少可靠身份 ID 时自动合并。
- 网站不展示论文摘要、摘要展开区或缺失摘要提示，也不将摘要写入 HTML、JSON-LD 或搜索索引；论文详情直接连接讨论区。通过原始来源链接阅读摘要与全文。采集器不请求摘要字段，公开 SQLite 及导出仍保留严格的权利校验，拒绝保存未获授权的摘要。
- OpenAlex enrichment 目前不作为生产数据源启用，`OPENALEX_API_KEY` 只是预留配置；工作流不会请求它或产生额外 API 用量。
- MIT 许可覆盖本项目源码和原创文档，不授予第三方摘要、出版社内容或用户评论的权利。

## 备份、恢复与迁移

元数据同步、校验、测试和构建全部成功后，工作流才提交 DB 和报告，可用 Git 历史追溯。同步成功但后续构建失败时，只保留七天的恢复 artifact，不更新 main。维护前先停止并发本地写入，使用 SQLite backup 创建一致性备份：

```bash
mkdir -p .local
python -c 'import sqlite3; source=sqlite3.connect("data/journals.sqlite"); target=sqlite3.connect(".local/journals-backup.sqlite"); source.backup(target); target.close(); source.close()'
```

把重要备份另存到仓库外。恢复时先备份当前文件，再选择已知正常的提交：

```bash
git log --oneline -- data/journals.sqlite
git restore --source=KNOWN_GOOD_COMMIT -- data/journals.sqlite data/sync-report.md
AJR_ENV=production AJR_DB_PATH=data/journals.sqlite python scripts/cli.py validate --production
AJR_ENV=production AJR_DB_PATH=data/journals.sqlite npm run build
```

验证恢复结果后提交恢复变更并 push；不要重写共享 Git 历史。若恢复的是较旧快照，请确认期间没有需要保留的新公开 ID。Discussions 评论存放在 GitHub，恢复数据库不会删除评论，但改变期刊 public ID 会使嵌入映射失联。

数据库结构由 `data/migrations/` 管理，`db-init` 仅执行未应用迁移。新增迁移前备份；验证旧快照可升级，保留已有 ID、slug 和外键关系。

## 规模指标与故障排查

`python scripts/build_metrics.py --db data/journals.sqlite --dist dist --build-seconds 120` 会生成忽略的 `build-metrics.json` / `.md`。Actions 将报告写入运行 Summary，包含数据库体积、文章/期次/作者数量、HTML 页数、站点和 Pagefind 大小、构建耗时。

扩充期刊前可按需运行离线规模检查（最大一档不会在每次 PR 中执行）：

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

此命令重建本地 `.generated/` 和 `dist/`，使用独立的合成数据文件；完成后把 `AJR_DB_PATH` 改回需要预览的数据库并重新构建。

| 指标 | 工程预警 | 阻止提交 / 部署 |
| --- | --- | --- |
| SQLite | 50 MB | 95 MB，提前迁移快照存储 |
| 静态站点 | 500 MB | 900 MB，保留 Pages 容量余量 |
| Pagefind | 50 MB | 结合站点总量限制 |
| 构建耗时 | 5 分钟 | 作业有明确超时 |

这些是工程预算。[GitHub Pages 的官方限制](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)包括站点不超过 1 GB、部署超过 10 分钟超时。达到预算应分析索引/页面成本，再迁移存储或采用 API 方案，同时保留已有 URL 与评论 ID；不能静默丢弃论文页面。

| 现象 | 处理 |
| --- | --- |
| `initial_import` / watermark 错误 | 手动启用同步和历史导入，`journal` 选择需要补导的期刊，`from_year` 匹配其 registry 起始年份或留空 |
| Crossref 429 / 超时 / 分页失败 | 查看非敏感错误报告，稍后重跑；失败不会提交半成品快照 |
| Bot push rejected | 检查 Actions 写权限、main 并发更新和分支保护，不能 force push |
| main 禁止 Bot 直推 | 改用同步 PR → 人工审核合并 → main 部署流程，单独处理 Bot PR 测试触发；不要为此关闭保护 |
| 页面正常但 CSS / 搜索 404 | 检查 `PUBLIC_SITE_URL` 与 `PUBLIC_BASE_PATH`；项目 Pages 默认 `/open-utd` |
| 搜索在 dev 不工作 | 使用 `npm run build && npm run preview` |
| 定时任务长时间未运行 | 检查 Actions 是否启用；公开仓库 60 天无活动可能停用 schedule，计划任务也可能延迟 |
| 评论未启用 | 完成 giscus App 授权、Discussions 类别及四个公开变量，再重新部署 |

## 工程说明

数据流：Crossref → SQLite → 分片 JSON → Astro 静态 HTML → Pagefind → GitHub Pages。浏览器接收静态页面、搜索索引和公开评论 JSON，评论组件另由 giscus 加载；SQLite 不作为网站资源发布。无需自建应用服务器或用户数据库；真实评论功能需要 GitHub 账户。

使用 Node 24、Python 3.12 的 GitHub 托管 runner。官方 Actions 已核对并固定到具体 commit；升级时需重新检查版本与权限：[checkout](https://github.com/actions/checkout)、[setup-node](https://github.com/actions/setup-node)、[setup-python](https://github.com/actions/setup-python)、[configure-pages](https://github.com/actions/configure-pages)、[upload-pages-artifact](https://github.com/actions/upload-pages-artifact)、[deploy-pages](https://github.com/actions/deploy-pages)。Pages 配置使用 v6，上传与部署使用 v5；部分官方示例仍显示旧版，不照抄示例中的版本号。

更多设计背景见[技术路线](academic-journal-reviews-technical-roadmap-github-actions.md)。实现以可运行代码和本 README 为准。人工验收仍包括真实 giscus 账户的评论/回复测试，以及把当前 Crossref 覆盖情况与出版社最新期目录进行核对。
