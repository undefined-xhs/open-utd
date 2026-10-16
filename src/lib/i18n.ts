import { copy } from './copy';
import { zh } from './copy.zh';
export type Locale = 'en' | 'zh-CN';
const translations: Record<string,string> = {};
function collect(english: unknown, chinese: unknown): void {
  if(typeof english === 'string' && typeof chinese === 'string') {translations[english]=chinese;return;}
  if(english && chinese && typeof english === 'object' && typeof chinese === 'object') {
    for(const key of Object.keys(english)) collect((english as Record<string,unknown>)[key],(chinese as Record<string,unknown>)[key]);
  }
}
collect(copy,zh);
Object.assign(translations, {
  'Find a paper to discuss':'查找论文，参与讨论','Choose a journal':'选择期刊，交流经验','Journal reviews':'期刊评论','Browse archive':'浏览期刊档案','Browse by year':'按年份浏览','Select a year to see its issues.':'选择年份，再查看该年的期次。','Issues in this year':'本年期次','All years':'全部年份','All issues in this year':'本年全部期次','Unassigned articles':'暂未分配期次的论文','Article pagination':'论文分页','Previous page':'上一页','Next page':'下一页',
  'Home':'首页','Open UTD home':'Open UTD 首页','Main navigation':'主导航','Footer navigation':'页脚导航','Breadcrumb':'面包屑导航','Skip to content':'跳到正文','Switch color theme':'切换浅色 / 深色主题','Interface language':'界面语言','Use English interface':'使用英文界面',
  'Good research starts':'好的研究，','with':'始于','discovery.':'发现。','An open research collection':'开放的学术期刊目录','Ideas':'想法，','worth':'值得','exploring.':'探索。','Knowledge':'知识，','is a shared':'在交流中','pursuit.':'生长。','Research · Reflection · Discovery':'研究 · 思考 · 发现','Collection / 2006 onward':'收录范围 / 2006 年起','A place for research, and the people behind it.':'关注研究，也关注研究背后的人。','journals in the collection':'本收录期刊','indexed articles':'篇已索引论文','Browse & discover':'浏览与发现','Beyond the bibliography':'书目之外','About this project':'关于本项目','About the data':'了解数据',
  'Reviews & experiences':'评论与经验','Journal reviews & experiences':'期刊评论与经验','Reviews & submission experiences':'评论与投稿经验','Browse issues':'浏览期次','Journal information':'期刊信息','Collection window':'收录范围','Data & sources':'数据与来源','No unassigned articles in the current snapshot.':'当前快照中暂无未分配期次的论文。','Not recorded':'暂无记录','Year not recorded':'年份未记录','Authors not recorded':'作者未记录','Unspecified issue':'未注明期次','Journal':'期刊','Article':'论文','JOURNAL':'期刊','All issues':'全部期次','About this issue':'关于本期','Articles in this issue':'本期论文','Publication details':'发表信息','Read at original source':'前往原始来源阅读','Discuss this article':'讨论这篇论文','About this metadata':'了解这些元数据',
  'The publishing experience':'投稿与发表经历','Research in conversation':'在交流中理解研究','Article discussion':'论文讨论','Discuss the methods, findings, and questions raised by this paper. Share thoughtful comments, Markdown, and replies through GitHub.':'讨论这篇论文的方法、发现与问题。通过 GitHub 发表有依据的观点，支持 Markdown 与回复。','An independent discussion for this article will appear once the maintainer connects GitHub Discussions.':'维护者连接 GitHub Discussions 后，这篇论文的独立讨论区会显示在这里。','Enable JavaScript to use the GitHub discussion.':'请启用 JavaScript 后使用 GitHub 讨论区。',
  'Find a journal':'查找期刊','Filter by academic field':'按研究领域筛选','Filter issues by year':'按年份筛选期次','Search the catalog':'搜索目录','Search the collection':'搜索期刊与论文','Filter by journal':'按期刊筛选','Filter by publication year':'按发表年份筛选','Filter by content type':'按内容类型筛选','Search results':'搜索结果','Search requires JavaScript. You can still':'搜索需要启用 JavaScript，你仍可','browse every journal and issue':'浏览全部期刊与期次',
  'Page not found':'页面不存在','404 / Page not found':'404 / 页面不存在','A little outside':'这页暂时不在','the collection.':'收录范围内。','This page is not available. Browse the journals or search the catalog to find your way.':'此页面暂不可用。请浏览期刊或搜索目录，继续查找所需内容。','Browse journals':'浏览期刊',
  'Contact & references':'联系与参考资料','Project issues':'项目问题反馈','Contact the maintainer':'联系维护者','Crossref REST API':'Crossref REST API','Crossref metadata reuse':'Crossref 元数据使用说明','OpenAlex documentation':'OpenAlex 文档','GitHub privacy statement':'GitHub 隐私声明','giscus privacy policy':'giscus 隐私政策',
});
export function currentLocale(): Locale {
  return typeof document !== 'undefined' && document.documentElement.lang === 'zh-CN' ? 'zh-CN' : 'en';
}
export function translate(text: string, locale: Locale = currentLocale()): string {
  if(locale === 'en')return text;
  if(translations[text])return translations[text];
  const leadingArrow=text.match(/^([↗→←↓])\s*(.*?)$/);
  if(leadingArrow && translations[leadingArrow[2]])return `${leadingArrow[1]} ${translations[leadingArrow[2]]}`;
  const arrow = text.match(/^(.*?)\s*([↗→←↓])$/);
  if(arrow && translations[arrow[1]])return `${translations[arrow[1]]} ${arrow[2]}`;
  return text
    .replace(/^([\d,]+) articles$/,'$1 篇论文')
    .replace(/^([\d,]+) issues$/,'$1 个期次')
    .replace(/^Page (\d+) of (\d+)$/,'第 $1 页，共 $2 页')
    .replace(/^(\d{4}) onward$/,'$1 年起')
    .replace(/^Volume (.+?) · Issue (.+)$/,'第 $1 卷 · 第 $2 期')
    .replace(/^Volume (.+)$/,'第 $1 卷')
    .replace(/^Issue (.+)$/,'第 $1 期')
    .replace(/^pp\. (.+)$/,'第 $1 页')
    .replace(/^Explore ideas across ([\d,]+) articles and ([\d,]+) journals\.$/,'探索 $2 本期刊、$1 篇论文中的研究与想法。');
}
export function localizedDate(value:string, locale:Locale=currentLocale()): string {
  if(!value)return translate('Not recorded',locale);
  if(/^\d{4}$/.test(value))return value;
  const monthOnly=/^\d{4}-\d{2}$/.test(value);
  const parsed=new Date(monthOnly ? `${value}-01T00:00:00Z` : value.length===10 ? `${value}T00:00:00Z` : value);
  if(Number.isNaN(parsed.getTime()))return value;
  return new Intl.DateTimeFormat(locale,{year:'numeric',month:monthOnly?'long':'short',...(monthOnly?{}:{day:'numeric' as const}),timeZone:'UTC'}).format(parsed);
}
const originalText = new WeakMap<Text,string>();
const originalAttributes = new WeakMap<Element,Map<string,string>>();
const protectedSelector = '[data-original], [data-ui-dynamic], script, style, noscript, code, pre, textarea, .giscus';
/** Translate only authored UI; all source metadata is explicitly protected with data-original. */
export function localizeUi(root:Element=document.body, locale:Locale=currentLocale()): void {
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let node:Node|null;
  while((node=walker.nextNode())) {
    const textNode=node as Text;
    if(textNode.parentElement?.closest(protectedSelector) || textNode.parentElement?.closest('time[datetime]'))continue;
    const english=originalText.get(textNode) ?? textNode.data;
    originalText.set(textNode,english);
    const trimmed=english.trim();
    if(trimmed)textNode.data=english.replace(trimmed,translate(trimmed,locale));
  }
  root.querySelectorAll('[aria-label],[title],[placeholder]').forEach(element=>{
    if(element.closest('[data-original],script,style,noscript,code,pre,textarea,.giscus'))return;
    const saved=originalAttributes.get(element) ?? new Map<string,string>();
    for(const attr of ['aria-label','title','placeholder']) {
      const value=saved.get(attr) ?? element.getAttribute(attr);
      if(value!==null){saved.set(attr,value);element.setAttribute(attr,translate(value,locale));}
    }
    originalAttributes.set(element,saved);
  });
  root.querySelectorAll<HTMLTimeElement>('time[datetime]').forEach(element=>{element.textContent=localizedDate(element.dateTime,locale);});
  root.querySelectorAll<HTMLElement>('[data-snapshot]').forEach(element=>{
    const {journals,issues,articles,updated}=JSON.parse(element.dataset.snapshot!) as {journals:number;issues:number;articles:number;updated:string};
    const n=(value:number)=>value.toLocaleString(locale);
    element.textContent=locale==='zh-CN' ? `当前快照：${n(journals)} 本期刊 · ${n(issues)} 个期次 · ${n(articles)} 篇论文。元数据更新时间：${localizedDate(updated,locale)}。` : `Current snapshot: ${n(journals)} journals · ${n(issues)} issues · ${n(articles)} articles. Metadata updated: ${localizedDate(updated,locale)}.`;
  });
}
export function setLocale(locale:Locale): void {
  document.documentElement.lang=locale;
  const title=document.querySelector<HTMLTitleElement>('title[data-ui-title]');
  if(title && !title.hasAttribute('data-original-title')) {
    const english=title.dataset.uiTitle || '';
    document.title=english===copy.name ? `${copy.name} — ${translate(copy.fullName,locale)}` : `${translate(english,locale)} — ${copy.name}`;
  }
  try{localStorage.setItem('open-utd-language',locale);}catch{/* Storage may be disabled. */}
  localizeUi();
  document.querySelectorAll<HTMLButtonElement>('[data-set-language]').forEach(button=>{button.setAttribute('aria-pressed',String(button.dataset.setLanguage===locale));});
  document.dispatchEvent(new CustomEvent('open-utd:language',{detail:{locale}}));
}
