# Source Inventory

## Live site

- Canonical domain: `https://codefromkarl.xyz`
- Public article prefix: `/post/`
- Published posts in the 2026-07-29 sitemap:
  - `contextatlas-harness-engineering`
  - `vibecoding升级之路`
  - `我是如何在两个月之内从-0-开始成长为一个合格的-ai-全栈开发`
- Public pages: `/`, `/posts`, `/lab`, `/tech-stack`, `/friend-links`.

## Old repository

- Exact Markdown available:
  `contextatlas-harness-engineering.md`.
- Other author-written candidate draft:
  `docs/如何一天之内开发并且上线一个旅游智能体.md`; it is not in the
  current live sitemap and is therefore not part of the three-post production
  migration.
- Branding assets:
  `public/images/avatar.png`, `public/images/home-bg.webp`, and root favicon
  files.
- Identity fallback:
  `src/blog.config.ts`.
- Lab and tech-stack copy:
  `messages/zh.json` plus theme page implementations.

## CMS export behavior

The native export writes:

```text
posts/<slug>/index.md
posts/<slug>/content.json
posts/<slug>/images/<R2 key>
tags.json
manifest.json
```

Markdown image sources are rewritten to `./images/<key>`. The export includes
referenced article images, not the entire R2 media library.

## Admin OAuth blocker

On 2026-07-29, a no-redirect request to the live Better Auth social-sign-in
endpoint generated:

- GitHub client ID: `Ov23liOVclBczuurzabr`
- Redirect URI:
  `https://codefromkarl.xyz/api/auth/callback/github`

The GitHub authorization page rejected that URI as not associated with the
application. The live application and source agree on the intended callback,
so the GitHub OAuth App registration for that client ID, or the deployed
`GITHUB_CLIENT_ID` secret selecting the app, must be corrected before the user
can enter the admin export UI through GitHub login.

## Alternative export availability

The local old-blog checkout currently has no installed Wrangler binary, no
Cloudflare/D1 environment variables, and no project-level `wrangler.jsonc`.
Therefore a direct remote D1 export cannot be performed from this machine
without the user's Cloudflare login or a scoped API token.

Two alternatives remain:

1. Export the remote D1 database from the Cloudflare dashboard/CLI and provide
   the SQL outside the Git tree. This preserves TipTap JSON and metadata but the
   SQL also contains private tables, so conversion must select only posts/tags.
2. Reconstruct published content from public sources. The ContextAtlas post has
   an exact local Markdown source; the other two posts are available in live
   HTML and full-text RSS. The sitemap supplies canonical slugs and update
   dates. Public page inspection found no inline article images, reducing the
   remaining reconstruction risk to Markdown structure and link fidelity.

## Approved source for this run

On 2026-07-29, the user selected alternative 2. The Firefly project already
declares a lockfile-pinned Wrangler dependency, which will be installed for
future Cloudflare tooling. Installing Wrangler does not grant Cloudflare
credentials and this migration will not authenticate to Cloudflare, export D1,
or modify any remote service.

## Firefly target

- Post content schema: `src/content.config.ts`.
- Route ID: derived from content path and rendered under `/posts/<id>/`.
- Site feature configuration: `src/config/`.
- Static source images: `src/assets/`; directly served assets: `public/`.
- Static compatibility redirects: `public/_redirects`.

## Data intentionally excluded

- Comments and moderation metadata.
- Better Auth users and email addresses.
- D1/R2 private backups.
- Admin, revisions, workflows, MCP, and OAuth state.

## Final validation evidence

- Wrangler installed locally at version `4.114.0`; no Cloudflare login, token,
  D1 export, remote write, deployment, or domain change occurred.
- The final static build contains exactly three post routes. A semantic
  comparison between live HTML and built HTML matched headings, link targets,
  list items, paragraphs, and blockquotes for all three posts.
- Cloudflare Pages local runtime results:
  - enabled pages, all three posts, RSS, sitemap, and search: HTTP 200;
  - `/post/*`, `/posts`, `/friend-links`, and `/about`: expected HTTP 301;
  - dynamic, friends, guestbook, gallery, anime, Bangumi, sponsor, and dynamic
    API routes: HTTP 404.
- The sitemap contains the three canonical post URLs and no disabled feature
  or redirect-source URLs.
- Desktop previews covered home, archive, all posts, search, lab, and tech
  stack; the home page was also inspected at `390x844`.
- `pnpm check`, `pnpm type-check`, `pnpm build`, targeted Biome checks, and
  `git diff --check` passed. Build warnings are limited to the expected empty
  dynamic collection, the existing bundle-size advisory, and Chinese Pagefind
  stemming support.
