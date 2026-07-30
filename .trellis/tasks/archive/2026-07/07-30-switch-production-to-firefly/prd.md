# Switch production domain to Firefly

## Goal

Move `https://codefromkarl.xyz` from the legacy Flare Stack Blog Worker to the
new static Firefly site with a verified preview and an immediate rollback path.

## Requirements

- Keep the existing Cloudflare-managed apex domain and TLS certificate.
- Deploy Firefly as a separate Worker named `firefly`; do not overwrite or
  delete the legacy `my-blog` Worker.
- Do not delete or mutate legacy D1, R2, KV, Queue, Workflow, or Durable Object
  resources.
- Build Firefly for the root-domain target (`https://codefromkarl.xyz`, `/`).
- Validate a `workers.dev` preview before changing the Custom Domain binding.
- Preserve `_redirects`, including legacy article-path redirects.
- Switch the Custom Domain only after preview validation passes.
- Keep the legacy `my-blog` deployment runnable as the rollback mechanism.
- Commit and push durable deployment configuration separately from the live
  domain switch.

## Acceptance Criteria

- [x] Cloudflare authentication identifies the account that owns `my-blog` and
      the `codefromkarl.xyz` zone.
- [x] The legacy Worker/deployment identity and rollback command are recorded
      before cutover.
- [x] `pnpm check`, `pnpm type-check`, and the root production build pass.
- [x] A Firefly `workers.dev` preview serves the homepage, all sitemap pages,
      RSS, Pagefind, hashed assets, and expected 404 routes.
- [x] `codefromkarl.xyz` is associated with the `firefly` Worker.
- [x] The apex homepage, all three migrated posts, RSS, search, sitemap, assets,
      legacy redirects, and disabled-route 404 behavior pass live HTTP checks.
- [x] The legacy data resources and `my-blog` Worker still exist.
- [x] The production configuration and cutover evidence are committed and
      pushed.

## Notes

The domain switch is an externally visible mutation. If any preview or
preflight check fails, stop before cutover. If post-cutover checks fail, restore
the Custom Domain to `my-blog` immediately.
