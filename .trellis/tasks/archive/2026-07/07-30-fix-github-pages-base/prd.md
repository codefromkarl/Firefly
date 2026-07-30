# Fix GitHub Pages base path

## Goal

Make the deployed GitHub Pages site usable at the repository subpath while
preserving root-path behavior for local development and custom-domain
deployments.

## Requirements

- GitHub Pages builds must use `/Firefly/` as Astro's base path and
  `https://codefromkarl.github.io` as the build site origin.
- Local builds and Cloudflare/custom-domain builds must keep `/` as the base
  path and `https://codefromkarl.xyz` as the canonical site URL.
- Use the existing `url()` and `import.meta.env.BASE_URL` path handling instead
  of rewriting links throughout the application.
- Keep the change limited to build configuration and deployment workflow.

## Acceptance Criteria

- [x] A normal `pnpm build` emits root-based URLs for `codefromkarl.xyz`.
- [x] A GitHub Pages build emits assets and internal links below `/Firefly/`.
- [x] `pnpm check`, `pnpm type-check`, and both build modes pass.
- [x] The GitHub Pages workflow succeeds for the patch commit.
- [x] The deployed homepage, archive, search, RSS, and all three migrated posts
      return HTTP 200 with required assets available.
- [x] Disabled routes return 404 on the deployed site.

## Notes

This is a deployment compatibility repair discovered during production
verification. It is intentionally a lightweight, PRD-only task.
