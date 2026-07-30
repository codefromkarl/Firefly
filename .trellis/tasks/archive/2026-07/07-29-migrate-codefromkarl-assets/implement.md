# Implementation Plan

## 1. Establish authoritative inputs

- [x] Record that the native CMS export is unavailable because admin OAuth is
      blocked; external OAuth repair is not part of this local migration.
- [x] Receive explicit approval to use public-source reconstruction (方案 2).
- [x] Install the lockfile-pinned Wrangler dependency without authenticating to
      Cloudflare or exporting D1.
- [x] Inventory the exact local Markdown, live HTML, full-text RSS, sitemap
      metadata, Markdown features, and images.
- [x] Confirm the three live slugs against the old sitemap.

## 2. Remove template content

- [x] Delete upstream sample posts and their adjacent demo images.
- [x] Delete sample dynamic entries.
- [x] Replace special-page demo copy and active friend/comment demo data.
- [x] Preserve generic theme implementation code unless it causes active demo
      output.

## 3. Convert public content

- [x] Convert all three posts to Firefly frontmatter.
- [x] Use original slugs as directory paths and keep relative images adjacent.
- [x] Audit headings, lists, links, code blocks, and dates against source.
- [x] Convert current lab and tech-stack copy into static Firefly pages.
- [x] Write concise CodeFromKarl About/profile content.

## 4. Migrate identity and assets

- [x] Copy avatar, background, and favicon assets with unambiguous personal
      filenames.
- [x] Update site/profile/navigation/background configuration.
- [x] Remove or disable active upstream demo identities and remote demo media.
- [x] Disable comments, guestbook, and high-maintenance optional modules.
- [x] Keep Umami integration configurable without adding secrets.

## 5. Preserve compatibility

- [x] Add Cloudflare `_redirects` for old post and public page routes.
- [x] Verify no rule shadows Firefly's `/posts/<slug>/` output.
- [x] Check canonical URL, RSS, sitemap, robots, and Pagefind output.

## 6. Validate

```bash
pnpm install --frozen-lockfile
pnpm check
pnpm type-check
pnpm build
pnpm preview
```

- [x] Search for stale public-facing Firefly/CuteLeaf demo identity.
- [x] Search for migrated comments, user emails, database exports, or secrets.
- [x] Inspect home, archive, all posts, search, lab, tech stack, and mobile
      layout in the production preview.
- [x] Test redirect behavior using the Cloudflare-compatible output/config.
- [x] Review generated LQIP, font, Pagefind, and lockfile changes.
- [x] Run `trellis-check` before reporting implementation complete.

## Rollback Points

- Before content removal: Git source is the recovery point.
- Before conversion: keep source export outside the repository.
- Before generated-file cleanup: review `git status` and restore only migration
  scope if needed.
- No production rollback is required because deployment is out of scope.
