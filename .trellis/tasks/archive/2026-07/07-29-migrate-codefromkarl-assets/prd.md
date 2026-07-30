# Migrate CodeFromKarl assets to Firefly

## Goal

Replace the upstream Firefly demo site with a low-maintenance personal
CodeFromKarl site while preserving the public technical writing, personal
identity, stable links, and rollback safety of the existing blog.

## Requirements

### Content

- Migrate the three posts currently published at `https://codefromkarl.xyz`.
- Preserve each post's title, stable slug, publication date, last-updated date,
  description, tags, links, headings, code blocks, and local images.
- Store posts as `src/content/posts/<stable-slug>/index.md`; use Firefly-native
  frontmatter names and let Firefly derive reading time and navigation.
- Remove all upstream Firefly sample posts and sample dynamic entries.
- Do not migrate old comments, users, comment threads, moderation data, or
  email identities.

### Personal identity and presentation

- Set the canonical site URL to `https://codefromkarl.xyz`.
- Migrate the existing CodeFromKarl title, description, GitHub/email/RSS links,
  avatar, home background, and favicon assets.
- Replace upstream Firefly/CuteLeaf demo identity and links in active site
  configuration and public-facing content.
- Preserve the existing `/lab` and `/tech-stack` public information using
  Firefly-native static pages.

### Low-maintenance scope

- Disable comments and the guestbook.
- Disable dynamic posts, Bangumi, anime tracking, gallery, sponsor, Live2D,
  music, background video, and other demo-only modules in the active
  configuration/navigation.
- Keep articles, archive, Pagefind search, About/profile presentation, RSS,
  sitemap, dark mode, and Umami configuration support.
- Keep generic dormant Firefly feature implementations unless removing them is
  required to prevent public demo behavior; avoid an upstream-hostile rewrite.

### Compatibility and safety

- Preserve old article traffic with permanent redirects from
  `/post/<slug>` to `/posts/<slug>/`.
- Preserve or deliberately redirect existing `/posts`, `/friend-links`,
  `/lab`, `/tech-stack`, and `/about` routes.
- Do not modify or delete the old `flare-stack-blog`, D1 database, R2 bucket,
  Worker deployment, or domain routing.
- Do not commit, push, deploy, or mutate external services in this task.
- Keep private exports and database backups outside the Firefly Git tree.

## Acceptance Criteria

- [x] The production build contains exactly the three migrated published posts
      and no upstream demo posts or sample dynamics.
- [x] Each migrated post builds at `/posts/<original-slug>/` with preserved
      dates, description, tags, headings, links, code, and referenced images.
- [x] No old comment content or user data exists in the Firefly repository, and
      comment UI/guestbook are disabled.
- [x] Site title, canonical URL, profile, social links, avatar, background, and
      favicons identify CodeFromKarl rather than Firefly/CuteLeaf.
- [x] `/lab` and `/tech-stack` preserve the existing public information in
      static Firefly pages.
- [x] Unused high-maintenance/demo features are absent from active navigation
      and disabled by configuration.
- [x] A Cloudflare static-assets redirect maps `/post/*` to `/posts/:splat/`
      with HTTP 301 semantics.
- [x] `pnpm check`, `pnpm type-check`, and `pnpm build` pass.
- [x] A local production preview is inspected for home, archive, all posts,
      search, About/lab, tech stack, RSS, sitemap, mobile layout, and redirects.
- [x] The old blog repository and production services remain unchanged.

## Confirmed Facts

- The live sitemap contains three published posts.
- The current repository has an exact Markdown source only for
  `contextatlas-harness-engineering`.
- The two other published posts are available publicly through rendered HTML
  and RSS, but no native CMS export ZIP is present locally.
- The CMS native export includes Markdown, lossless TipTap JSON, tags, and
  referenced R2 images, but it is unavailable for this migration run.
- Current public branding assets are `avatar.png`, `home-bg.webp`, and favicon
  files under the old repository's `public/`.
- Existing `/about` redirects to `/lab`; the lab and tech-stack copy is stored
  in the old source/i18n messages.
- The user explicitly chose to remove old comments.

## Out of Scope

- Migrating authentication, D1, R2, post revisions, admin UI, or MCP.
- Importing old comments into Giscus, Twikoo, Waline, or another provider.
- Publishing the site or switching production traffic.
- Rebuilding Firefly's dormant optional modules.

## Source Decision

- On 2026-07-29, the user explicitly authorized public-source reconstruction
  (方案 2) after the native CMS export was blocked by GitHub OAuth.
- The existing repository Markdown remains authoritative for
  `contextatlas-harness-engineering`; live HTML, full-text RSS, and the sitemap
  are the approved sources for the other two published posts.
- Wrangler will be installed from the Firefly lockfile for future Cloudflare
  tooling, but this run does not authenticate to Cloudflare or export D1.
