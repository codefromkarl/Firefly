# Content and Configuration

## Content Collections

`src/content.config.ts` defines three collections:

- `posts`: Markdown/MDX articles under `src/content/posts/`;
- `spec`: special Markdown pages such as about, friends, and guestbook;
- `dynamic`: short Markdown entries under `src/content/dynamic/`.

Post URLs come from the content entry ID/file path, not merely a `slug`
frontmatter field. For a stable article URL, use:

```text
src/content/posts/<stable-slug>/index.md
```

and keep adjacent article images in that directory. Renaming the path changes
the generated `/posts/<stable-slug>/` URL and requires a permanent redirect.

## Post Frontmatter

The schema requires `title` and `published`; other fields receive defaults.
Use schema-native names:

- `description`, not `summary`;
- `published` and optional `updated`, not `publishedAt`/`updatedAt`;
- `draft: true` for unpublished content;
- one `category` plus an array of `tags`;
- `comment: false` when a post must not mount the configured comment provider.

Do not add navigation-only fields such as `prevSlug` manually. They are derived
by `src/utils/content-utils.ts`.

## Images

- Relative Markdown images may live beside the post, for example
  `./images/diagram.webp`.
- Use `src/assets/` for site images that should be optimized by Astro.
- Use `public/` for stable, directly served paths such as favicons, redirects,
  robots files, or vendor assets.
- Remote images bypass local optimization and may require referrer policy
  handling configured in `siteConfig.imageOptimization`.

References: `src/components/common/ImageWrapper.astro`,
`src/components/common/CoverImage.astro`, and `src/utils/image-utils.ts`.

## Site Configuration

All user-editable site behavior is split by feature in `src/config/`.

- Update the matching type in `src/types/` when a config shape changes.
- Prefer imports from `@/config`, whose barrel is `src/config/index.ts`.
- Keep site identity and core page switches in `siteConfig.ts`; do not merge
  unrelated feature configuration into it.
- Keep profile, navigation, analytics, comments, wallpapers, effects, music,
  gallery, and friend links in their dedicated modules.
- Search all consumers before changing a shared config value or enum.

Configuration is bundled into the static site. Never place secrets in these
files.

## Personalization Checklist

When creating a personal site from the template, search for and replace or
remove all upstream demo identity:

```bash
rg -n "Firefly|CuteLeaf|cuteleaf|xiaye|夏夜流萤" src public
```

Review at least:

- `siteConfig.ts`, `profileConfig.ts`, `navBarConfig.ts`;
- `backgroundWallpaper.ts`, `friendsConfig.ts`, `commentConfig.ts`;
- analytics, license, sponsor, music, gallery, anime, and Live2D configs;
- sample posts, dynamic entries, public media, and source images.

Disable unused features at both the page/config level and navigation/sidebar
entry points when applicable.

## Scenario: Disable a Feature on Static Hosting

### 1. Scope / Trigger

This contract applies when a feature page is disabled for a static Firefly
deployment. A `siteConfig.pages.* = false` guard can hide navigation and render
an empty redirect response during the Astro build, but the emitted file may
still be served with HTTP 200 by Cloudflare Pages.

### 2. Signatures

- Feature switch: `siteConfig.pages.<feature>: boolean`.
- Static route entry: `src/pages/<feature>.astro` or
  `src/pages/<feature>/**`.
- Optional public API entry: `src/pages/api/<feature>.*`.
- Compatibility rules: `public/_redirects` using
  `<source> <destination> 301`.

### 3. Contracts

- A fully disabled feature has no navigation/sidebar entry and no source route
  or public API route in the low-maintenance static build.
- Reusable components and types may remain dormant; route entry files are the
  static publication boundary.
- Redirect source URLs must be excluded from sitemap output; redirect
  destinations and enabled canonical pages remain included.
- Put literal redirect rules before splat rules.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Enabled canonical page | HTTP 200 and present in sitemap |
| Disabled feature page/API | HTTP 404 and absent from sitemap |
| Legacy route | HTTP 301 with the expected `Location` |
| Redirect source in sitemap | Validation failure |
| Disabled route emitted as an empty HTML file | Validation failure even if navigation hides it |

### 5. Good / Base / Bad Cases

- Good: remove the disabled page/API entry, keep reusable components, rebuild,
  and verify 404 with `wrangler pages dev dist`.
- Base: a config flag hides the navigation entry, but the built output and
  status code are still checked.
- Bad: accept a 200 empty page because `Astro.redirect("/404/")` appears in the
  source route.

### 6. Tests Required

After changing page availability:

```bash
pnpm check
pnpm type-check
pnpm build
pnpm exec wrangler pages dev dist
```

Assert enabled URLs return 200, disabled route and API prefixes return 404,
legacy routes return 301 with exact `Location` headers, and `dist/sitemap-*.xml`
contains no disabled or redirected source URL.

### 7. Wrong vs Correct

```astro
<!-- Wrong for a fully static deployment: a file can still be emitted. -->
if (!siteConfig.pages.gallery) return Astro.redirect("/404/");
```

```text
# Correct for a deliberately removed static feature:
# no src/pages/gallery route entry; reusable gallery components may remain.
```

## Scenario: Deploy Below a Hosting Subpath

