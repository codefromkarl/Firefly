# Content and Configuration

## Content Collections

`src/content.config.ts` defines five collections:

- `posts`: Markdown/MDX articles under `src/content/posts/`;
- `spec`: special Markdown pages such as about, friends, and guestbook;
- `dynamic`: short Markdown entries under `src/content/dynamic/`;
- `books`: book metadata and notes in `src/content/books/<slug>/index.md`;
- `bookGraphs`: adjacent graph data in
  `src/content/books/<slug>/graph.json`.

Post URLs come from the content entry ID/file path, not merely a `slug`
frontmatter field. For a stable article URL, use:

```text
src/content/posts/<stable-slug>/index.md
```

and keep adjacent article images in that directory. Renaming the path changes
the generated `/posts/<stable-slug>/` URL and requires a permanent redirect.

## Scenario: Maintain a Book and Its Knowledge Graph

### 1. Scope / Trigger

This contract applies when adding or changing a book, its cover, reading stage,
notes, graph nodes, or graph relationships.

### 2. Signatures

- Book source: `src/content/books/<slug>/index.{md,mdx}`.
- Graph source: `src/content/books/<slug>/graph.json`.
- Cover source: `src/content/books/<slug>/cover.webp`.
- Route: `/books/<slug>/`.
- Primary shelf:
  `shelf: "cognition-and-decisions" | "wealth-and-growth" | "psychology-and-relationships"`.
- Resolver:
  `getGraphForBook(book: CollectionEntry<"books">): Promise<CollectionEntry<"bookGraphs">>`.
- Node evidence:
  `provenance: "source_summary" | "editorial_inference" | "personal_note"`
  plus non-empty `sourceRefs`.
- Source reference:
  `{ basis: "metadata" | "toc" | "epub" | "notes"; locator: string; quote?: string }`.
- Optional whole-book spine: `graph.json.bookMap` with `archetype`,
  `coreQuestion`, `thesis`, `conclusion`, ordered `parts`, and directed
  `transitions`.

### 3. Contracts

- The directory slug is the stable ID for both entries and the public URL.
- Every book has exactly one `shelf` from `BOOK_SHELF_VALUES`; `topics` remains
  a non-empty multi-value list. Directory grouping uses `shelf`, while
  cross-category discovery uses `topics`.
- `graph.json.book` references that same `books` entry.
- Every published book has exactly one adjacent graph; graph ID and book ID
  match.
- `book.graphStage` and `graph.stage` match. Upgrade both from `preview` to
  `reading` or `reviewed` in the same change.
- Graph node and edge IDs are unique kebab-case values. Every edge endpoint
  names an existing node, self-edges are rejected, and every graph has a
  `core` node.
- A `reviewed` graph includes `notes` in `basis`. An AI-assisted preview states
  its basis and must not be presented as the author's personal reading
  conclusion.
- Every node declares its provenance and at least one source reference.
  Relationships declare provenance and may add source references when a direct
  location is known.
- `source_summary` is a paraphrase grounded in EPUB text or notes.
  `editorial_inference` is used for AI/editor interpretation from metadata,
  directory structure, or unverified cross-concept relationships.
  `personal_note` requires a notes source.
- A source reference basis must also appear in the graph-level `basis`. The
  locator describes its real precision: use `目录主题` or `内容分区` when an
  exact chapter/page is unavailable.
- Public content is summary-first. A verified quote is optional, collapsed in
  the UI, and limited to 240 characters; never split long original text across
  several references to evade the limit.
- `bookMap` is the author-order orientation layer; `nodes` / `edges` remains
  the semantic exploration layer. Do not infer the author-order spine from
  force-graph proximity or concept similarity.
- Every map part has a unique positive `order`, a controlled argument `role`,
  entering/leaving understanding, and at least one existing concept node ID.
  Map transitions have unique IDs, valid part endpoints, no self-reference,
  move forward in part order, and must make every part reachable from the first
  ordered part.
- Whole-book statements, parts, and transitions use the same provenance and
  source-reference rules as graph nodes. A table-of-contents synthesis stays
  `editorial_inference`; it does not become `source_summary` without EPUB or
  notes evidence.
- EPUB files and full chapter text remain local inputs. Commit only compact
  metadata, original short summaries, and the optimized cover derivative.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Missing or duplicate graph for a book | Build fails in `getGraphForBook` |
| Graph reference points to a missing book | Content sync/build fails |
| Book omits `shelf` or uses an unknown value | Content sync/build fails |
| Graph and book live under different slugs | Build fails |
| `graphStage` and `stage` differ | Build fails |
| Duplicate ID, missing endpoint, self-edge, or no `core` node | Schema validation fails |
| Node lacks provenance or source references | Schema validation fails |
| Source reference basis is absent from graph `basis` | Schema validation fails |
| `source_summary` lacks an EPUB/notes reference | Schema validation fails |
| `personal_note` lacks a notes reference | Schema validation fails |
| Source quote exceeds 240 characters | Schema validation fails |
| `bookMap` part points to a missing concept node | Schema validation fails |
| Duplicate/unreachable map part or invalid transition endpoint | Schema validation fails |
| Map transition points backward in part order | Schema validation fails |
| `stage=reviewed` without notes basis | Schema validation fails |
| Production book has `draft: true` | Omitted from the book list and routes |

### 5. Good / Base / Bad Cases

- Good: add `index.md`, `graph.json`, and `cover.webp` in one slug directory;
  assign one stable shelf, keep both stage fields aligned, declare per-node
  evidence, preserve the author's ordered parts in `bookMap`, and validate the
  complete build.
- Base: a preview concept inferred from a table of contents uses
  `editorial_inference` and a `toc` locator without claiming an exact page.
