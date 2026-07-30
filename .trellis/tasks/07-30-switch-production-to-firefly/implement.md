# Implementation Plan

- [x] Complete Wrangler OAuth and confirm the owning account.
- [x] Read current `my-blog` deployments/versions and record rollback evidence.
- [x] Verify the current apex response still comes from the legacy site.
- [x] Load frontend deployment/configuration specs.
- [x] Update `wrangler.jsonc` for the `firefly` production Worker and Custom
      Domain.
- [x] Run Biome, `pnpm check`, `pnpm type-check`, and a root `pnpm build`.
- [x] Deploy the route-free `firefly` Workers Static Assets preview and capture
      its URL.
- [x] Validate preview sitemap pages, RSS, search assets, redirects, and 404s.
- [x] Run `trellis-check` and update deployment specs if needed.
- [ ] Commit and push production configuration before cutover.
- [ ] Deploy `firefly` with the apex Custom Domain.
- [ ] Validate apex HTTP behavior and confirm legacy resources still exist.
- [ ] If validation fails, trigger the legacy `my-blog` deployment immediately.
- [ ] Disable the temporary `workers.dev` route through the production deploy.
- [ ] Archive the task and record the production session.

## Validation commands

```bash
pnpm exec biome check wrangler.jsonc
pnpm check
pnpm type-check
pnpm build
pnpm exec wrangler deployments list --name my-blog
pnpm exec wrangler deploy --config <preview-config>
pnpm exec wrangler deploy
```

HTTP acceptance covers every sitemap URL plus `rss.xml`,
`pagefind/pagefind.js`, `api/allPostMeta.json`, a hashed asset, legacy redirect
sources, and disabled routes.