### 1. Scope / Trigger

This contract applies when the same static build can be published either at a
custom-domain root or below a repository path such as GitHub Pages
`/Firefly/`.

### 2. Signatures

- Build origin: optional `ASTRO_SITE_URL`.
- Build base path: optional `ASTRO_BASE_PATH`.
- Internal path resolver: `url(path: string): string` in
  `src/utils/url-utils.ts`.

### 3. Contracts

- `astro.config.mjs` falls back to `siteConfig.site_url` and `/` when the
  deployment variables are absent.
- A subpath workflow sets both variables together; changing only `base` leaves
  canonical URLs, RSS, or sitemap output inconsistent.
- Components and generated feeds pass local paths through `url()`. To create an
  absolute URL, use `new URL(url(path), Astro.site)`.
- Markdown pages use base-independent relative links for local navigation.
- External `http:`, `https:`, and protocol-relative URLs pass through `url()`
  unchanged.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| No deployment variables | Root paths and `siteConfig.site_url` canonicals |
| Both variables set | Assets, navigation, RSS, and sitemap include the base |
| `href="/..."` in subpath output | Validation failure |
| Generated asset URL has no matching `dist/` file after removing the base | Validation failure |
| GitHub workflow succeeds but a required asset returns 404 | Deployment failure |

### 5. Good / Base / Bad Cases

- Good: GitHub Pages injects both variables and production URLs under
  `/Firefly/` return 200.
- Base: a root build continues to target `codefromkarl.xyz` without any
  deployment environment.
- Bad: hard-code `/rss.xml` in a component or change `base` globally for every
  hosting target.

### 6. Tests Required

```bash
pnpm check
pnpm type-check
pnpm build
ASTRO_SITE_URL=https://codefromkarl.github.io \
  ASTRO_BASE_PATH=/Firefly \
  pnpm build
```

Inspect the subpath build for root-absolute `href`/`src` values, verify that
referenced assets exist in `dist/`, and after deployment request the homepage,
archive, search, RSS, migrated posts, and at least one hashed asset.

### 7. Wrong vs Correct

```astro
<!-- Wrong: bypasses the deployment base. -->
<a href="/rss.xml">RSS</a>

<!-- Correct: preserves root and subpath deployments. -->
<a href={url("/rss.xml")}>RSS</a>
```

## Scenario: Cut Over the Production Domain to a Static Worker

### 1. Scope / Trigger

This contract applies when publishing the root-domain Firefly build through
Cloudflare Workers Static Assets, especially when the Custom Domain already
belongs to another Worker.

### 2. Signatures

- Root build: `pnpm build`.
- Preview deploy: `wrangler deploy --config <route-free-config>`.
- Production deploy: `wrangler deploy` using the checked-in
  `wrangler.jsonc`.
- Production Worker: `firefly`.
- Custom Domain: `codefromkarl.xyz`.
- Asset binding: `assets.directory: "./dist"`.

### 3. Contracts

- Preview the actual `firefly` Worker on `workers.dev` without a route before
  attaching the Custom Domain.
- The checked-in production config declares the Custom Domain and disables
  `workers.dev`; the route-free preview config is temporary and must not
  become the production source of truth.
- A cutover changes only the domain association. Do not overwrite or delete
  the previous Worker or its D1, R2, KV, Queue, Workflow, or Durable Object
  resources.
- Record the previous Worker deployment/version and a domain-restoration
  procedure before switching.
- Treat live HTTP acceptance, not a successful upload, as the production
  completion signal.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Root build contains a deployment base path | Stop before deploy |
| Preview page, feed, search, asset, redirect, or 404 check fails | Stop before cutover |
| Custom Domain attachment fails | Keep the previous Worker active |
| Any production HTTP acceptance check fails | Restore the domain to the previous Worker |
| Previous Worker or bound data resource is missing after cutover | Cutover failure |

### 5. Good / Base / Bad Cases

- Good: deploy the root `dist/` without a route, validate every sitemap path,
  commit and push `wrangler.jsonc`, then attach the Custom Domain and repeat
  live validation.
- Base: a new domain with no legacy service can use the same production
  configuration without a restoration step.
- Bad: deploy static assets into the legacy Worker name, which can replace
  script/binding expectations and weaken rollback isolation.

### 6. Tests Required

```bash
pnpm exec biome check wrangler.jsonc
pnpm check
pnpm type-check
pnpm build
pnpm exec wrangler deploy --dry-run --outdir <temporary-directory>
```

On both preview and production, assert every sitemap URL, RSS, Pagefind,
`api/allPostMeta.json`, and a hashed asset return 200; legacy routes return the
exact expected 301 destinations; removed comment/admin/API routes return 404.
After cutover, also confirm the legacy Worker and its data resources still
exist.

### 7. Wrong vs Correct

```jsonc
// Wrong: replace the stateful legacy service with the static artifact.
{ "name": "my-blog", "assets": { "directory": "./dist" } }
```

```jsonc
// Correct: isolate the new static service and move only the Custom Domain.
{
	"name": "firefly",
	"workers_dev": false,
	"routes": [{ "pattern": "codefromkarl.xyz", "custom_domain": true }],
	"assets": { "directory": "./dist" }
}
```
