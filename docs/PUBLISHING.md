# Publishing

The radar and blog are static files. Publish them on the lab LAN, behind a tunnel, or on any static host. The OpenCTI platform stays private in every option.

## Option A — LAN (current)

Caddy listens on `:80` and serves `site/dist`. Nothing else is required.

```
http://192.168.0.180
```

The page is fully usable offline except for CARTO map tiles and Google Fonts. To make it work with zero internet dependency, vendor both (see `docs/DASHBOARD.md`).

## Option B — real domain + Caddy

1. Create an `A` record (and `AAAA` if you have IPv6) for `radar.example.org` → your public IP.
2. Forward ports 80 and 443. **Do not forward 8443, 9443 or 8080.**
3. Edit `caddy/Caddyfile`:

   ```caddyfile
   radar.example.org {
       root * /srv/radar
       encode zstd gzip
       try_files {path} {path}/ {path}/index.html /404.html
       file_server
   }

   opencti.example.org {
       reverse_proxy opencti:8080
   }
   ```

4. Add `opencti.example.org` to DNS if you want remote analyst access.
5. Update `.env`: `OPENCTI_BASE_URL=https://opencti.example.org`, then `docker compose up -d opencti`.
6. Restart Caddy: `docker compose restart caddy`.

Caddy obtains and renews Let's Encrypt certificates automatically. Port 80 must remain reachable for the HTTP-01 challenge unless you use DNS-01.

If the site is behind Cloudflare, set SSL/TLS to **Full (strict)** and keep the origin certificate valid; do not use Flexible, or Caddy will redirect-loop.

## Option C — static host (GitHub Pages, Cloudflare Pages, Netlify)

The site has no server dependency. The only runtime data is `site/public/data/latest.json`, which is committed to the repository.

### GitHub Pages

`.github/workflows/pages.yml` builds `site/` and deploys `site/dist`. Enable Pages → Source: GitHub Actions. Every push to `main` publishes the blog and the last committed snapshot.

The radar will show the snapshot's `generated_at`, so readers can see when it was last refreshed. To update it, commit a fresh `latest.json`:

```bash
# on the VM after a collector run
cp ~/aruba-ti/site/public/data/latest.json /path/to/repo/site/public/data/latest.json
git add site/public/data/latest.json && git commit -m "data: refresh $(date -I)" && git push
```

If you want this automatic, add a deploy key with write access and a cron job on the VM:

```bash
# /etc/cron.d/aruba-radar-publish
17 */6 * * * styx cd /home/styx/aruba-ti && git add site/public/data/latest.json && git commit -m "data: refresh $(date -I\%H:\%M)" && git push
```

Review the repository's commit noise tolerance before enabling that.

### Cloudflare Pages

- Build command: `npm run build`
- Root directory: `site`
- Output directory: `dist`
- Node version: 20 or 22

Add a `_headers` file in `site/public/` if you want cache and security headers on Pages.

## Option D — tunnel instead of port-forward

Cloudflare Tunnel or Tailscale Funnel avoids opening inbound ports:

```bash
cloudflared tunnel --url http://localhost:80
```

For the OpenCTI UI, put Cloudflare Access (or Tailscale identity) in front. A public OpenCTI login page without MFA is not acceptable.

## Caching

Caddy sets no long cache headers by default. For a public deployment add:

```caddyfile
@assets path /_astro/*
header @assets Cache-Control "public, max-age=31536000, immutable"

@data path /data/*
header @data Cache-Control "no-store"
```

The snapshot fetch already appends a timestamp, so `no-store` on `/data/*` is belt and braces.

## SEO and feeds

- `astro.config.mjs` sets `site` from `SITE_URL` (default `https://radar.arubati.org`). Set it to the real origin so canonical URLs and the RSS feed are correct.
- `/rss.xml` lists briefings.
- `robots.txt` allows everything and points at a sitemap. Add `@astrojs/sitemap` if you want a generated sitemap; the current build does not emit one.
- Open Graph tags are in `Layout.astro`. Add an `og:image` when a social card exists.

## Social distribution

The weekly brief is designed to be pasted into Facebook, LinkedIn and WhatsApp. Keep the first paragraph self-contained: the platform link is often stripped by previews. Post the radar link separately from the analysis so the algorithm does not treat it as a link dump.

## What not to publish

- The OpenCTI UI without MFA and access control.
- MISP on a public port.
- Raw indicators in a format that auto-links (defang before publishing anywhere).
- Victim names or unverified attribution.
- Internal IPs, hostnames or tokens in screenshots.
