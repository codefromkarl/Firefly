# Design: CodeFromKarl Firefly Migration

## Boundaries

The new Firefly repository becomes a static presentation and writing site.
The existing full-stack CMS remains untouched as the rollback source. Only
public content and brand assets cross the boundary; comments, users, secrets,
database state, and admin capabilities do not.

## Source-to-Target Flow

```text
local Markdown                    live HTML + full-text RSS + sitemap
(ContextAtlas)                    (the other two published posts)
       \                                      /
        \                                    /
         v                                  v
               content audit + conversion
                          |
                          v
          src/content/posts/<slug>/index.md
                          |
                          v
       Astro content schema -> static routes -> Pagefind/RSS/Sitemap
```

The user explicitly approved this public-source reconstruction on 2026-07-29.
The existing repository Markdown remains authoritative for the ContextAtlas
post. Wrangler is installed locally from the Firefly lockfile, but no
Cloudflare authentication or D1 export is part of this run.

## Content Contract

Map CMS frontmatter to Firefly:

| CMS | Firefly |
| --- | --- |
| `title` | `title` |
| `summary` | `description` |
| `publishedAt` | `published` |
| `updatedAt` | `updated` |
| `status` | `draft` boolean |
| `tags` | `tags` |
| `slug` | content directory path |
| `readTimeInMinutes` | omit; Firefly recalculates |

Use `lang: zh_CN`, a manually reviewed category, `comment: false`, and
`pinned: false` unless current source evidence says otherwise. Retain relative
`./images/...` paths and adjacent image directories.

## Configuration

Personalization uses existing Firefly config boundaries:

- `siteConfig.ts`: identity, URL, page switches, conservative visual defaults.
- `profileConfig.ts`: Karl profile and social links.
- `navBarConfig.ts`: home/archive/lab/tech stack/about links only.
- `backgroundWallpaper.ts`: existing static home background; no remote video.
- `commentConfig.ts`: provider `none`.
- dedicated config modules: disable demo-only music, Live2D, dynamic, gallery,
  sponsor, anime, and effects without deleting reusable implementation code.
- `analyticsConfig.ts`: leave a safe Umami placeholder unless a public/current
  website ID is available without exposing a secret.

## Static Pages

- `src/content/spec/about.md` owns concise profile/about content.
- `/lab` and `/tech-stack` use dedicated Astro pages so their current URLs do
  not regress. They reuse `MainGridLayout` and Markdown presentation patterns.
- Friend links are disabled unless authoritative approved-link data becomes
  available; old `/friend-links` redirects to the chosen stable destination.

## Redirects

Add `public/_redirects` for Cloudflare static assets:

```text
/posts /archive/ 301
/friend-links /lab/ 301
/friends /lab/ 301
/about /lab/ 301
/post/* /posts/:splat/ 301
```

Exact route behavior will be validated in the built output and preview. Source
and destination ordering must not shadow `/posts/<slug>/`.

## Rollback

- No writes occur in the old CMS or Cloudflare services.
- The Firefly change remains local and uncommitted unless separately
  authorized.
- Demo content removal is recoverable from Git.
- Production cutover is a separate task requiring explicit deployment
  authorization and a verified preview.

## Key Risks

- Public HTML/RSS reconstruction can flatten headings, links, lists, or code.
- Firefly URLs derive from file paths; renaming a content directory breaks old
  slugs even if frontmatter still contains `slug`.
- Default Firefly identity is spread across content, config, public media, and
  navigation; a repository-wide stale-identity search is mandatory.
- `pnpm build` regenerates LQIP/font/search artifacts; generated changes must be
  reviewed rather than blindly retained.
