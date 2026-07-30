# Cloudflare Topology Evidence

## Current production

- Public DNS resolves through Cloudflare.
- `https://codefromkarl.xyz/cdn-cgi/trace` confirms Cloudflare edge handling.
- Authenticated account ID: `df7eff124c99996394244b7e94324ffc`.
- Custom Domain record ID: `ebe1e213557bcdd58f06a50c91176b8c79a6a31a`.
- The domain record maps `codefromkarl.xyz` to service `my-blog` in the
  production environment.
- Active legacy version before cutover:
  `b1463da9-7b9c-43f8-82a7-4c47073033de` at 100% traffic.
- Active legacy deployment before cutover:
  `3d7bb082-67c6-4b64-b264-095971b62f37`.
- The latest known successful legacy deployment uploaded Worker `my-blog` and
  attached the apex as a Custom Domain.
- Legacy rollback workflow:
  `codefromkarl/flare-stack-blog/.github/workflows/deploy.yml`.
- Latest inspected successful legacy run:
  `https://github.com/codefromkarl/flare-stack-blog/actions/runs/26082614668`.

## Platform contracts

- Custom Domain Wrangler configuration:
  `https://developers.cloudflare.com/workers/configuration/routing/custom-domains/`
- Workers Static Assets redirects:
  `https://developers.cloudflare.com/workers/static-assets/redirects/`
- Workers Static Assets configuration:
  `https://developers.cloudflare.com/workers/wrangler/configuration/`
- Version previews:
  `https://developers.cloudflare.com/workers/versions-and-deployments/preview-urls/`
- Rollback behavior:
  `https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/`

## Safety decision

Create a separate `firefly` Worker and transfer only the Custom Domain
association. Do not upload a static-only version into `my-blog`, because that
legacy service owns Durable Object classes and other bindings that must remain
available for a clean rollback.

Before cutover, the account still contains:

- Worker `my-blog`;
- D1 database `blog-db`;
- R2 bucket `blog-assets`;
- KV namespace `blog-kv`;
- Queue `blog-queue`.

## Firefly pre-cutover evidence

- Route-free preview URL:
  `https://firefly.1069123094.workers.dev`.
- Preview version:
  `3da1fd27-1c50-45ab-847c-3008dfe15e97`.
- The preview serves all 11 sitemap URLs, RSS, Pagefind, post metadata, and a
  hashed JavaScript asset with HTTP 200.
- Legacy route sources return the expected HTTP 301 destinations.
- Removed `/comments/`, `/admin/`, and `/api/posts` routes return HTTP 404.
- The preview deploy did not attach or mutate the production Custom Domain.

Rollback command after a failed cutover:

```bash
pnpm exec wrangler rollback \
  b1463da9-7b9c-43f8-82a7-4c47073033de \
  --name my-blog \
  --message "Restore legacy blog after Firefly cutover"
```

If the Custom Domain has already moved to `firefly`, rerun the legacy
repository's deploy workflow so its `custom_domain` trigger reattaches the
domain to `my-blog`; a version rollback alone does not change domain
association.
