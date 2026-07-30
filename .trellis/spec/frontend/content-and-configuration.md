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
