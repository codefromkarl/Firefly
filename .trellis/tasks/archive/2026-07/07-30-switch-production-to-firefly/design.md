# Production Cutover Design

## Confirmed topology

- `codefromkarl.xyz` is currently a Cloudflare Workers Custom Domain.
- The active legacy service is `my-blog`.
- The legacy Worker depends on D1, R2, KV, Queues, Workflows, and Durable
  Objects; those resources are not migration targets.
- Firefly is a static Astro build with Workers Static Assets configuration.
- The GitHub Pages deployment is a validated fallback but does not own the apex
  domain.

## Boundaries

Firefly is deployed as a new Worker named `firefly`. The cutover changes only
the Custom Domain association for `codefromkarl.xyz`; it does not replace the
legacy Worker service or delete its bindings and data.

Workers Static Assets consumes `dist/`. The production configuration declares:

- `workers_dev: false`;
- `preview_urls: true`;
- `routes: [{ pattern: "codefromkarl.xyz", custom_domain: true }]`;
- `assets.directory: "./dist"`;
- `assets.not_found_handling: "404-page"`.

Cloudflare documents `_redirects` support for Workers Static Assets, so the
existing file in `public/` remains the redirect source of truth.

## Preview and cutover

1. Build the root-domain artifact locally.
2. Deploy the actual `firefly` Worker with a temporary route-free configuration
   that enables its `workers.dev` URL.
3. Validate preview content and status codes.
4. Deploy the committed `firefly` production configuration, which associates
   the apex Custom Domain with the new Worker.
5. Validate the apex domain until Cloudflare cache/route propagation settles.
6. Confirm the production configuration disables the temporary `workers.dev`
   route after production validation.

## Rollback

Record the active `my-blog` deployment/version before cutover. If production
validation fails, rerun the legacy repository's successful Cloudflare deploy
workflow; its `custom_domain` configuration restores the association to
`my-blog`. The old Worker and all bound resources remain intact throughout.

Do not use a gradual traffic split: Firefly uses content-hashed static assets,
and mixed versions can produce asset 404s when HTML and asset requests land on
different versions.

## Operational risks

- OAuth may authenticate the wrong Cloudflare account: stop if `my-blog` or the
  zone is absent.
- Attaching an already-used Custom Domain may fail rather than transfer: this
  is fail-safe because the old site remains live.
- Cached old HTML can outlive the association change briefly; verify with
  retries and a cache-busting query before declaring failure.
- A successful Wrangler deploy is not production acceptance; live HTTP checks
  are mandatory.
