import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import { loadEnv } from 'vite';

const env = { ...loadEnv(process.env.NODE_ENV || 'production', process.cwd(), ''), ...process.env };
const [owner, repository] = (env.GITHUB_REPOSITORY || 'undefined-xhs/open-utd').split('/');
const site = env.PUBLIC_SITE_URL || `https://${owner}.github.io`;
const inferredBase = env.GITHUB_ACTIONS && repository !== `${owner}.github.io` ? `/${repository}/` : '/';
const base = `/${(env.PUBLIC_BASE_PATH || inferredBase).replace(/^\/+|\/+$/g, '')}/`.replace('//', '/');

export default defineConfig({
  site,
  base,
  output: 'static',
  trailingSlash: 'always',
  integrations: [sitemap({ filter: (url) => !url.endsWith('/404/') && !url.endsWith('/search/') })],
  vite: { plugins: [tailwindcss()] },
  build: { format: 'directory' },
});
