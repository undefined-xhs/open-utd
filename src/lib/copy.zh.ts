import { copy } from './copy';
type Translation<T> = T extends string ? string : T extends readonly (infer U)[] ? readonly Translation<U>[] : { [K in keyof T]: Translation<T[K]> };
export const zh: Translation<typeof copy> = {
  name:'Open UTD', fullName:'学术期刊评论',
  description:'浏览学术期刊、发现研究成果，分享投稿经历。一个独立、开放的学术元数据目录。',
  nav:{journals:'期刊评论',comments:'最新评论',search:'搜索',about:'关于',github:'GitHub'},
  home:{eyebrow:'从这里，走近学术研究',title:'交流投稿经验。\n讨论学术研究。',lead:'按期刊交流投稿经历，找到感兴趣的论文，加入它的独立讨论。',search:'通过标题、作者或 DOI 查找论文',collection:'期刊目录',collectionNote:'收录 UT Dallas 商学院研究排名使用的 24 本期刊，时间从 2006 年开始。',browse:'浏览全部期刊',scope:'收录范围：2006 年起',update:'元数据每周更新',independent:'独立维护，开放源代码',recent:'最近更新',recentNote:'查看各期刊最近一次元数据同步。',note:'找到研究，也读懂背景。',noteBody:'在这里查找论文，讨论研究，也交流投稿经验。通过原始来源阅读论文，在期刊或论文的独立讨论区分享你的看法。'},
  common:{journals:'期刊',articles:'论文',issues:'期次',authors:'作者',publisher:'出版机构',field:'研究领域',issn:'ISSN',source:'元数据来源',updated:'元数据更新时间',browse:'浏览期刊',official:'出版机构网站',empty:'暂无记录。',back:'返回期刊目录',view:'查看论文',doi:'DOI',online:'在线优先 / 暂未分配期次',onlineNote:'这些记录尚未确认所属期次，可能是在线优先发表，也可能只是期次元数据不完整。',coverage:'收录情况取决于来源元数据，可能存在遗漏。',demo:'演示 / 合成数据 — 所有示例期刊与论文均为虚构。',countSuffix:'篇论文',noIssues:'尚未导入已分配期次的记录。',notSynced:'等待首次导入元数据',pages:'页码',published:'发表日期',loading:'正在加载…'},
  journal:{title:'聊聊投稿与发表。',intro:'选择一本期刊，阅读或分享投稿经验。也可以浏览期刊档案，找到论文并加入学术讨论。',filter:'查找期刊',all:'全部研究领域',noResults:'没有符合筛选条件的期刊。',archive:'历年期次',reviews:'期刊评论与投稿经验',reviewIntro:'欢迎分享亲身投稿经历，或提出建设性的问题。这里的内容是个人经验，不是官方期刊评价。',aiDisclosure:'由 AI Agent 撰写的评论须注明：written by AI Agent。',commentsOff:'评论功能尚未配置。',commentsOffBody:'维护者连接 GitHub Discussions 后，期刊讨论区会显示在这里。',guidelines:'阅读讨论规范',updated:'最近同步',contents:'本页目录',year:'全部年份'},
  search:{title:'让好奇心带路。',intro:'在目录中搜索期刊名称、论文标题、作者和 DOI。',placeholder:'论文标题、作者、期刊或 DOI',button:'搜索',journal:'全部期刊',year:'全部年份',type:'全部内容',start:'输入关键词，或选择筛选条件开始浏览。',empty:'没有找到匹配结果。请减少关键词或重置筛选条件。',failed:'搜索暂时无法加载，请重试。本地开发时，请先构建网站，再用 npm run preview 启用搜索索引。',more:'加载更多结果',loading:'正在搜索目录…',result:'条结果',reset:'重置筛选'},
  comments:{title:'最新评论',intro:'看看期刊和论文讨论中的最新评论与回复。',schedule:'评论变化后自动更新，每天补查一次，可能有几分钟延迟。',loading:'正在加载最新评论…',empty:'还没有评论。欢迎到期刊或论文页面发起讨论。',pending:'评论正在等待首次同步。',failed:'评论暂时无法加载，请重试。',retry:'重试',more:'加载更多评论',synced:'快照更新时间',journal:'期刊评论',article:'论文讨论',reply:'回复',deleted:'已删除的账户',source:'在 GitHub 查看评论',join:'参与讨论',noText:'这条评论没有可显示的文字预览。',noScript:'请启用 JavaScript 加载最新评论，或前往 GitHub 阅读。',github:'打开 GitHub Discussions',list:'最新评论与回复'},
  analytics:{
    title:'网站访问统计',intro:'公开展示 Open UTD 的页面浏览量、每日趋势、国家和地区及热门页面。',
    privacy:'仅公开汇总统计，不展示访客身份、IP 地址或个人浏览记录。',
    loading:'正在加载网站访问统计…',pending:'访问统计正在等待首次成功同步。',failed:'访问统计暂时无法加载，请重试。',retry:'重试',
    noScript:'请启用 JavaScript 加载网站访问统计。',seven:'近 7 天',thirty:'近 30 天',period:'统计周期',views:'页面浏览量',visits:'访问次数',visitsNote:'访问次数不等于去重人数。',synced:'快照更新时间',range:'统计日期',
    daily:'每日浏览量',details:'查看每日数据',date:'日期（UTC）',countries:'国家和地区',pages:'热门页面',country:'国家或地区',page:'页面',unknown:'未知',home:'首页',
    empty:'此统计周期内没有记录到页面浏览。',noCountries:'此统计周期暂无国家和地区明细。',noPages:'此统计周期暂无页面明细。',
    utc:'统计覆盖最近 7 或 30 个完整 UTC 日，不含当天。更新时间按你的浏览器时区显示。',
    history:'数据从启用访问统计时开始采集，无法补回接入前的访问记录。新接入的网站尚未积累完整的 7 天或 30 天历史。',
    limits:'数据来自 Cloudflare Web Analytics，可能经过估算或存在遗漏。浏览量不等于独立访客人数，也可能包含执行 JavaScript 的自动化访问。浏览器拦截和网络错误可能导致漏计。排行最多显示前 10 项，其合计可能小于总浏览量。',
    source:'来源：Cloudflare Web Analytics',stale:'此快照已超过 48 小时未更新，可能未包含近期访问。',privacyLink:'阅读隐私说明',
  },
  footer:{analytics:'网站访问统计',tagline:'发现研究，分享经验。',source:'开放元数据，追溯原始来源，保留独立观点。',sources:'数据来源',guidelines:'讨论规范',privacy:'隐私说明',issue:'报告错误',disclaimer:'独立项目，与 UT Dallas、INFORMS 及所列期刊无隶属关系。'},
  policy:{
    about:{title:'一个小而开放的学术交流空间。',eyebrow:'关于 Open UTD',intro:'Open UTD 将期刊元数据与学术交流汇集在一个易读、可搜索的目录中。',sections:[
      ['这里收录什么','收录 UT Dallas 商学院研究排名使用的 24 本期刊，目标范围从 2006 年开始。期刊页面连接历年期次、论文及投稿经验讨论，每篇论文也有独立讨论区。未来可通过期刊注册表扩展收录范围。'],
      ['独立维护','本项目独立且开源，与 UT Dallas、INFORMS 或所列期刊无隶属关系。收录不代表排名或推荐，个人投稿经历也不等于具有代表性的统计结果。'],
      ['可以追溯的目录','论文记录主要来自 Crossref，每条记录都链接到原始来源，并显示元数据更新时间。收录情况取决于出版机构提交的数据，可能有遗漏、延迟或分类错误。本站不托管论文全文。'],
      ['公开开发与维护','网站由带版本记录的 SQLite 数据快照生成，通过 GitHub Actions 发布。搜索在浏览器中运行。期刊和论文评论保存在 GitHub Discussions，稳定的公开标识让讨论在网站更新后仍然保持关联。']
    ]},
    'data-sources':{title:'每条记录，都有来处。',eyebrow:'数据与收录范围',intro:'了解书目元数据的来源、更新时间与局限，才能更好地使用它。',sections:[
      ['主要来源：Crossref','我们通过 Crossref REST API 获取 journal-article 记录，并以人工维护的 ISSN 注册表限定收录范围。标题、作者顺序、DOI、日期和期次关系均来自出版机构提交的数据。元数据计划每周更新；同步成功不意味着已完整覆盖出版机构的目录。'],
      ['从 2006 年开始收录','目标范围从 2006 年起，延伸至来源当前提供的最新记录。“在线优先 / 暂未分配期次”包含尚不能明确分配期次的记录，不应被理解为只收录待刊论文。发表日期保留来源提供的精度。'],
      ['前往原始来源阅读摘要','本站不展示论文摘要，也不将摘要纳入搜索索引。论文页面提供书目信息与讨论区；摘要和论文原文请通过页面上的原始来源链接阅读。'],
      ['可选的数据补充','OpenAlex 数据补充默认关闭，仅在配置后启用。补充的身份或元数据必须通过可靠标识进行匹配。同名作者不会被自动视为同一个人。'],
      ['缺失与纠错','期次、ORCID 或日期缺失，表示该字段不可获取或无法安全展示。如发现错误，请通过项目 GitHub Issues 提供论文网址、DOI 和相关依据。维护者审核后再更新目录。']
    ]},
    guidelines:{title:'让下一次交流更有帮助。',eyebrow:'讨论规范',intro:'期刊讨论欢迎有分寸的投稿经验，论文讨论欢迎认真、有依据的学术交流。',sections:[
      ['分享亲身经历与研究见解','期刊讨论欢迎投稿时间线、编辑沟通、修改流程和建设性建议。论文讨论欢迎围绕方法、发现、解释和可重复性提供有依据的观点。适当补充大致日期和背景，并区分亲身经历、个人解读与可核实的事实。'],
      ['标明 AI Agent 撰写的内容','如果评论或回复由 AI Agent 撰写，须在该条内容中明确注明“written by AI Agent”，保留这段英文原文。此要求同时适用于期刊和论文讨论。'],
      ['尊重他人与保密要求','请勿发布人身攻击、威胁、仇恨、垃圾广告、私人联系方式、保密稿件，或能够识别匿名审稿人的信息。避免无法证实的严重指控，也不要分享无权披露的材料。'],
      ['不要把个例当作统计','个人经历不是官方录用率、期刊排名或具有代表性的审稿时长估计。请说明具体投稿背景，避免据此推断所有作者或编辑的情况。'],
      ['公开交流与内容管理','评论、回复、Markdown 和表情回应由 GitHub Discussions 提供。维护者可以移除违规内容或锁定讨论，GitHub 的相关政策也同样适用。如需举报或申诉，请附上讨论链接联系维护者。']
    ]},
    privacy:{title:'了解你正在分享什么。',eyebrow:'隐私说明',intro:'浏览与搜索目录不需要注册账户。',sections:[
      ['浏览与搜索','本站为静态网站，不建立用户账户，也不使用广告追踪工具。搜索使用下载到浏览器的 Pagefind 索引。GitHub Pages 等托管及网络服务商可能依据各自政策处理请求日志。'],
      ['网站访问统计','启用后，Cloudflare Web Analytics 提供页面浏览量、来源网站、国家、设备、浏览器及页面性能的汇总统计。它不使用 Cookie、本地存储或指纹技术追踪个人访客，统计报告不会显示访客的姓名或 GitHub 账户。公开的 /analytics/ 页面展示按日、国家或地区、页面汇总的统计，不公开个人访问明细。Cloudflare 按其隐私政策处理统计数据。'],
      ['你的显示偏好','你选择的浅色或深色主题及界面语言保存在当前浏览器的本地存储中，不会据此建立个人档案。清除站点数据即可移除这些偏好。'],
      ['评论是公开的','启用评论后，期刊和论文页面会从 giscus.app 加载 giscus，并嵌入 GitHub Discussions 界面。这些第三方会收到连接信息，并可能按其政策处理 Cookie 或登录状态。发言需要 GitHub 账户及授权。你的 GitHub 用户名、评论、回复和表情回应均为公开内容，本站不保证匿名。'],
      ['管理你的内容','你可以通过 GitHub 管理账户和已发布内容。如需内容管理或纠错，请联系项目维护者。在本站移除内容，并不能保证第三方已保存的副本也被删除。']
    ]}
  }
};