- Bad: use a topic label as an ad hoc second shelf, copy a graph between
  directories without updating `book`, update only one stage field, or label a
  directory-based inference as `source_summary`. It is also invalid to publish
  a concept-cluster order as though it were the author's chapter progression.

### 6. Tests Required

```bash
pnpm exec biome check src/content.config.ts src/content/books
pnpm check
pnpm type-check
pnpm build
```

Assert that `/books/` and every non-draft `/books/<slug>/` page are emitted,
each detail has one graph and Book JSON-LD, invalid endpoints stop the build,
invalid evidence/provenance combinations stop content sync, optional quotes
stay within the limit, every book renders under exactly one shelf, and a
subpath build keeps book, cover, and island URLs below its configured base.
For a graph with `bookMap`, also assert valid part/transition references,
whole-spine reachability, and unchanged compatibility for graphs without it.

### 7. Wrong vs Correct

```json
// Wrong: a directory inference is presented as a verified source summary.
{
  "basis": ["metadata", "toc"],
  "nodes": [{
    "provenance": "source_summary",
    "sourceRefs": [{ "basis": "toc", "locator": "目录主题：风险" }]
  }]
}
```

```json
// Correct: the content claim matches the precision of its evidence.
{
  "book": "thinking-fast-and-slow",
  "stage": "preview",
  "basis": ["metadata", "toc", "epub"],
  "nodes": [{
    "provenance": "source_summary",
    "sourceRefs": [{ "basis": "epub", "locator": "内容分区：两个自我" }]
  }]
}
```

```json
// Wrong: an ungrounded part order is mixed into the concept network.
{
  "nodes": [{ "id": "social-diagnosis", "chapter": "第三章" }],
  "edges": [{ "source": "social-diagnosis", "target": "practice" }]
}
```

```json
// Correct: the ordered spine is explicit, sourced, and points back to concepts.
{
  "bookMap": {
    "archetype": "argumentative_monograph",
    "parts": [{
      "id": "social-diagnosis",
      "order": 3,
      "role": "diagnose",
      "conceptNodeIds": ["social-decline"],
      "provenance": "editorial_inference",
      "sourceRefs": [{ "basis": "toc", "locator": "第三章" }]
    }]
  }
}
```

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

### Convention: Render a Shared Wallpaper Once

When the mobile and desktop wallpaper config points to the same local image,
keep that source in `src/assets/` and render one `ImageWrapper` with a combined
responsive width set. Do not render separate hidden mobile and desktop image
branches for the same source: preload discovery can fetch both candidates
before responsive CSS hides one of them.

```astro
<!-- Wrong: the browser can discover and download both eager images. -->
<div class="lg:hidden"><ImageWrapper src={sharedSrc} loading="eager" /></div>
<div class="hidden lg:block"><ImageWrapper src={sharedSrc} loading="eager" /></div>

<!-- Correct: one responsive image owns source selection. -->
<ImageWrapper
	src={sharedSrc}
	widths={[640, 1080, 1280, 1920]}
	sizes="100vw"
	loading={isHomePage ? "eager" : "lazy"}
	fetchpriority={isHomePage ? "high" : "auto"}
/>
```

Keep separate mobile and desktop branches only when their configured source
images differ. The home route may prioritize its visual banner; non-home
routes must lazy-load the decorative banner so it cannot compete with page
content for initial bandwidth.

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

### Convention: Load Only the Active Locale and Fallbacks

`src/i18n/translation.ts` uses `import.meta.glob` so language files remain
separate client chunks. At module initialization it loads the configured
`siteConfig.lang`, English as the final fallback, and Chinese only when needed
for the existing missing-key fallback policy.

- Normalize configured language aliases before choosing a module.
- Keep locale lookup failures explicit; do not silently substitute an empty
  translation object.
- Adding a language means adding its file and alias mapping. Do not restore
  eager static imports of every locale, because global UI islands are present
  on nearly every route.
- Browser validation must confirm an ordinary page does not request unrelated
  locale chunks.

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
- Browser-cache rules: `public/_headers`, copied to `dist/_headers`.

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
- Apply `Cache-Control: public, max-age=31556952, immutable` only to
  `/_astro/*`, whose filenames are content-hashed. Keep HTML, Pagefind, and
  unversioned `public/` assets outside this immutable rule.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Root build contains a deployment base path | Stop before deploy |
| Preview page, feed, search, asset, redirect, or 404 check fails | Stop before cutover |
| Custom Domain attachment fails | Keep the previous Worker active |
| Any production HTTP acceptance check fails | Restore the domain to the previous Worker |
| Previous Worker or bound data resource is missing after cutover | Cutover failure |
| A content-hashed `/_astro/*` response lacks the immutable one-year policy | Static-cache contract failure |
| HTML, Pagefind, or an unversioned asset receives the immutable one-year policy | Stop; stale content can no longer be corrected promptly |

### 5. Good / Base / Bad Cases

- Good: deploy the root `dist/` without a route, validate every sitemap path,
  commit and push `wrangler.jsonc`, then attach the Custom Domain and repeat
  live validation.
- Base: a new domain with no legacy service can use the same production
  configuration without a restoration step.
- Bad: deploy static assets into the legacy Worker name, which can replace
  script/binding expectations and weaken rollback isolation.
- Bad: apply the immutable rule to `/*`; route HTML and mutable search indexes
  can remain stale after a deployment.

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
Assert a representative `/_astro/*` response has the immutable one-year
browser-cache policy, while `/`, `/pagefind/pagefind.js`, and an unversioned
public asset do not.
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

```text
# Wrong: immutable caching covers mutable routes and indexes.
/*
  Cache-Control: public, max-age=31556952, immutable

# Correct: only Astro's content-hashed asset namespace is immutable.
/_astro/*
  Cache-Control: public, max-age=31556952, immutable
```
