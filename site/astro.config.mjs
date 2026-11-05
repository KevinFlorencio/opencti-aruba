import { defineConfig } from 'astro/config';

// The site is fully static so it can be published on GitHub Pages, Cloudflare
// Pages, Netlify or any static host without exposing OpenCTI itself.
export default defineConfig({
  site: process.env.SITE_URL || 'https://radar.arubati.org',
  base: process.env.BASE_PATH || '/',
  output: 'static',
  build: {
    inlineStylesheets: 'auto',
  },
  vite: {
    build: {
      chunkSizeWarningLimit: 1600,
    },
  },
});
