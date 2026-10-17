export interface AnalyticsDay { date:string; page_views:number; visits:number|null; }
export interface AnalyticsPeriod {
  start_date:string; end_date:string; page_views:number; visits:number|null;
  daily:AnalyticsDay[];
  countries:{country_code:string;page_views:number}[];
  pages:{path:string;page_views:number}[];
}
export interface AnalyticsSnapshot {
  schema_version:1; source:'Cloudflare Web Analytics'; status:'ready'|'unavailable';
  updated_at:string|null; timezone:'UTC'; periods:Partial<Record<'7'|'30',AnalyticsPeriod>>;
}

function record(value:unknown):Record<string,unknown> {
  if(!value || typeof value!=='object' || Array.isArray(value))throw new Error('Invalid analytics object');
  return value as Record<string,unknown>;
}
function fields(value:Record<string,unknown>,keys:string[]):void {
  // Public snapshots must contain only these aggregates, including in future exports.
  if(Object.keys(value).length!==keys.length || !keys.every(key=>Object.hasOwn(value,key)))throw new Error('Unexpected analytics fields');
}
function count(value:unknown):value is number {return typeof value==='number' && Number.isSafeInteger(value) && value>=0;}
function visits(value:unknown):boolean {return value===null || count(value);}
function date(value:unknown):value is string {
  return typeof value==='string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0,10)===value;
}
/** Only canonical, public site routes can become links; no queries or arbitrary URLs. */
export function safeAnalyticsPath(value:unknown):value is string {
  return typeof value==='string' && /^\/(?:|(?:journals|comments|analytics|search|about|data-sources|guidelines|privacy)\/|articles\/[A-Za-z0-9_-]+\/|journals\/[a-z0-9][a-z0-9-]*\/(?:|reviews\/|years\/(?:\d{4}|undated)\/|issues\/[A-Za-z0-9_-]+\/|online-first\/[1-9]\d*\/))$/.test(value);
}
export function parseAnalytics(value:unknown):AnalyticsSnapshot {
  const data=record(value);
  fields(data,['schema_version','source','status','updated_at','timezone','periods']);
  if(data.schema_version!==1 || data.source!=='Cloudflare Web Analytics' || data.timezone!=='UTC' || !['ready','unavailable'].includes(String(data.status)))throw new Error('Invalid analytics snapshot');
  const periods=record(data.periods);
  if(data.status==='unavailable') {
    if(data.updated_at!==null || Object.keys(periods).length)throw new Error('Unavailable analytics must not contain counts');
    return data as unknown as AnalyticsSnapshot;
  }
  if(typeof data.updated_at!=='string' || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|\+00:00)$/.test(data.updated_at) || Number.isNaN(Date.parse(data.updated_at)))throw new Error('Invalid analytics update time');
  fields(periods,['7','30']);
  for(const key of ['7','30'] as const) {
    const period=record(periods[key]);
    fields(period,['start_date','end_date','page_views','visits','daily','countries','pages']);
    if(!date(period.start_date) || !date(period.end_date) || !count(period.page_views) || !visits(period.visits) || !Array.isArray(period.daily) || period.daily.length!==Number(key) || !Array.isArray(period.countries) || period.countries.length>10 || !Array.isArray(period.pages) || period.pages.length>10)throw new Error('Invalid analytics period');
    for(const [index,raw] of period.daily.entries()) {
      const day=record(raw);
      fields(day,['date','page_views','visits']);
      const expected=new Date(Date.parse(`${period.start_date}T00:00:00Z`)+index*86400000).toISOString().slice(0,10);
      if(day.date!==expected || !count(day.page_views) || !visits(day.visits))throw new Error('Invalid analytics day');
    }
    if(record(period.daily.at(-1)).date!==period.end_date)throw new Error('Invalid analytics range');
    if(period.daily.reduce((sum,day)=>sum+Number(record(day).page_views),0)!==period.page_views)throw new Error('Inconsistent analytics total');
    for(const raw of period.countries) {
      const country=record(raw);fields(country,['country_code','page_views']);
      if(typeof country.country_code!=='string' || !/^[A-Z]{2}$/.test(country.country_code) || !count(country.page_views))throw new Error('Invalid analytics country');
    }
    for(const raw of period.pages) {
      const page=record(raw);fields(page,['path','page_views']);
      if(!safeAnalyticsPath(page.path) || !count(page.page_views))throw new Error('Invalid analytics page');
    }
  }
  return data as unknown as AnalyticsSnapshot;
}
